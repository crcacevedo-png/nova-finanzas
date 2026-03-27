#!/usr/bin/env python3
"""
NovaVision API Updated Endpoints Test
Tests the newly implemented endpoints according to the specification:
- Login with superadmin/nova2024
- GET /api/expenses with pagination (page, limit)
- GET /api/expenses with search filter
- GET /api/expenses with date range filter
- GET /api/dashboard/summary returns new format
- GET /api/dashboard/upcoming returns overdue/due30/due60
- GET /api/reports/expenses?format=csv exports CSV
- POST /api/auth/logout invalidates token
- GET /api/users/:id returns single user
- PUT /api/users/:id updates user
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid

class NovaVisionUpdatedAPITester:
    def __init__(self, base_url: str = "https://novavision-finanzas.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.current_user = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.created_expense_id = None
        self.created_user_id = None

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
                    expected_status: int = 200, params: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=15)
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

    def test_superadmin_login(self) -> bool:
        """Test login with superadmin/nova2024 credentials"""
        data = {"username": "superadmin", "password": "nova2024"}
        success, response = self.make_request('POST', 'auth/login', data)
        
        if success:
            self.token = response.get('access_token')
            self.current_user = response.get('user')
            # Verify it's superadmin role
            is_superadmin = self.current_user.get('role') == 'superadmin'
            if not is_superadmin:
                success = False
                self.log_test("Superadmin Login", False, f"Expected superadmin role, got: {self.current_user.get('role')}")
            else:
                self.log_test("Superadmin Login", True, f"Logged in as {self.current_user.get('username')}")
        else:
            self.log_test("Superadmin Login", False, str(response))
        
        return success

    def test_expenses_pagination(self) -> bool:
        """Test GET /api/expenses with pagination (page, limit)"""
        # Test with different pagination parameters
        test_cases = [
            {"page": 1, "limit": 5},
            {"page": 1, "limit": 10},
            {"page": 2, "limit": 5}
        ]
        
        all_success = True
        details = []
        
        for params in test_cases:
            success, response = self.make_request('GET', 'expenses', params=params)
            if success:
                # Check response structure
                required_fields = ['data', 'total', 'page', 'limit', 'total_pages']
                missing_fields = [field for field in required_fields if field not in response]
                if missing_fields:
                    all_success = False
                    details.append(f"Missing fields in pagination response: {missing_fields}")
                else:
                    # Verify pagination values match request
                    if response['page'] != params['page'] or response['limit'] != params['limit']:
                        all_success = False
                        details.append(f"Pagination mismatch: requested {params}, got page={response['page']}, limit={response['limit']}")
            else:
                all_success = False
                details.append(f"Failed pagination test with params {params}: {response}")
        
        self.log_test("Expenses Pagination", all_success, "; ".join(details) if details else "")
        return all_success

    def test_expenses_search_filter(self) -> bool:
        """Test GET /api/expenses with search filter"""
        # First create a test expense to search for
        test_expense_data = {
            "name": f"Test Search Expense {uuid.uuid4().hex[:8]}",
            "type": "variable",
            "amount": 500.0,
            "date": datetime.now().strftime('%Y-%m-%d'),
            "notes": "Test expense for search functionality"
        }
        
        create_success, create_response = self.make_request('POST', 'expenses', test_expense_data, 200)
        if not create_success:
            self.log_test("Expenses Search Filter", False, f"Failed to create test expense: {create_response}")
            return False
        
        self.created_expense_id = create_response.get('id')
        
        # Test search by name
        search_term = test_expense_data["name"][:10]  # Use first 10 chars
        params = {"search": search_term}
        success, response = self.make_request('GET', 'expenses', params=params)
        
        if success:
            # Check if our created expense is in the results
            found_expense = False
            for expense in response.get('data', []):
                if expense.get('id') == self.created_expense_id:
                    found_expense = True
                    break
            
            if not found_expense:
                success = False
                self.log_test("Expenses Search Filter", False, f"Created expense not found in search results for '{search_term}'")
            else:
                self.log_test("Expenses Search Filter", True, f"Found expense in search results")
        else:
            self.log_test("Expenses Search Filter", False, str(response))
        
        return success

    def test_expenses_date_range_filter(self) -> bool:
        """Test GET /api/expenses with date range filter"""
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Test date range filter
        params = {
            "dateFrom": yesterday,
            "dateTo": tomorrow
        }
        
        success, response = self.make_request('GET', 'expenses', params=params)
        
        if success:
            # Verify response structure
            if 'data' not in response:
                success = False
                self.log_test("Expenses Date Range Filter", False, "Missing 'data' field in response")
            else:
                # Check if expenses are within date range (if any exist)
                expenses = response.get('data', [])
                self.log_test("Expenses Date Range Filter", True, f"Found {len(expenses)} expenses in date range")
        else:
            self.log_test("Expenses Date Range Filter", False, str(response))
        
        return success

    def test_dashboard_summary_new_format(self) -> bool:
        """Test GET /api/dashboard/summary returns new format"""
        success, response = self.make_request('GET', 'dashboard/summary')
        
        if success:
            # Check for new format fields
            required_fields = ['total_month', 'total_paid', 'total_pending', 'overdue_count', 'by_type']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                success = False
                self.log_test("Dashboard Summary New Format", False, f"Missing required fields: {missing_fields}")
            else:
                # Verify by_type structure
                by_type = response.get('by_type', [])
                if not isinstance(by_type, list):
                    success = False
                    self.log_test("Dashboard Summary New Format", False, "by_type should be a list")
                else:
                    # Check if by_type items have required fields
                    for item in by_type:
                        if not all(field in item for field in ['type', 'total', 'percentage']):
                            success = False
                            self.log_test("Dashboard Summary New Format", False, "by_type items missing required fields")
                            break
                    
                    if success:
                        self.log_test("Dashboard Summary New Format", True, f"Summary: month={response['total_month']}, paid={response['total_paid']}, pending={response['total_pending']}, overdue={response['overdue_count']}")
        else:
            self.log_test("Dashboard Summary New Format", False, str(response))
        
        return success

    def test_dashboard_upcoming_payments(self) -> bool:
        """Test GET /api/dashboard/upcoming returns overdue/due30/due60"""
        success, response = self.make_request('GET', 'dashboard/upcoming')
        
        if success:
            # Check for required fields
            required_fields = ['overdue', 'due30', 'due60']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                success = False
                self.log_test("Dashboard Upcoming Payments", False, f"Missing required fields: {missing_fields}")
            else:
                # Verify each category is a list
                for category in required_fields:
                    if not isinstance(response[category], list):
                        success = False
                        self.log_test("Dashboard Upcoming Payments", False, f"{category} should be a list")
                        break
                
                if success:
                    overdue_count = len(response['overdue'])
                    due30_count = len(response['due30'])
                    due60_count = len(response['due60'])
                    self.log_test("Dashboard Upcoming Payments", True, f"Overdue: {overdue_count}, Due30: {due30_count}, Due60: {due60_count}")
        else:
            self.log_test("Dashboard Upcoming Payments", False, str(response))
        
        return success

    def test_reports_csv_export(self) -> bool:
        """Test GET /api/reports/expenses?format=csv exports CSV"""
        params = {"format": "csv"}
        
        # Make request without expecting JSON response
        url = f"{self.base_url}/api/reports/expenses"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            success = response.status_code == 200
            
            if success:
                # Check if response is CSV format
                content_type = response.headers.get('content-type', '')
                if 'csv' in content_type.lower() or 'text/csv' in content_type.lower():
                    # Check if response contains CSV data
                    csv_content = response.text
                    if csv_content and 'ID,Nombre,Tipo,Monto' in csv_content:
                        self.log_test("Reports CSV Export", True, f"CSV export successful, {len(csv_content)} characters")
                    else:
                        success = False
                        self.log_test("Reports CSV Export", False, "CSV content doesn't contain expected headers")
                else:
                    success = False
                    self.log_test("Reports CSV Export", False, f"Expected CSV content-type, got: {content_type}")
            else:
                self.log_test("Reports CSV Export", False, f"HTTP {response.status_code}: {response.text}")
        
        except requests.exceptions.RequestException as e:
            success = False
            self.log_test("Reports CSV Export", False, str(e))
        
        return success

    def test_auth_logout(self) -> bool:
        """Test POST /api/auth/logout invalidates token"""
        # Store current token
        original_token = self.token
        
        # Test logout
        success, response = self.make_request('POST', 'auth/logout')
        
        if success:
            # Try to use the token after logout - should fail
            test_success, test_response = self.make_request('GET', 'auth/me', expected_status=401)
            
            if test_success:
                self.log_test("Auth Logout Token Invalidation", True, "Token successfully invalidated")
                # Re-login for remaining tests
                self.test_superadmin_login()
            else:
                success = False
                self.log_test("Auth Logout Token Invalidation", False, "Token still valid after logout")
        else:
            self.log_test("Auth Logout", False, str(response))
        
        return success

    def test_get_user_by_id(self) -> bool:
        """Test GET /api/users/:id returns single user"""
        # First get list of users to find a valid ID
        success, response = self.make_request('GET', 'users')
        
        if not success:
            self.log_test("Get User by ID", False, f"Failed to get users list: {response}")
            return False
        
        users = response
        if not users or len(users) == 0:
            self.log_test("Get User by ID", False, "No users found to test with")
            return False
        
        # Use the first user's ID
        user_id = users[0].get('id')
        if not user_id:
            self.log_test("Get User by ID", False, "User ID not found in users list")
            return False
        
        # Test getting single user
        success, response = self.make_request('GET', f'users/{user_id}')
        
        if success:
            # Verify response contains user data
            required_fields = ['id', 'username', 'name', 'role']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                success = False
                self.log_test("Get User by ID", False, f"Missing fields in user response: {missing_fields}")
            else:
                self.log_test("Get User by ID", True, f"Retrieved user: {response.get('username')} ({response.get('role')})")
        else:
            self.log_test("Get User by ID", False, str(response))
        
        return success

    def test_update_user_by_id(self) -> bool:
        """Test PUT /api/users/:id updates user"""
        # First create a test user to update
        test_user_data = {
            "username": f"testuser_{uuid.uuid4().hex[:8]}",
            "name": "Test User for Update",
            "password": "testpass123",
            "role": "usuario"
        }
        
        create_success, create_response = self.make_request('POST', 'users', test_user_data, 200)
        if not create_success:
            self.log_test("Update User by ID", False, f"Failed to create test user: {create_response}")
            return False
        
        self.created_user_id = create_response.get('id')
        
        # Update the user
        update_data = {
            "name": "Updated Test User Name",
            "role": "admin"
        }
        
        success, response = self.make_request('PUT', f'users/{self.created_user_id}', update_data)
        
        if success:
            # Verify the update was applied
            if response.get('name') == update_data['name'] and response.get('role') == update_data['role']:
                self.log_test("Update User by ID", True, f"User updated successfully: {response.get('name')} ({response.get('role')})")
            else:
                success = False
                self.log_test("Update User by ID", False, f"Update not reflected in response: expected name='{update_data['name']}', role='{update_data['role']}', got name='{response.get('name')}', role='{response.get('role')}'")
        else:
            self.log_test("Update User by ID", False, str(response))
        
        return success

    def cleanup_test_data(self):
        """Clean up test data created during tests"""
        if self.created_expense_id:
            self.make_request('DELETE', f'expenses/{self.created_expense_id}')
            print(f"🧹 Cleaned up test expense: {self.created_expense_id}")
        
        if self.created_user_id:
            self.make_request('DELETE', f'users/{self.created_user_id}')
            print(f"🧹 Cleaned up test user: {self.created_user_id}")

    def run_all_tests(self):
        """Run all updated API endpoint tests"""
        print("🚀 Starting NovaVision Updated API Endpoint Tests...")
        print("=" * 60)
        
        # Test sequence based on review request
        if not self.test_superadmin_login():
            print("❌ Superadmin login failed, stopping tests")
            return False
        
        # Test all the specified endpoints
        self.test_expenses_pagination()
        self.test_expenses_search_filter()
        self.test_expenses_date_range_filter()
        self.test_dashboard_summary_new_format()
        self.test_dashboard_upcoming_payments()
        self.test_reports_csv_export()
        self.test_get_user_by_id()
        self.test_update_user_by_id()
        self.test_auth_logout()  # Test logout last since it invalidates token
        
        # Cleanup
        self.cleanup_test_data()
        
        # Print results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All updated API endpoint tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    """Main test execution"""
    tester = NovaVisionUpdatedAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_updated_results.json', 'w') as f:
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