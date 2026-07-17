from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class SignosVitales(BaseModel):
    peso: Optional[str] = Field(None, description="Peso en kg")
    talla: Optional[str] = Field(None, description="Estatura en cm/m")
    temperatura: Optional[str] = Field(None, description="Temperatura en °C")
    presion_arterial: Optional[str] = Field(None, description="Ej: 120/80 mmHg")
    frecuencia_cardiaca: Optional[str] = Field(None, description="Latidos por minuto")
    frecuencia_respiratoria: Optional[str] = Field(None, description="Respiraciones por minuto")
    saturacion_oxigeno: Optional[str] = Field(None, description="Porcentaje de SpO2")

class ConsultaBase(BaseModel):
    paciente_id: str = Field(..., description="ID del paciente al que pertenece esta consulta")
    motivo_consulta: str = Field(..., description="Razón principal por la que acude el paciente")
    sintomas: Optional[str] = Field(None, description="Descripción de los síntomas")
    signos_vitales: Optional[SignosVitales] = Field(default_factory=SignosVitales, description="Mediciones físicas")
    diagnostico: Optional[str] = Field(None, description="Diagnóstico del médico")
    notas_evolucion: Optional[str] = Field(None, description="Notas clínicas adicionales")
    receta_id: Optional[str] = Field(None, description="ID de la receta generada en esta consulta (opcional)")

class ConsultaCreate(ConsultaBase):
    """Esquema para iniciar una nueva consulta."""
    pass

class ConsultaUpdate(BaseModel):
    """Esquema para actualizar una consulta (ej. agregar diagnóstico o receta más tarde)."""
    motivo_consulta: Optional[str] = None
    sintomas: Optional[str] = None
    signos_vitales: Optional[SignosVitales] = None
    diagnostico: Optional[str] = None
    notas_evolucion: Optional[str] = None
    receta_id: Optional[str] = None

class ConsultaResponse(ConsultaBase):
    """Esquema de respuesta al obtener una consulta."""
    id: str = Field(..., description="ID de la consulta en MongoDB")
    medico_id: str = Field(..., description="ID del médico que atendió la consulta")
    creado_en: datetime = Field(..., description="Fecha y hora de la consulta")
    actualizado_en: datetime = Field(..., description="Fecha de última modificación")

    class Config:
        from_attributes = True
