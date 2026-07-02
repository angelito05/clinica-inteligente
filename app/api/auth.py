from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.core.database import usuarios_col
from app.core.security import verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

# Molde Pydantic específico para recibir el login
class LoginRequest(BaseModel):
    correo: EmailStr
    password: str

@router.post("/login")
async def login_usuario(credenciales: LoginRequest):
    # 1. Buscar al usuario en MongoDB
    usuario_db = await usuarios_col.find_one({"correo": credenciales.correo})
    
    if not usuario_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    
    # 2. Verificar la contraseña encriptada
    if not verify_password(credenciales.password, usuario_db["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    
    # 3. Generar el Token JWT
    token_data = {
        "sub": str(usuario_db["_id"]),
        "rol": usuario_db["rol"]
    }
    access_token = create_access_token(data=token_data)
    
    # 4. Devolver los datos al frontend
    return {
        "token": access_token,
        "rol": usuario_db["rol"],
        "nombre": usuario_db["nombre"]
    }