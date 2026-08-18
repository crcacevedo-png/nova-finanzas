# /app/backend/seed/pacientes.py
"""
FASE 2: Pacientes Sintéticos
Genera 14 pacientes con perfiles específicos para pruebas E2E.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
import random

PRB = "PRB-"


def generar_dpi_ficticio(numero: int) -> str:
    """
    Genera DPI guatemalteco ficticio de prueba.
    Formato: XXXX XXXXX XXXX (13 dígitos)
    Prefijo PRB para identificar datos de prueba.
    """
    # Usar un patrón reconocible: 9999 + número + relleno
    base = f"9999{numero:05d}"
    # Completar a 13 dígitos
    dpi = f"{base}{random.randint(1000, 9999)}"[:13]
    return dpi


def generar_fecha_nacimiento(edad: int) -> str:
    """Genera fecha de nacimiento basada en edad aproximada"""
    hoy = datetime.now(timezone.utc)
    nacimiento = hoy - timedelta(days=edad * 365 + random.randint(0, 364))
    return nacimiento.strftime("%Y-%m-%d")


def generar_record_number(numero: int) -> str:
    """
    Genera número de expediente único para pacientes de prueba.
    Formato: PRB-EXP-XXXXXX (único y reconocible)
    """
    return f"PRB-EXP-{numero:06d}"


def generar_pacientes() -> List[Dict[str, Any]]:
    """
    Genera los 14 pacientes de prueba según especificación.
    Cada paciente tiene un perfil específico para probar diferentes flujos.
    """
    ahora = datetime.now(timezone.utc).isoformat()
    
    pacientes = [
        # 1. Adulto privado, catarata - Ruta completa clínica + POS
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0001",
            "primer_nombre": "Carlos",
            "segundo_nombre": "Eduardo",
            "primer_apellido": "Ramírez",
            "segundo_apellido": "Paz",
            "dpi": generar_dpi_ficticio(1),
            "fecha_nacimiento": generar_fecha_nacimiento(62),
            "genero": "masculino",
            "telefono": "5555-1001",
            "telefono_emergencia": "5555-1002",
            "email": "prb.carlos.ramirez@test.gt",
            "direccion": "Zona 10, Ciudad de Guatemala (PRB)",
            "ocupacion": "Ingeniero retirado",
            "tipo_sangre": "O+",
            "tipo_pagador": "privado",
            "institucion": None,
            "antecedentes_medicos": {
                "diabetes": True,
                "hipertension": False,
                "alergias": ["Penicilina"],
                "cirugias_previas": [],
                "medicamentos_actuales": ["Metformina 850mg"],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": False,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": True,
                    "tipo_lentes": "lectura"
                }
            },
            "notas": "Paciente de prueba #1 - Ruta clínica completa con catarata",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "clinico_catarata_privado",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 2. Adulto IGSS, catarata - Ruta quirúrgica con campos IGSS
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0002",
            "primer_nombre": "María",
            "segundo_nombre": "Elena",
            "primer_apellido": "López",
            "segundo_apellido": "de González",
            "dpi": generar_dpi_ficticio(2),
            "fecha_nacimiento": generar_fecha_nacimiento(58),
            "genero": "femenino",
            "telefono": "5555-2001",
            "telefono_emergencia": "5555-2002",
            "email": "prb.maria.lopez@test.gt",
            "direccion": "Zona 12, Ciudad de Guatemala (PRB)",
            "ocupacion": "Secretaria",
            "tipo_sangre": "A+",
            "tipo_pagador": "igss",
            "institucion": "IGSS",
            "igss_unidad": "Unidad de Oftalmología Central",
            "igss_afiliacion": "123456789-0",
            "igss_no_sps": f"{PRB}SPS-001",
            "igss_codigo": "OFT-CAT-001",
            "igss_nog": f"{PRB}NOG-001",
            "igss_tipo_compra": "Cirugía programada",
            "antecedentes_medicos": {
                "diabetes": False,
                "hipertension": True,
                "alergias": [],
                "cirugias_previas": ["Cesárea 1998"],
                "medicamentos_actuales": ["Losartán 50mg"],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": False,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": True,
                    "tipo_lentes": "bifocales"
                }
            },
            "notas": "Paciente de prueba #2 - Ruta quirúrgica IGSS",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "quirurgico_igss",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 3. Adulto con seguro médico - Cuenta por cobrar
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0003",
            "primer_nombre": "Roberto",
            "segundo_nombre": "Antonio",
            "primer_apellido": "Castillo",
            "segundo_apellido": "Morales",
            "dpi": generar_dpi_ficticio(3),
            "fecha_nacimiento": generar_fecha_nacimiento(45),
            "genero": "masculino",
            "telefono": "5555-3001",
            "telefono_emergencia": "5555-3002",
            "email": "prb.roberto.castillo@test.gt",
            "direccion": "Zona 14, Ciudad de Guatemala (PRB)",
            "ocupacion": "Ejecutivo",
            "tipo_sangre": "B+",
            "tipo_pagador": "seguro",
            "institucion": "Seguros Médicos",
            "numero_poliza": f"{PRB}POL-001",
            "antecedentes_medicos": {
                "diabetes": False,
                "hipertension": False,
                "alergias": ["Sulfas"],
                "cirugias_previas": [],
                "medicamentos_actuales": [],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": True,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": True,
                    "tipo_lentes": "progresivos"
                }
            },
            "notas": "Paciente de prueba #3 - Cuenta por cobrar con seguro",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "seguro_cxc",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 4. Adulto miope - Ruta de óptica pura (solo lentes)
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0004",
            "primer_nombre": "Ana",
            "segundo_nombre": "Lucía",
            "primer_apellido": "Méndez",
            "segundo_apellido": "Ruiz",
            "dpi": generar_dpi_ficticio(4),
            "fecha_nacimiento": generar_fecha_nacimiento(28),
            "genero": "femenino",
            "telefono": "5555-4001",
            "telefono_emergencia": "5555-4002",
            "email": "prb.ana.mendez@test.gt",
            "direccion": "Zona 1, Ciudad de Guatemala (PRB)",
            "ocupacion": "Diseñadora Gráfica",
            "tipo_sangre": "AB+",
            "tipo_pagador": "privado",
            "institucion": None,
            "antecedentes_medicos": {
                "diabetes": False,
                "hipertension": False,
                "alergias": [],
                "cirugias_previas": [],
                "medicamentos_actuales": [],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": False,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": True,
                    "tipo_lentes": "monofocales",
                    "graduacion_actual": {
                        "od": {"esfera": -3.25, "cilindro": -0.75, "eje": 180},
                        "oi": {"esfera": -3.00, "cilindro": -0.50, "eje": 175}
                    }
                }
            },
            "notas": "Paciente de prueba #4 - Óptica pura, miopía",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "optica_miopia",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 5. Adulto présbita - Óptica: progresivos
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0005",
            "primer_nombre": "Fernando",
            "segundo_nombre": "José",
            "primer_apellido": "García",
            "segundo_apellido": "Estrada",
            "dpi": generar_dpi_ficticio(5),
            "fecha_nacimiento": generar_fecha_nacimiento(52),
            "genero": "masculino",
            "telefono": "5555-5001",
            "telefono_emergencia": "5555-5002",
            "email": "prb.fernando.garcia@test.gt",
            "direccion": "Zona 15, Ciudad de Guatemala (PRB)",
            "ocupacion": "Contador",
            "tipo_sangre": "O-",
            "tipo_pagador": "privado",
            "institucion": None,
            "antecedentes_medicos": {
                "diabetes": False,
                "hipertension": False,
                "alergias": [],
                "cirugias_previas": [],
                "medicamentos_actuales": [],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": False,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": True,
                    "tipo_lentes": "progresivos",
                    "graduacion_actual": {
                        "od": {"esfera": +0.50, "cilindro": -0.25, "eje": 90, "adicion": +2.00},
                        "oi": {"esfera": +0.75, "cilindro": 0, "eje": 0, "adicion": +2.00}
                    }
                }
            },
            "notas": "Paciente de prueba #5 - Óptica progresivos, presbicia",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "optica_presbicia",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 6. Adulto con ojo seco - Solo receta de medicamentos + venta POS
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0006",
            "primer_nombre": "Claudia",
            "segundo_nombre": "Patricia",
            "primer_apellido": "Herrera",
            "segundo_apellido": "Vásquez",
            "dpi": generar_dpi_ficticio(6),
            "fecha_nacimiento": generar_fecha_nacimiento(38),
            "genero": "femenino",
            "telefono": "5555-6001",
            "telefono_emergencia": "5555-6002",
            "email": "prb.claudia.herrera@test.gt",
            "direccion": "Zona 7, Ciudad de Guatemala (PRB)",
            "ocupacion": "Abogada",
            "tipo_sangre": "A-",
            "tipo_pagador": "privado",
            "institucion": None,
            "antecedentes_medicos": {
                "diabetes": False,
                "hipertension": False,
                "alergias": [],
                "cirugias_previas": [],
                "medicamentos_actuales": [],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": False,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": False,
                    "condiciones": ["Síndrome de ojo seco"]
                }
            },
            "notas": "Paciente de prueba #6 - Ojo seco, solo medicamentos",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "medicamentos_ojo_seco",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 7. Niño (8 años) - Validación de edad, receta pediátrica
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0007",
            "primer_nombre": "Diego",
            "segundo_nombre": "Alejandro",
            "primer_apellido": "Martínez",
            "segundo_apellido": "Solís",
            "dpi": generar_dpi_ficticio(7),
            "fecha_nacimiento": generar_fecha_nacimiento(8),
            "genero": "masculino",
            "telefono": "5555-7001",
            "telefono_emergencia": "5555-7002",
            "email": "prb.diego.martinez@test.gt",
            "direccion": "Zona 11, Ciudad de Guatemala (PRB)",
            "ocupacion": "Estudiante",
            "tipo_sangre": "O+",
            "tipo_pagador": "privado",
            "institucion": None,
            "responsable": {
                "nombre": "Julia Solís de Martínez",
                "parentesco": "Madre",
                "telefono": "5555-7003",
                "dpi": generar_dpi_ficticio(107)
            },
            "antecedentes_medicos": {
                "diabetes": False,
                "hipertension": False,
                "alergias": [],
                "cirugias_previas": [],
                "medicamentos_actuales": [],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": False,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": True,
                    "tipo_lentes": "monofocales",
                    "graduacion_actual": {
                        "od": {"esfera": -1.50, "cilindro": 0, "eje": 0},
                        "oi": {"esfera": -1.75, "cilindro": 0, "eje": 0}
                    }
                }
            },
            "notas": "Paciente de prueba #7 - Pediátrico, 8 años",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "pediatrico",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 8. Adulto mayor (78 años) - Múltiples medicamentos + lentes (aislamiento cruzado)
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0008",
            "primer_nombre": "Esperanza",
            "segundo_nombre": "del Carmen",
            "primer_apellido": "Figueroa",
            "segundo_apellido": "viuda de Reyes",
            "dpi": generar_dpi_ficticio(8),
            "fecha_nacimiento": generar_fecha_nacimiento(78),
            "genero": "femenino",
            "telefono": "5555-8001",
            "telefono_emergencia": "5555-8002",
            "email": "prb.esperanza.figueroa@test.gt",
            "direccion": "Zona 5, Ciudad de Guatemala (PRB)",
            "ocupacion": "Jubilada",
            "tipo_sangre": "B-",
            "tipo_pagador": "privado",
            "institucion": None,
            "antecedentes_medicos": {
                "diabetes": True,
                "hipertension": True,
                "alergias": ["AINEs"],
                "cirugias_previas": ["Colecistectomía 2010", "Cirugía de catarata OD 2022"],
                "medicamentos_actuales": ["Metformina 1g", "Enalapril 10mg", "Aspirina 100mg"],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": True,
                    "cirugia_ocular_previa": True,
                    "usa_lentes": True,
                    "tipo_lentes": "progresivos",
                    "condiciones": ["Pseudofaquia OD", "Catarata OI", "Glaucoma sospechoso"]
                }
            },
            "notas": "Paciente de prueba #8 - CRÍTICO: Prueba de aislamiento cruzado clínica/óptica",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "aislamiento_cruzado",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 9. Usuario de lentes de contacto - Óptica: LC + líquido
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0009",
            "primer_nombre": "Sofía",
            "segundo_nombre": "Isabella",
            "primer_apellido": "Juárez",
            "segundo_apellido": "Pineda",
            "dpi": generar_dpi_ficticio(9),
            "fecha_nacimiento": generar_fecha_nacimiento(25),
            "genero": "femenino",
            "telefono": "5555-9001",
            "telefono_emergencia": "5555-9002",
            "email": "prb.sofia.juarez@test.gt",
            "direccion": "Zona 4, Ciudad de Guatemala (PRB)",
            "ocupacion": "Modelo",
            "tipo_sangre": "A+",
            "tipo_pagador": "privado",
            "institucion": None,
            "antecedentes_medicos": {
                "diabetes": False,
                "hipertension": False,
                "alergias": [],
                "cirugias_previas": [],
                "medicamentos_actuales": [],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": False,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": True,
                    "tipo_lentes": "lentes de contacto",
                    "graduacion_actual": {
                        "od": {"esfera": -2.00, "cilindro": -0.50, "eje": 180},
                        "oi": {"esfera": -2.25, "cilindro": -0.75, "eje": 170}
                    }
                }
            },
            "notas": "Paciente de prueba #9 - Lentes de contacto tóricos",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "optica_lc",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 10. Paciente de glaucoma en control - Múltiples citas históricas
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0010",
            "primer_nombre": "Héctor",
            "segundo_nombre": "Manuel",
            "primer_apellido": "Ortiz",
            "segundo_apellido": "Barrios",
            "dpi": generar_dpi_ficticio(10),
            "fecha_nacimiento": generar_fecha_nacimiento(65),
            "genero": "masculino",
            "telefono": "5555-0010",
            "telefono_emergencia": "5555-0011",
            "email": "prb.hector.ortiz@test.gt",
            "direccion": "Zona 18, Ciudad de Guatemala (PRB)",
            "ocupacion": "Agricultor",
            "tipo_sangre": "O+",
            "tipo_pagador": "privado",
            "institucion": None,
            "antecedentes_medicos": {
                "diabetes": False,
                "hipertension": True,
                "alergias": [],
                "cirugias_previas": [],
                "medicamentos_actuales": ["Amlodipino 5mg"],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": True,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": True,
                    "tipo_lentes": "bifocales",
                    "condiciones": ["Glaucoma primario de ángulo abierto AO"],
                    "tratamiento_actual": ["Timolol 0.5%", "Latanoprost 0.005%"]
                }
            },
            "notas": "Paciente de prueba #10 - Glaucoma en control, múltiples citas históricas",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "glaucoma_control",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 11. Paciente con evaluación sellada (retroactiva 30 h) - Prueba del sello de 24 h
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0011",
            "primer_nombre": "Patricia",
            "segundo_nombre": "Alejandra",
            "primer_apellido": "Monzón",
            "segundo_apellido": "de León",
            "dpi": generar_dpi_ficticio(11),
            "fecha_nacimiento": generar_fecha_nacimiento(42),
            "genero": "femenino",
            "telefono": "5555-0012",
            "telefono_emergencia": "5555-0013",
            "email": "prb.patricia.monzon@test.gt",
            "direccion": "Zona 6, Ciudad de Guatemala (PRB)",
            "ocupacion": "Enfermera",
            "tipo_sangre": "AB-",
            "tipo_pagador": "privado",
            "institucion": None,
            "antecedentes_medicos": {
                "diabetes": False,
                "hipertension": False,
                "alergias": ["Látex"],
                "cirugias_previas": [],
                "medicamentos_actuales": [],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": False,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": True,
                    "tipo_lentes": "progresivos"
                }
            },
            "notas": "Paciente de prueba #11 - SELLO 24H: Evaluación creada hace 30 horas",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "sello_24h",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 12. Paciente con cita no asistida - Estado no-show en agenda
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0012",
            "primer_nombre": "Luis",
            "segundo_nombre": "Alberto",
            "primer_apellido": "Sandoval",
            "segundo_apellido": "Pérez",
            "dpi": generar_dpi_ficticio(12),
            "fecha_nacimiento": generar_fecha_nacimiento(35),
            "genero": "masculino",
            "telefono": "5555-0014",
            "telefono_emergencia": "5555-0015",
            "email": "prb.luis.sandoval@test.gt",
            "direccion": "Zona 21, Ciudad de Guatemala (PRB)",
            "ocupacion": "Vendedor",
            "tipo_sangre": "O+",
            "tipo_pagador": "privado",
            "institucion": None,
            "antecedentes_medicos": {
                "diabetes": False,
                "hipertension": False,
                "alergias": [],
                "cirugias_previas": [],
                "medicamentos_actuales": [],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": False,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": False
                }
            },
            "notas": "Paciente de prueba #12 - No-show, cita no asistida",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "no_show",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 13. Duplicado intencional del paciente 1 - Prueba de detección de duplicados
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0013",
            "primer_nombre": "Carlos",
            "segundo_nombre": "Eduardo",
            "primer_apellido": "Ramirez",  # Sin tilde - variación ortográfica
            "segundo_apellido": "Pas",  # Error ortográfico intencional
            "dpi": generar_dpi_ficticio(1),  # MISMO DPI que paciente 1
            "fecha_nacimiento": generar_fecha_nacimiento(62),
            "genero": "masculino",
            "telefono": "5555-1001",  # Mismo teléfono
            "telefono_emergencia": "5555-1002",
            "email": "prb.carlos.ramirez2@test.gt",
            "direccion": "Zona 10, Ciudad de Guatemala (PRB)",
            "ocupacion": "Ingeniero",
            "tipo_sangre": "O+",
            "tipo_pagador": "privado",
            "institucion": None,
            "antecedentes_medicos": {
                "diabetes": True,
                "hipertension": False,
                "alergias": ["Penicilina"],
                "cirugias_previas": [],
                "medicamentos_actuales": ["Metformina 850mg"],
                "antecedentes_oftalmologicos": {}
            },
            "notas": "Paciente de prueba #13 - DUPLICADO INTENCIONAL de PAC-0001 para prueba de detección",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "duplicado_detectar",
            "es_duplicado_intencional": True,
            "duplicado_de": f"{PRB}PAC-0001",
            "created_at": ahora,
            "updated_at": ahora
        },
        
        # 14. Paciente creado desde la agenda en línea - Verificar no duplicación
        {
            "id": str(uuid.uuid4()),
            "codigo": f"{PRB}PAC-0014",
            "primer_nombre": "Gabriela",
            "segundo_nombre": "María",
            "primer_apellido": "Torres",
            "segundo_apellido": "Cifuentes",
            "dpi": generar_dpi_ficticio(14),
            "fecha_nacimiento": generar_fecha_nacimiento(30),
            "genero": "femenino",
            "telefono": "5555-0016",
            "telefono_emergencia": "5555-0017",
            "email": "prb.gabriela.torres@test.gt",
            "direccion": "Zona 16, Ciudad de Guatemala (PRB)",
            "ocupacion": "Maestra",
            "tipo_sangre": "A+",
            "tipo_pagador": "privado",
            "institucion": None,
            "antecedentes_medicos": {
                "diabetes": False,
                "hipertension": False,
                "alergias": [],
                "cirugias_previas": [],
                "medicamentos_actuales": [],
                "antecedentes_oftalmologicos": {
                    "glaucoma_familiar": False,
                    "cirugia_ocular_previa": False,
                    "usa_lentes": True,
                    "tipo_lentes": "monofocales"
                }
            },
            "notas": "Paciente de prueba #14 - Creado desde agenda, verificar no duplicación",
            "is_active": True,
            "esDatoPrueba": True,
            "perfil_prueba": "agenda_creacion",
            "creado_desde_agenda": True,
            "created_at": ahora,
            "updated_at": ahora
        }
    ]
    
    return pacientes


async def seed_pacientes(db) -> List[Dict[str, Any]]:
    """
    Ejecuta el seed de pacientes (Fase 2).
    """
    from seed import verificar_ambiente
    verificar_ambiente()
    
    pacientes = generar_pacientes()
    
    # Agregar record_number único a cada paciente
    for i, paciente in enumerate(pacientes, start=1):
        paciente["record_number"] = generar_record_number(i)
    
    # Insertar todos excepto el duplicado intencional (#13)
    # El #13 se usará para probar la detección de duplicados
    pacientes_a_insertar = [p for p in pacientes if not p.get("es_duplicado_intencional")]
    
    if pacientes_a_insertar:
        await db.patients.insert_many(pacientes_a_insertar)
    
    # Crear índice para esDatoPrueba y perfil_prueba
    try:
        await db.patients.create_index([("esDatoPrueba", 1)])
        await db.patients.create_index([("perfil_prueba", 1)])
        await db.patients.create_index([("codigo", 1)])
    except Exception:
        pass
    
    return pacientes
