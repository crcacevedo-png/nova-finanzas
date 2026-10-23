"""Siembra de demostración para Producción IGSS + verificación de descuentos y persistencia.
- 5 unidades, 5 NOG c/u, 100 pacientes asimétricos, 1 expediente por orden.
- Verifica descuento de NOG y persistencia de estados por día y por rango.
Ejecuta contra localhost:8001 (misma BD que el preview).
"""
import asyncio, os, requests, json, random, sys
from datetime import datetime
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient

API = 'http://localhost:8001'
random.seed(42)
DIAS = ['2026-06-01', '2026-06-02', '2026-06-03', '2026-06-04', '2026-06-05']
DIST = [40, 28, 18, 10, 4]  # asimétrico, suma 100
PROCS = ['Catarata OD', 'Catarata OS', 'Pterigion', 'Glaucoma', 'Retina', 'Refracción']


def login():
    r = requests.post(API + '/api/auth/login', json={'username': 'superadmin', 'password': 'nova2024'})
    d = r.json()
    return d.get('access_token') or d.get('token')


async def main():
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    token = login()
    H = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    # Limpieza de datos de demo previos (idempotente)
    prev_units = await db.igss_units.find({'name': {'$regex': '^PRUEBA U'}}, {'_id': 0, 'id': 1}).to_list(None)
    prev_ids = [u['id'] for u in prev_units]
    if prev_ids:
        prev_nogs = await db.igss_nogs.find({'unidad_id': {'$in': prev_ids}}, {'_id': 0, 'id': 1}).to_list(None)
        nids = [n['id'] for n in prev_nogs]
        pacs = await db.patients.find({'igss_unit_id': {'$in': prev_ids}}, {'_id': 0, 'id': 1}).to_list(None)
        pids = [p['id'] for p in pacs]
        await db.igss_nog_acreditaciones.delete_many({'nog_id': {'$in': nids}})
        await db.evaluaciones_oftalmologicas.delete_many({'paciente_id': {'$in': pids}})
        await db.igss_produccion.delete_many({'evaluacion_id': {'$in': []}})
        await db.patients.delete_many({'id': {'$in': pids}})
        await db.igss_nogs.delete_many({'unidad_id': {'$in': prev_ids}})
        await db.igss_units.delete_many({'id': {'$in': prev_ids}})
        print(f'Limpieza previa: {len(prev_ids)} unidades demo eliminadas')

    # Médico
    med = await db.doctors.find_one({}, {'_id': 0, 'id': 1, 'name': 1}) or {'id': 'm1', 'name': 'Dr. Demo'}

    # 1) Unidades + NOG
    unidades = []
    for i in range(5):
        u = requests.post(API + '/api/igss-units', headers=H,
                          data=json.dumps({'name': f'PRUEBA U{i+1}', 'code': f'PU{i+1}', 'description': 'Demo'})).json()
        nogs = []
        for j in range(5):
            numero = f'PU{i+1}-NOG{j+1}'
            precio = random.choice([500, 850, 1200, 1500, 2000, 2500])
            n = requests.post(API + f"/api/igss-units/{u['id']}/nogs", headers=H,
                             data=json.dumps({'numero': numero, 'nombre_servicio': random.choice(PROCS),
                                              'tipo_compra': 'contrato', 'cantidad': 60, 'precio': precio})).json()
            nogs.append({'numero': numero, 'precio': precio, 'id': n.get('id')})
        unidades.append({'id': u['id'], 'name': u['name'], 'nogs': nogs})
    print('Unidades creadas:', [u['name'] for u in unidades])

    # 2) Pacientes asimétricos + expedientes (1 por orden)
    total_ordenes = 0
    total_eval = 0
    esperado_por_nog = {}  # numero -> set(paciente) para descuento esperado
    eval_por_dia = {d: 0 for d in DIAS}
    pac_count = 0
    for ui, u in enumerate(unidades):
        for k in range(DIST[ui]):
            pac_count += 1
            dpi = f'9{random.randint(100000000000, 999999999999)}'
            # 1 o (15%) 2 órdenes con NOG distintos de la unidad
            n_ord = 2 if random.random() < 0.15 and len(u['nogs']) >= 2 else 1
            chosen = random.sample(u['nogs'], n_ord)
            ordenes = [{'nog': c['numero'], 'no_sps': f'SPS-{pac_count}-{idx+1}',
                        'codigo': f'C{pac_count}', 'procedimiento': random.choice(PROCS)}
                       for idx, c in enumerate(chosen)]
            payload = {'first_name': f'Paciente{pac_count}', 'last_name': f'Demo{ui+1}', 'gender': random.choice(['masculino', 'femenino']),
                       'birth_date': f'19{random.randint(50,99)}-0{random.randint(1,9)}-1{random.randint(0,9)}',
                       'phone': f'5{random.randint(1000000,9999999)}', 'dpi': dpi,
                       'referral_institution': 'igss', 'igss_unit_id': u['id'], 'igss_ordenes': ordenes}
            r = requests.post(API + '/api/patients', headers=H, data=json.dumps(payload))
            if r.status_code != 200:
                print('  ERROR patient', r.status_code, r.text[:120]); continue
            pac = r.json()
            pid = pac['id']
            for c in chosen:
                esperado_por_nog.setdefault(c['numero'], set()).add(pid)
            total_ordenes += len(chosen)
            # Un expediente por orden (línea de producción por orden)
            for oi, orden in enumerate(pac.get('igss_ordenes', ordenes)):
                dia = DIAS[(pac_count + oi) % len(DIAS)]
                ev = requests.post(API + '/api/evaluaciones', headers=H, data=json.dumps({
                    'paciente_id': pid, 'paciente_nombre': f'Paciente{pac_count} Demo{ui+1}',
                    'medico_id': med['id'], 'medico_nombre': med['name'], 'fecha': dia,
                    'igss_orden_id': orden.get('id'), 'igss_nog': orden.get('nog'),
                    'igss_no_sps': orden.get('no_sps'), 'igss_codigo': orden.get('codigo'),
                    'igss_procedimiento': orden.get('procedimiento')}))
                if ev.status_code == 200:
                    total_eval += 1; eval_por_dia[dia] += 1
    print(f'Pacientes creados: {pac_count} | órdenes: {total_ordenes} | expedientes: {total_eval}')
    print('Expedientes por día:', eval_por_dia)

    # 3) Verificar descuento de NOG
    print('\n=== DESCUENTO DE NOG ===')
    ok_desc = 0
    for u in unidades:
        for n in u['nogs']:
            doc = await db.igss_nogs.find_one({'id': n['id']}, {'_id': 0, 'acreditados': 1})
            esperado = len(esperado_por_nog.get(n['numero'], set()))
            real = int(doc.get('acreditados') or 0)
            if real == esperado:
                ok_desc += 1
            elif esperado > 0:
                print(f"  DIF {n['numero']}: esperado {esperado} acreditados {real}")
    print(f'NOG con descuento correcto: {ok_desc}/25')
    tot_acred = sum(len(s) for s in esperado_por_nog.values())
    print(f'Total acreditaciones esperadas (1 por NOG distinto por paciente): {tot_acred}')

    # 4) Producción: por rango
    rng = requests.get(API + '/api/igss-units/produccion', headers=H,
                       params={'desde': DIAS[0], 'hasta': DIAS[-1]}).json()
    print(f"\n=== PRODUCCIÓN rango {DIAS[0]}..{DIAS[-1]} ===")
    print('filas:', len(rng['data']), '| servicios:', rng['totales']['servicios'], '| producción Q:', rng['totales']['total_costo'])

    # 5) Marcar estados en 3 registros de DIAS[2] y confirmar persistencia por día y por rango
    dia_test = DIAS[2]
    dia_rows = [r for r in rng['data'] if r['fecha'] == dia_test][:3]
    marcados = []
    for r in dia_rows:
        requests.patch(API + f"/api/igss-units/produccion/{r['evaluacion_id']}", headers=H,
                       data=json.dumps({'impreso': True, 'enviado': True, 'facturado': True}))
        marcados.append(r['evaluacion_id'])
    print(f'\nMarcados impreso+enviado+facturado en {len(marcados)} registros del {dia_test}')

    def estados_de(data, eid):
        for r in data:
            if r['evaluacion_id'] == eid:
                return (r['impreso'], r['enviado'], r['facturado'])
        return None

    por_dia = requests.get(API + '/api/igss-units/produccion', headers=H, params={'fecha': dia_test}).json()
    por_rng = requests.get(API + '/api/igss-units/produccion', headers=H, params={'desde': DIAS[0], 'hasta': DIAS[-1]}).json()
    ok_dia = all(estados_de(por_dia['data'], e) == (True, True, True) for e in marcados)
    ok_rng = all(estados_de(por_rng['data'], e) == (True, True, True) for e in marcados)
    print(f'Persistencia por DÍA ({dia_test}): {"OK" if ok_dia else "FALLO"}')
    print(f'Persistencia por RANGO: {"OK" if ok_rng else "FALLO"}')
    print('Totales por estado (rango):', json.dumps(por_rng['totales']['por_estado']))
    print('\nSUBTOTALES por unidad:')
    # agrupar simple
    from collections import defaultdict
    g = defaultdict(lambda: [0, 0.0])
    for r in por_rng['data']:
        g[r['unidad_nombre']][0] += 1; g[r['unidad_nombre']][1] += r['costo']
    for k, v in sorted(g.items()):
        print(f'  {k}: {v[0]} servicios, Q{round(v[1],2)}')

if __name__ == '__main__':
    asyncio.run(main())
