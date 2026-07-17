import os
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt  # <-- Usamos bcrypt directamente, adiós passlib

from app.core.config import settings

# Llave secreta para firmar los JWT
SECRET_KEY = settings.JWT_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # El token dura 8 horas

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra su versión encriptada."""
    # Bcrypt requiere que todo esté en formato 'bytes'
    password_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    
    return bcrypt.checkpw(password_bytes, hash_bytes)

def get_password_hash(password: str) -> str:
    """Encripta la contraseña de forma segura."""
    # Convertimos el string a bytes
    pwd_bytes = password.encode('utf-8')
    
    # Generamos la "sal" y el hash nativo
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    
    # Lo decodificamos de vuelta a string para guardarlo en MongoDB
    return hashed_password.decode('utf-8')

def create_access_token(data: dict):
    """Genera el Token JWT para la sesión."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt