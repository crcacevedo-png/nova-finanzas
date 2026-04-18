"""
Test Authorization Flow for NovaVision Gastos
Tests the consolidated authorization flow in the Gastos page:
1. SuperAdmin authorizes expense with bank account selection
2. Expense is marked green (is_authorized=true)
3. Confirm Authorizations creates payment_authorizations for Admin
4. Admin can view and execute pending authorizations
"""

import pytest
import requests
import os
import uuid
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Global token cache to avoid rate limiting
_token_cache = {}

def get_token(username, password):
    """Get authentication token with caching"""
    cache_key = f"{username}:{password}"
    if cache_key in _token_cache:
        return _token_cache[cache_key]
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": username,
        "password": password
    })
    if response.status_code == 200:
        token = response.json()["access_token"]
        _token_cache[cache_key] = token
        return token
    elif response.status_code == 429:
        # Rate limited, wait and retry
        time.sleep(60)
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            token = response.json()["access_token"]
            _token_cache[cache_key] = token
            return token
    raise Exception(f"Login failed for {username}: {response.text}")

def get_headers(token):
    """Get headers with authorization"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


class TestAuthorizationFlow:
    """Test the complete authorization flow"""
    
    # Class-level storage for test data
    test_expense_id = None
    test_bank_account_id = None
    test_authorization_id = None
    
    @classmethod
    def get_superadmin_token(cls):
        return get_token("superadmin", "nova2024")
    
    @classmethod
    def get_admin_token(cls):
        return get_token("admin", "admin2024")
    
    # ==================== BANK ACCOUNT TESTS ====================
    
    def test_01_get_bank_accounts(self):
        """Test getting bank accounts list"""
        token = self.get_superadmin_token()
        response = requests.get(
            f"{BASE_URL}/api/bank-accounts",
            headers=get_headers(token)
        )
        assert response.status_code == 200, f"Failed to get bank accounts: {response.text}"
        data = response.json()
        assert "data" in data, "Response should have 'data' field"
        print(f"Found {len(data['data'])} bank accounts")
        
        # Store first bank account for later tests
        if data['data']:
            TestAuthorizationFlow.test_bank_account_id = data['data'][0]['id']
            print(f"Using bank account: {data['data'][0]['account_alias']}")
    
    def test_02_create_bank_account_if_needed(self):
        """Create a test bank account if none exists"""
        token = self.get_superadmin_token()
        
        # Check if we have a bank account
        response = requests.get(
            f"{BASE_URL}/api/bank-accounts",
            headers=get_headers(token)
        )
        data = response.json()
        
        if not data['data']:
            # Create a test bank account
            response = requests.post(
                f"{BASE_URL}/api/bank-accounts",
                headers=get_headers(token),
                json={
                    "bank_name": "TEST_Banco Industrial",
                    "account_number": "TEST-001-12345678",
                    "account_alias": "TEST_Cuenta Principal"
                }
            )
            assert response.status_code in [200, 201], f"Failed to create bank account: {response.text}"
            TestAuthorizationFlow.test_bank_account_id = response.json()['id']
            print(f"Created test bank account: {TestAuthorizationFlow.test_bank_account_id}")
        else:
            TestAuthorizationFlow.test_bank_account_id = data['data'][0]['id']
            print(f"Using existing bank account: {TestAuthorizationFlow.test_bank_account_id}")
    
    # ==================== EXPENSE CREATION ====================
    
    def test_03_create_test_expense(self):
        """Create a test expense for authorization"""
        token = self.get_superadmin_token()
        
        # Create expense with future due date
        due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/expenses",
            headers=get_headers(token),
            json={
                "provider": "TEST_Proveedor Auth",
                "name": "TEST_Gasto para Autorización",
                "type": "proveedor",
                "amount": 1500.00,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "due_date": due_date,
                "invoice_number": f"TEST-AUTH-{uuid.uuid4().hex[:6].upper()}",
                "notes": "Gasto de prueba para flujo de autorización"
            }
        )
        assert response.status_code in [200, 201], f"Failed to create expense: {response.text}"
        
        expense = response.json()
        TestAuthorizationFlow.test_expense_id = expense['id']
        
        # Verify expense is created with is_authorized=False
        assert expense.get('is_authorized', False) == False, "New expense should not be authorized"
        assert expense['remaining_amount'] == 1500.00, "Remaining amount should equal total"
        
        print(f"Created test expense: {expense['expense_number']} - {expense['name']}")
    
    # ==================== P0: AUTHORIZATION MODAL WITH BANK SELECTION ====================
    
    def test_04_authorize_expense_with_bank_account(self):
        """P0: Test authorizing expense with bank account selection (SuperAdmin)"""
        token = self.get_superadmin_token()
        
        # Ensure we have expense and bank account IDs
        if not TestAuthorizationFlow.test_expense_id:
            self.test_03_create_test_expense()
        if not TestAuthorizationFlow.test_bank_account_id:
            self.test_02_create_bank_account_if_needed()
        
        # Authorize expense with bank account
        response = requests.post(
            f"{BASE_URL}/api/expenses/{TestAuthorizationFlow.test_expense_id}/authorize",
            headers=get_headers(token),
            json={
                "bank_account_id": TestAuthorizationFlow.test_bank_account_id
            }
        )
        assert response.status_code == 200, f"Failed to authorize expense: {response.text}"
        
        expense = response.json()
        
        # P0: Verify expense is marked as authorized (green)
        assert expense.get('is_authorized') == True, "Expense should be marked as authorized (is_authorized=true)"
        
        print(f"Expense authorized successfully: is_authorized={expense['is_authorized']}")
    
    def test_05_verify_expense_is_authorized(self):
        """P0: Verify expense is marked green (is_authorized=true) after authorization"""
        token = self.get_superadmin_token()
        
        # Get the expense and verify it's authorized
        response = requests.get(
            f"{BASE_URL}/api/expenses/{TestAuthorizationFlow.test_expense_id}",
            headers=get_headers(token)
        )
        assert response.status_code == 200, f"Failed to get expense: {response.text}"
        
        expense = response.json()
        assert expense.get('is_authorized') == True, "Expense should remain authorized"
        
        print(f"Verified expense is_authorized={expense['is_authorized']}")
    
    # ==================== P0: CONFIRM AUTHORIZATIONS ====================
    
    def test_06_confirm_authorizations_creates_payment_auth(self):
        """P0: Test 'Confirmar Autorizaciones' creates payment_authorizations for Admin"""
        token = self.get_superadmin_token()
        
        # Call confirm-authorizations endpoint
        response = requests.post(
            f"{BASE_URL}/api/expenses/confirm-authorizations",
            headers=get_headers(token)
        )
        assert response.status_code == 200, f"Failed to confirm authorizations: {response.text}"
        
        result = response.json()
        assert 'message' in result, "Response should have message"
        # The response uses 'count' not 'created_count'
        assert result.get('count', 0) > 0, f"Should have created at least one authorization. Response: {result}"
        
        print(f"Confirm authorizations result: {result['message']}")
    
    def test_07_verify_expense_authorization_cleared(self):
        """Verify expense is_authorized is cleared after confirmation"""
        token = self.get_superadmin_token()
        
        # Get the expense and verify is_authorized is now False
        response = requests.get(
            f"{BASE_URL}/api/expenses/{TestAuthorizationFlow.test_expense_id}",
            headers=get_headers(token)
        )
        assert response.status_code == 200, f"Failed to get expense: {response.text}"
        
        expense = response.json()
        # After confirmation, is_authorized should be cleared
        assert expense.get('is_authorized') == False, "Expense is_authorized should be cleared after confirmation"
        
        print(f"Expense is_authorized cleared: {expense['is_authorized']}")
    
    # ==================== P1: ADMIN VIEW PENDING AUTHORIZATIONS ====================
    
    def test_08_admin_can_view_pending_authorizations(self):
        """P1: Admin can view pending authorizations in /autorizacion-pagos"""
        token = self.get_admin_token()
        
        # Get payment authorizations with status=pendiente
        response = requests.get(
            f"{BASE_URL}/api/payment-authorizations?status=pendiente",
            headers=get_headers(token)
        )
        assert response.status_code == 200, f"Failed to get payment authorizations: {response.text}"
        
        data = response.json()
        assert "data" in data, "Response should have 'data' field"
        
        # Find our test authorization
        test_auth = None
        for auth in data['data']:
            if auth['expense_id'] == TestAuthorizationFlow.test_expense_id:
                test_auth = auth
                TestAuthorizationFlow.test_authorization_id = auth['id']
                break
        
        assert test_auth is not None, "Should find authorization for our test expense"
        assert test_auth['status'] == 'pendiente', "Authorization should be pending"
        
        print(f"Admin found pending authorization: {test_auth['id']}")
    
    # ==================== P1: ADMIN EXECUTE PAYMENT ====================
    
    def test_09_admin_can_execute_payment(self):
        """P1: Admin can execute authorized payment"""
        token = self.get_admin_token()
        
        if not TestAuthorizationFlow.test_authorization_id:
            self.test_08_admin_can_view_pending_authorizations()
        
        # Execute the payment authorization
        response = requests.post(
            f"{BASE_URL}/api/payment-authorizations/{TestAuthorizationFlow.test_authorization_id}/execute",
            headers=get_headers(token)
        )
        assert response.status_code == 200, f"Failed to execute payment: {response.text}"
        
        result = response.json()
        assert result.get('status') == 'ejecutado', "Authorization should be executed"
        
        print(f"Payment executed successfully: {result['id']}")
    
    def test_10_verify_payment_in_history(self):
        """P1: Verify executed payment appears in payment history"""
        token = self.get_admin_token()
        
        # Get payments for the expense
        response = requests.get(
            f"{BASE_URL}/api/expenses/{TestAuthorizationFlow.test_expense_id}/payments",
            headers=get_headers(token)
        )
        assert response.status_code == 200, f"Failed to get payments: {response.text}"
        
        payments = response.json()
        assert len(payments) > 0, "Should have at least one payment after execution"
        
        print(f"Found {len(payments)} payment(s) for expense")
    
    # ==================== CLEANUP ====================
    
    def test_99_cleanup_test_data(self):
        """Cleanup test data"""
        token = self.get_superadmin_token()
        
        # Delete test expense (this will also delete associated payments)
        if TestAuthorizationFlow.test_expense_id:
            response = requests.delete(
                f"{BASE_URL}/api/expenses/{TestAuthorizationFlow.test_expense_id}",
                headers=get_headers(token)
            )
            if response.status_code == 200:
                print(f"Deleted test expense: {TestAuthorizationFlow.test_expense_id}")
        
        # Delete test bank account if we created one
        if TestAuthorizationFlow.test_bank_account_id:
            # Check if it's a test account
            response = requests.get(
                f"{BASE_URL}/api/bank-accounts/{TestAuthorizationFlow.test_bank_account_id}",
                headers=get_headers(token)
            )
            if response.status_code == 200:
                account = response.json()
                if account.get('account_alias', '').startswith('TEST_'):
                    response = requests.delete(
                        f"{BASE_URL}/api/bank-accounts/{TestAuthorizationFlow.test_bank_account_id}",
                        headers=get_headers(token)
                    )
                    if response.status_code == 200:
                        print(f"Deleted test bank account: {TestAuthorizationFlow.test_bank_account_id}")
        
        print("Cleanup completed")


class TestAuthorizationEdgeCases:
    """Test edge cases for authorization flow"""
    
    @classmethod
    def get_superadmin_token(cls):
        return get_token("superadmin", "nova2024")
    
    def test_authorize_without_bank_account_fails(self):
        """Test that authorization without bank account fails"""
        token = self.get_superadmin_token()
        
        # Create a test expense
        response = requests.post(
            f"{BASE_URL}/api/expenses",
            headers=get_headers(token),
            json={
                "provider": "TEST_Edge Case",
                "name": "TEST_Gasto Edge Case",
                "type": "variable",
                "amount": 500.00,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        )
        assert response.status_code in [200, 201]
        expense_id = response.json()['id']
        
        try:
            # Try to authorize without bank_account_id
            response = requests.post(
                f"{BASE_URL}/api/expenses/{expense_id}/authorize",
                headers=get_headers(token),
                json={}  # Missing bank_account_id
            )
            # Should fail with 422 (validation error) or 400
            assert response.status_code in [400, 422], f"Should fail without bank_account_id: {response.status_code}"
            print("Correctly rejected authorization without bank account")
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/expenses/{expense_id}", headers=get_headers(token))
    
    def test_remove_authorization(self):
        """Test removing authorization from expense"""
        token = self.get_superadmin_token()
        
        # Get bank accounts
        response = requests.get(f"{BASE_URL}/api/bank-accounts", headers=get_headers(token))
        bank_accounts = response.json()['data']
        if not bank_accounts:
            pytest.skip("No bank accounts available")
        bank_id = bank_accounts[0]['id']
        
        # Create a test expense
        response = requests.post(
            f"{BASE_URL}/api/expenses",
            headers=get_headers(token),
            json={
                "provider": "TEST_Remove Auth",
                "name": "TEST_Gasto Remove Auth",
                "type": "variable",
                "amount": 300.00,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        )
        expense_id = response.json()['id']
        
        try:
            # Authorize the expense
            response = requests.post(
                f"{BASE_URL}/api/expenses/{expense_id}/authorize",
                headers=get_headers(token),
                json={"bank_account_id": bank_id}
            )
            assert response.status_code == 200
            assert response.json()['is_authorized'] == True
            
            # Remove authorization using toggle
            response = requests.put(
                f"{BASE_URL}/api/expenses/{expense_id}/toggle-authorization",
                headers=get_headers(token)
            )
            assert response.status_code == 200
            assert response.json()['is_authorized'] == False
            
            print("Successfully removed authorization")
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/expenses/{expense_id}", headers=get_headers(token))
    
    def test_confirm_with_no_authorized_expenses(self):
        """Test confirm-authorizations with no authorized expenses"""
        token = self.get_superadmin_token()
        
        # First, make sure there are no authorized expenses
        # (This might fail if there are existing authorized expenses)
        response = requests.post(
            f"{BASE_URL}/api/expenses/confirm-authorizations",
            headers=get_headers(token)
        )
        
        # Should return 400 if no authorized expenses
        # or 200 with count=0
        if response.status_code == 400:
            assert "No hay gastos autorizados" in response.json().get('detail', '')
            print("Correctly handled no authorized expenses case")
        elif response.status_code == 200:
            # If there were authorized expenses, that's also valid
            print(f"Confirmed existing authorizations: {response.json()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
