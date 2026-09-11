#!/usr/bin/env python3
"""
Carga masiva de EVALUACIONES oftalmológicas a NovaVision.

Lee un archivo JSON (array de evaluaciones ya normalizadas desde Access),
inicia sesión, y las envía por lotes al endpoint /api/evaluaciones/import/batch.
Enlaza cada evaluación con su paciente por 'expediente' (record_number) o 'dpi'.

REQUISITOS: solo Python 3 (usa la librería estándar, sin dependencias externas).

USO:
    python importar_evaluaciones_masivo.py \\
        --file evaluaciones.json \\
        --url https://TU-APP.preview.emergentagent.com \\
        --username superadmin \\
        --password 'tu_password'

OPCIONES:
    --file            Ruta al archivo JSON (array de evaluaciones). [obligatorio]
    --url             URL base del backend (sin /api). [obligatorio]
    --username        Usuario admin/superadmin. [obligatorio]
    --password        Contraseña. [obligatorio]
    --batch-size      Tamaño de lote (por defecto 500).
    --validate-only   Solo valida una muestra y muestra el reporte; NO importa.
    --no-skip-duplicates   Inserta aunque exista el mismo id_origen (por defecto sí se omiten).
    --start-batch     Reanudar desde un número de lote (por defecto 1).
    --orphans-out     Archivo donde guardar las evaluaciones huérfanas (sin paciente). Por defecto 'huerfanas.json'.

EJEMPLO (solo validar):
    python importar_evaluaciones_masivo.py --file evals.json --url https://app... \\
        --username superadmin --password 'x' --validate-only
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error


def _post(url, payload, token=None, timeout=120):
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def login(base_url, username, password, max_intentos=5):
    """Inicia sesión y devuelve el access_token. Maneja el rate limit (429)."""
    url = f"{base_url}/api/auth/login"
    for intento in range(1, max_intentos + 1):
        try:
            status, body = _post(url, {"username": username, "password": password})
            token = body.get("access_token")
            if token:
                return token
            print(f"  Respuesta de login sin token: {body}")
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8", "ignore")
            if e.code == 429:
                espera = 65
                print(f"  Rate limit al iniciar sesión (429). Esperando {espera}s (intento {intento}/{max_intentos})...")
                time.sleep(espera)
                continue
            print(f"  Error de login HTTP {e.code}: {detalle}")
            break
        except Exception as e:  # noqa: BLE001
            print(f"  Error de conexión al iniciar sesión: {e}")
            time.sleep(5)
    raise SystemExit("No se pudo iniciar sesión. Verifica URL/credenciales.")


def cargar_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        # Buscar la primera propiedad que sea un array
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    print(f"  Detectado array en la propiedad '{k}'.")
                    return v
        raise SystemExit("El archivo JSON debe ser un array de evaluaciones.")
    return data


def _post_con_reintentos(url, payload, token, max_reintentos=3):
    for intento in range(1, max_reintentos + 1):
        try:
            return _post(url, payload, token)
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8", "ignore")
            if e.code in (429, 502, 503, 504):
                espera = 10 * intento
                print(f"    HTTP {e.code}, reintentando en {espera}s ({intento}/{max_reintentos})...")
                time.sleep(espera)
                continue
            raise SystemExit(f"Error HTTP {e.code}: {detalle}")
        except Exception as e:  # noqa: BLE001
            espera = 5 * intento
            print(f"    Error de conexión ({e}); reintentando en {espera}s ({intento}/{max_reintentos})...")
            time.sleep(espera)
    raise SystemExit("Se agotaron los reintentos para un lote.")


def main():
    ap = argparse.ArgumentParser(description="Carga masiva de evaluaciones a NovaVision")
    ap.add_argument("--file", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--username", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--batch-size", type=int, default=500)
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--no-skip-duplicates", action="store_true")
    ap.add_argument("--start-batch", type=int, default=1)
    ap.add_argument("--orphans-out", default="huerfanas.json")
    args = ap.parse_args()

    base_url = args.url.rstrip("/")
    print(f"Leyendo archivo: {args.file}")
    evaluaciones = cargar_json(args.file)
    total = len(evaluaciones)
    print(f"Evaluaciones a procesar: {total:,}")

    print(f"Iniciando sesión como '{args.username}'...")
    token = login(base_url, args.username, args.password)
    print("  Sesión iniciada.")

    # --- Validación de una muestra ---
    muestra = evaluaciones[: min(2000, total)]
    print(f"\nValidando una muestra de {len(muestra):,} evaluaciones...")
    _, val = _post_con_reintentos(f"{base_url}/api/evaluaciones/import/validate", muestra, token)
    print(f"  Enlazan con paciente : {val.get('linkable_records')}")
    print(f"  Sin paciente (huérf.): {val.get('huerfanas_count')}")
    print(f"  Sin clave de enlace  : {val.get('sin_clave_enlace')}")
    if val.get("sample"):
        print("  Ejemplo de enlace:")
        for s in val["sample"][:3]:
            print(f"    - {s.get('clave')} -> {s.get('paciente')} ({s.get('fecha')})")

    if args.validate_only:
        print("\n--validate-only activado. No se importó nada.")
        return

    if val.get("linkable_records", 0) == 0:
        print("\nNinguna evaluación de la muestra enlaza con un paciente.")
        print("Asegúrate de haber importado los pacientes primero, preservando su expediente.")
        resp = input("¿Continuar de todos modos? (s/N): ").strip().lower()
        if resp != "s":
            return

    # --- Importación por lotes ---
    skip_dup = not args.no_skip_duplicates
    batch_size = args.batch_size
    total_lotes = (total + batch_size - 1) // batch_size
    acum = {"inserted": 0, "orphaned": 0, "sin_clave": 0, "duplicates": 0}
    huerfanas = []

    print(f"\nImportando en {total_lotes} lote(s) de {batch_size} (skip_duplicates={skip_dup})...")
    for i in range(args.start_batch - 1, total_lotes):
        ini = i * batch_size
        lote = evaluaciones[ini: ini + batch_size]
        payload = {"items": lote, "batch_number": i + 1, "skip_duplicates": skip_dup}
        _, res = _post_con_reintentos(f"{base_url}/api/evaluaciones/import/batch", payload, token)
        for k in acum:
            acum[k] += res.get(k, 0)
        if res.get("orphaned_details"):
            huerfanas.extend(res["orphaned_details"])
        pct = round((i + 1) / total_lotes * 100)
        print(f"  Lote {i + 1}/{total_lotes} ({pct}%) -> insertadas: {res.get('inserted')}, "
              f"huérfanas: {res.get('orphaned')}, sin clave: {res.get('sin_clave')}, dup: {res.get('duplicates')}")

    print("\n=== RESUMEN FINAL ===")
    print(f"  Total procesadas : {total:,}")
    print(f"  Insertadas       : {acum['inserted']:,}")
    print(f"  Sin paciente     : {acum['orphaned']:,}")
    print(f"  Sin clave enlace : {acum['sin_clave']:,}")
    print(f"  Duplicadas (omit): {acum['duplicates']:,}")

    if huerfanas:
        with open(args.orphans_out, "w", encoding="utf-8") as f:
            json.dump(huerfanas, f, ensure_ascii=False, indent=2)
        print(f"\n  Se guardaron {len(huerfanas)} referencias huérfanas en '{args.orphans_out}' para revisión.")


if __name__ == "__main__":
    main()
