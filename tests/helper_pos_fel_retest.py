# Helper for iteration_130 retest: create / cleanup Óptica POS test sales
import os, sys, json, requests
BASE = open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0].rstrip('/') + '/api'
ACC = "1cedd3ef-7840-4c2a-8b3a-b5ac49d2b293"

def login(u, p):
    d = requests.post(f"{BASE}/auth/login", json={"username": u, "password": p}).json()
    s = requests.Session(); s.headers["Authorization"] = f"Bearer {d.get('access_token') or d.get('token')}"; return s

mode = sys.argv[1]
if mode == "create":
    o = login("optica", "Optica2024$"); out = []
    for i in range(int(sys.argv[2])):
        r = o.post(f"{BASE}/optica/sales/v2", json={"patient_name": f"TEST_RETEST_{i}", "items": [{"type": "accessory", "product_id": ACC, "quantity": 1, "unit_price": 45.0, "subtotal": 45.0}], "subtotal": 45.0, "discount": 0, "total": 45.0, "payments": [{"method": "Efectivo", "amount": 45.0}]})
        out.append({"id": r.json().get("id"), "order": r.json().get("order_number"), "status": r.status_code})
    print(json.dumps(out))
elif mode == "cancel":
    a = login("superadmin", "nova2024")
    for sid in sys.argv[2:]:
        d = a.get(f"{BASE}/optica/sales/{sid}").json()
        if (d.get("fel") or {}).get("estado") == "certificado":
            print("anular", a.post(f"{BASE}/fel/anular", json={"origen": "optica", "sale_id": sid, "motivo": "TEST cleanup"}).status_code)
        print(sid, "cancel", a.put(f"{BASE}/optica/sales/{sid}/cancel").status_code, d.get("order_number"))
elif mode == "status":
    a = login("superadmin", "nova2024")
    for sid in sys.argv[2:]:
        d = a.get(f"{BASE}/optica/sales/{sid}").json()
        print(sid, d.get("order_number"), d.get("status"), d.get("fel"))
