#!/usr/bin/env python3
"""
Script de Pruebas de Carga para NovaVision ERP
Mide rendimiento y capacidad de usuarios simultáneos
"""

import asyncio
import aiohttp
import time
import statistics
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import requests

# Configuración
BASE_URL = "https://novavision-finanzas.preview.emergentagent.com/api"
USERNAME = "superadmin"
PASSWORD = "nova2024"

# Resultados
results = {
    "timestamp": datetime.now().isoformat(),
    "base_url": BASE_URL,
    "tests": []
}

def get_token():
    """Obtener token de autenticación"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception as e:
        print(f"Error obteniendo token: {e}")
    return None

def test_endpoint_sync(endpoint, token, method="GET", data=None):
    """Probar endpoint de forma síncrona"""
    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=30)
        else:
            response = requests.post(f"{BASE_URL}{endpoint}", headers=headers, json=data, timeout=30)
        elapsed = (time.time() - start) * 1000  # ms
        return {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "time_ms": elapsed
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 0,
            "time_ms": (time.time() - start) * 1000,
            "error": str(e)
        }

async def test_endpoint_async(session, endpoint, token, semaphore):
    """Probar endpoint de forma asíncrona con semáforo"""
    headers = {"Authorization": f"Bearer {token}"}
    async with semaphore:
        start = time.time()
        try:
            async with session.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                await response.text()
                elapsed = (time.time() - start) * 1000
                return {
                    "success": response.status < 400,
                    "status_code": response.status,
                    "time_ms": elapsed
                }
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "time_ms": (time.time() - start) * 1000,
                "error": str(e)
            }

async def load_test_endpoint(endpoint, token, concurrent_users, total_requests):
    """Prueba de carga para un endpoint específico"""
    semaphore = asyncio.Semaphore(concurrent_users)
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            test_endpoint_async(session, endpoint, token, semaphore)
            for _ in range(total_requests)
        ]
        
        start_time = time.time()
        results_list = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
    
    # Calcular estadísticas
    successful = [r for r in results_list if r["success"]]
    failed = [r for r in results_list if not r["success"]]
    times = [r["time_ms"] for r in successful]
    
    stats = {
        "endpoint": endpoint,
        "concurrent_users": concurrent_users,
        "total_requests": total_requests,
        "successful_requests": len(successful),
        "failed_requests": len(failed),
        "success_rate": round(len(successful) / total_requests * 100, 2),
        "total_time_seconds": round(total_time, 2),
        "requests_per_second": round(total_requests / total_time, 2)
    }
    
    if times:
        stats["response_times_ms"] = {
            "min": round(min(times), 2),
            "max": round(max(times), 2),
            "avg": round(statistics.mean(times), 2),
            "median": round(statistics.median(times), 2),
            "p95": round(sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0], 2),
            "p99": round(sorted(times)[int(len(times) * 0.99)] if len(times) > 1 else times[0], 2)
        }
    
    return stats

def run_baseline_tests(token):
    """Pruebas base de cada endpoint crítico"""
    print("\n" + "="*60)
    print("🔬 PRUEBA 1: TIEMPOS DE RESPUESTA BASE (1 usuario)")
    print("="*60)
    
    endpoints = [
        ("/auth/me", "Autenticación"),
        ("/patients?limit=20", "Lista Pacientes"),
        ("/patients/search?q=Juan", "Búsqueda Pacientes"),
        ("/evaluaciones?limit=10", "Lista Evaluaciones"),
        ("/agenda/citas?fecha=2026-08-17", "Citas del Día"),
        ("/inventario/productos?limit=20", "Productos Inventario"),
        ("/ventas/bodega-pos", "Bodega POS"),
        ("/caja/estado", "Estado Caja"),
        ("/expenses?limit=20", "Lista Gastos"),
        ("/dashboard/stats", "Dashboard Stats"),
    ]
    
    baseline_results = []
    
    for endpoint, name in endpoints:
        times = []
        for _ in range(5):  # 5 repeticiones
            result = test_endpoint_sync(endpoint, token)
            if result["success"]:
                times.append(result["time_ms"])
        
        if times:
            avg_time = statistics.mean(times)
            status = "✅" if avg_time < 500 else "⚠️" if avg_time < 1000 else "❌"
            print(f"{status} {name:25} | Promedio: {avg_time:>8.2f} ms | Min: {min(times):>8.2f} ms | Max: {max(times):>8.2f} ms")
            baseline_results.append({
                "name": name,
                "endpoint": endpoint,
                "avg_ms": round(avg_time, 2),
                "min_ms": round(min(times), 2),
                "max_ms": round(max(times), 2)
            })
        else:
            print(f"❌ {name:25} | ERROR - No se pudo conectar")
            baseline_results.append({
                "name": name,
                "endpoint": endpoint,
                "error": "Connection failed"
            })
    
    return baseline_results

async def run_concurrent_tests(token):
    """Pruebas de concurrencia progresiva"""
    print("\n" + "="*60)
    print("🚀 PRUEBA 2: CARGA CONCURRENTE PROGRESIVA")
    print("="*60)
    
    # Endpoints críticos para prueba de carga
    test_endpoints = [
        "/patients?limit=10",
        "/agenda/citas?fecha=2026-08-17",
        "/inventario/productos?limit=10",
    ]
    
    concurrent_levels = [5, 10, 25, 50, 100]
    requests_per_level = 100
    
    load_results = []
    
    for concurrent in concurrent_levels:
        print(f"\n📊 Probando con {concurrent} usuarios simultáneos...")
        
        for endpoint in test_endpoints:
            stats = await load_test_endpoint(endpoint, token, concurrent, requests_per_level)
            
            status = "✅" if stats["success_rate"] >= 95 else "⚠️" if stats["success_rate"] >= 80 else "❌"
            
            print(f"  {status} {endpoint[:30]:30} | Éxito: {stats['success_rate']:>5}% | "
                  f"RPS: {stats['requests_per_second']:>6.1f} | "
                  f"Avg: {stats['response_times_ms']['avg'] if 'response_times_ms' in stats else 0:>7.1f}ms")
            
            load_results.append(stats)
    
    return load_results

async def run_stress_test(token):
    """Prueba de estrés para encontrar el límite"""
    print("\n" + "="*60)
    print("💪 PRUEBA 3: PRUEBA DE ESTRÉS (encontrar límite)")
    print("="*60)
    
    endpoint = "/patients?limit=5"
    
    stress_results = []
    max_successful_users = 0
    
    for concurrent in [50, 100, 150, 200, 250, 300]:
        print(f"\n🔥 Estrés con {concurrent} usuarios simultáneos (200 requests)...")
        
        stats = await load_test_endpoint(endpoint, token, concurrent, 200)
        
        success_rate = stats["success_rate"]
        avg_time = stats.get("response_times_ms", {}).get("avg", 0)
        
        if success_rate >= 95 and avg_time < 2000:
            status = "✅"
            max_successful_users = concurrent
        elif success_rate >= 80:
            status = "⚠️"
        else:
            status = "❌"
        
        print(f"  {status} Éxito: {success_rate}% | RPS: {stats['requests_per_second']:.1f} | "
              f"Avg: {avg_time:.1f}ms | P99: {stats.get('response_times_ms', {}).get('p99', 0):.1f}ms")
        
        stress_results.append({
            "concurrent_users": concurrent,
            "success_rate": success_rate,
            "requests_per_second": stats['requests_per_second'],
            "avg_response_ms": avg_time,
            "status": status
        })
        
        # Si el éxito cae por debajo del 70%, parar
        if success_rate < 70:
            print(f"  ⛔ Deteniendo prueba - tasa de éxito muy baja")
            break
    
    return stress_results, max_successful_users

def run_database_test(token):
    """Prueba de operaciones de base de datos"""
    print("\n" + "="*60)
    print("🗄️ PRUEBA 4: OPERACIONES DE BASE DE DATOS")
    print("="*60)
    
    db_results = []
    
    # Prueba de lectura
    print("\n📖 Lecturas complejas:")
    read_endpoints = [
        ("/patients?limit=50&skip=0", "50 pacientes"),
        ("/patients?limit=100&skip=0", "100 pacientes"),
        ("/evaluaciones?limit=50", "50 evaluaciones"),
        ("/expenses?limit=100", "100 gastos"),
    ]
    
    for endpoint, desc in read_endpoints:
        times = []
        for _ in range(3):
            result = test_endpoint_sync(endpoint, token)
            if result["success"]:
                times.append(result["time_ms"])
        
        if times:
            avg = statistics.mean(times)
            status = "✅" if avg < 1000 else "⚠️" if avg < 2000 else "❌"
            print(f"  {status} {desc:20} | Promedio: {avg:>8.2f} ms")
            db_results.append({"operation": desc, "avg_ms": round(avg, 2)})
    
    return db_results

def calculate_capacity(stress_results, max_users):
    """Calcular capacidad estimada de usuarios"""
    print("\n" + "="*60)
    print("📈 ANÁLISIS DE CAPACIDAD")
    print("="*60)
    
    # Encontrar el punto óptimo
    optimal = None
    for result in stress_results:
        if result["success_rate"] >= 95 and result["avg_response_ms"] < 1500:
            optimal = result
    
    if optimal:
        concurrent = optimal["concurrent_users"]
        # Asumiendo que cada usuario hace ~1 request cada 5 segundos en uso real
        estimated_real_users = concurrent * 5
        
        print(f"\n✅ CAPACIDAD ÓPTIMA DETECTADA:")
        print(f"   • Usuarios concurrentes estables: {concurrent}")
        print(f"   • Requests por segundo soportados: {optimal['requests_per_second']:.1f}")
        print(f"   • Tiempo de respuesta promedio: {optimal['avg_response_ms']:.0f}ms")
        print(f"\n📊 ESTIMACIÓN DE USUARIOS REALES:")
        print(f"   • Usuarios simultáneos activos: {concurrent} - {concurrent * 2}")
        print(f"   • Usuarios totales en la plataforma: {estimated_real_users} - {estimated_real_users * 2}")
        
        return {
            "optimal_concurrent": concurrent,
            "max_rps": optimal['requests_per_second'],
            "avg_response_ms": optimal['avg_response_ms'],
            "estimated_active_users": f"{concurrent}-{concurrent*2}",
            "estimated_total_users": f"{estimated_real_users}-{estimated_real_users*2}"
        }
    else:
        print(f"\n⚠️ No se encontró punto óptimo con >95% éxito")
        print(f"   El máximo con buen rendimiento fue: {max_users} usuarios")
        return {
            "max_users_tested": max_users,
            "note": "Se recomienda optimizar antes de producción"
        }

async def main():
    print("="*60)
    print("🏥 PRUEBAS DE RENDIMIENTO - NOVAVISION ERP")
    print("="*60)
    print(f"URL: {BASE_URL}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Obtener token
    print("\n🔐 Autenticando...")
    token = get_token()
    if not token:
        print("❌ No se pudo autenticar. Abortando pruebas.")
        return
    print("✅ Autenticación exitosa")
    
    # Ejecutar pruebas
    results["baseline"] = run_baseline_tests(token)
    results["load_tests"] = await run_concurrent_tests(token)
    stress_results, max_users = await run_stress_test(token)
    results["stress_tests"] = stress_results
    results["database_tests"] = run_database_test(token)
    results["capacity"] = calculate_capacity(stress_results, max_users)
    
    # Resumen final
    print("\n" + "="*60)
    print("📋 RESUMEN EJECUTIVO")
    print("="*60)
    
    # Guardar resultados
    with open("/app/test_reports/performance_report.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📁 Reporte completo guardado en: /app/test_reports/performance_report.json")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
