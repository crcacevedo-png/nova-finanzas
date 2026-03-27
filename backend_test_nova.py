#!/usr/bin/env python3
"""
NovaVision Financial Management System - Backend API Tests for New Schema
Tests the updated MongoDB schema with partial payments functionality
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class NovaVisionNewSchemaAPITester:
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

    def test_superadmin_login(self) -> bool:
        """Test login with superadmin credentials"""
        data = {"username": "superadmin", "password": "nova2024"}
        success, response = self.make_request('POST', 'auth/login', data)
        
        if success:
            self.token = response.get('access_token')
            self.current_user = response.get('user')
            # Verify superadmin role
            is_superadmin = self.current_user.get('role') == 'superadmin'
            if not is_superadmin:
                success = False
                self.log_test("Superadmin Login", False, f"Expected superadmin role, got: {self.current_user.get('role')}")
            else:
                self.log_test("Superadmin Login", True, f"Logged in as {self.current_user.get('username')}")
        else:
            self.log_test("Superadmin Login", False, str(response))
        
        return success

    def test_dashboard_stats(self) -> bool:
        """Test dashboard statistics with new schema"""
        success, response = self.make_request('GET', 'dashboard/stats')
        
        if success:
            required_fields = ['total_gastos', 'gastos_pendientes', 'gastos_pagados', 
                             'gastos_parciales', 'gastos_vencidos', 'total_fijos', 
                             'total_proveedores', 'total_variables', 'alertas_30_dias', 'alertas_60_dias']
            
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log_test("Dashboard Stats", False, f"Missing fields: {missing_fields}")
                return False
            
            # Check for partial payments stats
            parciales = response.get('gastos_parciales', 0)
            self.log_test("Dashboard Stats", True, f"Parciales: Q{parciales:.2f}")
        else:
            self.log_test("Dashboard Stats", False, str(response))
        
        return success

    def test_create_expense_new_schema(self) -> Optional[str]:
        """Test creating expense with new schema fields"""
        today = datetime.now().strftime('%Y-%m-%d')
        due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        data = {
            "name": "Prueba Gasto Nuevo Schema",
            "type": "proveedor",
            "amount": 5000.00,
            "date": today,
            "due_date": due_date,
            "invoice_number": "FAC-TEST-001",
            "notes": "Gasto de prueba con nuevo esquema MongoDB"
        }
        
        success, response = self.make_request('POST', 'expenses', data, 200)
        expense_id = response.get('id') if success else None
        
        if success:
            # Verify new schema fields
            required_fields = ['name', 'type', 'amount', 'date', 'due_date', 'invoice_number', 
                             'status', 'paid_amount', 'remaining_amount']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                self.log_test("Create Expense (New Schema)", False, f"Missing fields: {missing_fields}")
                return None
            
            # Verify initial values
            if (response.get('status') != 'pendiente' or 
                response.get('paid_amount') != 0 or 
                response.get('remaining_amount') != 5000.00):
                self.log_test("Create Expense (New Schema)", False, 
                             f"Incorrect initial values: status={response.get('status')}, paid={response.get('paid_amount')}, remaining={response.get('remaining_amount')}")
                return None
            
            self.log_test("Create Expense (New Schema)", True, f"ID: {expense_id}")
        else:
            self.log_test("Create Expense (New Schema)", False, str(response))
        
        return expense_id

    def test_register_partial_payment(self, expense_id: str) -> Optional[str]:
        """Test registering a partial payment"""
        data = {
            "expense_id": expense_id,
            "amount": 2000.00,
            "date": datetime.now().strftime('%Y-%m-%d'),
            "method": "Transferencia bancaria",
            "reference": "TXN-TEST-001",
            "notes": "Pago parcial de prueba"
        }
        
        success, response = self.make_request('POST', 'payments', data, 200)
        payment_id = response.get('id') if success else None
        
        if success:
            self.log_test("Register Partial Payment", True, f"Payment ID: {payment_id}")
        else:
            self.log_test("Register Partial Payment", False, str(response))
        
        return payment_id

    def test_expense_status_after_partial_payment(self, expense_id: str) -> bool:
        """Test that expense status changes to 'parcial' after partial payment"""
        success, response = self.make_request('GET', f'expenses/{expense_id}')
        
        if success:
            status = response.get('status')
            paid_amount = response.get('paid_amount')
            remaining_amount = response.get('remaining_amount')
            
            if (status == 'parcial' and 
                paid_amount == 2000.00 and 
                remaining_amount == 3000.00):
                self.log_test("Expense Status After Partial Payment", True, 
                             f"Status: {status}, Paid: Q{paid_amount}, Remaining: Q{remaining_amount}")
            else:
                self.log_test("Expense Status After Partial Payment", False, 
                             f"Expected: status=parcial, paid=2000, remaining=3000. Got: status={status}, paid={paid_amount}, remaining={remaining_amount}")
                return False
        else:
            self.log_test("Expense Status After Partial Payment", False, str(response))
            return False
        
        return success

    def test_expense_payment_history(self, expense_id: str) -> bool:
        """Test viewing expense payment history"""
        success, response = self.make_request('GET', f'expenses/{expense_id}/payments')
        
        if success:
            if isinstance(response, list) and len(response) > 0:
                payment = response[0]
                required_fields = ['id', 'expense_id', 'amount', 'date', 'method', 'reference']
                missing_fields = [field for field in required_fields if field not in payment]
                
                if missing_fields:
                    self.log_test("Expense Payment History", False, f"Missing payment fields: {missing_fields}")
                    return False
                
                self.log_test("Expense Payment History", True, f"Found {len(response)} payments")
            else:
                self.log_test("Expense Payment History", False, "No payments found")
                return False
        else:
            self.log_test("Expense Payment History", False, str(response))
            return False
        
        return success

    def test_expense_progress_calculation(self, expense_id: str) -> bool:
        """Test expense progress bar calculation"""
        success, response = self.make_request('GET', f'expenses/{expense_id}')
        
        if success:
            amount = response.get('amount', 0)
            paid_amount = response.get('paid_amount', 0)
            
            if amount > 0:
                progress = (paid_amount / amount) * 100
                expected_progress = (2000.00 / 5000.00) * 100  # 40%
                
                if abs(progress - expected_progress) < 0.01:  # Allow small floating point differences
                    self.log_test("Expense Progress Calculation", True, f"Progress: {progress:.1f}%")
                else:
                    self.log_test("Expense Progress Calculation", False, 
                                 f"Expected: {expected_progress:.1f}%, Got: {progress:.1f}%")
                    return False
            else:
                self.log_test("Expense Progress Calculation", False, "Amount is 0")
                return False
        else:
            self.log_test("Expense Progress Calculation", False, str(response))
            return False
        
        return success

    def test_filter_expenses_by_type_and_status(self) -> bool:
        """Test filtering expenses by type and status"""
        # Test type filter
        success1, response1 = self.make_request('GET', 'expenses?type=proveedor')
        
        # Test status filter  
        success2, response2 = self.make_request('GET', 'expenses?status=parcial')
        
        # Test combined filters
        success3, response3 = self.make_request('GET', 'expenses?type=proveedor&status=parcial')
        
        overall_success = success1 and success2 and success3
        
        if overall_success:
            type_count = len(response1) if isinstance(response1, list) else 0
            status_count = len(response2) if isinstance(response2, list) else 0
            combined_count = len(response3) if isinstance(response3, list) else 0
            
            self.log_test("Filter Expenses by Type and Status", True, 
                         f"Type filter: {type_count}, Status filter: {status_count}, Combined: {combined_count}")
        else:
            details = f"Type: {success1}, Status: {success2}, Combined: {success3}"
            self.log_test("Filter Expenses by Type and Status", False, details)
        
        return overall_success

    def test_existing_partial_payment_expense(self) -> bool:
        """Test that the existing partial payment expense exists as mentioned in context"""
        success, response = self.make_request('GET', 'expenses?status=parcial')
        
        if success and isinstance(response, list):
            # Look for the mentioned expense: "Alquiler oficina central, Q8000, Q3000 pagado = 38% progreso"
            found_expense = None
            for expense in response:
                if ('alquiler' in expense.get('name', '').lower() and 
                    'oficina' in expense.get('name', '').lower()):
                    found_expense = expense
                    break
            
            if found_expense:
                amount = found_expense.get('amount', 0)
                paid_amount = found_expense.get('paid_amount', 0)
                status = found_expense.get('status')
                
                # Check if it matches the expected values (Q8000 total, Q3000 paid, 38% progress)
                expected_total = 8000.00
                expected_paid = 3000.00
                expected_progress = 37.5  # 3000/8000 = 37.5%
                
                actual_progress = (paid_amount / amount * 100) if amount > 0 else 0
                
                if (abs(amount - expected_total) < 0.01 and 
                    abs(paid_amount - expected_paid) < 0.01 and 
                    status == 'parcial'):
                    self.log_test("Existing Partial Payment Expense", True, 
                                 f"Found: {found_expense.get('name')}, Progress: {actual_progress:.1f}%")
                else:
                    self.log_test("Existing Partial Payment Expense", False, 
                                 f"Values don't match expected. Amount: {amount}, Paid: {paid_amount}, Status: {status}")
                    return False
            else:
                self.log_test("Existing Partial Payment Expense", False, "Alquiler oficina central not found")
                return False
        else:
            self.log_test("Existing Partial Payment Expense", False, str(response))
            return False
        
        return success

    def run_all_tests(self):
        """Run complete test suite for new schema"""
        print("🚀 Starting NovaVision New Schema API Tests...")
        print("=" * 60)
        
        # Test sequence
        if not self.test_health_check():
            print("❌ API is not accessible, stopping tests")
            return False
        
        # Authentication test with specific credentials
        if not self.test_superadmin_login():
            print("❌ Superadmin login failed, stopping tests")
            return False
        
        # Dashboard test
        self.test_dashboard_stats()
        
        # Test existing partial payment expense
        self.test_existing_partial_payment_expense()
        
        # Create new expense with new schema
        expense_id = self.test_create_expense_new_schema()
        if not expense_id:
            print("❌ Could not create expense, stopping related tests")
            return False
        
        # Test partial payment functionality
        payment_id = self.test_register_partial_payment(expense_id)
        if payment_id:
            # Test status change after partial payment
            self.test_expense_status_after_partial_payment(expense_id)
            
            # Test payment history
            self.test_expense_payment_history(expense_id)
            
            # Test progress calculation
            self.test_expense_progress_calculation(expense_id)
        
        # Test filtering
        self.test_filter_expenses_by_type_and_status()
        
        # Print results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    """Main test execution"""
    tester = NovaVisionNewSchemaAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_nova_results.json', 'w') as f:
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