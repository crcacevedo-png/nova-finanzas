#!/usr/bin/env python3
# Uso: resumen.py ANTES [DESPUES] — totales por corrida (junit de /tmp/cmp/X) y cruce entre las dos.
import glob
import os
import sys
import xml.etree.ElementTree as ET

R = "/tmp/cmp"


def leer(x):
    res = {}
    for f in sorted(glob.glob(f"{R}/{x}/junit/*.xml")):
        archivo = os.path.basename(f)[:-4] + ".py"
        for tc in ET.parse(f).getroot().iter("testcase"):
            clase = tc.get("classname", "").split(".")[-1]
            nombre = f"{archivo}::{clase + '::' if clase.startswith('Test') else ''}{tc.get('name')}"
            estado, msg = "pasa", ""
            for tag, e in (("skipped", "omitida"), ("error", "error"), ("failure", "falla")):
                n = tc.find(tag)
                if n is not None:
                    estado, msg = e, (n.get("message") or "")[:220]
            res[nombre] = (estado, msg)
    return res


def totales(r):
    c = {}
    for e, _ in r.values():
        c[e] = c.get(e, 0) + 1
    return dict(sorted(c.items())) | {"total": len(r)}


a = leer(sys.argv[1])
print(sys.argv[1], totales(a))
if len(sys.argv) > 2:
    b = leer(sys.argv[2])
    print(sys.argv[2], totales(b))
    malo = ("falla", "error")
    for t in sorted(set(a) | set(b)):
        ea, eb = a.get(t, ("ausente", ""))[0], b.get(t, ("ausente", ""))[0]
        if ea != eb:
            print(f"  {ea:>8} -> {eb:<8} {t}  {b.get(t, ('', ''))[1] if eb in malo else ''}")
else:
    for t, (e, m) in sorted(a.items()):
        if e in ("falla", "error"):
            print(f"  {e}: {t}  {m}")
