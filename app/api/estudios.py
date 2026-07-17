import os
import shutil
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import uuid

from app.core.database import estudios_col, pacientes_col
from app.api.auth import get_usuario_actual
from app.models.estudios import EstudioResponse
from app.core.config import settings
import cloudinary.uploader
import cloudinary.api

router = APIRouter(prefix="/api/v1/estudios", tags=["Estudios de Laboratorio"])

def _format_estudio(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc

@router.post("/subir", response_model=EstudioResponse, status_code=status.HTTP_201_CREATED)
async def subir_estudio(
    paciente_id: str = Form(...),
    tipo_estudio: str = Form(...),
    notas_laboratorio: Optional[str] = Form(None),
    archivo: UploadFile = File(...),
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Sube un archivo de estudio (PDF/Imagen) asociado a un paciente.
    Debe ser realizado por un perfil de laboratorio (o un doctor autorizado).
    """
    # 1. Validar al paciente
    if not ObjectId.is_valid(paciente_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
        
    paciente = await pacientes_col.find_one({"_id": ObjectId(paciente_id)})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
        
    medico_id = paciente["medico_id"]
    laboratorio_id = str(usuario_actual["_id"])

    # 2. Validar formato
    ext = os.path.splitext(archivo.filename)[1]
    if ext.lower() not in [".pdf", ".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Formato no permitido. Solo PDF, JPG, PNG.")

    # 3. Subir a Cloudinary
    if not settings.CLOUDINARY_URL:
        raise HTTPException(status_code=500, detail="Cloudinary no está configurado en el servidor.")
        
    try:
        # cloudinary.uploader.upload acepta directamente el file buffer de FastAPI
        upload_result = cloudinary.uploader.upload(
            archivo.file,
            folder="clinica_inteligente/estudios",
            resource_type="auto" # Para soportar PDFs y fotos
        )
        secure_url = upload_result.get("secure_url")
        public_id = upload_result.get("public_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo a Cloudinary: {str(e)}")

    # 4. Guardar metadatos en MongoDB
    estudio_dict = {
        "paciente_id": paciente_id,
        "medico_id": medico_id,
        "laboratorio_id": laboratorio_id,
        "tipo_estudio": tipo_estudio,
        "notas_laboratorio": notas_laboratorio,
        "nombre_archivo": archivo.filename,
        "url_archivo": secure_url,
        "cloudinary_public_id": public_id,
        "creado_en": datetime.utcnow()
    }

    resultado = await estudios_col.insert_one(estudio_dict)
    estudio_dict["_id"] = resultado.inserted_id

    return _format_estudio(estudio_dict)

@router.get("/paciente/{paciente_id}", response_model=List[EstudioResponse])
async def listar_estudios_paciente(
    paciente_id: str,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Obtiene todos los estudios de un paciente.
    """
    if not ObjectId.is_valid(paciente_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
        
    # Obtener el paciente para validar acceso
    paciente = await pacientes_col.find_one({"_id": ObjectId(paciente_id)})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
        
    # Verificación simple: O es el doctor del paciente, o es el laboratorio (o admin)
    user_id = str(usuario_actual["_id"])
    if usuario_actual.get("rol") == "doctor" and paciente["medico_id"] != user_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este paciente")
        
    cursor = estudios_col.find({"paciente_id": paciente_id}).sort("creado_en", -1)
    estudios = await cursor.to_list(length=100)
    
    return [_format_estudio(e) for e in estudios]

@router.delete("/{estudio_id}")
async def eliminar_estudio(
    estudio_id: str,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Elimina un estudio y su archivo asociado.
    """
    if not ObjectId.is_valid(estudio_id):
        raise HTTPException(status_code=400, detail="ID inválido")
        
    estudio = await estudios_col.find_one({"_id": ObjectId(estudio_id)})
    if not estudio:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
        
    user_id = str(usuario_actual["_id"])
    if usuario_actual.get("rol") == "doctor" and estudio["medico_id"] != user_id:
        raise HTTPException(status_code=403, detail="No tienes permisos para eliminar este estudio")
    # Podríamos permitir que el laboratorio también lo borre:
    # elif usuario_actual.get("rol") == "laboratorio" and estudio["laboratorio_id"] != user_id: ...
        
    # Eliminar archivo de Cloudinary si existe el public_id
    public_id = estudio.get("cloudinary_public_id")
    if public_id:
        try:
            cloudinary.uploader.destroy(public_id, resource_type="image" if not public_id.endswith('.pdf') else "raw")
        except Exception as e:
            print(f"Error borrando archivo de Cloudinary: {e}")
    else:
        # Fallback local (por si quedan archivos viejos no migrados)
        file_path = os.path.join(os.getcwd(), estudio["url_archivo"].lstrip("/"))
        if os.path.exists(file_path):
            os.remove(file_path)
        
    # Eliminar de MongoDB
    await estudios_col.delete_one({"_id": ObjectId(estudio_id)})
    
    return {"mensaje": "Estudio eliminado"}

@router.post("/{estudio_id}/analizar")
async def analizar_estudio(
    estudio_id: str,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Toma un archivo de estudio existente y lo analiza con la IA de Gemini.
    """
    if not ObjectId.is_valid(estudio_id):
        raise HTTPException(status_code=400, detail="ID de estudio inválido")
        
    estudio = await estudios_col.find_one({"_id": ObjectId(estudio_id)})
    if not estudio:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
        
    user_id = str(usuario_actual["_id"])
    if usuario_actual.get("rol") == "doctor" and estudio["medico_id"] != user_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este estudio")
        
    file_url = estudio["url_archivo"]
    if not file_url:
        raise HTTPException(status_code=404, detail="El archivo no existe")

    from app.services.ai_agent import analizar_estudio_ia
    try:
        # Pasamos la URL remota de Cloudinary o el path relativo si es local
        analisis_markdown = await analizar_estudio_ia(file_url)
        
        # Opcional: Guardar el análisis en el estudio para no volver a gastar tokens
        await estudios_col.update_one(
            {"_id": ObjectId(estudio_id)},
            {"$set": {"analisis_ia": analisis_markdown}}
        )
        
        return {"analisis": analisis_markdown}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"🔥 ERROR AL ANALIZAR CON IA: {str(e)}")
        raise HTTPException(status_code=500, detail="Error procesando el archivo con IA.")
