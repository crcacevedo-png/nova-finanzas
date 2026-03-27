#!/usr/bin/env python3
"""
NovaVision Permission System Tests
Tests role-based permissions with seed users: superadmin, admin, usuario
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class PermissionTester:
    def __init__(self, base_url: str = "https://novavision-finanzas.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}  # Store tokens for each user
        self.users = {}   # Store user data for each role
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Seed user credentials
        self.seed_users = {
            "superadmin": {"email": "superadmin@novavision.gt", "password": "nova2024"},
            "admin": {"email": "admin@novavision.gt", "password": "admin2024"},
            "usuario": {"email": "usuario@novavision.gt", "password": "user2024"}
        }

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def make_request(self, method: str, endpoint: str, role: str = None, data: Optional[Dict] = None, 
                    expected_status: int = 200) -> tuple[bool, Dict]:
        """Make HTTP request with role-specific token"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if role and role in self.tokens:
            headers['Authorization'] = f'Bearer {self.tokens[role]}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}

            if not success:
                response_data["expected_status"] = expected_status
                response_data["actual_status"] = response.status_code

            return success, response_data

        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}

    def test_login_all_users(self) -> bool:
        """Test login for all seed users and verify permissions"""
        all_success = True
        
        for role, credentials in self.seed_users.items():
            print(f"\n🔐 Testing login for {role}...")
            
            success, response = self.make_request('POST', 'auth/login', data=credentials)
            
            if success:
                self.tokens[role] = response.get('access_token')
                user_data = response.get('user', {})
                self.users[role] = user_data
                
                # Verify role is correct
                actual_role = user_data.get('role')
                role_correct = actual_role == role
                
                # Verify permissions are included
                permissions = user_data.get('permissions', {})
                has_permissions = len(permissions) > 0
                
                self.log_test(f"Login {role}", success and role_correct and has_permissions, 
                             f"Role: {actual_role}, Permissions: {len(permissions)} items")
                
                if not (role_correct and has_permissions):
                    all_success = False
            else:
                self.log_test(f"Login {role}", False, str(response))
                all_success = False
        
        return all_success

    def test_permissions_in_response(self) -> bool:
        """Test that permissions are correctly returned in login response"""
        all_success = True
        
        expected_permissions = {
            "superadmin": ["view_expenses", "create_expenses", "edit_expenses", "delete_expenses", 
                          "register_payments", "manage_users", "view_user_management"],
            "admin": ["view_expenses", "create_expenses", "edit_expenses", "register_payments"],
            "usuario": ["view_expenses"]
        }
        
        for role, expected_perms in expected_permissions.items():
            if role not in self.users:
                continue
                
            user_permissions = self.users[role].get('permissions', {})
            
            # Check expected permissions are True
            missing_perms = []
            for perm in expected_perms:
                if not user_permissions.get(perm, False):
                    missing_perms.append(perm)
            
            # Check forbidden permissions are False
            forbidden_perms = []
            if role == "admin":
                if user_permissions.get('delete_expenses', False):
                    forbidden_perms.append('delete_expenses')
                if user_permissions.get('manage_users', False):
                    forbidden_perms.append('manage_users')
            elif role == "usuario":
                forbidden = ['create_expenses', 'edit_expenses', 'delete_expenses', 
                           'register_payments', 'manage_users']
                for perm in forbidden:
                    if user_permissions.get(perm, False):
                        forbidden_perms.append(perm)
            
            success = len(missing_perms) == 0 and len(forbidden_perms) == 0
            details = ""
            if missing_perms:
                details += f"Missing: {missing_perms} "
            if forbidden_perms:
                details += f"Forbidden but granted: {forbidden_perms}"
            
            self.log_test(f"Permissions for {role}", success, details)
            if not success:
                all_success = False
        
        return all_success

    def test_expense_creation_permissions(self) -> Dict[str, str]:
        """Test expense creation based on role permissions"""
        expense_data = {
            "concepto": "Test Expense - Permission Check",
            "monto": 100.0,
            "fecha": datetime.now().strftime('%Y-%m-%d'),
            "categoria": "gastos_fijos",
            "estado": "pendiente"
        }
        
        created_expenses = {}
        
        # SuperAdmin should be able to create
        success, response = self.make_request('POST', 'expenses', 'superadmin', expense_data, 200)
        if success:
            created_expenses['superadmin'] = response.get('id')
        self.log_test("SuperAdmin can create expenses", success, str(response) if not success else "")
        
        # Admin should be able to create
        success, response = self.make_request('POST', 'expenses', 'admin', expense_data, 200)
        if success:
            created_expenses['admin'] = response.get('id')
        self.log_test("Admin can create expenses", success, str(response) if not success else "")
        
        # Usuario should NOT be able to create (403 Forbidden)
        success, response = self.make_request('POST', 'expenses', 'usuario', expense_data, 403)
        self.log_test("Usuario cannot create expenses", success, 
                     f"Expected 403, got {response.get('actual_status')}" if not success else "")
        
        return created_expenses

    def test_expense_edit_permissions(self, expense_ids: Dict[str, str]) -> bool:
        """Test expense editing based on role permissions"""
        if not expense_ids:
            return False
            
        update_data = {"concepto": "Updated Test Expense", "monto": 150.0}
        all_success = True
        
        # Use superadmin's expense for testing
        expense_id = expense_ids.get('superadmin')
        if not expense_id:
            return False
        
        # SuperAdmin should be able to edit
        success, response = self.make_request('PUT', f'expenses/{expense_id}', 'superadmin', update_data)
        self.log_test("SuperAdmin can edit expenses", success, str(response) if not success else "")
        if not success:
            all_success = False
        
        # Admin should be able to edit
        success, response = self.make_request('PUT', f'expenses/{expense_id}', 'admin', update_data)
        self.log_test("Admin can edit expenses", success, str(response) if not success else "")
        if not success:
            all_success = False
        
        # Usuario should NOT be able to edit (403 Forbidden)
        success, response = self.make_request('PUT', f'expenses/{expense_id}', 'usuario', update_data, 403)
        self.log_test("Usuario cannot edit expenses", success, 
                     f"Expected 403, got {response.get('actual_status')}" if not success else "")
        if not success:
            all_success = False
        
        return all_success

    def test_expense_delete_permissions(self, expense_ids: Dict[str, str]) -> bool:
        """Test expense deletion based on role permissions"""
        all_success = True
        
        # Admin should NOT be able to delete (403 Forbidden)
        if 'admin' in expense_ids:
            success, response = self.make_request('DELETE', f'expenses/{expense_ids["admin"]}', 'admin', expected_status=403)
            self.log_test("Admin cannot delete expenses", success, 
                         f"Expected 403, got {response.get('actual_status')}" if not success else "")
            if not success:
                all_success = False
        
        # Usuario should NOT be able to delete (403 Forbidden)
        if 'superadmin' in expense_ids:
            success, response = self.make_request('DELETE', f'expenses/{expense_ids["superadmin"]}', 'usuario', expected_status=403)
            self.log_test("Usuario cannot delete expenses", success, 
                         f"Expected 403, got {response.get('actual_status')}" if not success else "")
            if not success:
                all_success = False
        
        # SuperAdmin should be able to delete
        for role, expense_id in expense_ids.items():
            success, response = self.make_request('DELETE', f'expenses/{expense_id}', 'superadmin')
            self.log_test(f"SuperAdmin can delete {role}'s expense", success, str(response) if not success else "")
            if not success:
                all_success = False
        
        return all_success

    def test_mark_as_paid_permissions(self) -> bool:
        """Test mark expense as paid functionality"""
        # Create a test expense as superadmin
        expense_data = {
            "concepto": "Test Payment Expense",
            "monto": 200.0,
            "fecha": datetime.now().strftime('%Y-%m-%d'),
            "categoria": "gastos_fijos",
            "estado": "pendiente"
        }
        
        success, response = self.make_request('POST', 'expenses', 'superadmin', expense_data, 200)
        if not success:
            self.log_test("Create expense for payment test", False, str(response))
            return False
        
        expense_id = response.get('id')
        all_success = True
        
        # SuperAdmin should be able to mark as paid
        success, response = self.make_request('PUT', f'expenses/{expense_id}/pay', 'superadmin')
        self.log_test("SuperAdmin can mark expense as paid", success, str(response) if not success else "")
        if not success:
            all_success = False
        
        # Create another expense for admin test
        success, response = self.make_request('POST', 'expenses', 'superadmin', expense_data, 200)
        if success:
            expense_id2 = response.get('id')
            
            # Admin should be able to mark as paid
            success, response = self.make_request('PUT', f'expenses/{expense_id2}/pay', 'admin')
            self.log_test("Admin can mark expense as paid", success, str(response) if not success else "")
            if not success:
                all_success = False
            
            # Usuario should NOT be able to mark as paid (403 Forbidden)
            success, response = self.make_request('PUT', f'expenses/{expense_id2}/pay', 'usuario', expected_status=403)
            self.log_test("Usuario cannot mark expense as paid", success, 
                         f"Expected 403, got {response.get('actual_status')}" if not success else "")
            if not success:
                all_success = False
            
            # Cleanup
            self.make_request('DELETE', f'expenses/{expense_id2}', 'superadmin')
        
        # Cleanup
        self.make_request('DELETE', f'expenses/{expense_id}', 'superadmin')
        
        return all_success

    def test_user_management_permissions(self) -> bool:
        """Test user management access based on role permissions"""
        all_success = True
        
        # SuperAdmin should be able to access user management
        success, response = self.make_request('GET', 'users', 'superadmin')
        self.log_test("SuperAdmin can access user management", success, str(response) if not success else "")
        if not success:
            all_success = False
        
        # Admin should NOT be able to access user management (403 Forbidden)
        success, response = self.make_request('GET', 'users', 'admin', expected_status=403)
        self.log_test("Admin cannot access user management", success, 
                     f"Expected 403, got {response.get('actual_status')}" if not success else "")
        if not success:
            all_success = False
        
        # Usuario should NOT be able to access user management (403 Forbidden)
        success, response = self.make_request('GET', 'users', 'usuario', expected_status=403)
        self.log_test("Usuario cannot access user management", success, 
                     f"Expected 403, got {response.get('actual_status')}" if not success else "")
        if not success:
            all_success = False
        
        return all_success

    def test_view_permissions(self) -> bool:
        """Test that all roles can view expenses and dashboard"""
        all_success = True
        
        for role in ['superadmin', 'admin', 'usuario']:
            # Test view expenses
            success, response = self.make_request('GET', 'expenses', role)
            self.log_test(f"{role} can view expenses", success, str(response) if not success else "")
            if not success:
                all_success = False
            
            # Test view dashboard stats
            success, response = self.make_request('GET', 'dashboard/stats', role)
            self.log_test(f"{role} can view dashboard stats", success, str(response) if not success else "")
            if not success:
                all_success = False
        
        return all_success

    def run_permission_tests(self):
        """Run complete permission test suite"""
        print("🔐 Starting NovaVision Permission System Tests...")
        print("=" * 60)
        
        # Test login for all seed users
        if not self.test_login_all_users():
            print("❌ Login tests failed, stopping")
            return False
        
        # Test permissions in login response
        self.test_permissions_in_response()
        
        # Test view permissions (all roles should have these)
        self.test_view_permissions()
        
        # Test expense creation permissions
        created_expenses = self.test_expense_creation_permissions()
        
        # Test expense editing permissions
        if created_expenses:
            self.test_expense_edit_permissions(created_expenses)
        
        # Test expense deletion permissions
        if created_expenses:
            self.test_expense_delete_permissions(created_expenses)
        
        # Test mark as paid permissions
        self.test_mark_as_paid_permissions()
        
        # Test user management permissions
        self.test_user_management_permissions()
        
        # Print results
        print("\n" + "=" * 60)
        print(f"📊 Permission Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All permission tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} permission tests failed")
            return False

def main():
    """Main test execution"""
    tester = PermissionTester()
    success = tester.run_permission_tests()
    
    # Save detailed results
    with open('/app/permission_test_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_tests': tester.tests_run,
            'passed_tests': tester.tests_passed,
            'success_rate': f"{(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%",
            'results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())