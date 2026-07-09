from fastapi import APIRouter, UploadFile, File, HTTPException, status, Body, Depends
from app.services.ai_agent import procesar_audio_receta
from app.models.schemas import RecetaEstructurada
from datetime import datetime
from app.core.database import db
from app.api.auth import login_usuario
from app.api.auth import get_usuario_actual

router = APIRouter(prefix="/api/v1/recetas", tags=["Recetas por Voz"])

@router.post("/procesar_audio", response_model=RecetaEstructurada)
async def crear_receta_desde_audio(audio: UploadFile = File(...)):
    """
    Recibe un archivo de audio (WebM/WAV) grabado desde el navegador, 
    lo procesa con IA y devuelve la receta estructurada.
    """
    if not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un formato de audio.")

    try:
        # Leer los bytes del archivo enviado
        audio_bytes = await audio.read()
        
        # Mandar los bytes al cerebro (Gemini)
        receta_json = await procesar_audio_receta(audio_bytes)
        
        # FastAPI y Pydantic validan automáticamente que el JSON de Gemini
        # coincida exactamente con nuestra plantilla RecetaEstructurada
        return receta_json

    except Exception as e:
        # ESTA LÍNEA ES NUEVA: Imprimirá el error real en la terminal
        print(f"🔥 ERROR FATAL EN IA: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando el audio con IA: {str(e)}"
        )

@router.post("/guardar")
async def guardar_receta_final(
    # Body(...) recibe el JSON del frontend
    receta: RecetaEstructurada = Body(...),
    # Depends(...) ejecuta el portero que creamos arriba antes de entrar aquí
    usuario_actual: dict = Depends(get_usuario_actual) 
):
    try:
        receta_dict = receta.model_dump()
        receta_dict["fecha_creacion"] = datetime.utcnow()
        
        # --- SELLO LEGAL DE LA RECETA ---
        # Como get_usuario_actual nos devolvió el diccionario de MongoDB, ahora SÍ podemos usar corchetes []
        receta_dict["doctor_id"] = str(usuario_actual["_id"])
        receta_dict["doctor_nombre"] = usuario_actual.get("nombre", "Doctor Desconocido")
        # Si el usuario no tiene cédula en la DB, ponemos un valor por defecto
        receta_dict["doctor_cedula"] = usuario_actual.get("cedula_profesional", "Cédula no registrada en sistema")
        
        # Validamos y creamos colección si no existe
        colecciones = await db.list_collection_names()
        if "recetas" not in colecciones:
            await db.create_collection("recetas")

        # Inserción en MongoDB
        resultado = await db.recetas.insert_one(receta_dict)
        
        return {
            "mensaje": "Receta guardada exitosamente y firmada digitalmente", 
            "id": str(resultado.inserted_id)
        }

    except Exception as e:
        print(f"🔥 ERROR AL GUARDAR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar la receta: {str(e)}"
        )