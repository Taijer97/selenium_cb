import asyncio
import os
import time
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pdf_converter import PDFConverter
from cache_manager import cache_manager
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoCleanupManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.pdf_converter = PDFConverter()
        self.is_running = False
        
    async def cleanup_pdfs_folder(self):
        """Limpia archivos PDF antiguos (más de 1 día)"""
        try:
            pdf_dir = "pdfs_generados"
            if not os.path.exists(pdf_dir):
                logger.info(f"📁 Directorio {pdf_dir} no existe, saltando limpieza")
                return 0
                
            current_time = time.time()
            archivos_eliminados = 0
            total_size_freed = 0
            
            for filename in os.listdir(pdf_dir):
                if filename.endswith('.pdf'):
                    filepath = os.path.join(pdf_dir, filename)
                    if os.path.exists(filepath):
                        stat_result = os.stat(filepath)
                        # Eliminar archivos más antiguos de 1 día (24 horas)
                        if (current_time - stat_result.st_mtime) > (24 * 3600):
                            file_size = stat_result.st_size
                            os.remove(filepath)
                            archivos_eliminados += 1
                            total_size_freed += file_size
                            logger.info(f"🗑️ PDF eliminado: {filename} ({file_size} bytes)")
            
            if archivos_eliminados > 0:
                logger.info(f"✅ Limpieza PDFs completada: {archivos_eliminados} archivos eliminados, {total_size_freed} bytes liberados")
            else:
                logger.info("📋 No hay PDFs antiguos para eliminar")
                
            return archivos_eliminados
            
        except Exception as e:
            logger.error(f"❌ Error en limpieza de PDFs: {e}")
            return 0
    
    async def cleanup_cache_folder(self):
        """Limpia cache expirado"""
        try:
            cleaned_entries = await cache_manager.cleanup_expired()
            
            # También limpiar archivos huérfanos en la carpeta cache
            cache_dir = Path("cache")
            if cache_dir.exists():
                current_time = time.time()
                orphaned_files = 0
                
                for file_path in cache_dir.glob("*"):
                    if file_path.is_file():
                        stat_result = file_path.stat()
                        # Eliminar archivos más antiguos de 1 día
                        if (current_time - stat_result.st_mtime) > (24 * 3600):
                            try:
                                file_path.unlink()
                                orphaned_files += 1
                                logger.info(f"🗑️ Archivo cache huérfano eliminado: {file_path.name}")
                            except Exception as e:
                                logger.error(f"⚠️ Error eliminando archivo cache {file_path}: {e}")
                
                if orphaned_files > 0:
                    logger.info(f"✅ Archivos cache huérfanos eliminados: {orphaned_files}")
            
            total_cleaned = cleaned_entries + (orphaned_files if 'orphaned_files' in locals() else 0)
            
            if total_cleaned > 0:
                logger.info(f"✅ Limpieza cache completada: {total_cleaned} elementos eliminados")
            else:
                logger.info("📋 No hay elementos de cache para eliminar")
                
            return total_cleaned
            
        except Exception as e:
            logger.error(f"❌ Error en limpieza de cache: {e}")
            return 0
    
    async def full_cleanup_task(self):
        """Tarea completa de limpieza que se ejecuta automáticamente"""
        logger.info("🧹 Iniciando limpieza automática diaria...")
        start_time = datetime.now()
        
        try:
            # Limpiar PDFs
            pdfs_cleaned = await self.cleanup_pdfs_folder()
            
            # Limpiar cache
            cache_cleaned = await self.cleanup_cache_folder()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ Limpieza automática completada en {duration:.2f}s")
            logger.info(f"📊 Resumen: {pdfs_cleaned} PDFs + {cache_cleaned} cache eliminados")
            
            return {
                "pdfs_cleaned": pdfs_cleaned,
                "cache_cleaned": cache_cleaned,
                "duration_seconds": duration,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error en limpieza automática: {e}")
            return {"error": str(e)}
    
    def start_scheduler(self):
        """Inicia el programador de tareas"""
        if self.is_running:
            logger.warning("⚠️ El programador ya está ejecutándose")
            return
            
        try:
            # Programar limpieza diaria a las 2:00 AM
            self.scheduler.add_job(
                self.full_cleanup_task,
                CronTrigger(hour=2, minute=00),  # Todos los días a las 2:00 AM
                id='daily_cleanup',
                name='Limpieza Automática Diaria',
                replace_existing=True
            )
            
            # También programar una limpieza cada 6 horas como respaldo
            self.scheduler.add_job(
                self.full_cleanup_task,
                CronTrigger(hour='*/6'),  # Cada 6 horas
                id='periodic_cleanup',
                name='Limpieza Periódica',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info("✅ Programador de limpieza automática iniciado")
            logger.info("📅 Limpieza diaria programada para las 2:00 AM")
            logger.info("🔄 Limpieza periódica cada 6 horas")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando programador: {e}")
    
    def stop_scheduler(self):
        """Detiene el programador de tareas"""
        if not self.is_running:
            return
            
        try:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 Programador de limpieza detenido")
        except Exception as e:
            logger.error(f"❌ Error deteniendo programador: {e}")
    
    def get_next_cleanup_time(self):
        """Obtiene la próxima hora de limpieza programada"""
        if not self.is_running:
            return None
            
        try:
            job = self.scheduler.get_job('daily_cleanup')
            if job:
                return job.next_run_time
        except Exception as e:
            logger.error(f"Error obteniendo próxima limpieza: {e}")
        return None

# Instancia global del manager
cleanup_manager = AutoCleanupManager()