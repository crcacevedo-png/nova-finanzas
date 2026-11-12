# Tests: Cierre de Producción Diario por Médico (Dra. Mariamercedes Palma)
# Cubre la agregación combinada clínica + Óptica, el token firmado del PDF,
# el envío manual, y el webhook de cron (auth).
#
# Nota: en este entorno, el cliente global de Mongo solo admite UNA consulta
# real por proceso de pytest antes de romperse entre límites de test async
# (limitación de motor + event loop por-test de pytest-asyncio, no de este
# código). Por eso todos los escenarios que tocan datos reales se agrupan en
# una sola función async (un solo event loop de principio a fin); las pruebas
# de funciones puras (PDF, token) van aparte porque no tocan la base de datos.
import os
import io
import uuid
import pytest
from pypdf import PdfReader
from pymongo import MongoClient

from utils.timezone import dia_gt_a_rango_utc
from routes.ventas import (
    _make_prod_medico_report_token,
    _verify_prod_medico_report_token,
    render_produccion_medico_pdf,
    PRODUCCION_MEDICO_PALMA_NOMBRE,
)

FECHA_TEST = "2026-02-02"
WEBHOOK_SECRET = os.environ.get("WEBHOOK_CRON_SECRET", "")
_sync_client = MongoClient(os.environ["MONGO_URL"])
_sync_db = _sync_client[os.environ["DB_NAME"]]


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


# ---------------------- PDF (función pura, sin DB) ----------------------
def test_render_pdf_con_datos():
    data = {
        "fecha": FECHA_TEST, "medico_nombre": "Dra. Mariamercedes Palma",
        "num_ventas": 2, "total_items": 2, "total_monto": 650.0,
        "items": [
            {"fecha": "02/02/2026 09:00", "numero_venta": "TEST-CLI-0001", "paciente_nombre": "Paciente Test Clinica",
             "nombre": "Consulta oftalmologica", "cantidad": 1, "monto": 250.0},
            {"fecha": "02/02/2026 10:00", "numero_venta": "TEST-OPT-0001", "paciente_nombre": "Paciente Test Optica",
             "nombre": "Armazon RayBan Test", "cantidad": 1, "monto": 400.0},
        ],
    }
    pdf_bytes = render_produccion_medico_pdf(FECHA_TEST, data)
    assert pdf_bytes[:4] == b"%PDF"
    text = _pdf_text(pdf_bytes)
    assert "Mariamercedes Palma" in text
    assert "Consulta oftalmologica" in text
    assert "650.00" in text  # total del día resaltado


def test_render_pdf_sin_datos_muestra_cero():
    data = {"fecha": "2020-01-01", "medico_nombre": "Dra. Mariamercedes Palma",
            "num_ventas": 0, "total_items": 0, "total_monto": 0, "items": []}
    pdf_bytes = render_produccion_medico_pdf("2020-01-01", data)
    text = _pdf_text(pdf_bytes)
    assert "Sin producción registrada este día" in text
    assert "0.00" in text


# ---------------------- Token firmado del enlace de descarga (función pura) ----------------------
def test_token_roundtrip_valido():
    token = _make_prod_medico_report_token(FECHA_TEST, "Dra. Mariamercedes Palma")
    fecha, nombre = _verify_prod_medico_report_token(token)
    assert fecha == FECHA_TEST
    assert nombre == "Dra. Mariamercedes Palma"


def test_token_invalido_rechazado():
    assert _verify_prod_medico_report_token("token-basura-invalido") is None


def test_token_manipulado_rechazado():
    token = _make_prod_medico_report_token(FECHA_TEST, "Dra. Mariamercedes Palma")
    alterado = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert _verify_prod_medico_report_token(alterado) is None


# ---------------------- Escenarios con datos reales (una sola función async) ----------------------
async def test_escenarios_con_datos_reales(client):
    doctor = _sync_db.doctors.find_one({"name": {"$regex": "mariamercedes", "$options": "i"}}, {"_id": 0})
    assert doctor, "La Dra. Mariamercedes Palma debe existir en db.doctors para estas pruebas"

    ini, _fin = dia_gt_a_rango_utc(FECHA_TEST)
    venta_clinica_id = str(uuid.uuid4())
    venta_optica_id = str(uuid.uuid4())
    venta_clinica = {
        "id": venta_clinica_id, "numero_venta": "TEST-CLI-0001", "fecha": ini,
        "origen": "clinica", "estado": "completada",
        "medico_id": doctor["id"], "medico_nombre": doctor["name"],
        "paciente_nombre": "Paciente Test Clinica",
        "items": [{"producto_id": "prod-1", "nombre": "Consulta oftalmologica", "cantidad": 1, "subtotal": 250.0}],
        "total": 250.0,
    }
    venta_optica = {
        "id": venta_optica_id, "order_number": "TEST-OPT-0001", "created_at": ini,
        "status": "pagado", "doctor_id": doctor["id"], "doctor_name": doctor["name"],
        "patient_name": "Paciente Test Optica",
        "items_v2": [
            {"type": "frame", "name": "Armazon RayBan Test", "quantity": 1, "subtotal": 400.0},
            {"type": "lens_type", "name": "Lente Antireflejo", "quantity": 2, "subtotal": 300.0},
        ],
        "total": 700.0,
    }

    try:
        _sync_db.ventas.insert_one(venta_clinica)
        _sync_db.optica_sales.insert_one(venta_optica)

        token = _make_prod_medico_report_token(FECHA_TEST, PRODUCCION_MEDICO_PALMA_NOMBRE)

        # 1) Combina clínica + Óptica (cualquier categoría) del mismo día
        r = await client.get(f"/api/ventas/produccion-medico/daily-report/pdf?token={token}")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        text = _pdf_text(r.content)
        assert "Mariamercedes Palma" in text
        assert "TEST-CLI" in text and "TEST-OPT" in text
        assert "Consulta oftalmologica" in text
        assert "Armazon RayBan Test" in text
        assert "Lente Antireflejo" in text
        assert "950.00" in text  # 250 (clínica) + 700 (óptica)

        # 2) Excluye ventas de Óptica canceladas
        _sync_db.optica_sales.update_one({"id": venta_optica_id}, {"$set": {"status": "cancelado"}})
        r = await client.get(f"/api/ventas/produccion-medico/daily-report/pdf?token={token}")
        assert r.status_code == 200
        text = _pdf_text(r.content)
        assert "TEST-CLI" in text
        assert "TEST-OPT" not in text
        assert "250.00" in text
        _sync_db.optica_sales.update_one({"id": venta_optica_id}, {"$set": {"status": "pagado"}})
    finally:
        _sync_db.ventas.delete_one({"id": venta_clinica_id})
        _sync_db.optica_sales.delete_one({"id": venta_optica_id})

    # 3) Día sin producción: igual responde con el cierre en cero (predecible)
    token_vacio = _make_prod_medico_report_token("2020-01-01", PRODUCCION_MEDICO_PALMA_NOMBRE)
    r = await client.get(f"/api/ventas/produccion-medico/daily-report/pdf?token={token_vacio}")
    assert r.status_code == 200
    text = _pdf_text(r.content)
    assert "Sin producción registrada este día" in text

    # 4) Token inválido -> 404
    r = await client.get("/api/ventas/produccion-medico/daily-report/pdf?token=invalido")
    assert r.status_code == 404

    # 5) Envío manual requiere admin/superadmin (sin auth -> rechazado)
    r = await client.post("/api/ventas/produccion-medico/daily-report/enviar")
    assert r.status_code in (401, 403)

    # 6) Webhook de cron: auth obligatoria
    if WEBHOOK_SECRET:
        r = await client.post("/api/cron/produccion-medico-diario")
        assert r.status_code == 401
        r = await client.post("/api/cron/produccion-medico-diario", headers={"Authorization": "Bearer token-incorrecto"})
        assert r.status_code == 401
