# /app/backend/seed/__init__.py
"""
Módulo de Generación de Datos de Prueba - NovaVision ERP
FASE 1-4: Datos Maestros, Pacientes y Recorridos E2E

REGLAS INVIOLABLES:
1. Todo dato lleva esDatoPrueba: true
2. Todo identificador visible lleva prefijo PRB-
3. Solo ejecutable si NODE_ENV !== "production"
4. No debilita reglas de negocio
"""

import os
from datetime import datetime, timezone

# Verificación de ambiente - CRÍTICO
def verificar_ambiente():
    """Verifica que NO estemos en producción"""
    env = os.environ.get('ENVIRONMENT', os.environ.get('NODE_ENV', 'development'))
    if env.lower() == 'production':
        raise RuntimeError(
            "❌ BLOQUEADO: El generador de datos de prueba NO puede ejecutarse en producción. "
            "Esta restricción no es negociable ni configurable."
        )
    return True

# Constantes
PREFIJO_PRUEBA = "PRB-"
BANDERA_PRUEBA = "esDatoPrueba"

# Verificar al importar
verificar_ambiente()
