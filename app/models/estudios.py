from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EstudioBase(BaseModel):
    paciente_id: str = Field(..., description="ID del paciente")
    tipo_estudio: str = Field(..., description="Tipo de estudio (e.g., Sangre, Rayos X)")
    notas_laboratorio: Optional[str] = Field(None, description="Observaciones del laboratorista")

class EstudioCreate(EstudioBase):
    pass

class EstudioResponse(EstudioBase):
    id: str = Field(..., description="ID del estudio")
    medico_id: str = Field(..., description="ID del médico (extraído del paciente)")
    laboratorio_id: str = Field(..., description="ID del laboratorio que lo subió")
    nombre_archivo: str = Field(..., description="Nombre original del archivo")
    url_archivo: str = Field(..., description="Ruta relativa para acceder al archivo")
    creado_en: datetime = Field(..., description="Fecha y hora de subida")

    class Config:
        from_attributes = True
