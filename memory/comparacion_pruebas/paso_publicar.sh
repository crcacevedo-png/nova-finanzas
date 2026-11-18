#!/bin/bash
# Uso: paso_publicar.sh — qué escribe EXACTAMENTE el arranque de la versión nueva sobre una base "como
# producción" (sin libro) y si la versión anterior vuelve a arrancar después. Todo en una copia aparte.
# 1) copia del preview → se le quita todo lo del libro (como producción hoy) → arranca la versión ANTERIOR
# 2) foto A → arranca la versión NUEVA → foto B → diff A/B (lo que escribe el paso único al publicar)
# 3) arranca otra vez la versión ANTERIOR → foto C → diff B/C y pruebas de humo
ANT=${ANT:-d3974f3}
R=/tmp/cmp/PUB
P=8141
D=/app/memory/comparacion_pruebas
source <(grep -E '^(MONGO_URL|DB_NAME)=' /app/backend/.env | sed 's/^/export /')
SRC=$DB_NAME
export DBP=cmp_PUB
# OJO: el servidor toma DB_NAME del entorno antes que del .env: se fija explícitamente a la copia
rm -rf $R && mkdir -p $R/nueva $R/anterior
mongodump --uri "$MONGO_URL" --db "$SRC" --gzip --archive=$R/snap.gz --quiet
mongorestore --uri "$MONGO_URL" --gzip --archive=$R/snap.gz --nsFrom "$SRC.*" --nsTo "$DBP.*" --drop --quiet
mongosh "$MONGO_URL/$DBP" --quiet --eval '
  ["igss_ordenes_libro","igss_atenciones_sin_orden","igss_libro_ajustes_cupo","igss_libro_config","igss_migracion_fotos",
   "igss_migracion_lotes","igss_migracion_turno","restauraciones","sesiones_actividad"].forEach(c => db.getCollection(c).drop());
  db.system_flags.deleteMany({key: "libro_estados_bloque1_v2"});
  db.igss_nogs.updateMany({}, {$unset: {nombre_servicio_norm: "", libro_ocupados: ""}});
  ["nog_unidad_numero_parcial","nog_unidad_servicio_sin_numero"].forEach(i => { try { db.igss_nogs.dropIndex(i) } catch(e) {} });
  db.doctors.updateMany({}, {$unset: {google_calendar: ""}});
  printjson(db.system_flags.find({}, {_id: 0}).toArray());' > $R/flags_inicio.txt
git -C /app archive $ANT backend | tar -x -C $R/anterior
rsync -a --exclude __pycache__ --exclude tests /app/backend $R/nueva/
for X in anterior nueva; do
  python3 - "$R/$X/backend/.env" <<'PY'
import sys, os
out = sys.argv[1]
lines = []
for l in open('/app/backend/.env').read().splitlines():
    k = l.split('=', 1)[0]
    if k == 'DB_NAME': l = f'DB_NAME="{os.environ["DBP"]}"'
    if k in ('EMERGENT_EMAIL_KEY', 'GOOGLE_CLIENT_SECRET'): l = f'{k}="desactivado-en-comparacion"'
    lines.append(l)
open(out, 'w').write('\n'.join(lines) + '\n')
PY
done
arrancar() {  # $1 = anterior|nueva, $2 = etiqueta
  cd $R/$1/backend
  DB_NAME=$DBP nohup python -m uvicorn server:app --host 127.0.0.1 --port $P > $R/server_$2.log 2>&1 &
  SPID=$!
  OK=no
  for i in $(seq 1 90); do curl -s -o /dev/null http://127.0.0.1:$P/api/health && OK=si && break; sleep 2; done
  sleep 5
  echo "arranque $2 ($1): $OK" >> $R/informe.txt
}
parar() { kill $SPID; sleep 3; }
humo() {  # pruebas de humo con el superadmin del preview
  T=$(curl -s -X POST http://127.0.0.1:$P/api/auth/login -H 'Content-Type: application/json' -d '{"username":"superadmin","password":"nova2024"}' | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))")
  for u in /api/patients?limit=1 /api/igss-units /api/surgeries?limit=1 /api/citas?limit=1; do
    echo "  $1 GET $u -> $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$P$u -H "Authorization: Bearer $T")" >> $R/informe.txt
  done
}
echo "Versión anterior = $ANT" > $R/informe.txt
python3 $D/foto_bd.py $SRC $R/preview_antes.json
arrancar anterior "1_anterior"; humo anterior; parar
python3 $D/foto_bd.py $DBP $R/A.json
arrancar nueva "2_nueva"; humo nueva; parar
python3 $D/foto_bd.py $DBP $R/B.json
mongosh "$MONGO_URL/$DBP" --quiet --eval 'printjson(db.system_flags.find({}, {_id: 0}).toArray())' > $R/flags_tras_nueva.txt
arrancar anterior "3_anterior_otra_vez"; humo anterior_otra_vez; parar
python3 $D/foto_bd.py $DBP $R/C.json
{ echo; echo "=== Lo que escribe el arranque de la versión NUEVA (A→B) ==="; python3 $D/foto_bd.py --diff $R/A.json $R/B.json
  echo; echo "=== Lo que escribe la versión ANTERIOR al volver (B→C) ==="; python3 $D/foto_bd.py --diff $R/B.json $R/C.json
  echo; echo "=== Errores en los logs ==="; grep -h -i "error\|traceback\|no creado\|no se pudo" $R/server_*.log | grep -v "INFO:" | sort | uniq -c | head -30
} >> $R/informe.txt
python3 $D/foto_bd.py $SRC $R/preview_despues.json
{ echo; echo "=== Control: cambios en la BD del PREVIEW durante la prueba (debe ser solo actividad propia) ==="; python3 $D/foto_bd.py --diff $R/preview_antes.json $R/preview_despues.json; } >> $R/informe.txt
mongosh "$MONGO_URL/$DBP" --quiet --eval 'db.dropDatabase()' > /dev/null
echo TERMINADO >> $R/informe.txt
