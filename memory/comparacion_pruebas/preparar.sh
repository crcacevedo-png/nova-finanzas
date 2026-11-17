#!/bin/bash
# Prepara 4 corridas aisladas: A=código viejo+pruebas viejas, B=código actual+pruebas viejas,
# C=código viejo+pruebas actuales, D=código actual+pruebas actuales. Cada una con su copia de BD y puerto.
set -e
BASE_COMMIT=d3974f3
R=/tmp/cmp
source <(grep -E '^(MONGO_URL|DB_NAME)=' /app/backend/.env | sed 's/^/export /')
SRC_DB=$DB_NAME
rm -rf $R && mkdir -p $R
mongodump --uri "$MONGO_URL" --db "$SRC_DB" --gzip --archive=$R/snap.gz --quiet
declare -A PORT=([A]=8101 [B]=8102 [C]=8103 [D]=8104)
for X in A B C D; do
  mkdir -p $R/$X/frontend
  if [[ $X == A || $X == C ]]; then
    git -C /app archive $BASE_COMMIT backend | tar -x -C $R/$X
  else
    rsync -a --exclude __pycache__ --exclude tests /app/backend $R/$X/
  fi
  rm -rf $R/$X/backend/tests
  if [[ $X == A || $X == B ]]; then
    git -C /app archive $BASE_COMMIT backend/tests | tar -x -C $R/$X
  else
    rsync -a --exclude __pycache__ /app/backend/tests $R/$X/backend/
  fi
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
  echo "REACT_APP_BACKEND_URL=http://127.0.0.1:${PORT[$X]}" > $R/$X/frontend/.env
  # rutas de los archivos de prueba -> esta copia
  find $R/$X/backend/tests -name '*.py' -exec sed -i \
    -e "s#/app/backend/#$R/$X/backend/#g" -e "s#/app/frontend/.env#$R/$X/frontend/.env#g" \
    -e 's#MongoClient("mongodb://localhost:27017")\["test_database"\]#MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]#g' {} +
  # límite de 5 inicios de sesión por minuto desactivado igual en las 4 copias (todo llega desde 127.0.0.1)
  sed -i 's#limiter = Limiter(key_func=get_remote_address, default_limits=\["200/minute"\])#limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"], enabled=False)#' $R/$X/backend/server.py
  grep -q 'enabled=False' $R/$X/backend/server.py || { echo "no se pudo desactivar limiter en $X"; exit 1; }
done
echo "$SRC_DB" > $R/src_db
echo PREPARADO
