import asyncio
import aiohttp
import time
import json
from datetime import datetime
import psutil

# Lista de DNIs para probar
DNIS_TEST = [
    "03016298", 
]

API_BASE_URL = "http://localhost:8100"

async def test_single_request(session, dni, request_id):
    """Realiza una petición individual y mide el tiempo"""
    start_time = time.time()
    
    try:
        async with session.post(
            f"{API_BASE_URL}/generate-pdf",
            json={"dni": dni},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status == 200:
                data = await response.json()
                return {
                    "request_id": request_id,
                    "dni": dni,
                    "status": "SUCCESS",
                    "duration": round(duration, 2),
                    "response": data,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                error_text = await response.text()
                return {
                    "request_id": request_id,
                    "dni": dni,
                    "status": "ERROR",
                    "duration": round(duration, 2),
                    "error": f"HTTP {response.status}: {error_text}",
                    "timestamp": datetime.now().isoformat()
                }
                
    except asyncio.TimeoutError:
        return {
            "request_id": request_id,
            "dni": dni,
            "status": "TIMEOUT",
            "duration": 60.0,
            "error": "Request timeout after 60 seconds",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        return {
            "request_id": request_id,
            "dni": dni,
            "status": "EXCEPTION",
            "duration": round(duration, 2),
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def test_concurrent_requests(max_concurrent=5):
    """Ejecuta peticiones concurrentes con límite de concurrencia"""
    print(f"🚀 Iniciando test con {len(DNIS_TEST)} DNIs")
    print(f"📊 Máximo {max_concurrent} peticiones simultáneas")
    print(f"🎯 API: {API_BASE_URL}")
    print("-" * 60)
    
    start_time = time.time()
    results = []
    
    # Crear semáforo para limitar concurrencia
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def limited_request(session, dni, request_id):
        async with semaphore:
            return await test_single_request(session, dni, request_id)
    
    # Crear sesión HTTP
    connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        
        # Crear tareas para todas las peticiones
        tasks = [
            limited_request(session, dni, i+1) 
            for i, dni in enumerate(DNIS_TEST)
        ]
        
        # Ejecutar todas las tareas y mostrar progreso
        completed = 0
        for task in asyncio.as_completed(tasks):
            result = await task
            results.append(result)
            completed += 1
            
            # Mostrar progreso
            status_icon = "✅" if result["status"] == "SUCCESS" else "❌"
            print(f"{status_icon} [{completed:2d}/{len(DNIS_TEST)}] DNI: {result['dni']} - {result['status']} ({result['duration']}s)")
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Generar estadísticas
    generate_statistics(results, total_duration)
    
    # Guardar resultados
    save_results(results, total_duration)
    
    return results

def generate_statistics(results, total_duration):
    """Genera estadísticas del test"""
    print("\n" + "=" * 60)
    print("📈 ESTADÍSTICAS DEL TEST")
    print("=" * 60)
    
    total_requests = len(results)
    successful = len([r for r in results if r["status"] == "SUCCESS"])
    errors = len([r for r in results if r["status"] == "ERROR"])
    timeouts = len([r for r in results if r["status"] == "TIMEOUT"])
    exceptions = len([r for r in results if r["status"] == "EXCEPTION"])
    
    durations = [r["duration"] for r in results if r["status"] == "SUCCESS"]
    
    print(f"📊 Total de peticiones: {total_requests}")
    print(f"✅ Exitosas: {successful} ({successful/total_requests*100:.1f}%)")
    print(f"❌ Errores: {errors} ({errors/total_requests*100:.1f}%)")
    print(f"⏰ Timeouts: {timeouts} ({timeouts/total_requests*100:.1f}%)")
    print(f"💥 Excepciones: {exceptions} ({exceptions/total_requests*100:.1f}%)")
    print(f"🕐 Tiempo total: {total_duration:.2f} segundos")
    
    if durations:
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        print(f"⚡ Tiempo promedio por petición: {avg_duration:.2f}s")
        print(f"🏃 Petición más rápida: {min_duration:.2f}s")
        print(f"🐌 Petición más lenta: {max_duration:.2f}s")
        print(f"🚀 Throughput: {successful/total_duration:.2f} peticiones/segundo")

def save_results(results, total_duration):
    """Guarda los resultados en un archivo JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results_{timestamp}.json"
    
    test_summary = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "total_requests": len(results),
            "total_duration": total_duration,
            "api_url": API_BASE_URL
        },
        "results": results
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(test_summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resultados guardados en: {filename}")

async def main():
    """Función principal"""
    print("🧪 TEST DE PETICIONES SIMULTÁNEAS")
    print("=" * 60)
    
    # Verificar que el servidor esté corriendo
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/") as response:
                if response.status == 200:
                    print("✅ Servidor disponible")
                else:
                    print(f"⚠️ Servidor responde con código: {response.status}")
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        print("💡 Asegúrate de que el servidor esté corriendo: python app.py")
        return
    
    # Ejecutar test con diferentes niveles de concurrencia
    for concurrency in [8]:
        print(f"\n🔄 Ejecutando test con concurrencia: {concurrency}")
        await test_concurrent_requests(max_concurrent=concurrency)
        print("\n" + "⏸️" * 20 + " PAUSA " + "⏸️" * 20)
        await asyncio.sleep(2)  # Pausa entre tests

def check_system_resources():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    
    print(f"💻 CPU: {cpu_percent}% | RAM: {memory_percent}%")
    
    if cpu_percent > 80 or memory_percent > 80:
        print("⚠️ Sistema con alta carga, considera reducir concurrencia")
        return False
    return True

async def test_with_cache_warmup():
    """Test que primero calienta el cache y luego prueba concurrencia"""
    print("🔥 Calentando cache con algunos DNIs...")
    
    # DNIs para calentar cache
    warmup_dnis = ["42912930", "43934955", "72125803"]
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        # Calentar cache secuencialmente
        for i, dni in enumerate(warmup_dnis):
            print(f"🔥 Calentando cache: {dni}")
            result = await test_single_request(session, dni, i+1)
            print(f"   Resultado: {result['status']} ({result['duration']}s)")
            await asyncio.sleep(1)  # Pausa entre requests
    
    print("\n📊 Verificando estadísticas de cache...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/cache/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        stats = data['stats']
                        print(f"📋 Cache: {stats['valid_entries']} entradas válidas")
                        print(f"💾 Tamaño: {stats['total_size_mb']} MB")
                    else:
                        print("⚠️ Error obteniendo estadísticas de cache")
                else:
                    print(f"⚠️ Cache stats no disponible (HTTP {response.status})")
        except Exception as e:
            print(f"⚠️ Error verificando cache: {e}")
    
    print("\n🚀 Iniciando test de concurrencia con cache...")
    # Ahora ejecutar test normal que debería usar cache
    await test_concurrent_requests(max_concurrent=4)  # Usar concurrencia más baja

if __name__ == "__main__":
    # Agregar opción para test con cache
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--with-cache":
        asyncio.run(test_with_cache_warmup())
    else:
        asyncio.run(test_concurrent_requests())