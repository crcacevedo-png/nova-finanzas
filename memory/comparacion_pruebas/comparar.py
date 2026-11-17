#!/usr/bin/env python3
# Compara las 4 corridas (junit XML) y escribe el detalle en /app/memory/comparacion_pruebas/resultado.json
import glob
import json
import os
import xml.etree.ElementTree as ET

R = "/tmp/cmp"
OUT = "/app/memory/comparacion_pruebas/resultado.json"


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
                    estado, msg = e, (n.get("message") or "")[:300]
            if nombre in res and res[nombre][0] in ("falla", "error"):
                continue
            res[nombre] = (estado, msg)
    return res


def resumen(r):
    c = {}
    for e, _ in r.values():
        c[e] = c.get(e, 0) + 1
    return dict(sorted(c.items())) | {"total": len(r)}


corr = {x: leer(x) for x in "ABCD"}
salida = {"totales": {x: resumen(corr[x]) for x in "ABCD"}}


def cruce(antes, ahora):
    a, b = corr[antes], corr[ahora]
    grupos = {"pasaba_y_ahora_falla": [], "fallaba_y_ahora_pasa": [], "falla_en_ambos": [],
              "solo_en_una": [], "cambia_omitida": []}
    for t in sorted(set(a) | set(b)):
        ea, eb = a.get(t, ("ausente", ""))[0], b.get(t, ("ausente", ""))[0]
        fila = {"prueba": t, "antes": ea, "ahora": eb, "msg_ahora": b.get(t, ("", ""))[1], "msg_antes": a.get(t, ("", ""))[1]}
        malo = ("falla", "error")
        if "ausente" in (ea, eb):
            grupos["solo_en_una"].append(fila)
        elif ea == "pasa" and eb in malo:
            grupos["pasaba_y_ahora_falla"].append(fila)
        elif ea in malo and eb == "pasa":
            grupos["fallaba_y_ahora_pasa"].append(fila)
        elif ea in malo and eb in malo:
            grupos["falla_en_ambos"].append(fila)
        elif (ea == "omitida") != (eb == "omitida"):
            grupos["cambia_omitida"].append(fila)
    return grupos


salida["pruebas_originales_A_vs_B"] = cruce("A", "B")
salida["pruebas_actuales_C_vs_D"] = cruce("C", "D")
json.dump(salida, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(salida["totales"], ensure_ascii=False))
for k in ("pruebas_originales_A_vs_B", "pruebas_actuales_C_vs_D"):
    print(k, {g: len(v) for g, v in salida[k].items()})
