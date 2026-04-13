"""
Test suite for Patients Module (Base de Datos de Pacientes)
Tests CRUD operations, DPI validation, age calculation, IGSS unit conditional field,
record number generation, search endpoint, and export functionality.
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_CREDS = {"username": "superadmin", "password": "nova2024"}
ADMIN_CREDS = {"username": "admin", "password": "admin2024"}
USER_CREDS = {"username": "usuario", "password": "user2024"}


@pytest.fixture(scope="module")
def superadmin_token():
    """Get SuperAdmin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERADMIN_CREDS)
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("SuperAdmin authentication failed")


@pytest.fixture(scope="module")
def admin_token():
    """Get Admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def user_token():
    """Get regular User authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=USER_CREDS)
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("User authentication failed")


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestIGSSUnits:
    """Tests for IGSS Units catalog (SuperAdmin only)"""
    
    created_unit_id = None
    
    def test_superadmin_can_list_igss_units(self, superadmin_token):
        """SuperAdmin can list all IGSS units"""
        response = requests.get(
            f"{BASE_URL}/api/igss-units",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        print(f"IGSS Units count: {data['total']}")
    
    def test_admin_can_read_igss_units(self, admin_token):
        """Admin can read IGSS units (for dropdown when creating patients)"""
        response = requests.get(
            f"{BASE_URL}/api/igss-units",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print("Admin can read IGSS units for patient creation")
    
    def test_admin_cannot_create_igss_units(self, admin_token):
        """Admin cannot create IGSS units (403)"""
        payload = {"name": "TEST_Admin Unit", "code": "ADM-001"}
        response = requests.post(
            f"{BASE_URL}/api/igss-units",
            json=payload,
            headers=auth_header(admin_token)
        )
        assert response.status_code == 403
        print("Admin correctly denied IGSS unit creation")
    
    def test_user_can_read_igss_units(self, user_token):
        """Regular user can read IGSS units (for viewing patient details)"""
        response = requests.get(
            f"{BASE_URL}/api/igss-units",
            headers=auth_header(user_token)
        )
        assert response.status_code == 200
        print("User can read IGSS units")
    
    def test_user_cannot_create_igss_units(self, user_token):
        """Regular user cannot create IGSS units (403)"""
        payload = {"name": "TEST_User Unit", "code": "USR-001"}
        response = requests.post(
            f"{BASE_URL}/api/igss-units",
            json=payload,
            headers=auth_header(user_token)
        )
        assert response.status_code == 403
        print("User correctly denied IGSS unit creation")
    
    def test_superadmin_can_create_igss_unit(self, superadmin_token):
        """SuperAdmin can create a new IGSS unit"""
        payload = {
            "name": "TEST_Hospital General de Enfermedades",
            "code": "HGE-001",
            "description": "Hospital principal del IGSS"
        }
        response = requests.post(
            f"{BASE_URL}/api/igss-units",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["code"] == payload["code"]
        assert "id" in data
        TestIGSSUnits.created_unit_id = data["id"]
        print(f"Created IGSS unit: {data['name']} (ID: {data['id']})")
    
    def test_superadmin_can_get_igss_unit_by_id(self, superadmin_token):
        """SuperAdmin can get a specific IGSS unit"""
        if not TestIGSSUnits.created_unit_id:
            pytest.skip("No unit created to fetch")
        
        response = requests.get(
            f"{BASE_URL}/api/igss-units/{TestIGSSUnits.created_unit_id}",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == TestIGSSUnits.created_unit_id
        print(f"Fetched IGSS unit: {data['name']}")
    
    def test_superadmin_can_update_igss_unit(self, superadmin_token):
        """SuperAdmin can update an IGSS unit"""
        if not TestIGSSUnits.created_unit_id:
            pytest.skip("No unit created to update")
        
        payload = {
            "description": "Hospital principal del IGSS - Zona 9"
        }
        response = requests.put(
            f"{BASE_URL}/api/igss-units/{TestIGSSUnits.created_unit_id}",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == payload["description"]
        print(f"Updated IGSS unit description")
    
    def test_duplicate_igss_unit_name_rejected(self, superadmin_token):
        """Duplicate IGSS unit name should be rejected"""
        payload = {
            "name": "TEST_Hospital General de Enfermedades",
            "code": "HGE-002"
        }
        response = requests.post(
            f"{BASE_URL}/api/igss-units",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 400
        print("Duplicate IGSS unit name correctly rejected")


class TestPatientsCRUD:
    """Tests for Patient CRUD operations"""
    
    created_patient_id = None
    created_patient_record_number = None
    
    def test_superadmin_can_list_patients(self, superadmin_token):
        """SuperAdmin can list all patients"""
        response = requests.get(
            f"{BASE_URL}/api/patients",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "total_pages" in data
        print(f"Patients count: {data['total']}")
    
    def test_admin_can_list_patients(self, admin_token):
        """Admin can list all patients"""
        response = requests.get(
            f"{BASE_URL}/api/patients",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print("Admin can list patients")
    
    def test_user_can_list_patients(self, user_token):
        """Regular user can list patients (view_patients permission)"""
        response = requests.get(
            f"{BASE_URL}/api/patients",
            headers=auth_header(user_token)
        )
        assert response.status_code == 200
        print("User can list patients (read-only)")
    
    def test_superadmin_can_create_patient(self, superadmin_token):
        """SuperAdmin can create a new patient with all fields"""
        # Calculate a birth date for a 30-year-old
        birth_date = (datetime.now() - timedelta(days=30*365)).strftime("%Y-%m-%d")
        
        payload = {
            "first_name": "TEST_Juan",
            "last_name": "Pérez García",
            "gender": "masculino",
            "birth_date": birth_date,
            "profession": "Ingeniero",
            "phone": "55551234",
            "email": "test.juan@example.com",
            "dpi": "9999999999901",
            "emergency_phone": "55559999",
            "emergency_contact_name": "María Pérez",
            "emergency_contact_relationship": "Esposa",
            "referral_institution": "particular",
            "comments": "Paciente de prueba"
        }
        response = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["first_name"] == payload["first_name"]
        assert data["last_name"] == payload["last_name"]
        assert data["gender"] == payload["gender"]
        assert data["dpi"] == payload["dpi"]
        assert "id" in data
        assert "record_number" in data
        assert "age" in data
        assert "full_name" in data
        
        # Verify record number format (EXP-YYYYMM-XXXX)
        assert data["record_number"].startswith("EXP-")
        
        # Verify age calculation (should be around 30)
        assert 29 <= data["age"] <= 31
        
        TestPatientsCRUD.created_patient_id = data["id"]
        TestPatientsCRUD.created_patient_record_number = data["record_number"]
        print(f"Created patient: {data['full_name']} (Record: {data['record_number']}, Age: {data['age']})")
    
    def test_admin_can_create_patient(self, admin_token):
        """Admin can create a new patient"""
        birth_date = (datetime.now() - timedelta(days=25*365)).strftime("%Y-%m-%d")
        
        payload = {
            "first_name": "TEST_María",
            "last_name": "López Hernández",
            "gender": "femenino",
            "birth_date": birth_date,
            "phone": "55552345",
            "referral_institution": "particular"
        }
        response = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload,
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == payload["first_name"]
        print(f"Admin created patient: {data['full_name']}")
    
    def test_user_cannot_create_patient(self, user_token):
        """Regular user cannot create patients (403)"""
        payload = {
            "first_name": "TEST_Unauthorized",
            "last_name": "User",
            "gender": "masculino",
            "birth_date": "1990-01-01",
            "phone": "55550000",
            "referral_institution": "particular"
        }
        response = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload,
            headers=auth_header(user_token)
        )
        assert response.status_code == 403
        print("User correctly denied patient creation")
    
    def test_get_patient_by_id(self, superadmin_token):
        """Can get patient details by ID"""
        if not TestPatientsCRUD.created_patient_id:
            pytest.skip("No patient created to fetch")
        
        response = requests.get(
            f"{BASE_URL}/api/patients/{TestPatientsCRUD.created_patient_id}",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == TestPatientsCRUD.created_patient_id
        assert "age" in data  # Age should be calculated dynamically
        print(f"Fetched patient: {data['full_name']}")
    
    def test_update_patient(self, superadmin_token):
        """SuperAdmin can update patient data"""
        if not TestPatientsCRUD.created_patient_id:
            pytest.skip("No patient created to update")
        
        payload = {
            "profession": "Ingeniero Civil",
            "comments": "Paciente actualizado"
        }
        response = requests.put(
            f"{BASE_URL}/api/patients/{TestPatientsCRUD.created_patient_id}",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["profession"] == payload["profession"]
        assert data["comments"] == payload["comments"]
        print(f"Updated patient profession to: {data['profession']}")
    
    def test_user_cannot_update_patient(self, user_token):
        """Regular user cannot update patients (403)"""
        if not TestPatientsCRUD.created_patient_id:
            pytest.skip("No patient created to update")
        
        payload = {"profession": "Hacker"}
        response = requests.put(
            f"{BASE_URL}/api/patients/{TestPatientsCRUD.created_patient_id}",
            json=payload,
            headers=auth_header(user_token)
        )
        assert response.status_code == 403
        print("User correctly denied patient update")


class TestDPIValidation:
    """Tests for DPI validation (13 digits, unique)"""
    
    def test_dpi_must_be_13_digits(self, superadmin_token):
        """DPI must be exactly 13 digits"""
        payload = {
            "first_name": "TEST_Invalid",
            "last_name": "DPI",
            "gender": "masculino",
            "birth_date": "1990-01-01",
            "phone": "55550001",
            "dpi": "12345",  # Invalid: too short
            "referral_institution": "particular"
        }
        response = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 422
        print("Short DPI correctly rejected (422)")
    
    def test_dpi_too_long_rejected(self, superadmin_token):
        """DPI longer than 13 digits should be rejected"""
        payload = {
            "first_name": "TEST_Invalid",
            "last_name": "DPI Long",
            "gender": "masculino",
            "birth_date": "1990-01-01",
            "phone": "55550002",
            "dpi": "12345678901234567",  # Invalid: too long
            "referral_institution": "particular"
        }
        response = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 422
        print("Long DPI correctly rejected (422)")
    
    def test_duplicate_dpi_rejected(self, superadmin_token):
        """Duplicate DPI should be rejected"""
        # First create a patient with a specific DPI
        payload1 = {
            "first_name": "TEST_Original",
            "last_name": "DPI Owner",
            "gender": "masculino",
            "birth_date": "1990-01-01",
            "phone": "55550003",
            "dpi": "8888888888888",
            "referral_institution": "particular"
        }
        response1 = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload1,
            headers=auth_header(superadmin_token)
        )
        assert response1.status_code == 200
        
        # Try to create another patient with the same DPI
        payload2 = {
            "first_name": "TEST_Duplicate",
            "last_name": "DPI Attempt",
            "gender": "femenino",
            "birth_date": "1985-05-15",
            "phone": "55550004",
            "dpi": "8888888888888",  # Same DPI
            "referral_institution": "particular"
        }
        response2 = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload2,
            headers=auth_header(superadmin_token)
        )
        assert response2.status_code == 400
        assert "DPI" in response2.json().get("detail", "")
        print("Duplicate DPI correctly rejected (400)")


class TestIGSSConditionalField:
    """Tests for IGSS unit conditional field"""
    
    igss_unit_id = None
    
    def test_create_igss_unit_for_patient(self, superadmin_token):
        """Create an IGSS unit to use with patient"""
        payload = {
            "name": "TEST_Unidad Periférica Zona 5",
            "code": "UPZ5-001"
        }
        response = requests.post(
            f"{BASE_URL}/api/igss-units",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        TestIGSSConditionalField.igss_unit_id = response.json()["id"]
        print(f"Created IGSS unit for patient test: {response.json()['name']}")
    
    def test_patient_with_igss_institution_requires_unit(self, superadmin_token):
        """Patient with IGSS institution should have igss_unit_id"""
        if not TestIGSSConditionalField.igss_unit_id:
            pytest.skip("No IGSS unit created")
        
        payload = {
            "first_name": "TEST_IGSS",
            "last_name": "Patient",
            "gender": "masculino",
            "birth_date": "1980-06-15",
            "phone": "55550005",
            "referral_institution": "igss",
            "igss_unit_id": TestIGSSConditionalField.igss_unit_id
        }
        response = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["referral_institution"] == "igss"
        assert data["igss_unit_id"] == TestIGSSConditionalField.igss_unit_id
        # Should have igss_unit_name populated
        assert "igss_unit_name" in data
        print(f"Created IGSS patient with unit: {data.get('igss_unit_name', 'N/A')}")
    
    def test_patient_with_seguro_privado(self, superadmin_token):
        """Patient with seguro_privado should have insurance_name"""
        payload = {
            "first_name": "TEST_Seguro",
            "last_name": "Privado Patient",
            "gender": "femenino",
            "birth_date": "1975-03-20",
            "phone": "55550006",
            "referral_institution": "seguro_privado",
            "insurance_name": "Seguros G&T Continental"
        }
        response = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["referral_institution"] == "seguro_privado"
        assert data["insurance_name"] == payload["insurance_name"]
        print(f"Created seguro_privado patient with insurance: {data['insurance_name']}")
    
    def test_patient_with_otra_institution(self, superadmin_token):
        """Patient with 'otra' institution should have other_institution_name"""
        payload = {
            "first_name": "TEST_Otra",
            "last_name": "Institution Patient",
            "gender": "otro",
            "birth_date": "1995-11-10",
            "phone": "55550007",
            "referral_institution": "otra",
            "other_institution_name": "Universidad San Carlos"
        }
        response = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["referral_institution"] == "otra"
        assert data["other_institution_name"] == payload["other_institution_name"]
        print(f"Created 'otra' institution patient: {data['other_institution_name']}")


class TestPatientSearch:
    """Tests for patient search endpoint (autocomplete)"""
    
    def test_search_patients_by_name(self, superadmin_token):
        """Search patients by name"""
        response = requests.get(
            f"{BASE_URL}/api/patients/search?q=TEST_",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Search returned {len(data)} patients matching 'TEST_'")
    
    def test_search_patients_by_dpi(self, superadmin_token):
        """Search patients by DPI"""
        response = requests.get(
            f"{BASE_URL}/api/patients/search?q=9999999999901",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Search by DPI returned {len(data)} patients")
    
    def test_search_returns_correct_fields(self, superadmin_token):
        """Search response should have id, record_number, full_name, dpi, phone"""
        response = requests.get(
            f"{BASE_URL}/api/patients/search?q=TEST_&limit=1",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            patient = data[0]
            assert "id" in patient
            assert "record_number" in patient
            assert "full_name" in patient
            assert "phone" in patient
            print(f"Search result fields verified: {list(patient.keys())}")
        else:
            print("No patients found for search verification")


class TestPatientFilters:
    """Tests for patient list filters"""
    
    def test_filter_by_referral_institution(self, superadmin_token):
        """Filter patients by referral institution"""
        response = requests.get(
            f"{BASE_URL}/api/patients?referral_institution=particular",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        # All returned patients should have particular institution
        for patient in data["data"]:
            assert patient["referral_institution"] == "particular"
        print(f"Filter by 'particular' returned {len(data['data'])} patients")
    
    def test_filter_by_gender(self, superadmin_token):
        """Filter patients by gender"""
        response = requests.get(
            f"{BASE_URL}/api/patients?gender=femenino",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        for patient in data["data"]:
            assert patient["gender"] == "femenino"
        print(f"Filter by 'femenino' returned {len(data['data'])} patients")
    
    def test_pagination(self, superadmin_token):
        """Test pagination parameters"""
        response = requests.get(
            f"{BASE_URL}/api/patients?page=1&limit=5",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 5
        assert len(data["data"]) <= 5
        print(f"Pagination: page {data['page']}, limit {data['limit']}, total {data['total']}")


class TestDuplicateCheck:
    """Tests for duplicate patient check endpoint"""
    
    def test_check_duplicate_by_dpi(self, superadmin_token):
        """Check duplicate by DPI"""
        response = requests.get(
            f"{BASE_URL}/api/patients/check-duplicate?dpi=9999999999901",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "exists" in data
        if data["exists"]:
            assert data["match_type"] == "dpi"
            print(f"Duplicate found by DPI: {data.get('patient_name', 'N/A')}")
        else:
            print("No duplicate found by DPI")
    
    def test_check_duplicate_by_name_birthdate(self, superadmin_token):
        """Check duplicate by name and birth date"""
        response = requests.get(
            f"{BASE_URL}/api/patients/check-duplicate?first_name=TEST_Juan&last_name=Pérez García&birth_date=1995-01-01",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "exists" in data
        print(f"Duplicate check by name/birthdate: exists={data['exists']}")


class TestRecordNumberGeneration:
    """Tests for correlative record number generation"""
    
    def test_record_number_format(self, superadmin_token):
        """Record number should follow EXP-YYYYMM-XXXX format"""
        payload = {
            "first_name": "TEST_Record",
            "last_name": "Number Test",
            "gender": "masculino",
            "birth_date": "1990-01-01",
            "phone": "55550008",
            "referral_institution": "particular"
        }
        response = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        record_number = data["record_number"]
        
        # Verify format: EXP-YYYYMM-XXXX
        assert record_number.startswith("EXP-")
        parts = record_number.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 6  # YYYYMM
        assert len(parts[2]) == 4  # XXXX
        print(f"Record number format verified: {record_number}")


class TestSoftDelete:
    """Tests for patient soft delete (deactivation)"""
    
    patient_to_delete_id = None
    
    def test_create_patient_for_deletion(self, superadmin_token):
        """Create a patient to test deletion"""
        payload = {
            "first_name": "TEST_ToDelete",
            "last_name": "Patient",
            "gender": "masculino",
            "birth_date": "1990-01-01",
            "phone": "55550009",
            "referral_institution": "particular"
        }
        response = requests.post(
            f"{BASE_URL}/api/patients",
            json=payload,
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        TestSoftDelete.patient_to_delete_id = response.json()["id"]
        print(f"Created patient for deletion test: {response.json()['full_name']}")
    
    def test_admin_cannot_delete_patient(self, admin_token):
        """Admin cannot delete patients (403)"""
        if not TestSoftDelete.patient_to_delete_id:
            pytest.skip("No patient created for deletion")
        
        response = requests.delete(
            f"{BASE_URL}/api/patients/{TestSoftDelete.patient_to_delete_id}",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 403
        print("Admin correctly denied patient deletion")
    
    def test_user_cannot_delete_patient(self, user_token):
        """Regular user cannot delete patients (403)"""
        if not TestSoftDelete.patient_to_delete_id:
            pytest.skip("No patient created for deletion")
        
        response = requests.delete(
            f"{BASE_URL}/api/patients/{TestSoftDelete.patient_to_delete_id}",
            headers=auth_header(user_token)
        )
        assert response.status_code == 403
        print("User correctly denied patient deletion")
    
    def test_superadmin_can_delete_patient(self, superadmin_token):
        """SuperAdmin can soft delete (deactivate) a patient"""
        if not TestSoftDelete.patient_to_delete_id:
            pytest.skip("No patient created for deletion")
        
        response = requests.delete(
            f"{BASE_URL}/api/patients/{TestSoftDelete.patient_to_delete_id}",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        print("SuperAdmin successfully deactivated patient")
    
    def test_deleted_patient_not_in_active_list(self, superadmin_token):
        """Deactivated patient should not appear in active list by default"""
        if not TestSoftDelete.patient_to_delete_id:
            pytest.skip("No patient created for deletion")
        
        response = requests.get(
            f"{BASE_URL}/api/patients?is_active=true",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        patient_ids = [p["id"] for p in data["data"]]
        assert TestSoftDelete.patient_to_delete_id not in patient_ids
        print("Deactivated patient not in active list")
    
    def test_superadmin_can_reactivate_patient(self, superadmin_token):
        """SuperAdmin can reactivate a deactivated patient"""
        if not TestSoftDelete.patient_to_delete_id:
            pytest.skip("No patient created for reactivation")
        
        response = requests.post(
            f"{BASE_URL}/api/patients/{TestSoftDelete.patient_to_delete_id}/reactivate",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] == True
        print("SuperAdmin successfully reactivated patient")


class TestExportEndpoints:
    """Tests for patient export endpoints"""
    
    def test_export_excel_endpoint_exists(self, superadmin_token):
        """Excel export endpoint should be accessible"""
        response = requests.get(
            f"{BASE_URL}/api/patients/export/excel",
            headers=auth_header(superadmin_token)
        )
        # Should return 200 with Excel file or appropriate response
        assert response.status_code == 200
        assert "spreadsheet" in response.headers.get("content-type", "") or "octet-stream" in response.headers.get("content-type", "")
        print(f"Excel export returned content-type: {response.headers.get('content-type')}")
    
    def test_export_pdf_endpoint_exists(self, superadmin_token):
        """PDF export endpoint should be accessible"""
        response = requests.get(
            f"{BASE_URL}/api/patients/export/pdf",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        assert "pdf" in response.headers.get("content-type", "")
        print(f"PDF export returned content-type: {response.headers.get('content-type')}")
    
    def test_download_template_endpoint(self, superadmin_token):
        """Import template download should be accessible"""
        response = requests.get(
            f"{BASE_URL}/api/patients/export/template",
            headers=auth_header(superadmin_token)
        )
        assert response.status_code == 200
        print(f"Template download returned content-type: {response.headers.get('content-type')}")
    
    def test_user_cannot_export(self, user_token):
        """Regular user cannot export patients (403)"""
        response = requests.get(
            f"{BASE_URL}/api/patients/export/excel",
            headers=auth_header(user_token)
        )
        assert response.status_code == 403
        print("User correctly denied export access")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_patients(self, superadmin_token):
        """Clean up TEST_ prefixed patients"""
        # Get all patients
        response = requests.get(
            f"{BASE_URL}/api/patients?limit=100",
            headers=auth_header(superadmin_token)
        )
        if response.status_code == 200:
            patients = response.json()["data"]
            deleted_count = 0
            for patient in patients:
                if patient["first_name"].startswith("TEST_"):
                    # Hard delete by deactivating (soft delete)
                    requests.delete(
                        f"{BASE_URL}/api/patients/{patient['id']}",
                        headers=auth_header(superadmin_token)
                    )
                    deleted_count += 1
            print(f"Cleaned up {deleted_count} test patients")
    
    def test_cleanup_test_igss_units(self, superadmin_token):
        """Clean up TEST_ prefixed IGSS units"""
        response = requests.get(
            f"{BASE_URL}/api/igss-units",
            headers=auth_header(superadmin_token)
        )
        if response.status_code == 200:
            units = response.json()["data"]
            deleted_count = 0
            for unit in units:
                if unit["name"].startswith("TEST_"):
                    requests.delete(
                        f"{BASE_URL}/api/igss-units/{unit['id']}",
                        headers=auth_header(superadmin_token)
                    )
                    deleted_count += 1
            print(f"Cleaned up {deleted_count} test IGSS units")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
