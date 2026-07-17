from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from typing import List
from bson import ObjectId
from datetime import datetime

from app.core.database import consultas_col, pacientes_col
from app.api.auth import get_usuario_actual
from app.models.consultas import ConsultaCreate, ConsultaUpdate, ConsultaResponse
from app.models.schemas import ConsultaDictadaIA
from app.services.ai_agent import procesar_audio_consulta_completa, generar_resumen_historial

router = APIRouter(prefix="/api/v1/consultas", tags=["Consultas Médicas"])

def _format_consulta(doc: dict) -> dict:
    """Convierte el documento de MongoDB al formato de respuesta."""
    doc["id"] = str(doc["_id"])
    return doc

@router.post("/procesar_audio", response_model=ConsultaDictadaIA)
async def crear_consulta_desde_audio(audio: UploadFile = File(...)):
    """
    Recibe el audio completo de la consulta médica y extrae formato SOAP estructurado.
    """
    if not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un formato de audio.")

    try:
        audio_bytes = await audio.read()
        consulta_json = await procesar_audio_consulta_completa(audio_bytes)
        return consulta_json
    except Exception as e:
        print(f"🔥 ERROR FATAL EN IA CONSULTA: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno procesando la consulta con IA. Por favor intente más tarde."
        )

@router.post("/", response_model=ConsultaResponse, status_code=status.HTTP_201_CREATED)
async def registrar_consulta(
    consulta: ConsultaCreate,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Inicia una nueva consulta médica para un paciente existente.
    """
    medico_id = str(usuario_actual["_id"])
    
    # 1. Verificar que el paciente existe y pertenece al médico actual
    if not ObjectId.is_valid(consulta.paciente_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
        
    paciente = await pacientes_col.find_one({
        "_id": ObjectId(consulta.paciente_id), 
        "medico_id": medico_id
    })
    
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado o no autorizado")
    
    # 2. Preparar el documento de la consulta
    consulta_dict = consulta.model_dump()
    consulta_dict["medico_id"] = medico_id
    consulta_dict["creado_en"] = datetime.utcnow()
    consulta_dict["actualizado_en"] = datetime.utcnow()
    
    # 3. Guardar en BD
    resultado = await consultas_col.insert_one(consulta_dict)
    consulta_dict["_id"] = resultado.inserted_id
    
    return _format_consulta(consulta_dict)

@router.get("/paciente/{paciente_id}", response_model=List[ConsultaResponse])
async def listar_consultas_por_paciente(
    paciente_id: str,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Obtiene el historial de consultas (Expediente Clínico) de un paciente específico.
    """
    medico_id = str(usuario_actual["_id"])
    
    # Verificamos si el médico tiene acceso a este paciente (es opcional pero buena práctica)
    if not ObjectId.is_valid(paciente_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
        
    paciente = await pacientes_col.find_one({"_id": ObjectId(paciente_id), "medico_id": medico_id})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado o no autorizado")
    
    # Buscamos las consultas ordenadas por la más reciente primero
    cursor = consultas_col.find({"paciente_id": paciente_id, "medico_id": medico_id}).sort("creado_en", -1)
    consultas = await cursor.to_list(length=100)
    
    return [_format_consulta(c) for c in consultas]

@router.get("/paciente/{paciente_id}/resumen")
async def obtener_resumen_historial_ia(
    paciente_id: str,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Genera un resumen clínico rápido usando IA del historial completo del paciente.
    """
    medico_id = str(usuario_actual["_id"])
    
    if not ObjectId.is_valid(paciente_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
        
    paciente = await pacientes_col.find_one({"_id": ObjectId(paciente_id), "medico_id": medico_id})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado o no autorizado")
    
    # Buscamos las últimas consultas (ej. las últimas 5)
    cursor = consultas_col.find({"paciente_id": paciente_id, "medico_id": medico_id}).sort("creado_en", -1).limit(5)
    consultas = await cursor.to_list(length=5)
    
    if not consultas:
        return {"resumen": "El paciente no tiene consultas previas en el historial."}

    # Formateamos como texto
    historial_texto = ""
    for c in consultas:
        fecha = c.get("creado_en", datetime.utcnow()).strftime("%Y-%m-%d")
        historial_texto += f"- Fecha: {fecha}\n"
        historial_texto += f"  Motivo: {c.get('motivo_consulta')}\n"
        historial_texto += f"  Diagnóstico: {c.get('diagnostico')}\n"
        sv = c.get('signos_vitales', {})
        historial_texto += f"  Signos: Peso {sv.get('peso')}, Talla {sv.get('talla')}, Temp {sv.get('temperatura')}, PA {sv.get('presion_arterial')}\n"
        historial_texto += "\n"

    try:
        resumen = await generar_resumen_historial(historial_texto)
        return {"resumen": resumen}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al generar el resumen con IA")

@router.get("/{consulta_id}", response_model=ConsultaResponse)
async def obtener_consulta(
    consulta_id: str,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Obtiene los detalles de una consulta específica.
    """
    if not ObjectId.is_valid(consulta_id):
        raise HTTPException(status_code=400, detail="ID de consulta inválido")
        
    medico_id = str(usuario_actual["_id"])
    
    consulta = await consultas_col.find_one({"_id": ObjectId(consulta_id), "medico_id": medico_id})
    
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta no encontrada o no autorizada")
        
    return _format_consulta(consulta)

@router.put("/{consulta_id}", response_model=ConsultaResponse)
async def actualizar_consulta(
    consulta_id: str,
    update_data: ConsultaUpdate,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Actualiza la información de una consulta (ej. para agregar el diagnóstico o asociar una receta).
    """
    if not ObjectId.is_valid(consulta_id):
        raise HTTPException(status_code=400, detail="ID de consulta inválido")
        
    medico_id = str(usuario_actual["_id"])
    
    datos_actualizar = update_data.model_dump(exclude_unset=True)
    
    if not datos_actualizar:
         raise HTTPException(status_code=400, detail="No se enviaron datos para actualizar")
         
    datos_actualizar["actualizado_en"] = datetime.utcnow()
    
    resultado = await consultas_col.find_one_and_update(
        {"_id": ObjectId(consulta_id), "medico_id": medico_id},
        {"$set": datos_actualizar},
        return_document=True
    )
    
    if not resultado:
        raise HTTPException(status_code=404, detail="Consulta no encontrada o no autorizada")
        
    return _format_consulta(resultado)
