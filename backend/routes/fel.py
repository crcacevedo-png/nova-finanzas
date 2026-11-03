"""Facturación Electrónica en Línea (FEL) - Guatemala vía Digifact.

Régimen General: emite FACT con IVA 12% incluido ("hacia adentro").
Documentación: https://documentacion.digifact.com/gt/api
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import os
import uuid
import base64
import logging
import httpx

from utils.timezone import now_gt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fel", tags=["FEL"])

_db = None


def get_db():
    global _db
    if _db is None:
        from server import db
        _db = db
    return _db


def auth_dep():
    from server import get_current_user

    async def _dep(current_user: dict = Depends(get_current_user)):
        return current_user

    return _dep


def admin_dep():
    from server import get_current_user

    async def _dep(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Solo Administradores pueden configurar FEL")
        return current_user

    return _dep


# ==================== DIGIFACT CLIENT ====================

BASE_URLS = {
    "test": "https://testnucgt.digifact.com/api",
    "prod": "https://nucgt.digifact.com/gt.com.apinuc/api",
}


def _build_auth(cfg: dict):
    """Construye (username_completo, password, taxid_12, usuario_corto).

    El usuario corto y la contraseña vienen del entorno (secretos). El NIT del
    emisor viene de la configuración FEL y se usa para formar GT.NIT12.USUARIO.
    """
    user = os.environ.get("DIGIFACT_USERNAME", "").strip()
    pwd = os.environ.get("DIGIFACT_PASSWORD", "").strip()
    if not user or not pwd:
        raise HTTPException(status_code=400, detail="Credenciales de Digifact no configuradas. Agrégalas en la configuración de secretos.")
    nit = (cfg.get("nit") or "").strip().replace("-", "")
    if not nit or not nit.isdigit():
        raise HTTPException(status_code=400, detail="Falta el NIT del emisor en Configuración FEL (solo dígitos).")
    taxid_12 = nit.zfill(12)
    full = f"GT.{taxid_12}.{user}"
    return full, pwd, taxid_12, user


async def _get_token(base: str, full: str, pwd: str) -> str:
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(f"{base}/login/get_token",
                              json={"Username": full, "Password": pwd},
                              headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Error de autenticación con Digifact ({r.status_code}): {r.text[:300]}")
        token = r.json().get("token")
        if not token:
            raise HTTPException(status_code=400, detail="Digifact no devolvió token")
        return token


async def _certificar_nuc(base: str, token: str, taxid_12: str, usuario: str, nuc: dict) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{base}/v2/transform/nuc_json",
            params={"TAXID": taxid_12, "FORMAT": "PDF|HTML|XML", "USERNAME": usuario},
            json=nuc,
            headers={"Content-Type": "application/json", "Authorization": token},
        )
        try:
            data = r.json()
        except Exception:
            raise HTTPException(status_code=400, detail=f"Respuesta inválida de Digifact ({r.status_code}): {r.text[:400]}")
        return data


# ==================== CONFIG ====================

class FELConfig(BaseModel):
    enabled: bool = False
    environment: str = "test"  # test | prod
    nit: str = ""
    emisor_nombre: str = ""
    nombre_comercial: Optional[str] = ""
    afiliacion_iva: str = "GEN"
    establecimiento_codigo: int = 1
    direccion: str = "Ciudad"
    municipio: str = "Guatemala"
    departamento: str = "Guatemala"
    codigo_postal: str = "01001"
    pais: str = "GT"
    frase_tipo: int = 1
    frase_escenario: int = 1


async def _load_config() -> dict:
    db = get_db()
    doc = await db.fel_config.find_one({"_id": "config"}) or {}
    cfg = FELConfig().model_dump()
    cfg.update({k: v for k, v in doc.items() if k != "_id"})
    return cfg


@router.get("/config")
async def get_fel_config(current_user: dict = Depends(admin_dep())):
    cfg = await _load_config()
    # Indicar si las credenciales están presentes (sin exponer valores)
    cfg["credenciales_configuradas"] = bool(os.environ.get("DIGIFACT_USERNAME") and os.environ.get("DIGIFACT_PASSWORD"))
    cfg["nit_emisor"] = (cfg.get("nit") or "").strip()
    return cfg


@router.put("/config")
async def set_fel_config(data: FELConfig, current_user: dict = Depends(admin_dep())):
    db = get_db()
    await db.fel_config.update_one({"_id": "config"}, {"$set": {**data.model_dump(), "updated_at": now_gt().isoformat(), "updated_by": current_user["id"]}}, upsert=True)
    return {"message": "Configuración FEL guardada", **data.model_dump()}


# ==================== NUC BUILDER ====================

def _round2(v: float) -> float:
    return round(float(v) + 1e-9, 2)


def _normalizar_venta(origen: str, sale: dict) -> dict:
    """Devuelve {items:[{descripcion, cantidad, precio_unitario, total_linea}], total}."""
    items = []
    total = _round2(sale.get("total", 0))
    if origen == "clinica":
        raw = sale.get("items", [])
        for it in raw:
            items.append({
                "descripcion": it.get("nombre", "Producto"),
                "cantidad": it.get("cantidad", 1),
                "precio_unitario": _round2(it.get("precio_unitario", 0)),
                "descuento": _round2(it.get("descuento", 0)),
                "total_linea": _round2(it.get("subtotal", 0)),
            })
    else:  # optica
        raw = sale.get("items_v2")
        if raw:
            for it in raw:
                items.append({
                    "descripcion": it.get("name") or it.get("lens_type_name") or "Producto óptico",
                    "cantidad": it.get("quantity", 1),
                    "precio_unitario": _round2(it.get("unit_price", 0)),
                    "descuento": 0,
                    "total_linea": _round2(it.get("subtotal", 0)),
                })
        else:
            # Fallback: armazón, lente de contacto, lentes oftálmicos
            if sale.get("frame_price", 0):
                items.append({"descripcion": "Armazón", "cantidad": 1, "precio_unitario": _round2(sale["frame_price"]), "descuento": 0, "total_linea": _round2(sale["frame_price"])})
            if sale.get("contact_lens_price", 0):
                items.append({"descripcion": "Lente de contacto", "cantidad": 1, "precio_unitario": _round2(sale["contact_lens_price"]), "descuento": 0, "total_linea": _round2(sale["contact_lens_price"])})
            for li in sale.get("lens_items", []):
                items.append({"descripcion": li.get("lens_type_name", "Lente oftálmico"), "cantidad": li.get("quantity", 1), "precio_unitario": _round2(li.get("unit_price", 0)), "descuento": 0, "total_linea": _round2(li.get("subtotal", 0))})

    if not items:
        raise HTTPException(status_code=400, detail="La venta no tiene ítems para facturar")

    # Distribuir descuento global proporcionalmente para que la suma de líneas == total
    suma_lineas = _round2(sum(i["total_linea"] for i in items))
    if suma_lineas > 0 and abs(suma_lineas - total) > 0.01:
        factor = total / suma_lineas
        for i in items:
            i["total_linea"] = _round2(i["total_linea"] * factor)
    return {"items": items, "total": total}


def _build_nuc(cfg: dict, taxid_12: str, norm: dict, receptor: dict) -> dict:
    items_nuc = []
    suma_iva = 0.0
    suma_total = 0.0
    for it in norm["items"]:
        total_linea = _round2(it["total_linea"])
        iva = _round2(total_linea * 12.0 / 112.0)
        base = _round2(total_linea - iva)
        total_item = _round2(base + iva)
        suma_iva = _round2(suma_iva + iva)
        suma_total = _round2(suma_total + total_item)
        item_obj = {
            "Type": "B",
            "Description": str(it["descripcion"])[:500],
            "Qty": it["cantidad"],
            "Price": it["precio_unitario"],
            "Taxes": {"Tax": [{"Code": 1, "Description": "IVA", "TaxableAmount": base, "Amount": iva}]},
            "Totals": {"TotalItem": total_item},
        }
        items_nuc.append(item_obj)

    rec_taxid = (receptor.get("nit") or "CF").strip().upper().replace("-", "") or "CF"
    rec_nombre = (receptor.get("nombre") or ("Consumidor Final" if rec_taxid == "CF" else "")).strip() or "Consumidor Final"

    nuc = {
        "NUC": {
            "Version": "1.0",
            "CountryCode": "GT",
            "Header": {
                "DocType": "FACT",
                "IssuedDateTime": now_gt().strftime("%Y-%m-%dT%H:%M:%S-06:00"),
                "Currency": "GTQ",
            },
            "Seller": {
                "TaxID": taxid_12,
                "TaxIDAdditionalInfo": [{"Name": "AfiliacionIVA", "Data": None, "Value": cfg.get("afiliacion_iva", "GEN")}],
                "Name": cfg.get("emisor_nombre", ""),
                "AdditionlInfo": [
                    {"Name": "TipoFrase", "Data": 1, "Value": cfg.get("frase_tipo", 1)},
                    {"Name": "CodigoEscenario", "Data": 1, "Value": cfg.get("frase_escenario", 1)},
                ],
                "BranchInfo": {
                    "Code": cfg.get("establecimiento_codigo", 1),
                    "AddressInfo": {
                        "Address": cfg.get("direccion", "Ciudad"),
                        "City": cfg.get("codigo_postal", "01001"),
                        "District": cfg.get("municipio", "Guatemala"),
                        "State": cfg.get("departamento", "Guatemala"),
                        "Country": "GT",
                    },
                },
            },
            "Buyer": {
                "TaxID": rec_taxid,
                "Name": rec_nombre,
                "AddressInfo": {
                    "Address": "Ciudad",
                    "City": "01001",
                    "District": "Guatemala",
                    "State": "Guatemala",
                    "Country": "GT",
                },
            },
            "Items": items_nuc,
            "Totals": {
                "TotalTaxes": {"TotalTax": [{"Description": "IVA", "Amount": suma_iva}]},
                "GrandTotal": {"InvoiceTotal": suma_total},
            },
            "AdditionalDocumentInfo": {
                "AdditionalInfo": [{"Code": str(uuid.uuid4()), "Type": "ADENDA"}]
            },
        }
    }
    return nuc


# ==================== ENDPOINTS ====================

class CertificarRequest(BaseModel):
    origen: str  # clinica | optica
    sale_id: str
    receptor_nit: Optional[str] = None
    receptor_nombre: Optional[str] = None


def _coleccion(origen: str) -> str:
    if origen == "clinica":
        return "ventas"
    if origen == "optica":
        return "optica_sales"
    raise HTTPException(status_code=400, detail="origen inválido (clinica|optica)")


async def _get_sale(origen: str, sale_id: str) -> dict:
    db = get_db()
    sale = await db[_coleccion(origen)].find_one({"id": sale_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return sale


@router.post("/certificar")
async def certificar(data: CertificarRequest, current_user: dict = Depends(auth_dep())):
    db = get_db()
    cfg = await _load_config()
    if not cfg.get("enabled"):
        raise HTTPException(status_code=400, detail="La facturación FEL no está habilitada. Actívala en Configuración FEL.")
    if not cfg.get("emisor_nombre"):
        raise HTTPException(status_code=400, detail="Falta configurar los datos del emisor en Configuración FEL.")

    full, pwd, taxid_12, usuario = _build_auth(cfg)
    sale = await _get_sale(data.origen, data.sale_id)

    if sale.get("fel") and sale["fel"].get("authNumber") and sale["fel"].get("estado") == "certificado":
        raise HTTPException(status_code=400, detail="Esta venta ya tiene una factura FEL certificada")

    norm = _normalizar_venta(data.origen, sale)
    receptor = {"nit": data.receptor_nit, "nombre": data.receptor_nombre}
    nuc = _build_nuc(cfg, taxid_12, norm, receptor)

    base = BASE_URLS[cfg.get("environment", "test")]
    token = await _get_token(base, full, pwd)
    resp = await _certificar_nuc(base, token, taxid_12, usuario, nuc)

    code = str(resp.get("code", ""))
    if code != "1":
        msg = resp.get("message") or resp.get("description") or "Error al certificar"
        logger.error(f"FEL certificar fallo: {resp}")
        raise HTTPException(status_code=400, detail=f"Digifact rechazó la factura: {msg}")

    fel_data = {
        "authNumber": resp.get("authNumber"),
        "serie": resp.get("batch"),
        "numero": resp.get("serial"),
        "fecha_certificacion": resp.get("enrolledTimeStamp") or resp.get("issuedTimeStamp"),
        "estado": "certificado",
        "environment": cfg.get("environment", "test"),
        "receptor_nit": (data.receptor_nit or "CF"),
        "receptor_nombre": data.receptor_nombre or "Consumidor Final",
        "total": norm["total"],
        "certificado_por": current_user["id"],
        "certificado_en": now_gt().isoformat(),
    }
    # Guardar PDF/XML/HTML en colección aparte
    doc_fel = {
        "id": str(uuid.uuid4()),
        "origen": data.origen,
        "sale_id": data.sale_id,
        **fel_data,
        "pdf_base64": resp.get("responseData3"),
        "xml_base64": resp.get("responseData1"),
        "html_base64": resp.get("responseData2"),
    }
    await db.fel_documents.insert_one(doc_fel)
    await db[_coleccion(data.origen)].update_one({"id": data.sale_id}, {"$set": {"fel": fel_data}})

    return {
        "message": "Factura certificada correctamente",
        "authNumber": fel_data["authNumber"],
        "serie": fel_data["serie"],
        "numero": fel_data["numero"],
        "fecha": fel_data["fecha_certificacion"],
        "pdf_base64": resp.get("responseData3"),
    }


class AnularRequest(BaseModel):
    origen: str
    sale_id: str
    motivo: str = Field(min_length=3)


@router.post("/anular")
async def anular(data: AnularRequest, current_user: dict = Depends(admin_dep())):
    db = get_db()
    cfg = await _load_config()
    full, pwd, taxid_12, usuario = _build_auth(cfg)
    sale = await _get_sale(data.origen, data.sale_id)
    fel = sale.get("fel") or {}
    if not fel.get("authNumber") or fel.get("estado") != "certificado":
        raise HTTPException(status_code=400, detail="Esta venta no tiene una factura FEL activa para anular")

    base = BASE_URLS[cfg.get("environment", "test")]
    token = await _get_token(base, full, pwd)
    nit = taxid_12.lstrip("0")
    body = {
        "Taxid": nit,
        "Autorizacion": fel["authNumber"],
        "IdReceptor": fel.get("receptor_nit") or "CF",
        "FechaEmisionDocumentoAnular": (fel.get("fecha_certificacion") or now_gt().strftime("%Y-%m-%dT%H:%M:%S")),
        "MotivoAnulacion": data.motivo,
        "Username": usuario,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{base}/CancelFelGT", json=body, headers={"Content-Type": "application/json", "Authorization": token})
        try:
            resp = r.json()
        except Exception:
            raise HTTPException(status_code=400, detail=f"Respuesta inválida de Digifact ({r.status_code}): {r.text[:300]}")

    codigo = str(resp.get("Codigo", ""))
    if codigo != "1":
        raise HTTPException(status_code=400, detail=f"Digifact no pudo anular: {resp.get('Mensaje', 'Error')}")

    fel_update = {**fel, "estado": "anulado", "motivo_anulacion": data.motivo, "anulado_por": current_user["id"], "anulado_en": now_gt().isoformat()}
    await db[_coleccion(data.origen)].update_one({"id": data.sale_id}, {"$set": {"fel": fel_update}})
    await db.fel_documents.update_one({"origen": data.origen, "sale_id": data.sale_id}, {"$set": {"estado": "anulado", "motivo_anulacion": data.motivo}})
    return {"message": "Factura anulada correctamente", "autorizacion": fel["authNumber"]}


@router.get("/documento")
async def obtener_documento(origen: str = Query(...), sale_id: str = Query(...), current_user: dict = Depends(auth_dep())):
    db = get_db()
    doc = await db.fel_documents.find_one({"origen": origen, "sale_id": sale_id}, sort=[("certificado_en", -1)])
    if not doc or not doc.get("pdf_base64"):
        raise HTTPException(status_code=404, detail="No hay documento FEL para esta venta")
    return {
        "authNumber": doc.get("authNumber"),
        "serie": doc.get("serie"),
        "numero": doc.get("numero"),
        "estado": doc.get("estado"),
        "pdf_base64": doc.get("pdf_base64"),
    }


@router.get("/estado")
async def estado(origen: str = Query(...), sale_id: str = Query(...), current_user: dict = Depends(auth_dep())):
    sale = await _get_sale(origen, sale_id)
    return sale.get("fel") or {"estado": "no_facturado"}
