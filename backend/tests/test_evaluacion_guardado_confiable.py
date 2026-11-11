"""Regression tests: Evaluación Oftalmológica reliable save (legacy null / string items -> no 422/500)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
PACIENTE_ID = "8c8723a3-bed5-467a-b894-9500bd191e02"  # María García López (seed)
LEGACY_EVAL_ID = "0aa16779-7517-43e7-930c-303c0a55a5c7"


@pytest.fixture(scope="module")
def s():
    r = requests.post(f"{API}/auth/login", json={"username": "superadmin", "password": "nova2024"}, timeout=30)
    if r.status_code != 200:
        pytest.skip("login failed")
    sess = requests.Session()
    sess.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return sess


@pytest.fixture(scope="module")
def created_ids(s):
    ids = []
    yield ids
    for i in ids:
        s.delete(f"{API}/evaluaciones/{i}", timeout=30)


# --- Legacy corrupted record read / autosave / update ---
class TestLegacyRecord:
    def test_get_legacy_record_no_500(self, s):
        r = s.get(f"{API}/evaluaciones/{LEGACY_EVAL_ID}", timeout=30)
        if r.status_code == 404:
            pytest.skip("legacy record already removed")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "TEST_LEGACY_NULL" in d["motivo_consulta"]
        assert d["diagnosticos"] == [] or isinstance(d["diagnosticos"], list)

    def test_list_includes_legacy_no_500(self, s):
        r = s.get(f"{API}/evaluaciones", params={"paciente_id": PACIENTE_ID}, timeout=30)
        assert r.status_code == 200, r.text
        assert isinstance(r.json()["data"], list)


# --- Create with nulls / legacy strings ---
class TestCreate:
    def test_post_with_null_lists_ok(self, s, created_ids):
        payload = {"paciente_id": PACIENTE_ID, "motivo_consulta": "TEST_NULLS_POST",
                   "diagnosticos": None, "medicamentos_actuales": None, "medicamentos_previos": None,
                   "procedimientos": None, "recomendaciones": None, "examen": None, "antecedentes": None}
        r = s.post(f"{API}/evaluaciones", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        created_ids.append(d["id"])
        assert d["diagnosticos"] == [] and d["procedimientos"] == []
        g = s.get(f"{API}/evaluaciones/{d['id']}", timeout=30)
        assert g.status_code == 200 and g.json()["motivo_consulta"] == "TEST_NULLS_POST"

    def test_post_with_legacy_string_items(self, s, created_ids):
        payload = {"paciente_id": PACIENTE_ID, "motivo_consulta": "TEST_STR_ITEMS",
                   "diagnosticos": ["TEST_Catarata", {"descripcion": "TEST_Glaucoma", "ojo": "OD"}, 5],
                   "medicamentos_actuales": ["TEST_Timolol"]}
        r = s.post(f"{API}/evaluaciones", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        created_ids.append(d["id"])
        assert [x["descripcion"] for x in d["diagnosticos"]] == ["TEST_Catarata", "TEST_Glaucoma"]
        assert d["medicamentos_actuales"][0]["nombre"] == "TEST_Timolol"

    def test_post_normal_full_data(self, s, created_ids):
        payload = {"paciente_id": PACIENTE_ID, "motivo_consulta": "TEST_NORMAL",
                   "diagnosticos": [{"descripcion": "TEST_Miopia", "codigo_cie10": "H52.1", "ojo": "OU"}],
                   "plan": "TEST plan", "examen": {"pio_od": "14"}}
        r = s.post(f"{API}/evaluaciones", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        created_ids.append(d["id"])
        g = s.get(f"{API}/evaluaciones/{d['id']}", timeout=30).json()
        assert g["diagnosticos"][0]["descripcion"] == "TEST_Miopia"
        assert g["examen"]["pio_od"] == "14"


# --- Autosave PATCH + PUT self-heal ---
class TestUpdate:
    def _mk(self, s, created_ids, motivo):
        r = s.post(f"{API}/evaluaciones", json={"paciente_id": PACIENTE_ID, "motivo_consulta": motivo}, timeout=30)
        assert r.status_code == 200, r.text
        created_ids.append(r.json()["id"])
        return r.json()["id"]

    def test_patch_nulls_and_strings_heals(self, s, created_ids):
        eid = self._mk(s, created_ids, "TEST_PATCH")
        r = s.patch(f"{API}/evaluaciones/{eid}/autoguardar",
                    json={"plan": "TEST_PLAN_PATCH", "diagnosticos": None, "medicamentos_previos": ["TEST_X"],
                          "procedimientos": None, "recomendaciones": None}, timeout=30)
        assert r.status_code == 200, r.text
        g = s.get(f"{API}/evaluaciones/{eid}", timeout=30).json()
        assert g["plan"] == "TEST_PLAN_PATCH"
        assert g["medicamentos_previos"][0]["nombre"] == "TEST_X"
        assert g["diagnosticos"] == []

    def test_put_with_nulls_ok(self, s, created_ids):
        eid = self._mk(s, created_ids, "TEST_PUT")
        r = s.put(f"{API}/evaluaciones/{eid}",
                  json={"paciente_id": PACIENTE_ID, "motivo_consulta": "TEST_PUT_UPD", "diagnosticos": None,
                        "procedimientos": ["TEST_YAG"], "recomendaciones": None}, timeout=30)
        assert r.status_code == 200, r.text
        g = s.get(f"{API}/evaluaciones/{eid}", timeout=30).json()
        assert g["motivo_consulta"] == "TEST_PUT_UPD"
        assert g["procedimientos"][0]["descripcion"] == "TEST_YAG"

    # Edge cases: nested nulls (legacy) — not covered by top-level None dropping
    def test_patch_nested_null_in_recomendaciones(self, s, created_ids):
        eid = self._mk(s, created_ids, "TEST_NESTED")
        r = s.patch(f"{API}/evaluaciones/{eid}/autoguardar",
                    json={"recomendaciones": {"estudios_a_realizar": None, "recomendaciones_generales": None}},
                    timeout=30)
        assert r.status_code == 200, f"nested null recomendaciones -> {r.status_code} {r.text[:300]}"

    def test_patch_item_with_null_field(self, s, created_ids):
        eid = self._mk(s, created_ids, "TEST_ITEMNULL")
        r = s.patch(f"{API}/evaluaciones/{eid}/autoguardar",
                    json={"diagnosticos": [{"descripcion": None, "ojo": "OD"}]}, timeout=30)
        assert r.status_code == 200, f"item null field -> {r.status_code} {r.text[:300]}"
        g = s.get(f"{API}/evaluaciones/{eid}", timeout=30)
        assert g.status_code == 200, f"GET after item-null patch -> {g.status_code}"

    def test_patch_examen_null(self, s, created_ids):
        eid = self._mk(s, created_ids, "TEST_EXNULL")
        r = s.patch(f"{API}/evaluaciones/{eid}/autoguardar", json={"examen": None, "antecedentes": None}, timeout=30)
        assert r.status_code == 200, f"examen null -> {r.status_code} {r.text[:300]}"
        g = s.get(f"{API}/evaluaciones/{eid}", timeout=30)
        assert g.status_code == 200
