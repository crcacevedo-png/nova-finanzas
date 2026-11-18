#!/bin/bash
# Uso: restaurar.sh NOMBRE PUERTO — prueba completa de "Restaurar respaldo" en una COPIA aislada:
# foto ACTUAL del preview → BD aparte → servidor propio → tests/test_respaldo_restaurar.py (PERMITIR_RESTAURAR=1).
# La BD del preview no se toca. Resultado y tiempos en /tmp/cmp/NOMBRE/.
X=$1
P=$2
R=/tmp/cmp
source <(grep -E '^(MONGO_URL|DB_NAME)=' /app/backend/.env | sed 's/^/export /')
SRC=$DB_NAME
rm -rf $R/$X && mkdir -p $R/$X/frontend
mongodump --uri "$MONGO_URL" --db "$SRC" --gzip --archive=$R/$X/snap.gz --quiet
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
  -e "s#/app/backend/#$R/$X/backend/#g" -e "s#/app/frontend/.env#$R/$X/frontend/.env#g" {} +
sed -i 's#limiter = Limiter(key_func=get_remote_address, default_limits=\["200/minute"\])#limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"], enabled=False)#' $R/$X/backend/server.py
cd $R/$X/backend
set -a; source .env; set +a
mongorestore --uri "$MONGO_URL" --gzip --archive=$R/$X/snap.gz --nsFrom "$SRC.*" --nsTo "$DB_NAME.*" --drop --quiet
mongosh "$MONGO_URL/$DB_NAME" --quiet --eval 'db.doctors.updateMany({}, {$unset: {google_calendar: ""}})' > /dev/null
export REACT_APP_BACKEND_URL=http://127.0.0.1:$P
nohup python -m uvicorn server:app --host 127.0.0.1 --port $P > $R/$X/server.log 2>&1 &
SPID=$!
for i in $(seq 1 90); do curl -s -o /dev/null http://127.0.0.1:$P/api/health && break; sleep 2; done
PERMITIR_RESTAURAR=1 timeout 1800 python -m pytest tests/test_respaldo_restaurar.py -p no:cacheprovider -q -s --tb=short > $R/$X/resultado.out 2>&1
echo "exit=$?" >> $R/$X/resultado.out
kill $SPID
sleep 3
mongosh "$MONGO_URL/$DB_NAME" --quiet --eval 'db.dropDatabase()' > /dev/null
echo TERMINADO >> $R/$X/resultado.out
