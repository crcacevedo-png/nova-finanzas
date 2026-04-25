"""
Test Suite for Sala de Operaciones (Surgery Module)
Tests CRUD operations for surgeries, equipment, supplies, and report exports.
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_CREDS = {"username": "superadmin", "password": "nova2024"}
ADMIN_CREDS = {"username": "admin", "password": "admin2024"}

# Store tokens and test data
tokens = {}
test_data = {}


class TestSurgeryAuth:
    """Authentication tests for surgery module"""
    
    def test_01_superadmin_login(self):
        """SuperAdmin can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERADMIN_CREDS)
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        tokens["superadmin"] = data["access_token"]
        print(f"SuperAdmin login successful, role: {data['user']['role']}")
    
    def test_02_admin_login(self):
        """Admin can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        tokens["admin"] = data["access_token"]
        print(f"Admin login successful, role: {data['user']['role']}")


class TestSurgeryList:
    """Tests for GET /api/surgeries endpoint"""
    
    def test_03_get_surgeries_list(self):
        """Can retrieve list of surgeries"""
        headers = {"Authorization": f"Bearer {tokens['superadmin']}"}
        response = requests.get(f"{BASE_URL}/api/surgeries", headers=headers)
        assert response.status_code == 200, f"Failed to get surgeries: {response.text}"
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "total_pages" in data
        print(f"Retrieved {len(data['data'])} surgeries, total: {data['total']}")
        
        # Store first surgery for later tests
        if data['data']:
            test_data['existing_surgery'] = data['data'][0]
    
    def test_04_get_surgeries_with_filters(self):
        """Can filter surgeries by surgeon, institution, eye"""
        headers = {"Authorization": f"Bearer {tokens['superadmin']}"}
        
        # Filter by institution
        response = requests.get(f"{BASE_URL}/api/surgeries?institution=IGSS", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"IGSS surgeries: {len(data['data'])}")
        
        # Filter by eye
        response = requests.get(f"{BASE_URL}/api/surgeries?eye=OD", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"OD surgeries: {len(data['data'])}")
    
    def test_05_get_surgery_options(self):
        """Can retrieve surgery options (surgeons, institutions, anesthesiologists)"""
        headers = {"Authorization": f"Bearer {tokens['superadmin']}"}
        response = requests.get(f"{BASE_URL}/api/surgeries/options", headers=headers)
        assert response.status_code == 200, f"Failed to get options: {response.text}"
        data = response.json()
        assert "surgeons" in data
        assert "institutions" in data
        assert "anesthesiologists" in data
        print(f"Options: {len(data['surgeons'])} surgeons, {len(data['institutions'])} institutions")


class TestSurgeryCRUD:
    """Tests for surgery CRUD operations"""
    
    def test_06_create_surgery_without_igss(self):
        """Admin can create a surgery without IGSS data"""
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        surgery_data = {
            "date": "2026-04-15",
            "time": "10:00",
            "patient_name": "TEST_Paciente Prueba",
            "procedure": "Facoemulsificación + LIO",
            "surgeon": "Dr. Test Surgeon",
            "eye": "OD",
            "anesthesia_type": "local",
            "anesthesiologist": "Dr. Test Anesthesiologist",
            "institution": "Privado",
            "observations": "Cirugía de prueba sin IGSS"
        }
        
        response = requests.post(f"{BASE_URL}/api/surgeries", json=surgery_data, headers=headers)
        assert response.status_code == 200, f"Failed to create surgery: {response.text}"
        data = response.json()
        assert data["patient_name"] == surgery_data["patient_name"]
        assert data["procedure"] == surgery_data["procedure"]
        assert data["institution"] == "Privado"
        assert data["igss_data"] is None
        test_data['surgery_no_igss'] = data
        print(f"Created surgery without IGSS: {data['id']}")
    
    def test_07_create_surgery_with_igss(self):
        """Admin can create a surgery with IGSS data"""
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        surgery_data = {
            "date": "2026-04-16",
            "time": "08:30",
            "patient_name": "TEST_Paciente IGSS",
            "procedure": "Vitrectomía",
            "surgeon": "Dr. Test Surgeon",
            "eye": "OI",
            "anesthesia_type": "retrobulbar",
            "anesthesiologist": "Dr. Test Anesthesiologist",
            "institution": "IGSS",
            "igss_data": {
                "unit": "Consulta Externa Z.9",
                "sps": "1234567",
                "affiliation_number": "A-123456",
                "code": "OFT-002",
                "procedure_cost": 4500.00
            },
            "observations": "Cirugía de prueba con IGSS"
        }
        
        response = requests.post(f"{BASE_URL}/api/surgeries", json=surgery_data, headers=headers)
        assert response.status_code == 200, f"Failed to create surgery: {response.text}"
        data = response.json()
        assert data["patient_name"] == surgery_data["patient_name"]
        assert data["institution"] == "IGSS"
        assert data["igss_data"] is not None
        assert data["igss_data"]["procedure_cost"] == 4500.00
        assert data["igss_data"]["unit"] == "Consulta Externa Z.9"
        test_data['surgery_with_igss'] = data
        print(f"Created surgery with IGSS: {data['id']}, cost: {data['igss_data']['procedure_cost']}")
    
    def test_08_get_surgery_by_id(self):
        """Can retrieve a specific surgery by ID"""
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        surgery_id = test_data['surgery_with_igss']['id']
        
        response = requests.get(f"{BASE_URL}/api/surgeries/{surgery_id}", headers=headers)
        assert response.status_code == 200, f"Failed to get surgery: {response.text}"
        data = response.json()
        assert data["id"] == surgery_id
        assert data["patient_name"] == "TEST_Paciente IGSS"
        print(f"Retrieved surgery: {data['patient_name']}")
    
    def test_09_update_surgery(self):
        """Admin can update a surgery"""
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        surgery_id = test_data['surgery_no_igss']['id']
        
        update_data = {
            "observations": "Observaciones actualizadas por prueba",
            "time": "11:00"
        }
        
        response = requests.put(f"{BASE_URL}/api/surgeries/{surgery_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Failed to update surgery: {response.text}"
        data = response.json()
        assert data["observations"] == update_data["observations"]
        assert data["time"] == "11:00"
        print(f"Updated surgery: {data['id']}")
    
    def test_10_admin_cannot_delete_surgery(self):
        """Admin cannot delete a surgery (only SuperAdmin can)"""
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        surgery_id = test_data['surgery_no_igss']['id']
        
        response = requests.delete(f"{BASE_URL}/api/surgeries/{surgery_id}", headers=headers)
        assert response.status_code == 403, f"Admin should not be able to delete: {response.text}"
        print("Admin correctly denied delete permission")


class TestSurgeryEquipment:
    """Tests for surgery equipment management"""
    
    def test_11_add_equipment_to_surgery(self):
        """Can add equipment to a surgery"""
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        surgery_id = test_data['surgery_with_igss']['id']
        
        equipment_data = {
            "name": "TEST_Facoemulsificador Centurion",
            "quantity": 1,
            "notes": "Equipo de prueba"
        }
        
        response = requests.post(f"{BASE_URL}/api/surgeries/{surgery_id}/equipment", json=equipment_data, headers=headers)
        assert response.status_code == 200, f"Failed to add equipment: {response.text}"
        data = response.json()
        assert len(data["equipment"]) > 0
        
        # Find the added equipment
        added_eq = next((e for e in data["equipment"] if e["name"] == equipment_data["name"]), None)
        assert added_eq is not None
        test_data['equipment_id'] = added_eq['id']
        print(f"Added equipment: {added_eq['name']}")
    
    def test_12_delete_equipment_from_surgery(self):
        """Can delete equipment from a surgery"""
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        surgery_id = test_data['surgery_with_igss']['id']
        equipment_id = test_data['equipment_id']
        
        response = requests.delete(f"{BASE_URL}/api/surgeries/{surgery_id}/equipment/{equipment_id}", headers=headers)
        assert response.status_code == 200, f"Failed to delete equipment: {response.text}"
        data = response.json()
        
        # Verify equipment was removed
        remaining_eq = [e for e in data["equipment"] if e["id"] == equipment_id]
        assert len(remaining_eq) == 0
        print(f"Deleted equipment: {equipment_id}")


class TestSurgerySupplies:
    """Tests for surgery supplies management"""
    
    def test_13_add_supply_to_surgery(self):
        """Can add supply with cost to a surgery"""
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        surgery_id = test_data['surgery_with_igss']['id']
        
        supply_data = {
            "name": "TEST_Lente AcrySof IQ",
            "category": "lente",
            "quantity": 1,
            "unit_cost": 2800.00,
            "notes": "Insumo de prueba"
        }
        
        response = requests.post(f"{BASE_URL}/api/surgeries/{surgery_id}/supplies", json=supply_data, headers=headers)
        assert response.status_code == 200, f"Failed to add supply: {response.text}"
        data = response.json()
        assert len(data["supplies"]) > 0
        
        # Find the added supply
        added_sup = next((s for s in data["supplies"] if s["name"] == supply_data["name"]), None)
        assert added_sup is not None
        assert added_sup["total_cost"] == 2800.00  # quantity * unit_cost
        test_data['supply_id'] = added_sup['id']
        print(f"Added supply: {added_sup['name']}, total_cost: {added_sup['total_cost']}")
    
    def test_14_add_multiple_supplies(self):
        """Can add multiple supplies and verify cost calculation"""
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        surgery_id = test_data['surgery_with_igss']['id']
        
        supply_data = {
            "name": "TEST_Viscoelástico Healon",
            "category": "viscoelastico",
            "quantity": 2,
            "unit_cost": 450.00,
            "notes": ""
        }
        
        response = requests.post(f"{BASE_URL}/api/surgeries/{surgery_id}/supplies", json=supply_data, headers=headers)
        assert response.status_code == 200, f"Failed to add supply: {response.text}"
        data = response.json()
        
        # Find the added supply
        added_sup = next((s for s in data["supplies"] if s["name"] == supply_data["name"]), None)
        assert added_sup is not None
        assert added_sup["total_cost"] == 900.00  # 2 * 450
        test_data['supply_id_2'] = added_sup['id']
        print(f"Added supply: {added_sup['name']}, qty: {added_sup['quantity']}, total: {added_sup['total_cost']}")
    
    def test_15_verify_total_cost_calculation(self):
        """Verify total cost = procedure_cost + supplies_total"""
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        surgery_id = test_data['surgery_with_igss']['id']
        
        response = requests.get(f"{BASE_URL}/api/surgeries/{surgery_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        procedure_cost = data["igss_data"]["procedure_cost"] if data["igss_data"] else 0
        supplies_total = sum(s["total_cost"] for s in data["supplies"])
        total_general = procedure_cost + supplies_total
        
        print(f"Procedure cost: {procedure_cost}")
        print(f"Supplies total: {supplies_total}")
        print(f"Total general: {total_general}")
        
        # Expected: 4500 (procedure) + 2800 (lente) + 900 (viscoelastico) = 8200
        assert procedure_cost == 4500.00
        assert supplies_total >= 3700.00  # At least our test supplies
    
    def test_16_delete_supply_from_surgery(self):
        """Can delete supply from a surgery"""
        headers = {"Authorization": f"Bearer {tokens['admin']}"}
        surgery_id = test_data['surgery_with_igss']['id']
        supply_id = test_data['supply_id_2']
        
        response = requests.delete(f"{BASE_URL}/api/surgeries/{surgery_id}/supplies/{supply_id}", headers=headers)
        assert response.status_code == 200, f"Failed to delete supply: {response.text}"
        data = response.json()
        
        # Verify supply was removed
        remaining_sup = [s for s in data["supplies"] if s["id"] == supply_id]
        assert len(remaining_sup) == 0
        print(f"Deleted supply: {supply_id}")


class TestSurgeryCancel:
    """Tests for surgery cancellation"""
    
    def test_17_cancel_surgery_with_reason(self):
        """SuperAdmin can cancel a surgery with reason"""
        headers = {"Authorization": f"Bearer {tokens['superadmin']}"}
        surgery_id = test_data['surgery_no_igss']['id']
        
        cancel_data = {
            "reason": "Paciente no se presentó",
            "reschedule_date": "2026-04-20"
        }
        
        response = requests.post(f"{BASE_URL}/api/surgeries/{surgery_id}/cancel", json=cancel_data, headers=headers)
        assert response.status_code == 200, f"Failed to cancel surgery: {response.text}"
        data = response.json()
        assert data["status"] == "cancelado"
        assert data["cancellation_reason"] == cancel_data["reason"]
        assert data["rescheduled_to"] == cancel_data["reschedule_date"]
        print(f"Cancelled surgery: {data['id']}, reason: {data['cancellation_reason']}")


class TestSurgeryReports:
    """Tests for surgery report exports"""
    
    def test_18_export_surgeries_excel(self):
        """Can export surgeries to Excel format"""
        headers = {"Authorization": f"Bearer {tokens['superadmin']}"}
        
        response = requests.get(f"{BASE_URL}/api/reports/surgeries?format=xlsx", headers=headers)
        assert response.status_code == 200, f"Failed to export Excel: {response.text}"
        assert response.headers.get('content-type') == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert len(response.content) > 0
        print(f"Excel export successful, size: {len(response.content)} bytes")
    
    def test_19_export_surgeries_pdf(self):
        """Can export surgeries to PDF format"""
        headers = {"Authorization": f"Bearer {tokens['superadmin']}"}
        
        response = requests.get(f"{BASE_URL}/api/reports/surgeries?format=pdf", headers=headers)
        assert response.status_code == 200, f"Failed to export PDF: {response.text}"
        assert response.headers.get('content-type') == 'application/pdf'
        assert len(response.content) > 0
        print(f"PDF export successful, size: {len(response.content)} bytes")
    
    def test_20_export_with_filters(self):
        """Can export surgeries with date filters"""
        headers = {"Authorization": f"Bearer {tokens['superadmin']}"}
        
        response = requests.get(
            f"{BASE_URL}/api/reports/surgeries?format=xlsx&dateFrom=2026-04-01&dateTo=2026-04-30&institution=IGSS",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to export with filters: {response.text}"
        print(f"Filtered export successful, size: {len(response.content)} bytes")


class TestSurgeryDelete:
    """Tests for surgery deletion (SuperAdmin only)"""
    
    def test_21_superadmin_can_delete_surgery(self):
        """SuperAdmin can delete a surgery"""
        headers = {"Authorization": f"Bearer {tokens['superadmin']}"}
        surgery_id = test_data['surgery_with_igss']['id']
        
        response = requests.delete(f"{BASE_URL}/api/surgeries/{surgery_id}", headers=headers)
        assert response.status_code == 200, f"Failed to delete surgery: {response.text}"
        print(f"Deleted surgery: {surgery_id}")
        
        # Verify deletion
        response = requests.get(f"{BASE_URL}/api/surgeries/{surgery_id}", headers=headers)
        assert response.status_code == 404
        print("Verified surgery was deleted")
    
    def test_22_cleanup_test_data(self):
        """Clean up remaining test data"""
        headers = {"Authorization": f"Bearer {tokens['superadmin']}"}
        
        # Delete the cancelled surgery
        if 'surgery_no_igss' in test_data:
            surgery_id = test_data['surgery_no_igss']['id']
            response = requests.delete(f"{BASE_URL}/api/surgeries/{surgery_id}", headers=headers)
            if response.status_code == 200:
                print(f"Cleaned up surgery: {surgery_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
