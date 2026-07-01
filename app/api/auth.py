from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime
from app.models.schemas import UsuarioCreate, UsuarioResponse, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.database import usuarios_col

router = APIRouter()

@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UsuarioCreate):
    """
    Registra un nuevo usuario en el sistema.
    Asigna el rol especificado (admin, medico, paciente).
    """
    # 1. Mitigación NoSQL: Validamos que el email sea un string a través de Pydantic.
    # Buscamos en la base de datos si el usuario ya existe.
    usuario_existente = await usuarios_col.find_one({"email": user_in.email})
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado."
        )

    # 2. Generar el hash de la contraseña (nunca guardar en texto plano)
    hashed_password = get_password_hash(user_in.password)

    # 3. Preparar el documento para insertar en MongoDB
    user_doc = {
        "nombre": user_in.nombre,
        "email": user_in.email,
        "rol": user_in.rol.value,
        "hashed_password": hashed_password,
        "creado_en": datetime.utcnow()
    }

    # 4. Insertar en la base de datos
    result = await usuarios_col.insert_one(user_doc)
    
    # 5. Formatear la respuesta (UsuarioResponse asegura que la contraseña no se exponga)
    return UsuarioResponse(
        id=str(result.inserted_id),
        nombre=user_doc["nombre"],
        email=user_doc["email"],
        rol=user_doc["rol"],
        creado_en=user_doc["creado_en"]
    )


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Autentica a un usuario y genera un JWT (JSON Web Token).
    Usa el estándar OAuth2PasswordRequestForm (username y password).
    """
    # OAuth2 usa 'username', pero nosotros esperamos un email ahí
    # Pydantic asegura internamente que form_data.username es string, mitigando inyección
    user_db = await usuarios_col.find_one({"email": form_data.username})
    
    # Verificamos si el usuario existe y la contraseña es correcta
    if not user_db or not verify_password(form_data.password, user_db["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generamos el token JWT incluyendo el email y rol en el payload
    access_token = create_access_token(
        data={"sub": user_db["email"], "rol": user_db["rol"]}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
