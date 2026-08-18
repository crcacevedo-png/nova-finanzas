# /app/backend/seed/datos_maestros.py
"""
FASE 1: Datos Maestros Semilla
Genera bodegas, proveedores, productos y usuarios de prueba.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
import random
import bcrypt

# Prefijo de prueba
PRB = "PRB-"

def hash_password(password: str) -> str:
    """Hash de contraseña con bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def generar_fecha_relativa(dias: int) -> str:
    """Genera fecha ISO relativa a hoy"""
    fecha = datetime.now(timezone.utc) + timedelta(days=dias)
    return fecha.isoformat()


def generar_nit_ficticio() -> str:
    """Genera NIT guatemalteco ficticio de prueba"""
    # Formato: XXXXXXXX-K donde K es dígito verificador
    base = random.randint(10000000, 99999999)
    return f"PRB{base}-9"


# ==================== BODEGAS ====================

def generar_bodegas() -> List[Dict[str, Any]]:
    """Genera las 4 bodegas de prueba según especificación"""
    ahora = datetime.now(timezone.utc).isoformat()
    
    return [
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}BOD-GEN",
            "nombre": "Bodega General de Prueba",
            "descripcion": "Bodega general para almacenamiento de productos clínicos",
            "origen": "clinica",
            "esPuntoVenta": False,
            "es_quirofano": False,
            "direccion": "Zona de Pruebas",
            "encargado": "Sistema de Pruebas",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}BOD-DIS",
            "nombre": "Dispensario de Prueba",
            "descripcion": "Punto de venta clínico para despacho directo",
            "origen": "clinica",
            "esPuntoVenta": True,
            "es_quirofano": False,
            "direccion": "Recepción - Pruebas",
            "encargado": "Sistema de Pruebas",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}BOD-QUI",
            "nombre": "Quirófano de Prueba",
            "descripcion": "Bodega de insumos quirúrgicos",
            "origen": "clinica",
            "esPuntoVenta": False,
            "es_quirofano": True,
            "direccion": "Quirófano - Pruebas",
            "encargado": "Sistema de Pruebas",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}BOD-OPT",
            "nombre": "Bodega Óptica de Prueba",
            "descripcion": "Almacén de aros y lentes de óptica",
            "origen": "optica",
            "esPuntoVenta": True,
            "es_quirofano": False,
            "direccion": "Óptica - Pruebas",
            "encargado": "Sistema de Pruebas",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        }
    ]


# ==================== PROVEEDORES ====================

def generar_proveedores() -> List[Dict[str, Any]]:
    """Genera 4 proveedores de prueba con diferentes plazos de crédito"""
    ahora = datetime.now(timezone.utc).isoformat()
    
    return [
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PROV-001",
            "nombre": "Farmacéutica Guatemala PRB",
            "tipo": "medicamentos",
            "nit": generar_nit_ficticio(),
            "direccion": "Zona 10, Ciudad de Guatemala",
            "telefono": "2222-0001",
            "email": "prb.farma@test.gt",
            "contacto": "Juan Pérez (PRB)",
            "plazo_credito_dias": 0,  # Contado
            "condiciones_pago": "Contado estricto",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PROV-002",
            "nombre": "Distribuidora Oftálmica PRB",
            "tipo": "medicamentos",
            "nit": generar_nit_ficticio(),
            "direccion": "Zona 9, Ciudad de Guatemala",
            "telefono": "2222-0002",
            "email": "prb.oftalmica@test.gt",
            "contacto": "María López (PRB)",
            "plazo_credito_dias": 15,
            "condiciones_pago": "Crédito 15 días",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PROV-003",
            "nombre": "Insumos Quirúrgicos Centroamérica PRB",
            "tipo": "insumos_quirurgicos",
            "nit": generar_nit_ficticio(),
            "direccion": "Zona 12, Ciudad de Guatemala",
            "telefono": "2222-0003",
            "email": "prb.quirurgicos@test.gt",
            "contacto": "Carlos Méndez (PRB)",
            "plazo_credito_dias": 30,
            "condiciones_pago": "Crédito 30 días neto",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PROV-004",
            "nombre": "Óptica Internacional PRB",
            "tipo": "optica",
            "nit": generar_nit_ficticio(),
            "direccion": "Zona 14, Ciudad de Guatemala",
            "telefono": "2222-0004",
            "email": "prb.optica@test.gt",
            "contacto": "Ana García (PRB)",
            "plazo_credito_dias": 60,
            "condiciones_pago": "Crédito 60 días",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        }
    ]


# ==================== PRODUCTOS CLÍNICA ====================

def generar_productos_clinica(bodega_dispensario_id: str, bodega_general_id: str, bodega_quirofano_id: str) -> List[Dict[str, Any]]:
    """
    Genera 18 productos clínicos de prueba:
    - 8 medicamentos oftálmicos
    - 4 insumos quirúrgicos
    - 3 servicios sin inventario
    - 3 productos de baja rotación
    """
    ahora = datetime.now(timezone.utc).isoformat()
    productos = []
    
    # Medicamentos oftálmicos (8)
    medicamentos = [
        {"nombre": "Tobramicina 0.3% Colirio", "precio": 85.00, "categoria": "antibiotico"},
        {"nombre": "Dexametasona 0.1% Colirio", "precio": 95.00, "categoria": "antiinflamatorio"},
        {"nombre": "Lágrimas Artificiales Carboximetilcelulosa", "precio": 45.00, "categoria": "lubricante"},
        {"nombre": "Timolol 0.5% Colirio", "precio": 120.00, "categoria": "hipotensor"},
        {"nombre": "Tropicamida 1% Midriático", "precio": 75.00, "categoria": "midriatico"},
        {"nombre": "Ciprofloxacina 0.3% Colirio", "precio": 110.00, "categoria": "antibiotico"},
        {"nombre": "Prednisolona 1% Colirio", "precio": 145.00, "categoria": "antiinflamatorio"},
        {"nombre": "Latanoprost 0.005% Colirio", "precio": 480.00, "categoria": "hipotensor"},
    ]
    
    for i, med in enumerate(medicamentos, 1):
        productos.append({
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}MED-{i:03d}",
            "nombre": f"{med['nombre']} (PRB)",
            "descripcion": f"Medicamento oftálmico de prueba - {med['categoria']}",
            "categoria": med['categoria'],
            "tipo": "medicamento",
            "unidad_medida": "frasco",
            "precio_venta": med['precio'],
            "precio_con_iva": True,
            "requiere_receta": True,
            "controla_lote": True,
            "controla_vencimiento": True,
            "existencia_minima": 5,
            "existencia_maxima": 50,
            "bodega_id": bodega_dispensario_id,
            "origen": "clinica",
            "is_active": True,
            "es_servicio": False,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        })
    
    # Insumos quirúrgicos (4)
    insumos = [
        {"nombre": "Lente Intraocular Monofocal", "precio": 2800.00},
        {"nombre": "Viscoelástico Hialuronato", "precio": 1200.00},
        {"nombre": "Set Facoemulsificación Desechable", "precio": 3500.00},
        {"nombre": "Sutura Vicryl 8-0 Oftálmica", "precio": 450.00},
    ]
    
    for i, ins in enumerate(insumos, 1):
        productos.append({
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}QUI-{i:03d}",
            "nombre": f"{ins['nombre']} (PRB)",
            "descripcion": "Insumo quirúrgico de prueba",
            "categoria": "quirurgico",
            "tipo": "insumo",
            "unidad_medida": "unidad",
            "precio_venta": ins['precio'],
            "precio_con_iva": True,
            "requiere_receta": False,
            "controla_lote": True,
            "controla_vencimiento": True,
            "existencia_minima": 2,
            "existencia_maxima": 20,
            "bodega_id": bodega_quirofano_id,
            "origen": "clinica",
            "is_active": True,
            "es_servicio": False,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        })
    
    # Servicios sin inventario (3)
    servicios = [
        {"nombre": "Consulta Oftalmológica", "precio": 350.00},
        {"nombre": "Campimetría Computarizada", "precio": 450.00},
        {"nombre": "Tomografía de Coherencia Óptica (OCT)", "precio": 650.00},
    ]
    
    for i, srv in enumerate(servicios, 1):
        productos.append({
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}SRV-{i:03d}",
            "nombre": f"{srv['nombre']} (PRB)",
            "descripcion": "Servicio oftalmológico de prueba - no descuenta inventario",
            "categoria": "servicio",
            "tipo": "servicio",
            "unidad_medida": "servicio",
            "precio_venta": srv['precio'],
            "precio_con_iva": True,
            "requiere_receta": False,
            "controla_lote": False,
            "controla_vencimiento": False,
            "existencia_minima": 0,
            "existencia_maxima": 0,
            "bodega_id": None,
            "origen": "clinica",
            "is_active": True,
            "es_servicio": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        })
    
    # Productos de baja rotación - Clase C (3)
    baja_rotacion = [
        {"nombre": "Colirio Vitamina A Retinol", "precio": 85.00},
        {"nombre": "Ungüento Oftálmico Eritromicina", "precio": 95.00},
        {"nombre": "Solución Salina Irrigación 500ml", "precio": 35.00},
    ]
    
    for i, br in enumerate(baja_rotacion, 1):
        productos.append({
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}LOW-{i:03d}",
            "nombre": f"{br['nombre']} (PRB)",
            "descripcion": "Producto de baja rotación (Clase C) para pruebas ABC",
            "categoria": "baja_rotacion",
            "tipo": "medicamento",
            "unidad_medida": "unidad",
            "precio_venta": br['precio'],
            "precio_con_iva": True,
            "requiere_receta": False,
            "controla_lote": True,
            "controla_vencimiento": True,
            "existencia_minima": 1,
            "existencia_maxima": 10,
            "bodega_id": bodega_general_id,
            "origen": "clinica",
            "is_active": True,
            "es_servicio": False,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        })
    
    return productos


# ==================== LOTES ====================

def generar_lotes(productos: List[Dict], bodega_dispensario_id: str, bodega_quirofano_id: str) -> List[Dict[str, Any]]:
    """
    Genera lotes para productos con control de lote.
    Requisitos:
    - 3 medicamentos con 3 lotes escalonados
    - 1 producto con lote vencido
    - 2 productos con costos distintos por lote
    - 1 producto con exactamente 1 unidad
    - 2 productos bajo mínimo
    """
    ahora = datetime.now(timezone.utc).isoformat()
    lotes = []
    
    for i, producto in enumerate(productos):
        if not producto.get("controla_lote"):
            continue
            
        producto_id = producto["id"]
        bodega_id = producto.get("bodega_id")
        
        if producto["codigo"] == f"{PRB}MED-001":
            # Producto con 3 lotes escalonados + costos distintos
            lotes.extend([
                {
                    "id": str(uuid.uuid4()),
                    "producto_id": producto_id,
                    "bodega_id": bodega_id,
                    "numero_lote": f"{PRB}L001-A",
                    "fecha_vencimiento": generar_fecha_relativa(20),  # Vence pronto
                    "cantidad": 8,
                    "cantidad_disponible": 8,
                    "costo_unitario": 45.00,
                    "origen": "clinica",
                    "is_active": True,
                    "esDatoPrueba": True,
                    "created_at": ahora
                },
                {
                    "id": str(uuid.uuid4()),
                    "producto_id": producto_id,
                    "bodega_id": bodega_id,
                    "numero_lote": f"{PRB}L001-B",
                    "fecha_vencimiento": generar_fecha_relativa(120),
                    "cantidad": 15,
                    "cantidad_disponible": 15,
                    "costo_unitario": 48.00,  # Costo distinto
                    "origen": "clinica",
                    "is_active": True,
                    "esDatoPrueba": True,
                    "created_at": ahora
                },
                {
                    "id": str(uuid.uuid4()),
                    "producto_id": producto_id,
                    "bodega_id": bodega_id,
                    "numero_lote": f"{PRB}L001-C",
                    "fecha_vencimiento": generar_fecha_relativa(400),
                    "cantidad": 20,
                    "cantidad_disponible": 20,
                    "costo_unitario": 52.00,
                    "origen": "clinica",
                    "is_active": True,
                    "esDatoPrueba": True,
                    "created_at": ahora
                }
            ])
        elif producto["codigo"] == f"{PRB}MED-002":
            # Producto con lote VENCIDO
            lotes.extend([
                {
                    "id": str(uuid.uuid4()),
                    "producto_id": producto_id,
                    "bodega_id": bodega_id,
                    "numero_lote": f"{PRB}L002-VENCIDO",
                    "fecha_vencimiento": generar_fecha_relativa(-10),  # Ya vencido
                    "cantidad": 5,
                    "cantidad_disponible": 5,
                    "costo_unitario": 50.00,
                    "origen": "clinica",
                    "is_active": True,
                    "esDatoPrueba": True,
                    "created_at": ahora
                },
                {
                    "id": str(uuid.uuid4()),
                    "producto_id": producto_id,
                    "bodega_id": bodega_id,
                    "numero_lote": f"{PRB}L002-OK",
                    "fecha_vencimiento": generar_fecha_relativa(180),
                    "cantidad": 12,
                    "cantidad_disponible": 12,
                    "costo_unitario": 52.00,
                    "origen": "clinica",
                    "is_active": True,
                    "esDatoPrueba": True,
                    "created_at": ahora
                }
            ])
        elif producto["codigo"] == f"{PRB}MED-003":
            # Producto con exactamente 1 unidad (para prueba de concurrencia)
            lotes.append({
                "id": str(uuid.uuid4()),
                "producto_id": producto_id,
                "bodega_id": bodega_id,
                "numero_lote": f"{PRB}L003-UNICO",
                "fecha_vencimiento": generar_fecha_relativa(90),
                "cantidad": 1,
                "cantidad_disponible": 1,
                "costo_unitario": 22.00,
                "origen": "clinica",
                "is_active": True,
                "esDatoPrueba": True,
                "created_at": ahora
            })
        elif producto["codigo"] in [f"{PRB}LOW-001", f"{PRB}LOW-002"]:
            # Productos BAJO MÍNIMO (mínimo es 1, tienen 0)
            # No crear lote = existencia 0 < mínimo 1
            pass
        elif producto["codigo"] == f"{PRB}MED-004":
            # Producto con 3 lotes escalonados
            lotes.extend([
                {
                    "id": str(uuid.uuid4()),
                    "producto_id": producto_id,
                    "bodega_id": bodega_id,
                    "numero_lote": f"{PRB}L004-A",
                    "fecha_vencimiento": generar_fecha_relativa(25),
                    "cantidad": 10,
                    "cantidad_disponible": 10,
                    "costo_unitario": 65.00,
                    "origen": "clinica",
                    "is_active": True,
                    "esDatoPrueba": True,
                    "created_at": ahora
                },
                {
                    "id": str(uuid.uuid4()),
                    "producto_id": producto_id,
                    "bodega_id": bodega_id,
                    "numero_lote": f"{PRB}L004-B",
                    "fecha_vencimiento": generar_fecha_relativa(150),
                    "cantidad": 18,
                    "cantidad_disponible": 18,
                    "costo_unitario": 68.00,
                    "origen": "clinica",
                    "is_active": True,
                    "esDatoPrueba": True,
                    "created_at": ahora
                },
                {
                    "id": str(uuid.uuid4()),
                    "producto_id": producto_id,
                    "bodega_id": bodega_id,
                    "numero_lote": f"{PRB}L004-C",
                    "fecha_vencimiento": generar_fecha_relativa(380),
                    "cantidad": 25,
                    "cantidad_disponible": 25,
                    "costo_unitario": 70.00,
                    "origen": "clinica",
                    "is_active": True,
                    "esDatoPrueba": True,
                    "created_at": ahora
                }
            ])
        elif producto["codigo"] == f"{PRB}MED-008":
            # Producto con costos muy distintos por lote (para prueba costo promedio)
            lotes.extend([
                {
                    "id": str(uuid.uuid4()),
                    "producto_id": producto_id,
                    "bodega_id": bodega_id,
                    "numero_lote": f"{PRB}L008-BARATO",
                    "fecha_vencimiento": generar_fecha_relativa(200),
                    "cantidad": 10,
                    "cantidad_disponible": 10,
                    "costo_unitario": 280.00,  # Costo bajo
                    "origen": "clinica",
                    "is_active": True,
                    "esDatoPrueba": True,
                    "created_at": ahora
                },
                {
                    "id": str(uuid.uuid4()),
                    "producto_id": producto_id,
                    "bodega_id": bodega_id,
                    "numero_lote": f"{PRB}L008-CARO",
                    "fecha_vencimiento": generar_fecha_relativa(300),
                    "cantidad": 5,
                    "cantidad_disponible": 5,
                    "costo_unitario": 350.00,  # Costo alto
                    "origen": "clinica",
                    "is_active": True,
                    "esDatoPrueba": True,
                    "created_at": ahora
                }
            ])
        else:
            # Lote estándar para otros productos
            lotes.append({
                "id": str(uuid.uuid4()),
                "producto_id": producto_id,
                "bodega_id": bodega_id,
                "numero_lote": f"{PRB}L-{producto['codigo'][-3:]}",
                "fecha_vencimiento": generar_fecha_relativa(180),
                "cantidad": 20,
                "cantidad_disponible": 20,
                "costo_unitario": producto["precio_venta"] * 0.55,  # Margen ~45%
                "origen": "clinica",
                "is_active": True,
                "esDatoPrueba": True,
                "created_at": ahora
            })
    
    return lotes


# ==================== USUARIOS DE PRUEBA ====================

def generar_usuarios_prueba() -> List[Dict[str, Any]]:
    """Genera usuarios de prueba por rol"""
    ahora = datetime.now(timezone.utc).isoformat()
    
    return [
        {
            "id": str(uuid.uuid4()),
            "username": "prb.superadmin",
            "name": "SuperAdmin de Prueba",
            "password": hash_password("PrbSuper2024!"),
            "role": "superadmin",
            "is_active": True,
            "must_change_password": False,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "username": "prb.admin",
            "name": "Admin de Prueba",
            "password": hash_password("PrbAdmin2024!"),
            "role": "admin",
            "is_active": True,
            "must_change_password": False,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "username": "prb.usuario",
            "name": "Usuario de Prueba",
            "password": hash_password("PrbUser2024!"),
            "role": "usuario",
            "is_active": True,
            "must_change_password": False,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "username": "prb.medico1",
            "name": "Dr. Roberto Prueba García",
            "password": hash_password("PrbMed1-2024!"),
            "role": "usuario",
            "is_active": True,
            "must_change_password": False,
            "medico_id": None,  # Se enlazará después
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "username": "prb.medico2",
            "name": "Dra. Carmen Prueba López",
            "password": hash_password("PrbMed2-2024!"),
            "role": "usuario",
            "is_active": True,
            "must_change_password": False,
            "medico_id": None,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        }
    ]


# ==================== MÉDICOS ====================

def generar_medicos() -> List[Dict[str, Any]]:
    """Genera médicos para agenda"""
    ahora = datetime.now(timezone.utc).isoformat()
    
    return [
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}DOC-001",
            "nombre": "Dr. Roberto Prueba García",
            "especialidad": "Oftalmología General",
            "colegiado": f"{PRB}12345",
            "color": "#4CAF50",  # Verde
            "telefono": "5555-0001",
            "email": "prb.roberto@test.gt",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}DOC-002",
            "nombre": "Dra. Carmen Prueba López",
            "especialidad": "Retina y Vítreo",
            "colegiado": f"{PRB}12346",
            "color": "#2196F3",  # Azul
            "telefono": "5555-0002",
            "email": "prb.carmen@test.gt",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}DOC-003",
            "nombre": "Dr. Miguel Prueba Hernández",
            "especialidad": "Glaucoma",
            "colegiado": f"{PRB}12347",
            "color": "#FF9800",  # Naranja
            "telefono": "5555-0003",
            "email": "prb.miguel@test.gt",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}DOC-004",
            "nombre": "Dr. Luis Prueba Morales (Anestesiólogo)",
            "especialidad": "Anestesiología",
            "colegiado": f"{PRB}12348",
            "color": "#9C27B0",  # Morado
            "telefono": "5555-0004",
            "email": "prb.luis@test.gt",
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        }
    ]


# ==================== TIPO DE PAGADOR ====================

def generar_tipo_pagador_prueba() -> Dict[str, Any]:
    """Genera el tipo de pagador PRB-Convenio Empresarial"""
    ahora = datetime.now(timezone.utc).isoformat()
    
    return {
        "id": str(uuid.uuid4()),
        "codigo": f"{PRB}PAG-001",
        "nombre": "PRB-Convenio Empresarial",
        "descripcion": "Convenio empresarial de prueba para testing",
        "porcentaje_cobertura": 80,
        "requiere_autorizacion": True,
        "plazo_pago_dias": 45,
        "is_active": True,
        "esDatoPrueba": True,
        "created_at": ahora,
        "updated_at": ahora
    }


# ==================== PRODUCTOS ÓPTICA ====================

def generar_productos_optica() -> Dict[str, List[Dict[str, Any]]]:
    """
    Genera productos de óptica:
    - 5 armazones
    - 4 tipos de lente
    - 3 lentes de contacto
    """
    ahora = datetime.now(timezone.utc).isoformat()
    
    # Armazones (5)
    frames = [
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}ARO-001",
            "brand": "RayBan PRB",
            "model": "Aviator Classic",
            "color": "Dorado",
            "material": "Metal",
            "size": "58-14-140",
            "gender": "unisex",
            "price": 850.00,
            "cost": 450.00,
            "stock": 8,
            "min_stock": 3,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}ARO-002",
            "brand": "Oakley PRB",
            "model": "Crosslink",
            "color": "Negro Mate",
            "material": "Acetato",
            "size": "54-18-135",
            "gender": "masculino",
            "price": 1200.00,
            "cost": 650.00,
            "stock": 5,
            "min_stock": 2,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}ARO-003",
            "brand": "Guess PRB",
            "model": "Fashion Cat",
            "color": "Carey",
            "material": "Acetato",
            "size": "52-16-140",
            "gender": "femenino",
            "price": 750.00,
            "cost": 380.00,
            "stock": 10,
            "min_stock": 3,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}ARO-004",
            "brand": "Tommy Hilfiger PRB",
            "model": "Classic Square",
            "color": "Azul Navy",
            "material": "Combinado",
            "size": "55-17-145",
            "gender": "unisex",
            "price": 980.00,
            "cost": 520.00,
            "stock": 6,
            "min_stock": 2,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}ARO-005",
            "brand": "Vogue PRB",
            "model": "Deluxe Round",
            "color": "Rosa Gold",
            "material": "Metal",
            "size": "50-20-140",
            "gender": "femenino",
            "price": 2800.00,
            "cost": 1500.00,
            "stock": 3,
            "min_stock": 1,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        }
    ]
    
    # Tipos de lente (4)
    lens_types = [
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}LNT-001",
            "name": "Monofocal CR-39 (PRB)",
            "description": "Lente monofocal estándar",
            "material": "CR-39",
            "type": "monofocal",
            "base_price": 180.00,
            "cost": 80.00,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}LNT-002",
            "name": "Monofocal Policarbonato (PRB)",
            "description": "Lente monofocal resistente a impactos",
            "material": "Policarbonato",
            "type": "monofocal",
            "base_price": 350.00,
            "cost": 150.00,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}LNT-003",
            "name": "Progresivo Premium (PRB)",
            "description": "Lente progresivo de alta gama",
            "material": "Alto Índice 1.67",
            "type": "progresivo",
            "base_price": 1800.00,
            "cost": 800.00,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}LNT-004",
            "name": "Bifocal Flat Top (PRB)",
            "description": "Lente bifocal tradicional",
            "material": "CR-39",
            "type": "bifocal",
            "base_price": 480.00,
            "cost": 200.00,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        }
    ]
    
    # Lentes de contacto (3)
    contact_lenses = [
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}LC-001",
            "brand": "Acuvue PRB",
            "name": "Oasys Mensual",
            "type": "blando_mensual",
            "material": "Hidrogel de Silicona",
            "replacement": "mensual",
            "price": 580.00,
            "cost": 280.00,
            "stock": 20,
            "min_stock": 5,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}LC-002",
            "brand": "Air Optix PRB",
            "name": "Toric Astigmatismo",
            "type": "torico",
            "material": "Hidrogel de Silicona",
            "replacement": "mensual",
            "price": 750.00,
            "cost": 380.00,
            "stock": 12,
            "min_stock": 3,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        },
        {
            "id": str(uuid.uuid4()),
            "code": f"{PRB}LC-003",
            "brand": "ReNu PRB",
            "name": "Solución Multipropósito 360ml",
            "type": "solucion",
            "material": "N/A",
            "replacement": "N/A",
            "price": 145.00,
            "cost": 65.00,
            "stock": 30,
            "min_stock": 10,
            "is_active": True,
            "esDatoPrueba": True,
            "created_at": ahora,
            "updated_at": ahora
        }
    ]
    
    return {
        "frames": frames,
        "lens_types": lens_types,
        "contact_lenses": contact_lenses
    }


# ==================== FUNCIÓN PRINCIPAL ====================

async def seed_datos_maestros(db) -> Dict[str, Any]:
    """
    Ejecuta el seed de datos maestros (Fase 1).
    Retorna diccionario con los IDs generados para uso en fases siguientes.
    """
    from seed import verificar_ambiente
    verificar_ambiente()
    
    resultado = {
        "bodegas": {},
        "proveedores": [],
        "productos_clinica": [],
        "productos_optica": {},
        "lotes": [],
        "usuarios": [],
        "medicos": [],
        "tipo_pagador": None
    }
    
    # 1. Bodegas
    bodegas = generar_bodegas()
    await db.bodegas_inventario.insert_many(bodegas)
    for b in bodegas:
        resultado["bodegas"][b["codigo"]] = b["id"]
    
    # 2. Proveedores
    proveedores = generar_proveedores()
    await db.proveedores.insert_many(proveedores)
    resultado["proveedores"] = [p["id"] for p in proveedores]
    
    # 3. Productos clínica
    bodega_dis = resultado["bodegas"][f"{PRB}BOD-DIS"]
    bodega_gen = resultado["bodegas"][f"{PRB}BOD-GEN"]
    bodega_qui = resultado["bodegas"][f"{PRB}BOD-QUI"]
    
    productos = generar_productos_clinica(bodega_dis, bodega_gen, bodega_qui)
    await db.productos_inventario.insert_many(productos)
    resultado["productos_clinica"] = productos
    
    # 4. Lotes
    lotes = generar_lotes(productos, bodega_dis, bodega_qui)
    if lotes:
        await db.lotes_inventario.insert_many(lotes)
    resultado["lotes"] = lotes
    
    # 5. Usuarios de prueba
    usuarios = generar_usuarios_prueba()
    await db.users.insert_many(usuarios)
    resultado["usuarios"] = usuarios
    
    # 6. Médicos
    medicos = generar_medicos()
    await db.medicos_agenda.insert_many(medicos)
    resultado["medicos"] = medicos
    
    # Enlazar usuarios médicos con sus registros de médico
    for i, medico in enumerate(medicos[:2]):  # Solo los 2 primeros
        await db.users.update_one(
            {"username": f"prb.medico{i+1}"},
            {"$set": {"medico_id": medico["id"]}}
        )
    
    # 7. Tipo de pagador
    pagador = generar_tipo_pagador_prueba()
    await db.tipos_pagador.insert_one(pagador)
    resultado["tipo_pagador"] = pagador["id"]
    
    # 8. Productos óptica
    optica = generar_productos_optica()
    await db.optica_frames.insert_many(optica["frames"])
    await db.optica_lens_types.insert_many(optica["lens_types"])
    await db.optica_contact_lenses.insert_many(optica["contact_lenses"])
    resultado["productos_optica"] = {
        "frames": [f["id"] for f in optica["frames"]],
        "lens_types": [l["id"] for l in optica["lens_types"]],
        "contact_lenses": [c["id"] for c in optica["contact_lenses"]]
    }
    
    # Crear índices para esDatoPrueba
    colecciones = [
        "bodegas_inventario", "proveedores", "productos_inventario",
        "lotes_inventario", "users", "medicos_agenda", "tipos_pagador",
        "optica_frames", "optica_lens_types", "optica_contact_lenses"
    ]
    for col in colecciones:
        try:
            await db[col].create_index([("esDatoPrueba", 1)])
        except Exception:
            pass
    
    return resultado
