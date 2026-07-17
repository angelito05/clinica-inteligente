from app.core.database import db
from app.core.config import settings
import jwt
from datetime import timezone, datetime
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from app.core.database import usuarios_col
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.schemas import UsuarioRegistro 
from bson import ObjectId

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
        "nombre": usuario_db["nombre"],
        "cedula": usuario_db.get("cedula_profesional", "No registrada")
    }

@router.post("/registro", status_code=status.HTTP_201_CREATED)
async def registrar_usuario(usuario: UsuarioRegistro):
    # 1. Verificar si el correo ya está en uso
    existe = await usuarios_col.find_one({"correo": usuario.correo})
    if existe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este correo ya está registrado en el sistema."
        )
    
    # 2. Convertir el modelo a diccionario
    usuario_dict = usuario.model_dump()
    
    # 3. Hashear la contraseña y eliminar la versión en texto plano
    password_plano = usuario_dict.pop("password")
    usuario_dict["password_hash"] = get_password_hash(password_plano)
    
    # 4. Agregar metadatos
    usuario_dict["fecha_registro"] = datetime.now(timezone.utc)
    usuario_dict["estado"] = "activo"
    
    # 5. Guardar en MongoDB
    await usuarios_col.insert_one(usuario_dict)
    
    return {
        "mensaje": "Cuenta creada exitosamente.",
        "rol": usuario_dict["rol"]
    }

async def get_usuario_actual(request: Request):
    """
    Middleware que lee el Token JWT de la cabecera, lo decodifica, 
    y busca al doctor en la base de datos para devolver su perfil completo.
    """
    auth_header = request.headers.get("Authorization")
    
    # 1. Validar que enviaron el Token
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado. Inicie sesión nuevamente."
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        # 2. Decodificar el Token (Asegúrate de usar la misma clave secreta y algoritmo que en tu login)
        # Si usas jose en vez de jwt: from jose import jwt
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
            
        # 3. Buscar al doctor en MongoDB para extraer su Cédula y Nombre real
        usuario_db = await db.usuarios.find_one({"_id": ObjectId(user_id)})
        
        if not usuario_db:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El usuario ya no existe")
            
        # Devolvemos el documento completo de MongoDB como un diccionario
        return usuario_db
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Error validando sesión: {str(e)}"
        )