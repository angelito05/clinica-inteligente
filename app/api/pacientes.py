from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from bson import ObjectId
from datetime import datetime

from app.core.database import pacientes_col
from app.api.auth import get_usuario_actual
from app.models.pacientes import PacienteCreate, PacienteUpdate, PacienteResponse

router = APIRouter(prefix="/api/v1/pacientes", tags=["Gestión de Pacientes"])

def _format_paciente(doc: dict) -> dict:
    """Convierte el documento de MongoDB al formato de respuesta."""
    doc["id"] = str(doc["_id"])
    return doc

@router.post("/", response_model=PacienteResponse, status_code=status.HTTP_201_CREATED)
async def registrar_paciente(
    paciente: PacienteCreate,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Registra un nuevo paciente en la cartera del médico actual.
    """
    medico_id = str(usuario_actual["_id"])
    
    paciente_dict = paciente.model_dump()
    paciente_dict["medico_id"] = medico_id
    paciente_dict["creado_en"] = datetime.utcnow()
    paciente_dict["actualizado_en"] = datetime.utcnow()
    
    resultado = await pacientes_col.insert_one(paciente_dict)
    paciente_dict["_id"] = resultado.inserted_id
    
    return _format_paciente(paciente_dict)

@router.get("/", response_model=List[PacienteResponse])
async def listar_mis_pacientes(
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Obtiene la lista de pacientes exclusivos del médico autenticado.
    """
    medico_id = str(usuario_actual["_id"])
    
    cursor = pacientes_col.find({"medico_id": medico_id})
    pacientes = await cursor.to_list(length=100) # Límite de 100 por ahora
    return [_format_paciente(p) for p in pacientes]

@router.get("/laboratorio/buscar", response_model=List[PacienteResponse])
async def buscar_paciente_laboratorio(
    q: str,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Permite al rol 'laboratorio' buscar pacientes por nombre para asignarles estudios.
    """
    if usuario_actual.get("rol") != "laboratorio":
        raise HTTPException(status_code=403, detail="Acceso denegado. Solo personal de laboratorio puede buscar en la base global.")
        
    # Búsqueda insensible a mayúsculas/minúsculas usando regex
    cursor = pacientes_col.find({"nombre_completo": {"$regex": q, "$options": "i"}})
    pacientes = await cursor.to_list(length=20)
    
    return [_format_paciente(p) for p in pacientes]

@router.get("/{paciente_id}", response_model=PacienteResponse)
async def obtener_paciente(
    paciente_id: str,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Obtiene los detalles de un paciente específico, si pertenece al médico.
    """
    if not ObjectId.is_valid(paciente_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
        
    medico_id = str(usuario_actual["_id"])
    
    paciente = await pacientes_col.find_one({"_id": ObjectId(paciente_id), "medico_id": medico_id})
    
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado o no autorizado")
        
    return _format_paciente(paciente)

@router.put("/{paciente_id}", response_model=PacienteResponse)
async def actualizar_paciente(
    paciente_id: str,
    update_data: PacienteUpdate,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Actualiza la información de un paciente existente.
    """
    if not ObjectId.is_valid(paciente_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
        
    medico_id = str(usuario_actual["_id"])
    
    # Filtramos solo los campos que se enviaron
    datos_actualizar = update_data.model_dump(exclude_unset=True)
    
    if not datos_actualizar:
         raise HTTPException(status_code=400, detail="No se enviaron datos para actualizar")
         
    datos_actualizar["actualizado_en"] = datetime.utcnow()
    
    resultado = await pacientes_col.find_one_and_update(
        {"_id": ObjectId(paciente_id), "medico_id": medico_id},
        {"$set": datos_actualizar},
        return_document=True
    )
    
    if not resultado:
        raise HTTPException(status_code=404, detail="Paciente no encontrado o no autorizado")
        
    return _format_paciente(resultado)

@router.delete("/{paciente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_paciente(
    paciente_id: str,
    usuario_actual: dict = Depends(get_usuario_actual)
):
    """
    Elimina a un paciente del registro del médico.
    """
    if not ObjectId.is_valid(paciente_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
        
    medico_id = str(usuario_actual["_id"])
    
    resultado = await pacientes_col.delete_one({"_id": ObjectId(paciente_id), "medico_id": medico_id})
    
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Paciente no encontrado o no autorizado")
