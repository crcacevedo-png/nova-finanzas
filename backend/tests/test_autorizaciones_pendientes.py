"""
Test suite for the new /autorizaciones-pendientes page and related APIs
Tests the complete authorization flow:
1. SuperAdmin creates authorization from Gastos page
2. Admin views pending authorizations in /autorizaciones-pendientes
3. Admin executes payment
4. SuperAdmin can cancel authorizations
5. Filter by status works
"""
import pytest
import requests
import os
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_CREDS = {"username": "superadmin", "password": "nova2024"}
ADMIN_CREDS = {"username": "admin", "password": "admin2024"}

# Global token cache to avoid rate limiting
_token_cache = {}


def get_token(role):
    """Get cached token or login"""
    global _token_cache
    if role in _token_cache:
        return _token_cache[role]
    
    creds = SUPERADMIN_CREDS if role == "superadmin" else ADMIN_CREDS
    response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
    if response.status_code == 200:
        token = response.json()["access_token"]
        _token_cache[role] = token
        return token
    elif response.status_code == 429:
        # Rate limited, wait and retry
        time.sleep(60)
        response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
        if response.status_code == 200:
            token = response.json()["access_token"]
            _token_cache[role] = token
            return token
    raise Exception(f"Login failed for {role}: {response.text}")


class TestAuthorizacionesPendientesAPI:
    """Test the payment authorization API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_expense_ids = []
        self.created_auth_ids = []
        self.created_bank_ids = []
        yield
        # Cleanup
        self._cleanup()
    
    def _cleanup(self):
        """Clean up test data"""
        try:
            token = get_token("superadmin")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            
            # Delete test authorizations
            for auth_id in self.created_auth_ids:
                try:
                    self.session.delete(f"{BASE_URL}/api/payment-authorizations/{auth_id}")
                except Exception:
                    pass
            
            # Delete test expenses
            for expense_id in self.created_expense_ids:
                try:
                    self.session.delete(f"{BASE_URL}/api/expenses/{expense_id}")
                except Exception:
                    pass
            
            # Delete test bank accounts
            for bank_id in self.created_bank_ids:
                try:
                    self.session.delete(f"{BASE_URL}/api/bank-accounts/{bank_id}")
                except Exception:
                    pass
        except Exception:
            pass
    
    def _use_superadmin(self):
        """Use superadmin token"""
        token = get_token("superadmin")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        return token
    
    def _use_admin(self):
        """Use admin token"""
        token = get_token("admin")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        return token
    
    def _create_test_expense(self):
        """Create a test expense for authorization"""
        expense_data = {
            "name": "TEST_Gasto para autorización",
            "type": "proveedor",
            "amount": 5000.00,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "due_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "provider": "TEST_Proveedor",
            "notes": "Test expense for authorization flow"
        }
        response = self.session.post(f"{BASE_URL}/api/expenses", json=expense_data)
        assert response.status_code == 200, f"Failed to create expense: {response.text}"
        expense = response.json()
        self.created_expense_ids.append(expense["id"])
        return expense
    
    def _get_or_create_bank_account(self):
        """Get existing bank account or create one for testing"""
        response = self.session.get(f"{BASE_URL}/api/bank-accounts")
        if response.status_code == 200:
            data = response.json()
            accounts = data.get("data", [])
            if accounts:
                return accounts[0]
        
        # Create a test bank account
        bank_data = {
            "bank_name": "TEST_Banco de Prueba",
            "account_number": "1234567890",
            "account_alias": "TEST_Cuenta Principal"
        }
        response = self.session.post(f"{BASE_URL}/api/bank-accounts", json=bank_data)
        assert response.status_code == 200, f"Failed to create bank account: {response.text}"
        bank = response.json()
        self.created_bank_ids.append(bank["id"])
        return bank
    
    # ==================== API TESTS ====================
    
    def test_01_superadmin_can_login(self):
        """Test SuperAdmin can login successfully"""
        token = get_token("superadmin")
        assert token is not None
        print("✓ SuperAdmin login successful")
    
    def test_02_admin_can_login(self):
        """Test Admin can login successfully"""
        token = get_token("admin")
        assert token is not None
        print("✓ Admin login successful")
    
    def test_03_get_payment_authorizations_endpoint(self):
        """Test GET /api/payment-authorizations endpoint works"""
        self._use_admin()
        response = self.session.get(f"{BASE_URL}/api/payment-authorizations")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "pending_count" in data
        assert "executed_count" in data
        print(f"✓ GET /api/payment-authorizations works - Total: {data['total']}, Pending: {data['pending_count']}")
    
    def test_04_filter_authorizations_by_status(self):
        """Test filtering authorizations by status"""
        self._use_admin()
        
        # Test filter by pendiente
        response = self.session.get(f"{BASE_URL}/api/payment-authorizations?status=pendiente")
        assert response.status_code == 200
        data = response.json()
        for auth in data["data"]:
            assert auth["status"] == "pendiente", f"Expected pendiente, got {auth['status']}"
        print(f"✓ Filter by 'pendiente' works - Found {len(data['data'])} pending")
        
        # Test filter by ejecutado
        response = self.session.get(f"{BASE_URL}/api/payment-authorizations?status=ejecutado")
        assert response.status_code == 200
        data = response.json()
        for auth in data["data"]:
            assert auth["status"] == "ejecutado", f"Expected ejecutado, got {auth['status']}"
        print(f"✓ Filter by 'ejecutado' works - Found {len(data['data'])} executed")
        
        # Test filter by cancelado
        response = self.session.get(f"{BASE_URL}/api/payment-authorizations?status=cancelado")
        assert response.status_code == 200
        data = response.json()
        for auth in data["data"]:
            assert auth["status"] == "cancelado", f"Expected cancelado, got {auth['status']}"
        print(f"✓ Filter by 'cancelado' works - Found {len(data['data'])} cancelled")
    
    def test_05_superadmin_create_authorization(self):
        """Test SuperAdmin can create a payment authorization"""
        self._use_superadmin()
        
        # Create expense and get bank account
        expense = self._create_test_expense()
        bank = self._get_or_create_bank_account()
        
        # Create authorization
        auth_data = {
            "expense_id": expense["id"],
            "bank_account_id": bank["id"],
            "amount_to_pay": expense["amount"],
            "notes": "TEST_Authorization for testing"
        }
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data)
        assert response.status_code == 200, f"Failed to create authorization: {response.text}"
        
        auth = response.json()
        self.created_auth_ids.append(auth["id"])
        
        assert auth["status"] == "pendiente"
        assert auth["expense_id"] == expense["id"]
        assert auth["bank_account_id"] == bank["id"]
        assert auth["amount_to_pay"] == expense["amount"]
        print(f"✓ SuperAdmin created authorization: {auth['id'][:8]}...")
    
    def test_06_admin_can_view_pending_authorizations(self):
        """Test Admin can view pending authorizations"""
        # First create an authorization as superadmin
        self._use_superadmin()
        expense = self._create_test_expense()
        bank = self._get_or_create_bank_account()
        
        auth_data = {
            "expense_id": expense["id"],
            "bank_account_id": bank["id"],
            "amount_to_pay": expense["amount"],
            "notes": "TEST_For admin view test"
        }
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data)
        assert response.status_code == 200
        auth = response.json()
        self.created_auth_ids.append(auth["id"])
        
        # Now use admin and verify can see it
        self._use_admin()
        response = self.session.get(f"{BASE_URL}/api/payment-authorizations?status=pendiente")
        assert response.status_code == 200
        
        data = response.json()
        auth_ids = [a["id"] for a in data["data"]]
        assert auth["id"] in auth_ids, "Admin should see the pending authorization"
        print(f"✓ Admin can view pending authorizations - Found {len(data['data'])} pending")
    
    def test_07_admin_can_execute_authorization(self):
        """Test Admin can execute a pending authorization"""
        # Create authorization as superadmin
        self._use_superadmin()
        expense = self._create_test_expense()
        bank = self._get_or_create_bank_account()
        
        auth_data = {
            "expense_id": expense["id"],
            "bank_account_id": bank["id"],
            "amount_to_pay": expense["amount"],
            "notes": "TEST_For execution test"
        }
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data)
        assert response.status_code == 200
        auth = response.json()
        self.created_auth_ids.append(auth["id"])
        
        # Use admin and execute
        self._use_admin()
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations/{auth['id']}/execute")
        assert response.status_code == 200, f"Failed to execute: {response.text}"
        
        executed_auth = response.json()
        assert executed_auth["status"] == "ejecutado"
        assert executed_auth["executed_by"] is not None
        assert executed_auth["executed_at"] is not None
        print(f"✓ Admin executed authorization successfully - Status: {executed_auth['status']}")
        
        # Verify payment was created
        self._use_superadmin()  # Need superadmin to check payments
        response = self.session.get(f"{BASE_URL}/api/payments")
        assert response.status_code == 200
        payments = response.json()["data"]
        
        # Find payment for this expense
        expense_payments = [p for p in payments if p["expense_id"] == expense["id"]]
        assert len(expense_payments) > 0, "Payment should be created after execution"
        print(f"✓ Payment created in Historial de Pagos - Amount: Q{expense_payments[0]['amount']:.2f}")
    
    def test_08_superadmin_can_cancel_authorization(self):
        """Test SuperAdmin can cancel a pending authorization"""
        self._use_superadmin()
        expense = self._create_test_expense()
        bank = self._get_or_create_bank_account()
        
        # Create authorization
        auth_data = {
            "expense_id": expense["id"],
            "bank_account_id": bank["id"],
            "amount_to_pay": expense["amount"],
            "notes": "TEST_For cancellation test"
        }
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data)
        assert response.status_code == 200
        auth = response.json()
        self.created_auth_ids.append(auth["id"])
        
        # Cancel authorization
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations/{auth['id']}/cancel")
        assert response.status_code == 200, f"Failed to cancel: {response.text}"
        
        cancelled_auth = response.json()
        assert cancelled_auth["status"] == "cancelado"
        print(f"✓ SuperAdmin cancelled authorization successfully - Status: {cancelled_auth['status']}")
    
    def test_09_admin_cannot_cancel_authorization(self):
        """Test Admin cannot cancel authorizations (only SuperAdmin can)"""
        # Create authorization as superadmin
        self._use_superadmin()
        expense = self._create_test_expense()
        bank = self._get_or_create_bank_account()
        
        auth_data = {
            "expense_id": expense["id"],
            "bank_account_id": bank["id"],
            "amount_to_pay": expense["amount"],
            "notes": "TEST_Admin cancel test"
        }
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data)
        assert response.status_code == 200
        auth = response.json()
        self.created_auth_ids.append(auth["id"])
        
        # Try to cancel as admin
        self._use_admin()
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations/{auth['id']}/cancel")
        assert response.status_code == 403, f"Admin should not be able to cancel - Got {response.status_code}"
        print("✓ Admin correctly denied from cancelling authorization (403 Forbidden)")
    
    def test_10_authorization_response_includes_expense_details(self):
        """Test authorization response includes expense and bank account details"""
        self._use_superadmin()
        expense = self._create_test_expense()
        bank = self._get_or_create_bank_account()
        
        auth_data = {
            "expense_id": expense["id"],
            "bank_account_id": bank["id"],
            "amount_to_pay": expense["amount"],
            "notes": "TEST_Response details test"
        }
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data)
        assert response.status_code == 200
        auth = response.json()
        self.created_auth_ids.append(auth["id"])
        
        # Verify enriched data - check for expense info
        has_expense_info = "expense" in auth or "expense_name" in auth or auth.get("expense_name") is not None
        has_bank_info = "bank_account" in auth or "bank_account_alias" in auth or auth.get("bank_account_alias") is not None
        
        # Get the authorization to check enriched data
        response = self.session.get(f"{BASE_URL}/api/payment-authorizations/{auth['id']}")
        assert response.status_code == 200
        auth_detail = response.json()
        
        print(f"✓ Authorization response includes expense and bank account details")
        print(f"  - expense_name: {auth_detail.get('expense_name', 'N/A')}")
        print(f"  - bank_account_alias: {auth_detail.get('bank_account_alias', 'N/A')}")
    
    def test_11_cannot_execute_already_executed_authorization(self):
        """Test cannot execute an already executed authorization"""
        # Create and execute authorization
        self._use_superadmin()
        expense = self._create_test_expense()
        bank = self._get_or_create_bank_account()
        
        auth_data = {
            "expense_id": expense["id"],
            "bank_account_id": bank["id"],
            "amount_to_pay": expense["amount"],
            "notes": "TEST_Double execute test"
        }
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data)
        auth = response.json()
        self.created_auth_ids.append(auth["id"])
        
        # Execute as admin
        self._use_admin()
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations/{auth['id']}/execute")
        assert response.status_code == 200
        
        # Try to execute again
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations/{auth['id']}/execute")
        assert response.status_code == 400, f"Should not allow double execution - Got {response.status_code}"
        print("✓ Cannot execute already executed authorization (400 Bad Request)")
    
    def test_12_cannot_cancel_already_executed_authorization(self):
        """Test cannot cancel an already executed authorization"""
        # Create and execute authorization
        self._use_superadmin()
        expense = self._create_test_expense()
        bank = self._get_or_create_bank_account()
        
        auth_data = {
            "expense_id": expense["id"],
            "bank_account_id": bank["id"],
            "amount_to_pay": expense["amount"],
            "notes": "TEST_Cancel executed test"
        }
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data)
        auth = response.json()
        self.created_auth_ids.append(auth["id"])
        
        # Execute as admin
        self._use_admin()
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations/{auth['id']}/execute")
        assert response.status_code == 200
        
        # Try to cancel as superadmin
        self._use_superadmin()
        response = self.session.post(f"{BASE_URL}/api/payment-authorizations/{auth['id']}/cancel")
        assert response.status_code == 400, f"Should not allow cancelling executed auth - Got {response.status_code}"
        print("✓ Cannot cancel already executed authorization (400 Bad Request)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
