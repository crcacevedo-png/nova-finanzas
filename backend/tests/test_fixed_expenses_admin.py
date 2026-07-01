"""
Test Fixed Expenses Admin Permissions
Tests that admin user can create, view, edit, and delete fixed expenses
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://novavision-finanzas.preview.emergentagent.com')

class TestFixedExpensesAdminPermissions:
    """Test admin permissions for fixed expenses module"""
    
    admin_token = None
    superadmin_token = None
    test_supplier_id = None
    test_fixed_expense_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        pass
    
    def test_01_admin_login(self):
        """Test admin login with credentials from test_credentials.md"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "Admin2024Nuevo!"
        })
        print(f"Admin login response: {response.status_code}")
        print(f"Admin login body: {response.text[:500]}")
        
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        TestFixedExpensesAdminPermissions.admin_token = data["access_token"]
        print(f"Admin token obtained: {TestFixedExpensesAdminPermissions.admin_token[:50]}...")
    
    def test_02_superadmin_login(self):
        """Test superadmin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "superadmin",
            "password": "nova2024"
        })
        print(f"SuperAdmin login response: {response.status_code}")
        
        assert response.status_code == 200, f"SuperAdmin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        TestFixedExpensesAdminPermissions.superadmin_token = data["access_token"]
        print(f"SuperAdmin token obtained")
    
    def test_03_admin_get_suppliers(self):
        """Test admin can get suppliers list"""
        headers = {"Authorization": f"Bearer {TestFixedExpensesAdminPermissions.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/suppliers", headers=headers)
        print(f"Get suppliers response: {response.status_code}")
        print(f"Suppliers: {response.text[:500]}")
        
        assert response.status_code == 200, f"Failed to get suppliers: {response.text}"
        data = response.json()
        
        # Store first supplier ID for testing
        if data.get("data") and len(data["data"]) > 0:
            TestFixedExpensesAdminPermissions.test_supplier_id = data["data"][0]["id"]
            print(f"Using supplier ID: {TestFixedExpensesAdminPermissions.test_supplier_id}")
        else:
            print("No suppliers found, will create one")
    
    def test_04_admin_create_supplier_if_needed(self):
        """Create a supplier if none exists"""
        if TestFixedExpensesAdminPermissions.test_supplier_id:
            print("Supplier already exists, skipping creation")
            return
        
        headers = {"Authorization": f"Bearer {TestFixedExpensesAdminPermissions.admin_token}"}
        response = requests.post(f"{BASE_URL}/api/suppliers", headers=headers, json={
            "name": "TEST_Proveedor_Admin",
            "contact_name": "Test Contact",
            "phone": "12345678"
        })
        print(f"Create supplier response: {response.status_code}")
        print(f"Create supplier body: {response.text}")
        
        assert response.status_code in [200, 201], f"Failed to create supplier: {response.text}"
        data = response.json()
        TestFixedExpensesAdminPermissions.test_supplier_id = data["id"]
        print(f"Created supplier ID: {TestFixedExpensesAdminPermissions.test_supplier_id}")
    
    def test_05_admin_get_fixed_expenses(self):
        """Test admin can view fixed expenses list"""
        headers = {"Authorization": f"Bearer {TestFixedExpensesAdminPermissions.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/fixed-expenses", headers=headers)
        print(f"Get fixed expenses response: {response.status_code}")
        print(f"Fixed expenses: {response.text[:500]}")
        
        assert response.status_code == 200, f"Admin cannot view fixed expenses: {response.text}"
        data = response.json()
        assert "data" in data
        assert "total" in data
        print(f"Admin can view {data['total']} fixed expenses")
    
    def test_06_admin_create_fixed_expense(self):
        """Test admin can create a fixed expense - THIS IS THE MAIN TEST"""
        assert TestFixedExpensesAdminPermissions.test_supplier_id, "No supplier ID available"
        
        headers = {"Authorization": f"Bearer {TestFixedExpensesAdminPermissions.admin_token}"}
        payload = {
            "supplier_id": TestFixedExpensesAdminPermissions.test_supplier_id,
            "expense_name": "TEST_Gasto_Fijo_Admin",
            "amount": 1500.00,
            "day_of_month": 15,
            "duration_type": "ilimitado",
            "end_date": None
        }
        print(f"Creating fixed expense with payload: {payload}")
        
        response = requests.post(f"{BASE_URL}/api/fixed-expenses", headers=headers, json=payload)
        print(f"Create fixed expense response: {response.status_code}")
        print(f"Create fixed expense body: {response.text}")
        
        assert response.status_code in [200, 201], f"Admin cannot create fixed expense: {response.text}"
        data = response.json()
        assert "id" in data
        TestFixedExpensesAdminPermissions.test_fixed_expense_id = data["id"]
        print(f"Admin successfully created fixed expense ID: {TestFixedExpensesAdminPermissions.test_fixed_expense_id}")
    
    def test_07_admin_update_fixed_expense(self):
        """Test admin can update a fixed expense"""
        assert TestFixedExpensesAdminPermissions.test_fixed_expense_id, "No fixed expense ID available"
        
        headers = {"Authorization": f"Bearer {TestFixedExpensesAdminPermissions.admin_token}"}
        payload = {
            "expense_name": "TEST_Gasto_Fijo_Admin_Updated",
            "amount": 2000.00
        }
        
        response = requests.put(
            f"{BASE_URL}/api/fixed-expenses/{TestFixedExpensesAdminPermissions.test_fixed_expense_id}",
            headers=headers,
            json=payload
        )
        print(f"Update fixed expense response: {response.status_code}")
        print(f"Update fixed expense body: {response.text}")
        
        assert response.status_code == 200, f"Admin cannot update fixed expense: {response.text}"
        data = response.json()
        assert data["expense_name"] == "TEST_Gasto_Fijo_Admin_Updated"
        assert data["amount"] == 2000.00
        print("Admin successfully updated fixed expense")
    
    def test_08_admin_delete_fixed_expense(self):
        """Test admin can delete a fixed expense"""
        assert TestFixedExpensesAdminPermissions.test_fixed_expense_id, "No fixed expense ID available"
        
        headers = {"Authorization": f"Bearer {TestFixedExpensesAdminPermissions.admin_token}"}
        
        response = requests.delete(
            f"{BASE_URL}/api/fixed-expenses/{TestFixedExpensesAdminPermissions.test_fixed_expense_id}",
            headers=headers
        )
        print(f"Delete fixed expense response: {response.status_code}")
        print(f"Delete fixed expense body: {response.text}")
        
        assert response.status_code == 200, f"Admin cannot delete fixed expense: {response.text}"
        print("Admin successfully deleted fixed expense")
    
    def test_09_verify_deletion(self):
        """Verify the fixed expense was deleted (soft delete)"""
        headers = {"Authorization": f"Bearer {TestFixedExpensesAdminPermissions.admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/fixed-expenses/{TestFixedExpensesAdminPermissions.test_fixed_expense_id}",
            headers=headers
        )
        print(f"Get deleted fixed expense response: {response.status_code}")
        
        # Should return 404 since it's soft deleted
        assert response.status_code == 404, f"Fixed expense should be deleted: {response.text}"
        print("Fixed expense correctly deleted (soft delete)")
    
    def test_10_cleanup_test_supplier(self):
        """Cleanup test supplier if we created one"""
        if not TestFixedExpensesAdminPermissions.test_supplier_id:
            print("No test supplier to cleanup")
            return
        
        # Check if it's a test supplier we created
        headers = {"Authorization": f"Bearer {TestFixedExpensesAdminPermissions.superadmin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/suppliers/{TestFixedExpensesAdminPermissions.test_supplier_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("name", "").startswith("TEST_"):
                # Delete test supplier
                delete_response = requests.delete(
                    f"{BASE_URL}/api/suppliers/{TestFixedExpensesAdminPermissions.test_supplier_id}",
                    headers=headers
                )
                print(f"Cleanup test supplier: {delete_response.status_code}")
        
        print("Cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
