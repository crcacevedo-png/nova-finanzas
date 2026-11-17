#!/bin/bash
# Uso: correr.sh X   (X = A|B|C|D). Levanta el servidor de la copia y corre los 26 archivos uno por uno.
X=$1
R=/tmp/cmp
declare -A PORT=([A]=8101 [B]=8102 [C]=8103 [D]=8104)
P=${PORT[$X]}
FILES="test_igss_libro.py test_gestion_nog.py test_igss_nogs.py test_igss_ordenes_multiples.py test_nog_por_autorizacion.py test_optica_ventas_cancel_nog.py test_conciliacion_igss.py test_produccion_igss.py test_produccion_consolidacion.py test_mantenimiento_borradores.py test_igss_admin_role_audit.py test_agendar_cirugia_igss.py test_igss_medicamentos_frecuencia.py test_patients.py test_surgeries.py test_rbac_fixes_regression.py test_cierre_diario.py test_cuentas_cobrar.py test_iter147_cxc_perms_and_exports.py test_evaluacion_oftalmologica.py test_evaluaciones_permisos.py test_evaluacion_guardado_confiable.py test_surgeries_cancel_delete_usuario.py test_surgeries_manage_permission.py test_surgeries_usuario_permissions.py test_medico_role_access.py test_igss_solo_libro.py"
cd $R/$X/backend
set -a; source .env; set +a
# una sola copia de BD a la vez (mongod del preview tiene límite de 1024 archivos abiertos)
mongorestore --uri "$MONGO_URL" --gzip --archive=$R/snap.gz --nsFrom "$(cat $R/src_db).*" --nsTo "$DB_NAME.*" --drop --quiet
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
