from pydantic import BaseModel, EmailStr, Field
from enum import Enum
from typing import Optional
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

class UsuarioCreate(UsuarioBase):
    """
    Esquema para la creación de un nuevo usuario (Registro).
    Incluye la contraseña en texto plano que será hasheada.
    """
    password: str = Field(..., description="Contraseña en texto plano", min_length=6)

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
