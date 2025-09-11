import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import aiofiles
import asyncio
from pathlib import Path

class PDFCacheManager:
    def __init__(self, cache_dir: str = "cache", max_age_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.max_age_hours = max_age_hours
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_file = self.cache_dir / "cache_index.json"
        
        # Crear directorio de cache si no existe
        self.cache_dir.mkdir(exist_ok=True)
        
    def _get_cache_key(self, dni: str) -> str:
        """Genera una clave única para el DNI"""
        return hashlib.md5(dni.encode()).hexdigest()
    
    def _get_pdf_cache_path(self, cache_key: str) -> Path:
        """Obtiene la ruta del PDF en cache"""
        return self.cache_dir / f"pdf_{cache_key}.pdf"
    
    async def _load_cache_index(self) -> Dict[str, Any]:
        """Carga el índice de cache desde disco"""
        try:
            if self.cache_file.exists():
                async with aiofiles.open(self.cache_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
        except Exception as e:
            print(f"⚠️ Error cargando cache index: {e}")
        return {}
    
    async def _save_cache_index(self, index: Dict[str, Any]):
        """Guarda el índice de cache en disco"""
        try:
            async with aiofiles.open(self.cache_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(index, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"⚠️ Error guardando cache index: {e}")
    
    def _is_expired(self, timestamp: float) -> bool:
        """Verifica si un elemento del cache ha expirado"""
        expiry_time = timestamp + (self.max_age_hours * 3600)
        return time.time() > expiry_time
    
    async def get_cached_pdf(self, dni: str) -> Optional[Dict[str, Any]]:
        """Obtiene un PDF del cache si existe y no ha expirado"""
        cache_key = self._get_cache_key(dni)
        
        # Verificar cache en memoria primero
        if cache_key in self.memory_cache:
            cache_entry = self.memory_cache[cache_key]
            if not self._is_expired(cache_entry['timestamp']):
                print(f"📋 Cache HIT (memoria): {dni}")
                return cache_entry
            else:
                # Eliminar entrada expirada de memoria
                del self.memory_cache[cache_key]
        
        # Verificar cache en disco
        cache_index = await self._load_cache_index()
        if cache_key in cache_index:
            cache_entry = cache_index[cache_key]
            if not self._is_expired(cache_entry['timestamp']):
                pdf_path = self._get_pdf_cache_path(cache_key)
                if pdf_path.exists():
                    # Cargar en memoria para próximas consultas
                    cache_entry['pdf_path'] = str(pdf_path)
                    self.memory_cache[cache_key] = cache_entry
                    print(f"📋 Cache HIT (disco): {dni}")
                    return cache_entry
        
        print(f"📋 Cache MISS: {dni}")
        return None
    
    async def cache_pdf(self, dni: str, pdf_path: str, metadata: Dict[str, Any] = None) -> bool:
        """Guarda un PDF en el cache"""
        try:
            cache_key = self._get_cache_key(dni)
            timestamp = time.time()
            
            # Copiar PDF al directorio de cache
            cached_pdf_path = self._get_pdf_cache_path(cache_key)
            
            # Copiar archivo PDF
            async with aiofiles.open(pdf_path, 'rb') as src:
                content = await src.read()
                async with aiofiles.open(cached_pdf_path, 'wb') as dst:
                    await dst.write(content)
            
            # Crear entrada de cache
            cache_entry = {
                'dni': dni,
                'timestamp': timestamp,
                'pdf_path': str(cached_pdf_path),
                'original_path': pdf_path,
                'file_size': len(content),
                'created_at': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # Guardar en memoria
            self.memory_cache[cache_key] = cache_entry
            
            # Actualizar índice en disco
            cache_index = await self._load_cache_index()
            cache_index[cache_key] = cache_entry.copy()
            cache_index[cache_key]['pdf_path'] = str(cached_pdf_path)  # Ruta relativa al cache
            await self._save_cache_index(cache_index)
            
            print(f"💾 PDF cacheado: {dni} -> {cached_pdf_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error cacheando PDF para {dni}: {e}")
            return False
    
    async def cleanup_expired(self) -> int:
        """Limpia entradas expiradas del cache"""
        cleaned_count = 0
        
        # Limpiar memoria
        expired_keys = []
        for key, entry in self.memory_cache.items():
            if self._is_expired(entry['timestamp']):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
            cleaned_count += 1
        
        # Limpiar disco
        cache_index = await self._load_cache_index()
        expired_disk_keys = []
        
        for key, entry in cache_index.items():
            if self._is_expired(entry['timestamp']):
                expired_disk_keys.append(key)
                # Eliminar archivo PDF
                pdf_path = self._get_pdf_cache_path(key)
                try:
                    if pdf_path.exists():
                        pdf_path.unlink()
                except Exception as e:
                    print(f"⚠️ Error eliminando PDF expirado {pdf_path}: {e}")
        
        # Actualizar índice
        for key in expired_disk_keys:
            del cache_index[key]
            cleaned_count += 1
        
        if expired_disk_keys:
            await self._save_cache_index(cache_index)
        
        if cleaned_count > 0:
            print(f"🧹 Cache limpiado: {cleaned_count} entradas expiradas eliminadas")
        
        return cleaned_count
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache"""
        cache_index = await self._load_cache_index()
        
        total_entries = len(cache_index)
        memory_entries = len(self.memory_cache)
        
        # Calcular tamaño total
        total_size = 0
        valid_entries = 0
        
        for entry in cache_index.values():
            if not self._is_expired(entry['timestamp']):
                valid_entries += 1
                total_size += entry.get('file_size', 0)
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': total_entries - valid_entries,
            'memory_entries': memory_entries,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_dir': str(self.cache_dir),
            'max_age_hours': self.max_age_hours
        }

# Instancia global del cache
cache_manager = PDFCacheManager(cache_dir="cache", max_age_hours=24)