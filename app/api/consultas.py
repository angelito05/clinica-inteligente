from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from bson import ObjectId
from datetime import datetime

from app.core.database import consultas_col, pacientes_col
from app.api.auth import get_usuario_actual
from app.models.consultas import ConsultaCreate, ConsultaUpdate, ConsultaResponse

router = APIRouter(prefix="/api/v1/consultas", tags=["Consultas Médicas"])

def _format_consulta(doc: dict) -> dict:
    """Convierte el documento de MongoDB al formato de respuesta."""
    doc["id"] = str(doc["_id"])
    return doc

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
