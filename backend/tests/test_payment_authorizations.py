"""
Test suite for Payment Authorization module - NovaVision
Tests the complete authorization workflow:
- SuperAdmin creates authorizations
- Admin executes authorizations
- SuperAdmin cancels/deletes authorizations
- User access restrictions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_CREDS = {"username": "superadmin", "password": "nova2024"}
ADMIN_CREDS = {"username": "admin", "password": "admin2024"}
USER_CREDS = {"username": "usuario", "password": "user2024"}


class TestAuthHelper:
    """Helper class for authentication"""
    
    @staticmethod
    def login(credentials):
        """Login and return token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=credentials)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    @staticmethod
    def get_auth_header(token):
        """Return authorization header"""
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def superadmin_token():
    """Get SuperAdmin token"""
    token = TestAuthHelper.login(SUPERADMIN_CREDS)
    if not token:
        pytest.skip("SuperAdmin login failed")
    return token


@pytest.fixture(scope="module")
def admin_token():
    """Get Admin token"""
    token = TestAuthHelper.login(ADMIN_CREDS)
    if not token:
        pytest.skip("Admin login failed")
    return token


@pytest.fixture(scope="module")
def user_token():
    """Get User token"""
    token = TestAuthHelper.login(USER_CREDS)
    if not token:
        pytest.skip("User login failed")
    return token


@pytest.fixture(scope="module")
def test_bank_account(superadmin_token):
    """Create a test bank account for authorization tests"""
    headers = TestAuthHelper.get_auth_header(superadmin_token)
    
    # Create test bank account
    account_data = {
        "bank_name": "TEST_Banco de Prueba",
        "account_number": "TEST_1234567890",
        "account_alias": "TEST_Cuenta Principal"
    }
    
    response = requests.post(f"{BASE_URL}/api/bank-accounts", json=account_data, headers=headers)
    
    if response.status_code == 201:
        account = response.json()
        yield account
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bank-accounts/{account['id']}", headers=headers)
    else:
        # Try to find existing test account
        response = requests.get(f"{BASE_URL}/api/bank-accounts", headers=headers)
        if response.status_code == 200:
            accounts = response.json().get("data", [])
            test_account = next((a for a in accounts if a.get("account_number", "").startswith("TEST_")), None)
            if test_account:
                yield test_account
            else:
                pytest.skip("Could not create or find test bank account")
        else:
            pytest.skip("Could not access bank accounts")


@pytest.fixture(scope="module")
def test_expense(superadmin_token):
    """Create a test expense for authorization tests"""
    headers = TestAuthHelper.get_auth_header(superadmin_token)
    
    # Create test expense
    expense_data = {
        "name": "TEST_Gasto para Autorización",
        "type": "proveedor",
        "amount": 5000.00,
        "date": "2024-03-01",
        "due_date": "2024-04-01",
        "notes": "Gasto de prueba para autorización"
    }
    
    response = requests.post(f"{BASE_URL}/api/expenses", json=expense_data, headers=headers)
    
    if response.status_code == 200:
        expense = response.json()
        yield expense
        # Cleanup
        requests.delete(f"{BASE_URL}/api/expenses/{expense['id']}", headers=headers)
    else:
        pytest.skip(f"Could not create test expense: {response.text}")


class TestPaymentAuthorizationEndpoints:
    """Test Payment Authorization API endpoints"""
    
    def test_superadmin_can_view_authorizations(self, superadmin_token):
        """SuperAdmin can view payment authorizations list"""
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        response = requests.get(f"{BASE_URL}/api/payment-authorizations", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "pending_count" in data
        assert "executed_count" in data
        print(f"✓ SuperAdmin can view authorizations - Total: {data['total']}, Pending: {data['pending_count']}")
    
    def test_admin_can_view_authorizations(self, admin_token):
        """Admin can view payment authorizations list"""
        headers = TestAuthHelper.get_auth_header(admin_token)
        response = requests.get(f"{BASE_URL}/api/payment-authorizations", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        print(f"✓ Admin can view authorizations - Total: {data['total']}")
    
    def test_user_cannot_view_authorizations(self, user_token):
        """User cannot view payment authorizations (403 Forbidden)"""
        headers = TestAuthHelper.get_auth_header(user_token)
        response = requests.get(f"{BASE_URL}/api/payment-authorizations", headers=headers)
        
        assert response.status_code == 403
        print("✓ User correctly denied access to authorizations")
    
    def test_superadmin_can_view_pending_expenses(self, superadmin_token):
        """SuperAdmin can view expenses pending authorization"""
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        response = requests.get(f"{BASE_URL}/api/expenses-pending-authorization", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        print(f"✓ SuperAdmin can view pending expenses - Total: {data['total']}")
    
    def test_admin_cannot_view_pending_expenses(self, admin_token):
        """Admin cannot view expenses pending authorization (403 Forbidden)"""
        headers = TestAuthHelper.get_auth_header(admin_token)
        response = requests.get(f"{BASE_URL}/api/expenses-pending-authorization", headers=headers)
        
        assert response.status_code == 403
        print("✓ Admin correctly denied access to pending expenses endpoint")
    
    def test_filter_authorizations_by_status(self, superadmin_token):
        """Test filtering authorizations by status"""
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        
        for status in ["pendiente", "ejecutado", "cancelado"]:
            response = requests.get(f"{BASE_URL}/api/payment-authorizations?status={status}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            # All returned items should have the filtered status
            for auth in data.get("data", []):
                assert auth["status"] == status
        
        print("✓ Status filter works correctly for all statuses")


class TestPaymentAuthorizationCRUD:
    """Test Create, Read, Update, Delete operations for Payment Authorizations"""
    
    def test_superadmin_create_authorization(self, superadmin_token, test_expense, test_bank_account):
        """SuperAdmin can create a payment authorization"""
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        
        auth_data = {
            "expense_id": test_expense["id"],
            "bank_account_id": test_bank_account["id"],
            "amount_to_pay": test_expense["remaining_amount"],
            "notes": "TEST_Autorización de prueba"
        }
        
        response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["expense_id"] == test_expense["id"]
        assert data["bank_account_id"] == test_bank_account["id"]
        assert data["amount_to_pay"] == test_expense["remaining_amount"]
        assert data["status"] == "pendiente"
        assert "authorized_by" in data
        assert "authorized_at" in data
        
        print(f"✓ SuperAdmin created authorization - ID: {data['id']}")
        
        # Store for later tests
        pytest.auth_id = data["id"]
        return data
    
    def test_admin_cannot_create_authorization(self, admin_token, test_expense, test_bank_account):
        """Admin cannot create payment authorizations (403 Forbidden)"""
        headers = TestAuthHelper.get_auth_header(admin_token)
        
        auth_data = {
            "expense_id": test_expense["id"],
            "bank_account_id": test_bank_account["id"],
            "amount_to_pay": 100.00,
            "notes": "TEST_Should fail"
        }
        
        response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers)
        
        assert response.status_code == 403
        print("✓ Admin correctly denied from creating authorizations")
    
    def test_get_authorization_by_id(self, superadmin_token):
        """Get a specific authorization by ID"""
        if not hasattr(pytest, 'auth_id'):
            pytest.skip("No authorization created in previous test")
        
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        response = requests.get(f"{BASE_URL}/api/payment-authorizations/{pytest.auth_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pytest.auth_id
        assert "expense_name" in data
        assert "bank_account_alias" in data
        print(f"✓ Retrieved authorization details - Expense: {data.get('expense_name')}")
    
    def test_duplicate_authorization_rejected(self, superadmin_token, test_expense, test_bank_account):
        """Cannot create duplicate pending authorization for same expense"""
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        
        auth_data = {
            "expense_id": test_expense["id"],
            "bank_account_id": test_bank_account["id"],
            "amount_to_pay": 100.00,
            "notes": "TEST_Duplicate"
        }
        
        response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers)
        
        assert response.status_code == 400
        assert "Ya existe una autorización pendiente" in response.json().get("detail", "")
        print("✓ Duplicate authorization correctly rejected")


class TestPaymentAuthorizationExecution:
    """Test authorization execution workflow"""
    
    def test_admin_can_execute_authorization(self, admin_token, superadmin_token, test_expense, test_bank_account):
        """Admin can execute a pending authorization"""
        # First, cancel any existing authorization and create a new one
        headers_super = TestAuthHelper.get_auth_header(superadmin_token)
        headers_admin = TestAuthHelper.get_auth_header(admin_token)
        
        # Cancel existing if any
        if hasattr(pytest, 'auth_id'):
            requests.post(f"{BASE_URL}/api/payment-authorizations/{pytest.auth_id}/cancel", headers=headers_super)
        
        # Create new authorization
        auth_data = {
            "expense_id": test_expense["id"],
            "bank_account_id": test_bank_account["id"],
            "amount_to_pay": 500.00,  # Partial amount
            "notes": "TEST_Para ejecutar"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers_super)
        if create_response.status_code != 200:
            pytest.skip(f"Could not create authorization: {create_response.text}")
        
        auth_id = create_response.json()["id"]
        
        # Admin executes the authorization
        response = requests.post(f"{BASE_URL}/api/payment-authorizations/{auth_id}/execute", headers=headers_admin)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ejecutado"
        assert data["executed_by"] is not None
        assert data["executed_at"] is not None
        
        print(f"✓ Admin executed authorization - Payment created for Q{auth_data['amount_to_pay']}")
        
        # Verify payment was created
        payments_response = requests.get(f"{BASE_URL}/api/payments?expenseId={test_expense['id']}", headers=headers_admin)
        assert payments_response.status_code == 200
        payments = payments_response.json().get("data", [])
        
        # Find the payment created by this authorization
        auth_payment = next((p for p in payments if f"Auth: {auth_id[:8]}" in p.get("reference", "")), None)
        assert auth_payment is not None
        assert auth_payment["amount"] == 500.00
        print(f"✓ Payment record verified - Amount: Q{auth_payment['amount']}")
    
    def test_superadmin_cannot_execute_authorization(self, superadmin_token, test_expense, test_bank_account):
        """SuperAdmin cannot execute authorizations (only Admin can)"""
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        
        # Create new authorization
        auth_data = {
            "expense_id": test_expense["id"],
            "bank_account_id": test_bank_account["id"],
            "amount_to_pay": 100.00,
            "notes": "TEST_SuperAdmin execute test"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers)
        if create_response.status_code != 200:
            pytest.skip(f"Could not create authorization: {create_response.text}")
        
        auth_id = create_response.json()["id"]
        
        # SuperAdmin tries to execute
        response = requests.post(f"{BASE_URL}/api/payment-authorizations/{auth_id}/execute", headers=headers)
        
        # SuperAdmin doesn't have execute_payment_authorizations permission
        assert response.status_code == 403
        print("✓ SuperAdmin correctly denied from executing authorizations")
        
        # Cleanup - cancel the authorization
        requests.post(f"{BASE_URL}/api/payment-authorizations/{auth_id}/cancel", headers=headers)


class TestPaymentAuthorizationCancelDelete:
    """Test cancel and delete operations"""
    
    def test_superadmin_can_cancel_authorization(self, superadmin_token, test_expense, test_bank_account):
        """SuperAdmin can cancel a pending authorization"""
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        
        # Create authorization
        auth_data = {
            "expense_id": test_expense["id"],
            "bank_account_id": test_bank_account["id"],
            "amount_to_pay": 100.00,
            "notes": "TEST_Para cancelar"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers)
        if create_response.status_code != 200:
            pytest.skip(f"Could not create authorization: {create_response.text}")
        
        auth_id = create_response.json()["id"]
        
        # Cancel
        response = requests.post(f"{BASE_URL}/api/payment-authorizations/{auth_id}/cancel", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelado"
        print(f"✓ SuperAdmin cancelled authorization - ID: {auth_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/payment-authorizations/{auth_id}", headers=headers)
    
    def test_admin_cannot_cancel_authorization(self, admin_token, superadmin_token, test_expense, test_bank_account):
        """Admin cannot cancel authorizations (403 Forbidden)"""
        headers_super = TestAuthHelper.get_auth_header(superadmin_token)
        headers_admin = TestAuthHelper.get_auth_header(admin_token)
        
        # Create authorization as SuperAdmin
        auth_data = {
            "expense_id": test_expense["id"],
            "bank_account_id": test_bank_account["id"],
            "amount_to_pay": 100.00,
            "notes": "TEST_Admin cancel test"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers_super)
        if create_response.status_code != 200:
            pytest.skip(f"Could not create authorization: {create_response.text}")
        
        auth_id = create_response.json()["id"]
        
        # Admin tries to cancel
        response = requests.post(f"{BASE_URL}/api/payment-authorizations/{auth_id}/cancel", headers=headers_admin)
        
        assert response.status_code == 403
        print("✓ Admin correctly denied from cancelling authorizations")
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/payment-authorizations/{auth_id}/cancel", headers=headers_super)
        requests.delete(f"{BASE_URL}/api/payment-authorizations/{auth_id}", headers=headers_super)
    
    def test_superadmin_can_delete_pending_authorization(self, superadmin_token, test_expense, test_bank_account):
        """SuperAdmin can delete a pending/cancelled authorization"""
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        
        # Create authorization
        auth_data = {
            "expense_id": test_expense["id"],
            "bank_account_id": test_bank_account["id"],
            "amount_to_pay": 100.00,
            "notes": "TEST_Para eliminar"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers)
        if create_response.status_code != 200:
            pytest.skip(f"Could not create authorization: {create_response.text}")
        
        auth_id = create_response.json()["id"]
        
        # Delete
        response = requests.delete(f"{BASE_URL}/api/payment-authorizations/{auth_id}", headers=headers)
        
        assert response.status_code == 200
        print(f"✓ SuperAdmin deleted authorization - ID: {auth_id}")
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/payment-authorizations/{auth_id}", headers=headers)
        assert get_response.status_code == 404
        print("✓ Authorization confirmed deleted")
    
    def test_cannot_delete_executed_authorization(self, admin_token, superadmin_token, test_expense, test_bank_account):
        """Cannot delete an executed authorization"""
        headers_super = TestAuthHelper.get_auth_header(superadmin_token)
        headers_admin = TestAuthHelper.get_auth_header(admin_token)
        
        # Create and execute authorization
        auth_data = {
            "expense_id": test_expense["id"],
            "bank_account_id": test_bank_account["id"],
            "amount_to_pay": 50.00,
            "notes": "TEST_Executed delete test"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers_super)
        if create_response.status_code != 200:
            pytest.skip(f"Could not create authorization: {create_response.text}")
        
        auth_id = create_response.json()["id"]
        
        # Execute as Admin
        execute_response = requests.post(f"{BASE_URL}/api/payment-authorizations/{auth_id}/execute", headers=headers_admin)
        if execute_response.status_code != 200:
            pytest.skip(f"Could not execute authorization: {execute_response.text}")
        
        # Try to delete executed authorization
        response = requests.delete(f"{BASE_URL}/api/payment-authorizations/{auth_id}", headers=headers_super)
        
        assert response.status_code == 400
        assert "ejecutadas" in response.json().get("detail", "").lower()
        print("✓ Executed authorization correctly protected from deletion")


class TestPaymentAuthorizationValidation:
    """Test validation rules for payment authorizations"""
    
    def test_amount_exceeds_remaining_rejected(self, superadmin_token, test_expense, test_bank_account):
        """Authorization amount cannot exceed expense remaining amount"""
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        
        # Get current remaining amount
        expense_response = requests.get(f"{BASE_URL}/api/expenses/{test_expense['id']}", headers=headers)
        remaining = expense_response.json().get("remaining_amount", 0)
        
        auth_data = {
            "expense_id": test_expense["id"],
            "bank_account_id": test_bank_account["id"],
            "amount_to_pay": remaining + 1000.00,  # Exceeds remaining
            "notes": "TEST_Should fail"
        }
        
        response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers)
        
        assert response.status_code == 400
        assert "excede" in response.json().get("detail", "").lower()
        print("✓ Amount exceeding remaining correctly rejected")
    
    def test_invalid_expense_id_rejected(self, superadmin_token, test_bank_account):
        """Authorization with invalid expense ID is rejected"""
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        
        auth_data = {
            "expense_id": "invalid-expense-id-12345",
            "bank_account_id": test_bank_account["id"],
            "amount_to_pay": 100.00,
            "notes": "TEST_Invalid expense"
        }
        
        response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers)
        
        assert response.status_code == 404
        print("✓ Invalid expense ID correctly rejected")
    
    def test_invalid_bank_account_rejected(self, superadmin_token, test_expense):
        """Authorization with invalid bank account ID is rejected"""
        headers = TestAuthHelper.get_auth_header(superadmin_token)
        
        auth_data = {
            "expense_id": test_expense["id"],
            "bank_account_id": "invalid-bank-account-12345",
            "amount_to_pay": 100.00,
            "notes": "TEST_Invalid bank"
        }
        
        response = requests.post(f"{BASE_URL}/api/payment-authorizations", json=auth_data, headers=headers)
        
        assert response.status_code == 404
        print("✓ Invalid bank account ID correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
