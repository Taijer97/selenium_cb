from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import glob
from generate import selenium_dni_async
import uvicorn
from typing import Optional
from cache_manager import cache_manager
from fastapi import BackgroundTasks

app = FastAPI(
    title="Generador de Reportes PDF",
    description="API para generar reportes PDF de créditos usando DNI",
    version="1.0.0"
)

class DNIRequest(BaseModel):
    dni: str
    
class DNIResponse(BaseModel):
    success: bool
    message: str
    pdf_filename: Optional[str] = None
    file_size: Optional[int] = None

@app.get("/")
async def root():
    """Endpoint de bienvenida"""
    return {
        "message": "API Generador de Reportes PDF",
        "version": "1.0.0",
        "endpoints": {
            "/generate-pdf": "POST - Generar PDF por DNI",
            "/download/{filename}": "GET - Descargar PDF generado",
            "/list-pdfs": "GET - Listar PDFs disponibles"
        }
    }

@app.post("/generate-pdf", response_model=DNIResponse)
async def generate_pdf(request: DNIRequest):
    """Generar PDF y devolver información del archivo - VERSIÓN ASÍNCRONA"""
    try:
        resultado = await selenium_dni_async(request.dni)
        
        if not resultado.get("success", False):
            raise HTTPException(status_code=500, detail=resultado.get("error", "Error desconocido"))
            
        return DNIResponse(
            success=True,
            message="PDF generado exitosamente",
            pdf_filename=resultado["filename"],
            file_size=resultado["file_size"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post("/generate-and-download-pdf")
async def generate_and_download_pdf(request: DNIRequest):
    """Generar y descargar PDF directamente - VERSIÓN ASÍNCRONA"""
    try:
        resultado = await selenium_dni_async(request.dni)
        
        if not resultado.get("success", False):
            raise HTTPException(status_code=500, detail=resultado.get("error", "Error desconocido"))
        
        pdf_path = resultado["filename"]
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {pdf_path}")
        
        return FileResponse(
            path=pdf_path,
            filename=pdf_path,
            media_type='application/pdf',
            headers={
                "Content-Disposition": f"attachment; filename={pdf_path}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/download/{filename}")
async def download_pdf(filename: str):
    """
    Descarga un PDF específico
    """
    try:
        # Validar que el archivo existe y es un PDF
        if not filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
        
        # Construir la ruta completa del archivo
        file_path = os.path.join("pdfs_generados", filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/pdf'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error descargando archivo: {str(e)}")

@app.get("/list-pdfs")
async def list_pdfs():
    """
    Lista todos los PDFs disponibles
    """
    try:
        pdf_files = glob.glob(os.path.join("pdfs_generados", "reporte_*.pdf"))
        
        pdfs_info = []
        for pdf_file in pdf_files:
            file_stats = os.stat(pdf_file)
            pdfs_info.append({
                "filename": os.path.basename(pdf_file),
                "size_bytes": file_stats.st_size,
                "created_timestamp": file_stats.st_ctime,
                "download_url": f"/download/{os.path.basename(pdf_file)}"
            })
        
        # Ordenar por fecha de creación (más reciente primero)
        pdfs_info.sort(key=lambda x: x['created_timestamp'], reverse=True)
        
        return {
            "total_pdfs": len(pdfs_info),
            "pdfs": pdfs_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando PDFs: {str(e)}")

@app.delete("/cleanup-pdfs")
async def cleanup_old_pdfs():
    """
    Limpia PDFs antiguos (más de 1 hora)
    """
    try:
        from pdf_converter import PDFConverter
        
        converter = PDFConverter()
        eliminados = converter.limpiar_pdfs_antiguos(os.path.join("pdfs_generados", "reporte_*.pdf"), minutos=60)
        
        return {
            "message": f"Limpieza completada. {len(eliminados)} archivos eliminados",
            "deleted_files": eliminados
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en limpieza: {str(e)}")

@app.get("/cache/stats")
async def get_cache_stats():
    """Obtiene estadísticas del cache"""
    try:
        stats = await cache_manager.get_cache_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/cache/cleanup")
async def cleanup_cache():
    """Limpia entradas expiradas del cache"""
    try:
        cleaned = await cache_manager.cleanup_expired()
        return {"success": True, "cleaned_entries": cleaned}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")