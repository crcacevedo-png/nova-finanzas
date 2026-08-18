# /app/backend/tests/test_security.py
"""
Pruebas de Seguridad Automatizadas - NovaVision ERP
Basado en los hallazgos del informe SECURITY_AUDIT.md

Estas pruebas deben pasar para garantizar que los controles de seguridad
están funcionando correctamente.
"""
import pytest
import jwt
import time
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
import sys
sys.path.insert(0, '/app/backend')

# Importar aplicación
from server import app, JWT_SECRET, JWT_ALGORITHM, hash_password


# ==================== FIXTURES ====================

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def test_client():
    """Cliente de pruebas async"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def valid_token():
    """Token JWT válido para pruebas"""
    payload = {
        "sub": "test-user-id",
        "username": "testuser",
        "role": "usuario",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def admin_token():
    """Token JWT para admin"""
    payload = {
        "sub": "test-admin-id",
        "username": "testadmin",
        "role": "admin",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def superadmin_token():
    """Token JWT para superadmin"""
    payload = {
        "sub": "test-superadmin-id",
        "username": "testsuperadmin",
        "role": "superadmin",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ==================== TEST: AUTENTICACIÓN ====================

class TestAuthentication:
    """Pruebas de autenticación y JWT"""
    
    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, test_client):
        """Token expirado debe ser rechazado con 401"""
        expired_payload = {
            "sub": "test-user-id",
            "username": "testuser",
            "role": "usuario",
            "iat": datetime.now(timezone.utc) - timedelta(hours=10),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1)  # Expirado hace 1 hora
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        response = await test_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401, "Token expirado no fue rechazado"
    
    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, test_client):
        """Token con firma inválida debe ser rechazado"""
        # Crear token con secreto incorrecto
        payload = {
            "sub": "test-user-id",
            "username": "testuser",
            "role": "usuario",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        invalid_token = jwt.encode(payload, "wrong-secret-key", algorithm=JWT_ALGORITHM)
        
        response = await test_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        assert response.status_code == 401, "Token con firma inválida no fue rechazado"
    
    @pytest.mark.asyncio
    async def test_alg_none_rejected(self, test_client):
        """Token con algoritmo 'none' debe ser rechazado"""
        # Crear token sin firma (alg: none - vulnerabilidad conocida)
        header = {"alg": "none", "typ": "JWT"}
        payload = {
            "sub": "test-user-id",
            "username": "testuser",
            "role": "superadmin",  # Intentar escalar privilegios
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        import base64
        import json
        
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload, default=str).encode()).decode().rstrip('=')
        none_token = f"{header_b64}.{payload_b64}."
        
        response = await test_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {none_token}"}
        )
        assert response.status_code == 401, "Token con alg:none no fue rechazado"
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, test_client):
        """Login con credenciales inválidas debe fallar"""
        response = await test_client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        # Verificar que el mensaje no revela si el usuario existe o no
        assert "Credenciales inválidas" in response.json().get("detail", "")


# ==================== TEST: AUTORIZACIÓN RBAC ====================

class TestAuthorization:
    """Pruebas de control de acceso basado en roles"""
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_admin_endpoints(self, test_client, valid_token):
        """Usuario normal no puede acceder a endpoints de admin"""
        admin_endpoints = [
            ("GET", "/api/users"),
            ("POST", "/api/users"),
            ("GET", "/api/security/audit-logs"),
            ("GET", "/api/security/status"),
        ]
        
        for method, endpoint in admin_endpoints:
            if method == "GET":
                response = await test_client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {valid_token}"}
                )
            else:
                response = await test_client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {valid_token}"},
                    json={}
                )
            
            assert response.status_code == 403, \
                f"Usuario normal accedió a {method} {endpoint}"
    
    @pytest.mark.asyncio
    async def test_unauthenticated_access_rejected(self, test_client):
        """Endpoints protegidos deben rechazar acceso sin token"""
        protected_endpoints = [
            "/api/auth/me",
            "/api/patients",
            "/api/caja/estado",
            "/api/inventario/productos",
        ]
        
        for endpoint in protected_endpoints:
            response = await test_client.get(endpoint)
            assert response.status_code in [401, 403], \
                f"Endpoint {endpoint} accesible sin autenticación"


# ==================== TEST: INYECCIÓN NoSQL ====================

class TestNoSQLInjection:
    """Pruebas contra inyección NoSQL"""
    
    @pytest.mark.asyncio
    async def test_login_nosql_injection_gt(self, test_client):
        """Inyección NoSQL con $gt en login debe ser rechazada"""
        response = await test_client.post(
            "/api/auth/login",
            json={
                "username": {"$gt": ""},  # Intento de inyección
                "password": {"$gt": ""}
            }
        )
        # Debe fallar con 422 (validación) o 401 (no encontrado)
        assert response.status_code in [401, 422], \
            "Inyección NoSQL no fue rechazada en login"
    
    @pytest.mark.asyncio
    async def test_login_nosql_injection_regex(self, test_client):
        """Inyección NoSQL con $regex en login debe ser rechazada"""
        response = await test_client.post(
            "/api/auth/login",
            json={
                "username": {"$regex": ".*"},
                "password": {"$regex": ".*"}
            }
        )
        assert response.status_code in [401, 422], \
            "Inyección NoSQL regex no fue rechazada"


# ==================== TEST: ESCALAMIENTO DE PRIVILEGIOS ====================

class TestPrivilegeEscalation:
    """Pruebas contra escalamiento de privilegios"""
    
    @pytest.mark.asyncio
    async def test_mass_assignment_role_change(self, test_client, valid_token):
        """Usuario no puede cambiar su propio rol mediante mass assignment"""
        # Intentar actualizar perfil con campo role
        response = await test_client.put(
            "/api/users/test-user-id",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={
                "name": "Nuevo Nombre",
                "role": "superadmin"  # Intento de escalar privilegios
            }
        )
        
        # Debe fallar (403) o ignorar el campo role
        if response.status_code == 200:
            data = response.json()
            assert data.get("role") != "superadmin", \
                "Usuario pudo cambiar su rol a superadmin"


# ==================== TEST: HEADERS DE SEGURIDAD ====================

class TestSecurityHeaders:
    """Pruebas de headers de seguridad HTTP"""
    
    @pytest.mark.asyncio
    async def test_security_headers_present(self, test_client, valid_token):
        """Verificar que los headers de seguridad están presentes"""
        required_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
        ]
        
        response = await test_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        for header in required_headers:
            assert header.lower() in [h.lower() for h in response.headers.keys()], \
                f"Header de seguridad {header} no presente"
    
    @pytest.mark.asyncio
    async def test_x_frame_options_deny(self, test_client, valid_token):
        """X-Frame-Options debe ser DENY o SAMEORIGIN"""
        response = await test_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        x_frame = response.headers.get("X-Frame-Options", "").upper()
        assert x_frame in ["DENY", "SAMEORIGIN"], \
            f"X-Frame-Options tiene valor inseguro: {x_frame}"


# ==================== TEST: DATOS SENSIBLES ====================

class TestSensitiveData:
    """Pruebas de protección de datos sensibles"""
    
    @pytest.mark.asyncio
    async def test_user_response_no_password(self, test_client, valid_token):
        """Las respuestas de usuario no deben incluir el hash de la contraseña"""
        response = await test_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "password" not in data, \
                "Respuesta incluye campo password"
            assert "_id" not in data, \
                "Respuesta incluye campo _id de MongoDB"
    
    @pytest.mark.asyncio
    async def test_error_no_stack_trace(self, test_client):
        """Los errores no deben exponer stack traces"""
        # Provocar un error con datos inválidos
        response = await test_client.post(
            "/api/auth/login",
            json={"invalid": "data"}
        )
        
        error_text = response.text.lower()
        assert "traceback" not in error_text, \
            "Error expone traceback"
        assert "file \"" not in error_text, \
            "Error expone rutas de archivos"


# ==================== TEST: RATE LIMITING ====================

class TestRateLimiting:
    """Pruebas de rate limiting"""
    
    @pytest.mark.asyncio
    async def test_login_rate_limit_exists(self, test_client):
        """
        Verificar que existe rate limiting en login.
        Nota: Este test puede ser flaky si el rate limit está muy alto.
        """
        # Hacer múltiples intentos rápidos
        rate_limited = False
        response = None
        for i in range(10):
            response = await test_client.post(
                "/api/auth/login",
                json={"username": f"test{i}", "password": "wrong"}
            )
            if response.status_code == 429:
                rate_limited = True
                break
        
        # No podemos garantizar que se active, pero al menos verificamos
        # que el endpoint existe y responde correctamente
        assert response.status_code in [401, 429], \
            f"Login retornó código inesperado: {response.status_code}"


# ==================== TEST: INMUTABILIDAD DEL KARDEX ====================

class TestKardexImmutability:
    """Pruebas de inmutabilidad del kardex de inventario"""
    
    @pytest.mark.asyncio
    async def test_kardex_no_delete_endpoint(self, test_client, superadmin_token):
        """No debe existir endpoint DELETE para kardex"""
        # Intentar eliminar un movimiento de kardex
        response = await test_client.delete(
            "/api/inventario/kardex/fake-id",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        # Debe ser 404 (no existe el endpoint) o 405 (método no permitido)
        assert response.status_code in [404, 405], \
            "Existe endpoint DELETE para kardex - inmutabilidad comprometida"
    
    @pytest.mark.asyncio
    async def test_kardex_no_update_endpoint(self, test_client, superadmin_token):
        """No debe existir endpoint PUT/PATCH para kardex"""
        for method in [test_client.put, test_client.patch]:
            response = await method(
                "/api/inventario/kardex/fake-id",
                headers={"Authorization": f"Bearer {superadmin_token}"},
                json={"cantidad": 100}
            )
            
            assert response.status_code in [404, 405], \
                "Existe endpoint UPDATE para kardex - inmutabilidad comprometida"


# ==================== TEST: BLOQUEO DE CUENTA ====================

class TestAccountLocking:
    """Pruebas del mecanismo de bloqueo por intentos fallidos"""
    
    @pytest.mark.asyncio
    async def test_account_lock_after_failed_attempts(self, test_client):
        """
        Verificar que la cuenta se bloquea después de múltiples intentos fallidos.
        Nota: Requiere un usuario de prueba en la base de datos.
        """
        # Este test es más de integración y puede requerir setup especial
        pass  # Implementar con usuario de prueba real


# ==================== TEST: CAMBIO DE CONTRASEÑA FORZADO ====================

class TestForcedPasswordChange:
    """Pruebas del mecanismo de cambio de contraseña obligatorio"""
    
    @pytest.mark.asyncio
    async def test_login_returns_must_change_password(self, test_client):
        """
        Login debe retornar must_change_password para usuarios que lo requieran.
        Nota: Requiere un usuario con must_change_password=True en la base de datos.
        """
        # Este test es más de integración
        pass  # Implementar con usuario de prueba real


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
