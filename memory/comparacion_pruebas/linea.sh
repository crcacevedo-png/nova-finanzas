#!/bin/bash
# Uso: linea.sh NOMBRE PUERTO  — copia el backend ACTUAL (código + pruebas) a /tmp/cmp/NOMBRE, restaura la
# misma foto de BD (/tmp/cmp/snap_base.gz, se toma una sola vez) en una BD aparte y corre los archivos uno por uno.
X=$1
P=$2
R=/tmp/cmp
FILES="test_igss_libro.py test_gestion_nog.py test_igss_nogs.py test_igss_ordenes_multiples.py test_nog_por_autorizacion.py test_optica_ventas_cancel_nog.py test_conciliacion_igss.py test_produccion_igss.py test_produccion_consolidacion.py test_mantenimiento_borradores.py test_igss_admin_role_audit.py test_agendar_cirugia_igss.py test_igss_medicamentos_frecuencia.py test_patients.py test_surgeries.py test_rbac_fixes_regression.py test_cierre_diario.py test_cuentas_cobrar.py test_iter147_cxc_perms_and_exports.py test_evaluacion_oftalmologica.py test_evaluaciones_permisos.py test_evaluacion_guardado_confiable.py test_surgeries_cancel_delete_usuario.py test_surgeries_manage_permission.py test_surgeries_usuario_permissions.py test_medico_role_access.py test_igss_solo_libro.py test_igss_migracion_simular.py $EXTRA"
source <(grep -E '^(MONGO_URL|DB_NAME)=' /app/backend/.env | sed 's/^/export /')
mkdir -p $R
if [ ! -f $R/snap_base.gz ]; then
  mongodump --uri "$MONGO_URL" --db "$DB_NAME" --gzip --archive=$R/snap_base.gz --quiet
  echo "$DB_NAME" > $R/src_db_base
fi
rm -rf $R/$X && mkdir -p $R/$X/frontend
rsync -a --exclude __pycache__ /app/backend $R/$X/
python3 - "$R/$X/backend/.env" "cmp_$X" <<'PY'
import sys
out, db = sys.argv[1], sys.argv[2]
lines = []
for l in open('/app/backend/.env').read().splitlines():
    k = l.split('=', 1)[0]
    if k == 'DB_NAME': l = f'DB_NAME="{db}"'
    if k in ('EMERGENT_EMAIL_KEY', 'GOOGLE_CLIENT_SECRET'): l = f'{k}="desactivado-en-comparacion"'
    lines.append(l)
open(out, 'w').write('\n'.join(lines) + '\n')
PY
echo "REACT_APP_BACKEND_URL=http://127.0.0.1:$P" > $R/$X/frontend/.env
find $R/$X/backend/tests -name '*.py' -exec sed -i \
  -e "s#/app/backend/#$R/$X/backend/#g" -e "s#/app/frontend/.env#$R/$X/frontend/.env#g" \
  -e 's#MongoClient("mongodb://localhost:27017")\["test_database"\]#MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]#g' {} +
sed -i 's#limiter = Limiter(key_func=get_remote_address, default_limits=\["200/minute"\])#limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"], enabled=False)#' $R/$X/backend/server.py
grep -q 'enabled=False' $R/$X/backend/server.py || { echo "no se pudo desactivar limiter" > $R/$X/progreso.log; exit 1; }
cd $R/$X/backend
set -a; source .env; set +a
mongorestore --uri "$MONGO_URL" --gzip --archive=$R/snap_base.gz --nsFrom "$(cat $R/src_db_base).*" --nsTo "$DB_NAME.*" --drop --quiet
mongosh "$MONGO_URL/$DB_NAME" --quiet --eval 'db.doctors.updateMany({}, {$unset: {google_calendar: ""}})' > /dev/null
export REACT_APP_BACKEND_URL=http://127.0.0.1:$P
nohup python -m uvicorn server:app --host 127.0.0.1 --port $P > $R/$X/server.log 2>&1 &
SPID=$!
for i in $(seq 1 90); do curl -s -o /dev/null http://127.0.0.1:$P/api/health && break; sleep 2; done
mkdir -p $R/$X/junit
for f in $FILES; do
  [ -f tests/$f ] || { echo "$f AUSENTE" >> $R/$X/progreso.log; continue; }
  timeout 900 python -m pytest tests/$f -p no:cacheprovider -q --tb=line --junitxml=$R/$X/junit/${f%.py}.xml > $R/$X/junit/${f%.py}.out 2>&1
  echo "$f exit=$? $(tail -1 $R/$X/junit/${f%.py}.out)" >> $R/$X/progreso.log
done
kill $SPID
sleep 3
mongosh "$MONGO_URL/$DB_NAME" --quiet --eval 'db.dropDatabase()' > /dev/null
echo TERMINADO >> $R/$X/progreso.log
