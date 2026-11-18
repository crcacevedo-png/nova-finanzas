#!/usr/bin/env python3
# Uso: foto_bd.py DB_NAME salida.json — huella por documento y por campo + índices de cada colección.
# Uso: foto_bd.py --diff a.json b.json — qué escribió alguien entre la foto A y la B.
import asyncio
import hashlib
import json
import os
import sys

from motor.motor_asyncio import AsyncIOMotorClient


def h(v):
    return hashlib.blake2b(json.dumps(v, sort_keys=True, ensure_ascii=False, default=str).encode(), digest_size=8).hexdigest()


async def foto(db_name, salida):
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[db_name]
    out = {}
    for c in sorted(await db.list_collection_names()):
        docs = {}
        async for d in db[c].find({}):
            docs[str(d["_id"])] = {k: h(v) for k, v in d.items() if k != "_id"}
        idx = sorted([json.dumps({k: v for k, v in s.items() if k != "ns"}, sort_keys=True, default=str)
                      async for s in db[c].list_indexes()])
        out[c] = {"docs": docs, "indexes": idx}
    json.dump(out, open(salida, "w"))


def diff(a_path, b_path):
    a, b = json.load(open(a_path)), json.load(open(b_path))
    cambios = 0
    for c in sorted(set(a) | set(b)):
        ca, cb = a.get(c, {"docs": {}, "indexes": []}), b.get(c, {"docs": {}, "indexes": []})
        if c not in a:
            print(f"+ colección nueva: {c} ({len(cb['docs'])} docs)")
        if c not in b:
            print(f"- colección borrada: {c}")
        nuevos = set(cb["docs"]) - set(ca["docs"])
        borrados = set(ca["docs"]) - set(cb["docs"])
        campos = {}
        for k in set(ca["docs"]) & set(cb["docs"]):
            da, db_ = ca["docs"][k], cb["docs"][k]
            for f in set(da) | set(db_):
                if da.get(f) != db_.get(f):
                    campos[f] = campos.get(f, 0) + 1
        idx_mas = sorted(set(cb["indexes"]) - set(ca["indexes"]))
        idx_menos = sorted(set(ca["indexes"]) - set(cb["indexes"]))
        if nuevos or borrados or campos or idx_mas or idx_menos:
            cambios += 1
            print(f"== {c}: docs nuevos {len(nuevos)}, borrados {len(borrados)}, campos cambiados {campos or '-'}")
            for i in idx_mas:
                print(f"   + índice {json.loads(i).get('name')}: {i}")
            for i in idx_menos:
                print(f"   - índice {json.loads(i).get('name')}")
    print(f"TOTAL colecciones con cambios: {cambios}")


if __name__ == "__main__":
    if sys.argv[1] == "--diff":
        diff(sys.argv[2], sys.argv[3])
    else:
        asyncio.run(foto(sys.argv[1], sys.argv[2]))
