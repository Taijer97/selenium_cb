import os
import asyncio
import aiofiles
import subprocess
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFConverter:
    def __init__(self):
        self.node_path = "node"
        self.script_path = "convertir.js"
        self.timeout = 30
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    def verificar_dependencias(self):
        """Verifica que Node.js esté disponible"""
        try:
            result = subprocess.run([self.node_path, "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info(f"Node.js encontrado: {result.stdout.strip()}")
                return True
            else:
                logger.error("Node.js no está disponible")
                return False
        except Exception as e:
            logger.error(f"Error verificando Node.js: {e}")
            return False
    
    async def _file_exists_async(self, file_path):
        """Verifica si un archivo existe de forma asíncrona"""
        try:
            # Usar os.path.exists en lugar de aiofiles.os.stat
            loop = asyncio.get_event_loop()
            exists = await loop.run_in_executor(None, os.path.exists, file_path)
            return exists
        except Exception as e:
            logger.error(f"Error verificando archivo {file_path}: {e}")
            return False
    
    def _convertir_sync(self, html_file, pdf_file):
        """Función síncrona para ejecutar la conversión"""
        try:
            logger.info(f"Iniciando conversión: {html_file} -> {pdf_file}")
            
            # Ejecutar el comando de conversión
            cmd = [self.node_path, self.script_path, html_file, pdf_file]
            logger.info(f"Ejecutando comando: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                logger.info(f"Conversión exitosa. Salida: {result.stdout}")
                return {"success": True, "message": result.stdout}
            else:
                error_msg = f"Error en conversión. Código: {result.returncode}, Error: {result.stderr}"
                logger.error(error_msg)
                return {"success": False, "message": error_msg}
                
        except subprocess.TimeoutExpired:
            error_msg = f"Timeout en conversión después de {self.timeout} segundos"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Error inesperado en conversión: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
    
    async def convertir_async(self, html_file, pdf_file):
        """Convierte HTML a PDF de forma asíncrona (compatible con Windows)"""
        try:
            logger.info(f"Iniciando conversión asíncrona: {html_file} -> {pdf_file}")
            
            # Verificar dependencias
            if not self.verificar_dependencias():
                return {"success": False, "message": "Node.js no está disponible"}
            
            # Verificar que el archivo HTML existe
            if not await self._file_exists_async(html_file):
                error_msg = f"Archivo HTML no encontrado: {html_file}"
                logger.error(error_msg)
                return {"success": False, "message": error_msg}
            
            # Ejecutar conversión en un hilo separado
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, 
                self._convertir_sync, 
                html_file, 
                pdf_file
            )
            
            if result["success"]:
                # Verificar que el PDF se creó correctamente
                if await self._file_exists_async(pdf_file):
                    file_size = await self._get_file_size_async(pdf_file)
                    logger.info(f"PDF creado exitosamente: {pdf_file} ({file_size} bytes)")
                    return {"success": True, "message": f"PDF generado exitosamente: {pdf_file}"}
                else:
                    error_msg = "PDF no se creó correctamente"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg}
            else:
                return result
                
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
    
    async def _get_file_size_async(self, file_path):
        """Obtiene el tamaño de un archivo de forma asíncrona"""
        try:
            loop = asyncio.get_event_loop()
            size = await loop.run_in_executor(None, lambda: os.path.getsize(file_path))
            return size
        except Exception as e:
            logger.error(f"Error obteniendo tamaño de {file_path}: {e}")
            return 0
    
    async def limpiar_pdfs_antiguos_async(self, directorio=".", dias=1):
        """Limpia PDFs antiguos de forma asíncrona"""
        try:
            import time
            current_time = time.time()
            archivos_eliminados = 0
            
            for filename in os.listdir(directorio):
                if filename.endswith('.pdf'):
                    filepath = os.path.join(directorio, filename)
                    if await self._file_exists_async(filepath):
                        stat_result = os.stat(filepath)
                        if (current_time - stat_result.st_mtime) > (dias * 24 * 3600):
                            os.remove(filepath)
                            archivos_eliminados += 1
                            logger.info(f"PDF antiguo eliminado: {filename}")
            
            return archivos_eliminados
        except Exception as e:
            logger.error(f"Error limpiando PDFs antiguos: {e}")
            return 0
    
    def limpiar_pdfs_antiguos(self, directorio=".", minutos=60):
        """Limpia PDFs antiguos de forma síncrona"""
        try:
            import time
            import glob
            current_time = time.time()
            archivos_eliminados = []
            
            # Si directorio contiene un patrón como "reporte_*.pdf", usar glob
            if "*" in directorio:
                pattern = directorio
                archivos = glob.glob(pattern)
            else:
                # Si es un directorio, buscar PDFs en él
                if os.path.isdir(directorio):
                    archivos = [os.path.join(directorio, f) for f in os.listdir(directorio) if f.endswith('.pdf')]
                else:
                    archivos = []
            
            for filepath in archivos:
                if os.path.exists(filepath):
                    stat_result = os.stat(filepath)
                    # Convertir minutos a segundos
                    if (current_time - stat_result.st_mtime) > (minutos * 60):
                        os.remove(filepath)
                        archivos_eliminados.append(os.path.basename(filepath))
                        logger.info(f"PDF antiguo eliminado: {os.path.basename(filepath)}")
            
            return archivos_eliminados
        except Exception as e:
            logger.error(f"Error limpiando PDFs antiguos: {e}")
            return []
    
    def obtener_info_ultima_conversion(self):
        """Obtiene información de la última conversión"""
        try:
            # Buscar el PDF más reciente
            pdfs = [f for f in os.listdir('.') if f.endswith('.pdf')]
            if not pdfs:
                return None
            
            pdf_mas_reciente = max(pdfs, key=lambda x: os.path.getmtime(x))
            stat_info = os.stat(pdf_mas_reciente)
            
            return {
                'archivo': pdf_mas_reciente,
                'tamaño': stat_info.st_size,
                'fecha_creacion': datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            }
        except Exception as e:
            logger.error(f"Error obteniendo info de última conversión: {e}")
            return None