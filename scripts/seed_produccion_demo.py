"""Siembra de demostración para Producción IGSS.
- 5 unidades, 5 NOG c/u (precios variados), 110 pacientes únicos distribuidos
  asimétricamente entre las unidades.
- 1 expediente por paciente, en FECHAS DIFERENTES (varios días recientes,
  incluyendo HOY para que se vea en la vista por defecto del módulo).
- NOG variado por paciente (round-robin) y descuento (acreditación) automático.
- Verifica variedad (unidades/NOG/fechas) y el descuento de NOG.
Ejecuta contra localhost:8001 (misma BD que el preview).
"""
import asyncio, os, requests, json, random
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient
from utils.timezone import today_str_gt

API = 'http://localhost:8001'
random.seed(7)
DIST = [35, 28, 22, 15, 10]  # asimétrico, suma 110
PROCS = ['Catarata OD', 'Catarata OS', 'Pterigion', 'Glaucoma', 'Retina',
         'Refracción', 'Vitrectomía', 'Chalazión']


def login():
    r = requests.post(API + '/api/auth/login', json={'username': 'superadmin', 'password': 'nova2024'})
    d = r.json()
    return d.get('access_token') or d.get('token')


def build_fechas(n_dias=45):
    """Lista de días hábiles recientes terminando HOY (GT), del más reciente al más antiguo."""
    hoy = datetime.strptime(today_str_gt(), '%Y-%m-%d')
    fechas = []
    d = hoy
    while len(fechas) < n_dias:
        if d.weekday() < 6:  # lun-sab
            fechas.append(d.strftime('%Y-%m-%d'))
        d -= timedelta(days=1)
    return fechas


async def main():
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    token = login()
    assert token, 'No se pudo autenticar'
    H = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    HOY = today_str_gt()
    FECHAS = build_fechas(45)

    # --- Limpieza idempotente de demo previo (PRUEBA U*) ---
    prev_units = await db.igss_units.find({'name': {'$regex': '^PRUEBA U'}}, {'_id': 0, 'id': 1}).to_list(None)
    prev_ids = [u['id'] for u in prev_units]
    if prev_ids:
        prev_nogs = await db.igss_nogs.find({'unidad_id': {'$in': prev_ids}}, {'_id': 0, 'id': 1}).to_list(None)
        nids = [n['id'] for n in prev_nogs]
        pacs = await db.patients.find({'igss_unit_id': {'$in': prev_ids}}, {'_id': 0, 'id': 1}).to_list(None)
        pids = [p['id'] for p in pacs]
        evs = await db.evaluaciones_oftalmologicas.find({'paciente_id': {'$in': pids}}, {'_id': 0, 'id': 1}).to_list(None)
        eids = [e['id'] for e in evs]
        await db.igss_nog_acreditaciones.delete_many({'nog_id': {'$in': nids}})
        await db.igss_produccion.delete_many({'evaluacion_id': {'$in': eids}})
        await db.evaluaciones_oftalmologicas.delete_many({'paciente_id': {'$in': pids}})
        await db.patients.delete_many({'id': {'$in': pids}})
        await db.igss_nogs.delete_many({'unidad_id': {'$in': prev_ids}})
        await db.igss_units.delete_many({'id': {'$in': prev_ids}})
        print(f'Limpieza previa: {len(prev_ids)} unidades demo eliminadas ({len(eids)} expedientes)')

    med = await db.doctors.find_one({}, {'_id': 0, 'id': 1, 'name': 1}) or {'id': 'm1', 'name': 'Dr. Demo'}

    # --- 1) Unidades + NOG ---
    unidades = []
    for i in range(5):
        u = requests.post(API + '/api/igss-units', headers=H,
                          data=json.dumps({'name': f'PRUEBA U{i+1}', 'code': f'PU{i+1}', 'description': 'Demo'})).json()
        nogs = []
        for j in range(5):
            numero = f'PU{i+1}-NOG{j+1}'
            precio = [500, 850, 1200, 1500, 2000][j]
            n = requests.post(API + f"/api/igss-units/{u['id']}/nogs", headers=H,
                             data=json.dumps({'numero': numero, 'nombre_servicio': PROCS[j],
                                              'tipo_compra': 'contrato', 'cantidad': 80, 'precio': precio})).json()
            nogs.append({'numero': numero, 'precio': precio, 'id': n.get('id')})
        unidades.append({'id': u['id'], 'name': u['name'], 'nogs': nogs})
    print('Unidades creadas:', [u['name'] for u in unidades])

    # --- 2) Pacientes + expedientes (1 por paciente, fecha variada) ---
    pac_count = 0
    total_eval = 0
    esperado_por_nog = {}      # nog_id -> set(paciente)
    eval_por_dia = {}
    for ui, u in enumerate(unidades):
        for k in range(DIST[ui]):
            pac_count += 1
            nog = u['nogs'][k % 5]  # round-robin => se usan los 5 NOG de la unidad
            dpi = f'9{random.randint(100000000000, 999999999999)}'
            orden = {'nog': nog['numero'], 'no_sps': f'SPS-{pac_count}',
                     'codigo': f'C{pac_count}', 'procedimiento': random.choice(PROCS)}
            payload = {'first_name': f'Paciente{pac_count}', 'last_name': f'Demo U{ui+1}',
                       'gender': random.choice(['masculino', 'femenino']),
                       'birth_date': f'19{random.randint(50,99)}-0{random.randint(1,9)}-1{random.randint(0,9)}',
                       'phone': f'5{random.randint(1000000,9999999)}', 'dpi': dpi,
                       'referral_institution': 'igss', 'igss_unit_id': u['id'], 'igss_ordenes': [orden]}
            r = requests.post(API + '/api/patients', headers=H, data=json.dumps(payload))
            if r.status_code != 200:
                print('  ERROR patient', r.status_code, r.text[:120]); continue
            pac = r.json()
            pid = pac['id']
            orden_real = (pac.get('igss_ordenes') or [orden])[0]
            esperado_por_nog.setdefault(nog['id'], set()).add(pid)

            # ~15 primeros expedientes HOY; el resto repartido en días recientes
            if pac_count <= 15:
                dia = HOY
            else:
                dia = FECHAS[pac_count % len(FECHAS)]
            ev = requests.post(API + '/api/evaluaciones', headers=H, data=json.dumps({
                'paciente_id': pid, 'paciente_nombre': f'Paciente{pac_count} Demo U{ui+1}',
                'medico_id': med['id'], 'medico_nombre': med['name'], 'fecha': dia,
                'igss_orden_id': orden_real.get('id'), 'igss_nog': nog['numero'],
                'igss_no_sps': orden_real.get('no_sps'), 'igss_codigo': orden_real.get('codigo'),
                'igss_procedimiento': orden_real.get('procedimiento')}))
            if ev.status_code == 200:
                total_eval += 1
                eval_por_dia[dia] = eval_por_dia.get(dia, 0) + 1
            else:
                print('  ERROR eval', ev.status_code, ev.text[:120])
    print(f'Pacientes creados: {pac_count} | expedientes: {total_eval}')
    print(f'Días distintos usados: {len(eval_por_dia)} | hoy ({HOY}): {eval_por_dia.get(HOY, 0)} expedientes')

    # --- 3) Verificar descuento de NOG ---
    ok_desc = 0
    for u in unidades:
        for n in u['nogs']:
            doc = await db.igss_nogs.find_one({'id': n['id']}, {'_id': 0, 'acreditados': 1})
            esperado = len(esperado_por_nog.get(n['id'], set()))
            real = int((doc or {}).get('acreditados') or 0)
            if real == esperado:
                ok_desc += 1
            else:
                print(f"  DIF {n['numero']}: esperado {esperado} acreditados {real}")
    print(f'NOG con descuento correcto: {ok_desc}/25')

    # --- 4) Producción por RANGO (verificación de variedad) ---
    rng = requests.get(API + '/api/igss-units/produccion', headers=H,
                       params={'desde': FECHAS[-1], 'hasta': HOY}).json()
    data = rng['data']
    unidades_distintas = len({r['unidad_nombre'] for r in data})
    nogs_distintos = len({r['nog'] for r in data})
    fechas_distintas = len({r['fecha'] for r in data})
    pacientes_distintos = len({r['paciente_id'] for r in data})
    print(f"\n=== PRODUCCIÓN rango {FECHAS[-1]}..{HOY} ===")
    print(f"filas: {len(data)} | servicios: {rng['totales']['servicios']} | producción Q: {rng['totales']['total_costo']}")
    print(f"unidades distintas: {unidades_distintas} | NOG distintos: {nogs_distintos} | "
          f"fechas distintas: {fechas_distintas} | pacientes distintos: {pacientes_distintos}")

    # --- 5) Vista por DÍA (hoy) ---
    hoy_rows = requests.get(API + '/api/igss-units/produccion', headers=H, params={'fecha': HOY}).json()
    print(f"\nVista por DÍA (hoy {HOY}): {len(hoy_rows['data'])} expedientes, "
          f"{len({r['nog'] for r in hoy_rows['data']})} NOG distintos")

if __name__ == '__main__':
    asyncio.run(main())
