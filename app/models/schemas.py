from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import List, Optional
from enum import Enum
from datetime import datetime

# Definición estricta de roles permitidos
class RolUsuario(str, Enum):
    ADMIN = "admin"
    MEDICO = "medico"
    PACIENTE = "paciente"

# ==========================================
# Esquemas para Autenticación y Tokens
# ==========================================
class Token(BaseModel):
    """
    Esquema para la respuesta de un login exitoso.
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Esquema para los datos codificados dentro del JWT.
    """
    email: Optional[str] = None

# ==========================================
# Esquemas de Usuario
# ==========================================
class UsuarioBase(BaseModel):
    """
    Campos comunes para la creación y lectura de usuarios.
    """
    nombre: str = Field(..., description="Nombre completo del usuario", min_length=2)
    email: EmailStr = Field(..., description="Correo electrónico único del usuario")
    rol: RolUsuario = Field(default=RolUsuario.PACIENTE, description="Rol del usuario en el sistema")
    cedula_profesional: Optional[str] = Field(default="No registrada")

class UsuarioRegistro(BaseModel):
    """Esquema de validación para nuevos registros duales."""
    nombre: str = Field(..., min_length=3, max_length=100)
    correo: EmailStr
    password: str = Field(..., min_length=6)
    rol: str = Field(..., pattern="^(doctor|laboratorio)$")
    
    # Campos condicionales
    cedula_profesional: Optional[str] = Field(default=None)
    nombre_laboratorio: Optional[str] = Field(default=None)

    @model_validator(mode='after')
    def validar_campos_por_rol(self):
        # Si elige doctor, exigimos la cédula
        if self.rol == 'doctor' and not self.cedula_profesional:
            raise ValueError('La cédula profesional es obligatoria para los médicos.')
        # Si elige laboratorio, exigimos el nombre del laboratorio
        if self.rol == 'laboratorio' and not self.nombre_laboratorio:
            raise ValueError('El nombre del laboratorio es obligatorio.')
        return self

class UsuarioResponse(UsuarioBase):
    """
    Esquema para devolver datos del usuario a través de la API.
    NUNCA incluye la contraseña.
    """
    id: str = Field(..., description="ID del usuario en MongoDB")
    creado_en: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación del usuario")

    class Config:
        # Permite mapear desde diccionarios de MongoDB fácilmente
        from_attributes = True

class Medicamento(BaseModel):
    nombre: Optional[str] = Field(default="No especificado", description="Nombre del medicamento")
    dosis: Optional[str] = Field(default="No especificada", description="Cantidad a tomar")
    frecuencia: Optional[str] = Field(default="No especificada", description="Cada cuánto tiempo")
    duracion: Optional[str] = Field(default="No especificada", description="Por cuántos días")

class RecetaEstructurada(BaseModel):
    paciente_nombre: Optional[str] = Field(default="No especificado", description="Nombre del paciente")
    edad: Optional[str] = Field(default="No especificada", description="Edad del paciente")
    peso: Optional[str] = Field(default="No especificado", description="Peso del paciente")
    talla: Optional[str] = Field(default="No especificada", description="Estatura del paciente")
    temperatura: Optional[str] = Field(default="No especificada", description="Temperatura corporal")
    presion_arterial: Optional[str] = Field(default="No especificada", description="Presión arterial")
    # Aquí estaba el problema: lo cambiamos a Optional
    diagnostico: Optional[str] = Field(default="No especificado", description="Diagnóstico principal detectado en el audio")
    medicamentos: List[Medicamento] = Field(default_factory=list, description="Lista de medicamentos recetados")
    indicaciones_adicionales: Optional[str] = Field(default="Ninguna", description="Dieta, reposo o cuidados extra")