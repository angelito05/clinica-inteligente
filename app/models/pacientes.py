from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class Antecedente(BaseModel):
    tipo: str = Field(..., description="Ej: Alergia, Crónico, Quirúrgico, Familiar")
    descripcion: str = Field(..., description="Detalle del antecedente")

class PacienteBase(BaseModel):
    nombre_completo: str = Field(..., min_length=2, description="Nombre completo del paciente")
    fecha_nacimiento: Optional[str] = Field(None, description="Formato YYYY-MM-DD")
    sexo: Optional[str] = Field(None, description="Masculino, Femenino, Otro")
    telefono: Optional[str] = Field(None, description="Número de contacto")
    email: Optional[EmailStr] = Field(None, description="Correo electrónico del paciente")
    tipo_sangre: Optional[str] = Field(None, description="Ej: O+, A-, etc.")
    alergias: List[str] = Field(default_factory=list, description="Lista simple de alergias")
    antecedentes: List[Antecedente] = Field(default_factory=list, description="Historial de antecedentes médicos")

class PacienteCreate(PacienteBase):
    """Esquema para crear un paciente nuevo. El medico_id se asignará en el backend."""
    pass

class PacienteUpdate(BaseModel):
    """Esquema para actualizar un paciente. Todos los campos son opcionales."""
    nombre_completo: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    sexo: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    tipo_sangre: Optional[str] = None
    alergias: Optional[List[str]] = None
    antecedentes: Optional[List[Antecedente]] = None

class PacienteResponse(PacienteBase):
    """Esquema de respuesta de un paciente."""
    id: str = Field(..., description="ID del paciente en MongoDB")
    medico_id: str = Field(..., description="ID del médico que atiende a este paciente")
    creado_en: datetime = Field(..., description="Fecha de registro")
    actualizado_en: datetime = Field(..., description="Fecha de última actualización")

    class Config:
        from_attributes = True
