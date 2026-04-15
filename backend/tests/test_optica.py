"""
Test suite for Optica Module
Tests: Doctors, Frames Inventory, Lens Types, and Sales
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
OPTICA_USER = {"username": "optica", "password": "optica2024"}
SUPERADMIN_USER = {"username": "superadmin", "password": "nova2024"}
ADMIN_USER = {"username": "admin", "password": "admin2024"}
USUARIO_USER = {"username": "usuario", "password": "user2024"}


class TestAuth:
    """Authentication tests for optica user"""
    
    def test_optica_login_success(self):
        """Test optica user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=OPTICA_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "optica"
        assert data["user"]["permissions"]["view_optica"] == True
        assert data["user"]["permissions"]["manage_optica_inventory"] == True
        print(f"✓ Optica user login successful, role: {data['user']['role']}")
    
    def test_superadmin_has_optica_permissions(self):
        """Test superadmin has optica permissions"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERADMIN_USER)
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["permissions"]["view_optica"] == True
        print("✓ SuperAdmin has optica permissions")
    
    def test_admin_no_optica_permissions(self):
        """Test admin does NOT have optica permissions"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["permissions"]["view_optica"] == False
        print("✓ Admin does NOT have optica permissions (correct)")
    
    def test_usuario_no_optica_permissions(self):
        """Test usuario does NOT have optica permissions"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=USUARIO_USER)
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["permissions"]["view_optica"] == False
        print("✓ Usuario does NOT have optica permissions (correct)")


@pytest.fixture(scope="session")
def optica_token():
    """Get optica user token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=OPTICA_USER)
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Optica login failed")


@pytest.fixture(scope="session")
def superadmin_token():
    """Get superadmin token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERADMIN_USER)
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("SuperAdmin login failed")


@pytest.fixture(scope="session")
def admin_token():
    """Get admin token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Admin login failed")


class TestDoctors:
    """Tests for Doctors CRUD"""
    
    def test_list_doctors(self, optica_token):
        """Test listing doctors"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        response = requests.get(f"{BASE_URL}/api/doctors", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "data" in data
        assert "total" in data
        print(f"✓ Listed {data['total']} doctors")
    
    def test_create_doctor(self, optica_token):
        """Test creating a doctor"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        doctor_data = {
            "name": f"TEST_Dr. Prueba {datetime.now().strftime('%H%M%S%f')}",
            "specialty": "Oftalmología General",
            "phone": "5555-9999",
            "email": "test.doctor@clinic.com",
            "license_number": "99999"
        }
        response = requests.post(f"{BASE_URL}/api/doctors", json=doctor_data, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["name"] == doctor_data["name"]
        assert data["specialty"] == doctor_data["specialty"]
        assert "id" in data
        print(f"✓ Created doctor: {data['name']} (ID: {data['id']})")
        return data["id"]
    
    def test_get_doctor_by_id(self, optica_token):
        """Test getting doctor by ID"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        # First create a doctor
        doctor_data = {"name": f"TEST_Dr. GetById {datetime.now().strftime('%H%M%S%f')}", "specialty": "Retina"}
        create_resp = requests.post(f"{BASE_URL}/api/doctors", json=doctor_data, headers=headers)
        assert create_resp.status_code == 200
        doctor_id = create_resp.json()["id"]
        
        # Get by ID
        response = requests.get(f"{BASE_URL}/api/doctors/{doctor_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doctor_id
        assert data["name"] == doctor_data["name"]
        print(f"✓ Got doctor by ID: {data['name']}")
    
    def test_update_doctor(self, optica_token):
        """Test updating a doctor"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        # Create
        doctor_data = {"name": f"TEST_Dr. ToUpdate {datetime.now().strftime('%H%M%S%f')}", "specialty": "Original"}
        create_resp = requests.post(f"{BASE_URL}/api/doctors", json=doctor_data, headers=headers)
        assert create_resp.status_code == 200
        doctor_id = create_resp.json()["id"]
        
        # Update
        update_data = {"specialty": "Updated Specialty", "phone": "1234-5678"}
        response = requests.put(f"{BASE_URL}/api/doctors/{doctor_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["specialty"] == "Updated Specialty"
        assert data["phone"] == "1234-5678"
        print(f"✓ Updated doctor specialty to: {data['specialty']}")
    
    def test_search_doctors(self, optica_token):
        """Test searching doctors"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        response = requests.get(f"{BASE_URL}/api/doctors/search?q=Dr&limit=5", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Search returned {len(data)} doctors")
    
    def test_delete_doctor(self, optica_token):
        """Test deleting a doctor"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        # Create
        doctor_data = {"name": f"TEST_Dr. ToDelete {datetime.now().strftime('%H%M%S%f')}", "specialty": "Delete Me"}
        create_resp = requests.post(f"{BASE_URL}/api/doctors", json=doctor_data, headers=headers)
        assert create_resp.status_code == 200
        doctor_id = create_resp.json()["id"]
        
        # Delete
        response = requests.delete(f"{BASE_URL}/api/doctors/{doctor_id}", headers=headers)
        assert response.status_code == 200
        print(f"✓ Deleted doctor: {doctor_id}")
        
        # Verify deleted
        get_resp = requests.get(f"{BASE_URL}/api/doctors/{doctor_id}", headers=headers)
        assert get_resp.status_code == 404


class TestFrameInventory:
    """Tests for Frame Inventory CRUD"""
    
    def test_list_frames(self, optica_token):
        """Test listing frames"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        response = requests.get(f"{BASE_URL}/api/optica/frames", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "data" in data
        assert "total" in data
        print(f"✓ Listed {data['total']} frames")
    
    def test_create_frame(self, optica_token):
        """Test creating a frame"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        frame_data = {
            "brand": "TEST_Brand",
            "code": f"TEST-{datetime.now().strftime('%H%M%S')}",
            "model": "Test Model",
            "color": "Negro",
            "cost_price": 100.00,
            "sale_price": 250.00,
            "stock": 10
        }
        response = requests.post(f"{BASE_URL}/api/optica/frames", json=frame_data, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["brand"] == frame_data["brand"]
        assert data["code"] == frame_data["code"]
        assert data["sale_price"] == frame_data["sale_price"]
        assert "id" in data
        print(f"✓ Created frame: {data['brand']} {data['code']} (ID: {data['id']})")
        return data["id"]
    
    def test_get_frame_by_id(self, optica_token):
        """Test getting frame by ID"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        # First create
        frame_data = {
            "brand": "TEST_GetById",
            "code": f"GETID-{datetime.now().strftime('%H%M%S')}",
            "cost_price": 50,
            "sale_price": 100,
            "stock": 5
        }
        create_resp = requests.post(f"{BASE_URL}/api/optica/frames", json=frame_data, headers=headers)
        assert create_resp.status_code == 200
        frame_id = create_resp.json()["id"]
        
        # Get by ID
        response = requests.get(f"{BASE_URL}/api/optica/frames/{frame_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == frame_id
        print(f"✓ Got frame by ID: {data['brand']} {data['code']}")
    
    def test_update_frame(self, optica_token):
        """Test updating a frame"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        # Create
        frame_data = {
            "brand": "TEST_Update",
            "code": f"UPD-{datetime.now().strftime('%H%M%S')}",
            "cost_price": 100,
            "sale_price": 200,
            "stock": 5
        }
        create_resp = requests.post(f"{BASE_URL}/api/optica/frames", json=frame_data, headers=headers)
        assert create_resp.status_code == 200
        frame_id = create_resp.json()["id"]
        
        # Update
        update_data = {"sale_price": 300, "stock": 15}
        response = requests.put(f"{BASE_URL}/api/optica/frames/{frame_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["sale_price"] == 300
        assert data["stock"] == 15
        print(f"✓ Updated frame price to: {data['sale_price']}")
    
    def test_search_frames(self, optica_token):
        """Test searching frames"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        response = requests.get(f"{BASE_URL}/api/optica/frames/search?q=Ray&limit=5", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Frame search returned {len(data)} results")
    
    def test_filter_low_stock(self, optica_token):
        """Test filtering low stock frames"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        response = requests.get(f"{BASE_URL}/api/optica/frames?low_stock=true", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # All returned frames should have stock <= 5
        for frame in data["data"]:
            assert frame["stock"] <= 5, f"Frame {frame['code']} has stock {frame['stock']} > 5"
        print(f"✓ Low stock filter returned {len(data['data'])} frames")
    
    def test_delete_frame(self, optica_token):
        """Test deleting a frame"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        # Create
        frame_data = {
            "brand": "TEST_Delete",
            "code": f"DEL-{datetime.now().strftime('%H%M%S')}",
            "cost_price": 10,
            "sale_price": 20,
            "stock": 1
        }
        create_resp = requests.post(f"{BASE_URL}/api/optica/frames", json=frame_data, headers=headers)
        assert create_resp.status_code == 200
        frame_id = create_resp.json()["id"]
        
        # Delete
        response = requests.delete(f"{BASE_URL}/api/optica/frames/{frame_id}", headers=headers)
        assert response.status_code == 200
        print(f"✓ Deleted frame: {frame_id}")


class TestLensTypes:
    """Tests for Lens Types Catalog CRUD"""
    
    def test_list_lens_types(self, optica_token):
        """Test listing lens types"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        response = requests.get(f"{BASE_URL}/api/optica/lens-types", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "data" in data
        assert "total" in data
        print(f"✓ Listed {data['total']} lens types")
    
    def test_create_lens_type(self, optica_token):
        """Test creating a lens type"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        lens_type_data = {
            "name": f"TEST_Lente Especial {datetime.now().strftime('%H%M%S')}",
            "description": "Lente de prueba",
            "default_price": 350.00
        }
        response = requests.post(f"{BASE_URL}/api/optica/lens-types", json=lens_type_data, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["name"] == lens_type_data["name"]
        assert data["default_price"] == lens_type_data["default_price"]
        assert "id" in data
        print(f"✓ Created lens type: {data['name']} (ID: {data['id']})")
        return data["id"]
    
    def test_update_lens_type(self, optica_token):
        """Test updating a lens type"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        # Create
        lens_type_data = {
            "name": f"TEST_Update {datetime.now().strftime('%H%M%S')}",
            "default_price": 100
        }
        create_resp = requests.post(f"{BASE_URL}/api/optica/lens-types", json=lens_type_data, headers=headers)
        assert create_resp.status_code == 200
        lens_type_id = create_resp.json()["id"]
        
        # Update
        update_data = {"default_price": 200, "description": "Updated description"}
        response = requests.put(f"{BASE_URL}/api/optica/lens-types/{lens_type_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["default_price"] == 200
        assert data["description"] == "Updated description"
        print(f"✓ Updated lens type price to: {data['default_price']}")
    
    def test_delete_lens_type(self, optica_token):
        """Test deleting a lens type"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        # Create
        lens_type_data = {
            "name": f"TEST_Delete {datetime.now().strftime('%H%M%S')}",
            "default_price": 50
        }
        create_resp = requests.post(f"{BASE_URL}/api/optica/lens-types", json=lens_type_data, headers=headers)
        assert create_resp.status_code == 200
        lens_type_id = create_resp.json()["id"]
        
        # Delete
        response = requests.delete(f"{BASE_URL}/api/optica/lens-types/{lens_type_id}", headers=headers)
        assert response.status_code == 200
        print(f"✓ Deleted lens type: {lens_type_id}")


class TestOpticaSales:
    """Tests for Optica Sales"""
    
    def test_list_sales(self, optica_token):
        """Test listing sales"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        response = requests.get(f"{BASE_URL}/api/optica/sales", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "data" in data
        assert "total" in data
        print(f"✓ Listed {data['total']} sales")
    
    def test_create_sale_requires_patient(self, optica_token):
        """Test that creating a sale requires a patient"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        sale_data = {
            "patient_id": "",  # Empty patient
            "payment_method": "efectivo"
        }
        response = requests.post(f"{BASE_URL}/api/optica/sales", json=sale_data, headers=headers)
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print("✓ Sale creation correctly requires patient_id")
    
    def test_create_sale_with_patient(self, optica_token):
        """Test creating a sale with a patient"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        
        # First get a patient
        patients_resp = requests.get(f"{BASE_URL}/api/patients?limit=1", headers=headers)
        if patients_resp.status_code != 200 or not patients_resp.json().get("data"):
            pytest.skip("No patients available for testing")
        
        patient_id = patients_resp.json()["data"][0]["id"]
        
        # Get a frame
        frames_resp = requests.get(f"{BASE_URL}/api/optica/frames?limit=1", headers=headers)
        frame_id = None
        if frames_resp.status_code == 200 and frames_resp.json().get("data"):
            frame_id = frames_resp.json()["data"][0]["id"]
        
        # Get a lens type
        lens_types_resp = requests.get(f"{BASE_URL}/api/optica/lens-types", headers=headers)
        lens_items = []
        if lens_types_resp.status_code == 200 and lens_types_resp.json().get("data"):
            lt = lens_types_resp.json()["data"][0]
            lens_items = [{
                "lens_type_id": lt["id"],
                "quantity": 1,
                "unit_price": lt["default_price"],
                "subtotal": lt["default_price"]
            }]
        
        sale_data = {
            "patient_id": patient_id,
            "frame_id": frame_id,
            "lens_items": lens_items,
            "payment_method": "efectivo",
            "discount_percent": 0,
            "initial_payment": 0,
            "notes": "TEST_Sale created by automated test"
        }
        
        response = requests.post(f"{BASE_URL}/api/optica/sales", json=sale_data, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "order_number" in data
        assert data["patient_id"] == patient_id
        assert data["status"] == "pendiente"
        print(f"✓ Created sale: {data['order_number']} (Total: Q{data['total']})")
        return data["id"]
    
    def test_get_sale_by_id(self, optica_token):
        """Test getting sale by ID"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        
        # Get existing sales
        sales_resp = requests.get(f"{BASE_URL}/api/optica/sales?limit=1", headers=headers)
        if sales_resp.status_code != 200 or not sales_resp.json().get("data"):
            pytest.skip("No sales available for testing")
        
        sale_id = sales_resp.json()["data"][0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/optica/sales/{sale_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sale_id
        print(f"✓ Got sale by ID: {data['order_number']}")
    
    def test_add_payment_to_sale(self, optica_token):
        """Test adding a payment to a pending sale"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        
        # Get a pending sale
        sales_resp = requests.get(f"{BASE_URL}/api/optica/sales?status=pendiente&limit=1", headers=headers)
        if sales_resp.status_code != 200 or not sales_resp.json().get("data"):
            pytest.skip("No pending sales available for testing")
        
        sale = sales_resp.json()["data"][0]
        sale_id = sale["id"]
        balance_due = sale["balance_due"]
        
        if balance_due <= 0:
            pytest.skip("Sale has no balance due")
        
        # Add partial payment
        payment_amount = min(100, balance_due)
        payment_data = {
            "amount": payment_amount,
            "payment_method": "efectivo",
            "reference": "TEST_PAYMENT",
            "notes": "Test payment"
        }
        
        response = requests.post(f"{BASE_URL}/api/optica/sales/{sale_id}/payments", json=payment_data, headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["amount"] == payment_amount
        print(f"✓ Added payment of Q{payment_amount} to sale {sale['order_number']}")


class TestAccessControl:
    """Tests for role-based access control"""
    
    def test_admin_cannot_access_optica_frames(self, admin_token):
        """Test that admin cannot access optica frames"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/optica/frames", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Admin correctly denied access to optica frames")
    
    def test_admin_cannot_access_optica_sales(self, admin_token):
        """Test that admin cannot access optica sales"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/optica/sales", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Admin correctly denied access to optica sales")
    
    def test_admin_cannot_access_doctors(self, admin_token):
        """Test that admin cannot access doctors"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/doctors", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Admin correctly denied access to doctors")
    
    def test_superadmin_can_access_optica(self, superadmin_token):
        """Test that superadmin can access optica module"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        
        # Frames
        frames_resp = requests.get(f"{BASE_URL}/api/optica/frames", headers=headers)
        assert frames_resp.status_code == 200
        
        # Sales
        sales_resp = requests.get(f"{BASE_URL}/api/optica/sales", headers=headers)
        assert sales_resp.status_code == 200
        
        # Doctors
        doctors_resp = requests.get(f"{BASE_URL}/api/doctors", headers=headers)
        assert doctors_resp.status_code == 200
        
        print("✓ SuperAdmin can access all optica endpoints")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_doctors(self, optica_token):
        """Clean up TEST_ prefixed doctors"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        response = requests.get(f"{BASE_URL}/api/doctors", headers=headers)
        if response.status_code == 200:
            doctors = response.json().get("data", [])
            deleted = 0
            for doc in doctors:
                if doc["name"].startswith("TEST_"):
                    del_resp = requests.delete(f"{BASE_URL}/api/doctors/{doc['id']}", headers=headers)
                    if del_resp.status_code == 200:
                        deleted += 1
            print(f"✓ Cleaned up {deleted} test doctors")
    
    def test_cleanup_test_frames(self, optica_token):
        """Clean up TEST_ prefixed frames"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        response = requests.get(f"{BASE_URL}/api/optica/frames", headers=headers)
        if response.status_code == 200:
            frames = response.json().get("data", [])
            deleted = 0
            for frame in frames:
                if frame["brand"].startswith("TEST_") or frame["code"].startswith("TEST"):
                    del_resp = requests.delete(f"{BASE_URL}/api/optica/frames/{frame['id']}", headers=headers)
                    if del_resp.status_code == 200:
                        deleted += 1
            print(f"✓ Cleaned up {deleted} test frames")
    
    def test_cleanup_test_lens_types(self, optica_token):
        """Clean up TEST_ prefixed lens types"""
        headers = {"Authorization": f"Bearer {optica_token}"}
        response = requests.get(f"{BASE_URL}/api/optica/lens-types", headers=headers)
        if response.status_code == 200:
            lens_types = response.json().get("data", [])
            deleted = 0
            for lt in lens_types:
                if lt["name"].startswith("TEST_"):
                    del_resp = requests.delete(f"{BASE_URL}/api/optica/lens-types/{lt['id']}", headers=headers)
                    if del_resp.status_code == 200:
                        deleted += 1
            print(f"✓ Cleaned up {deleted} test lens types")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
