"""
Configuración centralizada de pytest para NovaVision ERP
Este archivo contiene fixtures reutilizables para todos los tests
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
import os
import sys

# Asegurar que el directorio backend esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app


# ============= Configuración de Event Loop =============

@pytest.fixture(scope="session")
def event_loop():
    """Crear un event loop para toda la sesión de tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============= Fixtures de Autenticación =============

@pytest.fixture
def superadmin_credentials():
    """Credenciales de SuperAdmin para testing"""
    return {
        "username": "superadmin",
        "password": "nova2024"
    }


@pytest.fixture
def admin_credentials():
    """Credenciales de Admin para testing"""
    return {
        "username": "admin",
        "password": "Admin2024Nuevo!"
    }


@pytest.fixture
def usuario_credentials():
    """Credenciales de Usuario regular para testing"""
    return {
        "username": "usuario",
        "password": "user2024"
    }


@pytest.fixture
def optica_credentials():
    """Credenciales de Usuario óptica para testing"""
    return {
        "username": "optica",
        "password": "optica2024"
    }


# ============= Fixtures de Cliente HTTP =============

@pytest.fixture
async def client():
    """Cliente HTTP async para tests de API"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def auth_client(client, superadmin_credentials):
    """Cliente HTTP autenticado como SuperAdmin"""
    response = await client.post(
        "/api/auth/login",
        json=superadmin_credentials
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


@pytest.fixture
async def admin_client(client, admin_credentials):
    """Cliente HTTP autenticado como Admin"""
    response = await client.post(
        "/api/auth/login",
        json=admin_credentials
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


# ============= Fixtures de Datos de Prueba =============

@pytest.fixture
def sample_paciente():
    """Datos de paciente de prueba"""
    return {
        "nombre": "Juan",
        "apellido": "García Test",
        "dpi": f"1234567{datetime.now().strftime('%H%M%S')}",
        "telefono": "55512345",
        "email": f"test_{datetime.now().timestamp()}@test.com",
        "fecha_nacimiento": "1990-01-15",
        "direccion": "Ciudad de Guatemala",
        "genero": "M"
    }


@pytest.fixture
def sample_producto():
    """Datos de producto de prueba para inventario"""
    timestamp = datetime.now().strftime('%H%M%S')
    return {
        "codigo": f"TEST-{timestamp}",
        "nombre": f"Producto Test {timestamp}",
        "descripcion": "Producto creado para testing",
        "tipo": "producto",
        "precio_venta": 100.00,
        "costo_promedio": 60.00,
        "controla_inventario": True,
        "controla_lotes": True,
        "stock_minimo": 5,
        "activo": True
    }


@pytest.fixture
def sample_venta():
    """Datos de venta POS de prueba"""
    return {
        "items": [
            {
                "producto_id": "test_producto_id",
                "nombre": "Producto Test",
                "cantidad": 2,
                "precio_unitario": 50.00,
                "descuento": 0
            }
        ],
        "formas_pago": [
            {
                "metodo": "Efectivo",
                "monto": 112.00
            }
        ],
        "efectivo_recibido": 120.00,
        "paciente_nombre": "Cliente General"
    }


@pytest.fixture
def sample_gasto():
    """Datos de gasto de prueba"""
    return {
        "concepto": f"Gasto de prueba {datetime.now().strftime('%H%M%S')}",
        "monto": 500.00,
        "tipo_gasto": "variable",
        "proveedor_id": None,
        "fecha_vencimiento": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "notas": "Gasto creado para testing"
    }


# ============= Helpers =============

def assert_valid_response(response, expected_status=200):
    """Helper para validar respuestas de API"""
    assert response.status_code == expected_status, \
        f"Expected {expected_status}, got {response.status_code}: {response.text}"


def assert_contains_fields(data, required_fields):
    """Helper para validar que un dict contiene campos requeridos"""
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


# ============= Markers Personalizados =============

def pytest_configure(config):
    """Configurar markers personalizados"""
    config.addinivalue_line(
        "markers", "slow: marca tests lentos que pueden saltarse con -m 'not slow'"
    )
    config.addinivalue_line(
        "markers", "integration: marca tests de integración"
    )
    config.addinivalue_line(
        "markers", "e2e: marca tests end-to-end"
    )
    config.addinivalue_line(
        "markers", "auth: marca tests relacionados con autenticación"
    )
    config.addinivalue_line(
        "markers", "pos: marca tests del Punto de Venta"
    )
    config.addinivalue_line(
        "markers", "inventario: marca tests del módulo de inventario"
    )
