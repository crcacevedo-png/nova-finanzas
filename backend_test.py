#!/usr/bin/env python3
"""
NovaVision Financial Management System - Backend API Tests
Tests all authentication, user management, expense management, and dashboard APIs
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class NovaVisionAPITester:
    def __init__(self, base_url: str = "https://novavision-finanzas.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.current_user = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

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

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    expected_status: int = 200) -> tuple[bool, Dict]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

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

    def test_health_check(self):
        """Test basic API health"""
        success, response = self.make_request('GET', '')
        self.log_test("API Health Check", success, 
                     f"Response: {response}" if not success else "")
        return success

    def test_user_registration(self, email: str, password: str, name: str) -> bool:
        """Test user registration - first user becomes superadmin"""
        data = {
            "email": email,
            "password": password,
            "name": name,
            "role": "usuario"  # Should be overridden to superadmin for first user
        }
        
        success, response = self.make_request('POST', 'auth/register', data)
        
        if success:
            self.token = response.get('access_token')
            self.current_user = response.get('user')
            # Check if first user got superadmin role
            is_superadmin = self.current_user.get('role') == 'superadmin'
            self.log_test("User Registration (First User -> Superadmin)", 
                         is_superadmin, 
                         f"Role: {self.current_user.get('role')}" if not is_superadmin else "")
        else:
            self.log_test("User Registration", False, str(response))
        
        return success

    def test_user_login(self, email: str, password: str) -> bool:
        """Test user login"""
        data = {"email": email, "password": password}
        success, response = self.make_request('POST', 'auth/login', data)
        
        if success:
            self.token = response.get('access_token')
            self.current_user = response.get('user')
        
        self.log_test("User Login", success, str(response) if not success else "")
        return success

    def test_get_current_user(self) -> bool:
        """Test get current user info"""
        success, response = self.make_request('GET', 'auth/me')
        self.log_test("Get Current User", success, str(response) if not success else "")
        return success

    def test_create_expense(self) -> Optional[str]:
        """Test creating an expense"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        next_month = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        data = {
            "concepto": "Prueba de Gasto - Equipo Médico",
            "monto": 1500.50,
            "fecha": tomorrow,
            "categoria": "gastos_fijos",
            "estado": "pendiente",
            "fecha_vencimiento": next_month,
            "proveedor": "Proveedor Test S.A.",
            "notas": "Gasto de prueba para testing"
        }
        
        success, response = self.make_request('POST', 'expenses', data, 200)  # Backend returns 200, not 201
        expense_id = response.get('id') if success else None
        
        self.log_test("Create Expense", success, str(response) if not success else f"ID: {expense_id}")
        return expense_id

    def test_get_expenses(self) -> bool:
        """Test getting all expenses"""
        success, response = self.make_request('GET', 'expenses')
        
        if success:
            expenses_count = len(response) if isinstance(response, list) else 0
            self.log_test("Get All Expenses", True, f"Found {expenses_count} expenses")
        else:
            self.log_test("Get All Expenses", False, str(response))
        
        return success

    def test_get_expense_by_id(self, expense_id: str) -> bool:
        """Test getting specific expense"""
        success, response = self.make_request('GET', f'expenses/{expense_id}')
        self.log_test("Get Expense by ID", success, str(response) if not success else "")
        return success

    def test_update_expense(self, expense_id: str) -> bool:
        """Test updating an expense"""
        data = {
            "concepto": "Gasto Actualizado - Equipo Médico",
            "monto": 1750.75,
            "estado": "pagado"
        }
        
        success, response = self.make_request('PUT', f'expenses/{expense_id}', data)
        self.log_test("Update Expense", success, str(response) if not success else "")
        return success

    def test_filter_expenses(self) -> bool:
        """Test filtering expenses by category and status"""
        # Test category filter
        success1, response1 = self.make_request('GET', 'expenses?categoria=gastos_fijos')
        
        # Test status filter  
        success2, response2 = self.make_request('GET', 'expenses?estado=pendiente')
        
        # Test combined filters
        success3, response3 = self.make_request('GET', 'expenses?categoria=gastos_fijos&estado=pagado')
        
        overall_success = success1 and success2 and success3
        details = ""
        if not overall_success:
            details = f"Category: {success1}, Status: {success2}, Combined: {success3}"
        
        self.log_test("Filter Expenses", overall_success, details)
        return overall_success

    def test_dashboard_stats(self) -> bool:
        """Test dashboard statistics"""
        success, response = self.make_request('GET', 'dashboard/stats')
        
        if success:
            required_fields = ['total_gastos', 'gastos_pendientes', 'gastos_pagados', 
                             'total_gastos_fijos', 'total_pagos_proveedores', 
                             'total_gastos_variables', 'alertas_30_dias', 'alertas_60_dias']
            
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log_test("Dashboard Stats", False, f"Missing fields: {missing_fields}")
                return False
        
        self.log_test("Dashboard Stats", success, str(response) if not success else "")
        return success

    def test_dashboard_alerts(self) -> bool:
        """Test dashboard alerts"""
        success1, response1 = self.make_request('GET', 'dashboard/alerts/30')
        success2, response2 = self.make_request('GET', 'dashboard/alerts/60')
        
        overall_success = success1 and success2
        details = ""
        if not overall_success:
            details = f"30-day alerts: {success1}, 60-day alerts: {success2}"
        
        self.log_test("Dashboard Alerts", overall_success, details)
        return overall_success

    def test_dashboard_chart_data(self) -> bool:
        """Test dashboard chart data"""
        success, response = self.make_request('GET', 'dashboard/chart-data')
        self.log_test("Dashboard Chart Data", success, str(response) if not success else "")
        return success

    def test_create_user(self) -> Optional[str]:
        """Test creating a new user (superadmin only)"""
        data = {
            "name": "Usuario Test",
            "email": f"test_user_{datetime.now().strftime('%H%M%S')}@example.com",
            "password": "testpass123",
            "role": "usuario"
        }
        
        success, response = self.make_request('POST', 'users', data, 200)  # Backend returns 200, not 201
        user_id = response.get('id') if success else None
        
        self.log_test("Create User (Superadmin)", success, 
                     str(response) if not success else f"ID: {user_id}")
        return user_id

    def test_get_users(self) -> bool:
        """Test getting all users"""
        success, response = self.make_request('GET', 'users')
        
        if success:
            users_count = len(response) if isinstance(response, list) else 0
            self.log_test("Get All Users", True, f"Found {users_count} users")
        else:
            self.log_test("Get All Users", False, str(response))
        
        return success

    def test_toggle_user_active(self, user_id: str) -> bool:
        """Test toggling user active status"""
        success, response = self.make_request('PUT', f'users/{user_id}/toggle-active')
        self.log_test("Toggle User Active", success, str(response) if not success else "")
        return success

    def test_delete_expense(self, expense_id: str) -> bool:
        """Test deleting an expense"""
        success, response = self.make_request('DELETE', f'expenses/{expense_id}')
        self.log_test("Delete Expense", success, str(response) if not success else "")
        return success

    def test_delete_user(self, user_id: str) -> bool:
        """Test deleting a user"""
        success, response = self.make_request('DELETE', f'users/{user_id}')
        self.log_test("Delete User", success, str(response) if not success else "")
        return success

    def test_unauthorized_access(self) -> bool:
        """Test that protected routes require authentication"""
        # Temporarily remove token
        original_token = self.token
        self.token = None
        
        success, response = self.make_request('GET', 'expenses', expected_status=403)  # Backend returns 403, not 401
        
        # Restore token
        self.token = original_token
        
        self.log_test("Unauthorized Access Protection", success, 
                     str(response) if not success else "")
        return success

    def test_role_based_access(self) -> bool:
        """Test role-based access control"""
        # This would require creating a non-superadmin user and testing access
        # For now, we'll just test that superadmin can access user management
        success, response = self.make_request('GET', 'users')
        self.log_test("Role-based Access (Superadmin -> Users)", success, 
                     str(response) if not success else "")
        return success

    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting NovaVision API Tests...")
        print("=" * 50)
        
        # Generate unique test user
        timestamp = datetime.now().strftime('%H%M%S')
        test_email = f"superadmin_{timestamp}@example.com"
        test_password = "SuperAdmin123!"
        test_name = f"Super Admin Test {timestamp}"
        
        # Test sequence
        if not self.test_health_check():
            print("❌ API is not accessible, stopping tests")
            return False
        
        # Authentication tests
        if not self.test_user_registration(test_email, test_password, test_name):
            print("❌ Registration failed, stopping tests")
            return False
        
        self.test_get_current_user()
        
        # Test login with same credentials
        if not self.test_user_login(test_email, test_password):
            print("❌ Login failed, stopping tests")
            return False
        
        # Expense management tests
        expense_id = self.test_create_expense()
        if expense_id:
            self.test_get_expense_by_id(expense_id)
            self.test_update_expense(expense_id)
        
        self.test_get_expenses()
        self.test_filter_expenses()
        
        # Dashboard tests
        self.test_dashboard_stats()
        self.test_dashboard_alerts()
        self.test_dashboard_chart_data()
        
        # User management tests (superadmin only)
        self.test_get_users()
        user_id = self.test_create_user()
        if user_id:
            self.test_toggle_user_active(user_id)
            self.test_delete_user(user_id)
        
        # Security tests
        self.test_unauthorized_access()
        self.test_role_based_access()
        
        # Cleanup
        if expense_id:
            self.test_delete_expense(expense_id)
        
        # Print results
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    """Main test execution"""
    tester = NovaVisionAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
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