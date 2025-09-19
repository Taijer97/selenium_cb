import json
from functools import wraps
import time
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from pdf_converter import PDFConverter
from bs4 import BeautifulSoup
import os
import aiofiles
from cache_manager import cache_manager
import shutil

load_dotenv()

# Crear carpeta para PDFs si no existe
PDF_OUTPUT_DIR = "pdfs_generados"
if not os.path.exists(PDF_OUTPUT_DIR):
    os.makedirs(PDF_OUTPUT_DIR)
    print(f"📁 Carpeta creada: {PDF_OUTPUT_DIR}")

url1_selenium = os.getenv('URL_SELENIUM_1')
url2_selenium = os.getenv('URL_SELENIUM_2')
user_s = os.getenv('USER_SELENIUM')
password_s = os.getenv('PASSWORD_SELENIUM')
button_s = os.getenv('BUTTON_SELECTOR')
input_s = os.getenv('INPUT_SELECTOR')

def buscar_elemento_creditos_directo(driver, texto_buscar="Créditos"):
    """
    Busca un elemento específico directamente en Selenium sin archivos intermedios
    """
    try:
        # Buscar todas las secciones tile-group
        tile_groups = driver.find_elements(By.CSS_SELECTOR, "div.tile-group.quadro")
        
        for group in tile_groups:
            try:
                # Buscar el título de la sección
                title = group.find_element(By.CSS_SELECTOR, "span.tile-group-title")
                if "Creditos" in title.text:
                    # Buscar el contenedor de tiles
                    tile_container = group.find_element(By.CSS_SELECTOR, "div.tile-container")
                    elementos = tile_container.find_elements(By.CSS_SELECTOR, "div[data-role='tile']")
                    
                    for elemento in elementos:
                        try:
                            label = elemento.find_element(By.CSS_SELECTOR, "span.tile-label")
                            if texto_buscar.lower() in label.text.lower():
                                return elemento
                        except:
                            continue
            except:
                continue
    except Exception as e:
        print(f"Error buscando elemento: {e}")
    
    return None

def buscar_input_busqueda_robusto(driver, placeholder_texto="N° CONTRATO / DNI / NOMBRE"):
    """
    Busca el input de búsqueda de forma robusta usando múltiples estrategias
    ya que el ID es mutable y el XPath no es confiable
    """
    try:
        print("Buscando input de búsqueda...")
        
        # Estrategia 1: Buscar por placeholder específico
        try:
            elemento = driver.find_element(By.CSS_SELECTOR, f"input[placeholder*='CONTRATO'][placeholder*='DNI'][placeholder*='NOMBRE']")
            if elemento.is_displayed() and elemento.is_enabled():
                print(f"Input encontrado por placeholder: {elemento.get_attribute('placeholder')}")
                return elemento
        except:
            pass
        
        # Estrategia 2: Buscar por clase CSS específica
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, "input.x-form-field.x-form-text")
            for elemento in elementos:
                if elemento.is_displayed() and elemento.is_enabled():
                    placeholder = elemento.get_attribute('placeholder') or ''
                    if 'CONTRATO' in placeholder.upper() or 'DNI' in placeholder.upper():
                        print(f"Input encontrado por clase CSS: {placeholder}")
                        return elemento
        except:
            pass
        
        # Estrategia 3: Buscar por atributos de rol y tipo
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, "input[type='text'][role='textbox']")
            for elemento in elementos:
                if elemento.is_displayed() and elemento.is_enabled():
                    placeholder = elemento.get_attribute('placeholder') or ''
                    name = elemento.get_attribute('name') or ''
                    if ('search' in name.lower() or 'buscar' in name.lower() or 
                        'CONTRATO' in placeholder.upper() or 'DNI' in placeholder.upper()):
                        print(f"Input encontrado por rol/tipo: {placeholder}")
                        return elemento
        except:
            pass
        
        # Estrategia 4: Buscar en estructura de tabla (más específico)
        try:
            # Buscar inputs dentro de tablas que contengan el texto esperado
            tabla_inputs = driver.find_elements(By.CSS_SELECTOR, "table input[type='text']")
            for elemento in tabla_inputs:
                if elemento.is_displayed() and elemento.is_enabled():
                    placeholder = elemento.get_attribute('placeholder') or ''
                    if 'DNI' in placeholder.upper() or 'CONTRATO' in placeholder.upper():
                        print(f"Input encontrado en tabla: {placeholder}")
                        return elemento
        except:
            pass
        
        # Estrategia 5: Buscar por ID que contenga 'search' o 'input'
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, "input[id*='search'], input[id*='input'], input[id*='field']")
            for elemento in elementos:
                if elemento.is_displayed() and elemento.is_enabled():
                    placeholder = elemento.get_attribute('placeholder') or ''
                    if placeholder and ('DNI' in placeholder.upper() or 'CONTRATO' in placeholder.upper()):
                        print(f"Input encontrado por ID pattern: {elemento.get_attribute('id')}")
                        return elemento
        except:
            pass
        
        # Estrategia 6: Buscar el primer input visible de texto en la página
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            for elemento in elementos:
                if elemento.is_displayed() and elemento.is_enabled():
                    # Verificar si está en una posición prominente (arriba en la página)
                    location = elemento.location
                    if location['y'] < 500:  # Está en la parte superior
                        placeholder = elemento.get_attribute('placeholder') or ''
                        print(f"Input encontrado como primer campo visible: {placeholder}")
                        return elemento
        except:
            pass
        
        # Estrategia 7: Debugging - mostrar todos los inputs disponibles
        print("=== DEBUGGING: Inputs disponibles ===")
        try:
            all_inputs = driver.find_elements(By.CSS_SELECTOR, "input")
            for i, inp in enumerate(all_inputs[:10]):  # Mostrar solo los primeros 10
                if inp.is_displayed():
                    print(f"{i}: ID={inp.get_attribute('id')}, Type={inp.get_attribute('type')}, Placeholder={inp.get_attribute('placeholder')}, Name={inp.get_attribute('name')}")
        except:
            pass
            
    except Exception as e:
        print(f"Error buscando input: {e}")
    
    return None

def buscar_y_llenar_input_dni(driver, user_dni):
    """
    Función completa para buscar y llenar el campo de DNI
    """
    try:
        # Buscar el input usando la función robusta
        input_element = buscar_input_busqueda_robusto(driver)
        
        if not input_element:
            # Capturar screenshot para debugging
            driver.save_screenshot("input_not_found_debug.png")
            return {"error": "No se pudo encontrar el campo de búsqueda. Screenshot guardado para debugging."}
        
        # Limpiar el campo antes de escribir
        input_element.clear()
        
        # Enviar el DNI
        input_element.send_keys(str(user_dni))
        
        # Opcional: presionar Enter o buscar botón de búsqueda
        try:
            # Buscar botón de búsqueda cercano
            parent = input_element.find_element(By.XPATH, "./..")
            search_button = parent.find_element(By.CSS_SELECTOR, "button, input[type='submit'], *[class*='search'], *[class*='buscar']")
            search_button.click()
        except:
            # Si no encuentra botón, presionar Enter
            from selenium.webdriver.common.keys import Keys
            input_element.send_keys(Keys.RETURN)
        
        print(f"DNI {user_dni} ingresado correctamente")
        return {"success": True, "element_id": input_element.get_attribute('id')}
        
    except Exception as e:
        driver.save_screenshot("input_error_debug.png")
        return {"error": f"Error al llenar el campo de DNI: {str(e)}"}

async def selenium_dni_async(user_dni):
    """Función asíncrona que usa Selenium para extraer datos del DNI"""
    
    try:
        print(f"🔍 Procesando DNI: {user_dni}")
        
        # 1. Verificar cache primero
        cached_result = await cache_manager.get_cached_pdf(user_dni)
        if cached_result:
            print(f"📋 Cache HIT: {user_dni}")
            # Copiar PDF del cache al directorio de reportes
            cached_pdf_path = cached_result['pdf_path']
            target_filename = os.path.join(PDF_OUTPUT_DIR, f"reporte_{user_dni}.pdf")
            target_path = target_filename
            
            try:
                shutil.copy2(cached_pdf_path, target_path)
                print(f"📋 PDF servido desde cache: {target_filename}")
                
                return {
                    "success": True,
                    "filename": target_filename,
                    "message": f"PDF generado exitosamente desde cache para DNI {user_dni}",
                    "cached": True,
                    "cache_created_at": cached_result.get('created_at'),
                    "file_size": cached_result.get('file_size', 0)
                }
            except Exception as e:
                print(f"⚠️ Error copiando desde cache, regenerando: {e}")
                # Si falla la copia, continuar con generación normal
        else:
            print(f"📋 Cache MISS: {user_dni}")
        
        # 2. Generar PDF normalmente si no está en cache
        print(f"🔄 Generando nuevo PDF para DNI: {user_dni}")

    except Exception as e:
        print(f"⚠️ Error en la operación de Selenium: {e}")
        return {
            "success": False,
            "message": f"Error en la operación de Selenium para DNI {user_dni}: {e}"
        }
    
    
    def _selenium_sync_operation(user_dni):
        """Operación síncrona de Selenium que se ejecutará en un hilo separado"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--incognito')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        try:
            driver.get(url1_selenium)

            # 🔹 Iniciar sesión en la web
            driver.find_element(By.XPATH, "//input[@class='mdl-textfield__input']").send_keys(user_s)
            driver.find_element(By.XPATH, "//input[@id='password']").send_keys(password_s)
            driver.find_element(By.XPATH, "//button[@id='login-btn']").click()
            time.sleep(1)
            
            # ✅ VERSIÓN DIRECTA - Sin archivos intermedios
            elemento_creditos = buscar_elemento_creditos_directo(driver, "Créditos")
            if elemento_creditos:
                elemento_creditos.click()
                time.sleep(2)
            else:
                print("No se encontró el elemento Créditos")
                return {"error": "No se pudo acceder a la sección de Créditos"}
            
            # Esperar a que cargue la nueva página
            time.sleep(3)
            
            # Usar la nueva función robusta para buscar y llenar el DNI
            resultado_input = buscar_y_llenar_input_dni(driver, user_dni)
            if not resultado_input.get("success"):
                return resultado_input
            
            time.sleep(2)
            

            # 🔹 Buscar en la tabla
            filas = driver.find_elements(By.XPATH, "/html/body/div[1]/div[2]/div[2]/div[2]/div[4]/div/table//tr")

            # Si no hay resultados
            if len(filas) == 0:
                return {"error": "Cliente no encontrado o sin crédito activo"}

            # Extraer datos de la primera fila
            data_dict = {}
            for row in filas:
                celdas = row.find_elements(By.XPATH, ".//td")
                if len(celdas) == 9:
                    data_dict = {
                        'id': celdas[0].text,
                        'dni': celdas[1].text,
                        'name': celdas[2].text,
                        'status': celdas[8].text
                    }
                    break

            # 🔹 Verificar si el crédito está cancelado
            if data_dict.get("status") == "CANCELADO":
                return {"error": "Ya canceló su crédito"}

            # 🔹 Descargar el reporte HTML
            id_unico = data_dict['id']
            driver.get(f"{url2_selenium}/{id_unico}?_cp=1")
            time.sleep(2)
            
            elemento = driver.find_element(By.XPATH, "/html")
            html_tabla = elemento.get_attribute('outerHTML')

            return {
                "html_content": html_tabla,
                "data_dict": data_dict,
                "success": True
            }
            
        except Exception as e:
            print(f"Error en selenium_dni: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if driver:
                driver.quit()
    
    # Ejecutar la operación de Selenium en un hilo separado
    loop = asyncio.get_event_loop()
    selenium_result = await loop.run_in_executor(None, _selenium_sync_operation, user_dni)
    
    if not selenium_result.get("success", False):
        return selenium_result
    
    try:
        # Crear nombre único para el archivo HTML
        html_filename = f"arch_{user_dni}.html"
        
        # Escribir HTML de forma asíncrona
        async with aiofiles.open(html_filename, "w", encoding="utf-8") as archivo:
            await archivo.write(selenium_result["html_content"])
        
        print("Generando reporte PDF...")
        
        # Crear instancia del convertidor
        converter = PDFConverter()
        data_dict = selenium_result["data_dict"]
        print(data_dict['dni'])
        
        # Definir ruta completa del PDF en la carpeta específica
        pdf_filename = os.path.join(PDF_OUTPUT_DIR, f"reporte_{data_dict['dni']}.pdf")
        
        # Convertir HTML a PDF de forma asíncrona
        resultado = await converter.convertir_async(
            html_filename, 
            pdf_filename
        )
        
        if resultado['success']:
            # Verificar que el archivo existe y obtener su tamaño
            if os.path.exists(pdf_filename):
                file_size = os.path.getsize(pdf_filename)
                print(f"✅ PDF generado: {pdf_filename}")
                print(f"📁 Tamaño: {file_size} bytes")
                
                # 3. Guardar en cache
                try:
                    await cache_manager.cache_pdf(user_dni, pdf_filename)
                    print(f"💾 PDF guardado en cache: {user_dni}")
                except Exception as cache_error:
                    print(f"⚠️ Error guardando en cache: {cache_error}")
                
                # Limpiar archivo HTML temporal
                try:
                    if os.path.exists(html_filename):
                        os.remove(html_filename)
                        print(f"🗑️ Archivo HTML temporal eliminado: {html_filename}")
                except Exception as cleanup_error:
                    print(f"⚠️ Error eliminando HTML temporal: {cleanup_error}")
                
                # Opcional: limpiar PDFs antiguos de forma asíncrona
                try:
                    eliminados = await converter.limpiar_pdfs_antiguos_async(PDF_OUTPUT_DIR, dias=1)
                    if eliminados:
                        print(f"🗑️ Eliminados {eliminados} PDFs antiguos")
                except Exception as cleanup_error:
                    print(f"Advertencia en limpieza: {cleanup_error}")
                    
                # Devolver información completa del archivo
                return {
                    "filename": pdf_filename,
                    "file_size": file_size,
                    "success": True
                }
            else:
                return {
                    "success": False,
                    "error": f"PDF no encontrado después de la conversión: {pdf_filename}"
                }
        else:
            print(f"❌ Error generando PDF: {resultado['message']}")
            return {
                "success": False,
                "error": resultado['message']
            }
            
    except Exception as e:
        print(f"Error en procesamiento asíncrono: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def selenium_dni(user_dni):
    """Wrapper síncrono para la función asíncrona"""
    return asyncio.run(selenium_dni_async(user_dni))