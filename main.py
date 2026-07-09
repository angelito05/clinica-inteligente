# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import check_db_connection
from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.recetas import router as recetas_router

# El 'lifespan' maneja lo que pasa cuando el servidor se enciende y se apaga
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando Motor de IA Clínica...")
    # Probamos que MongoDB esté conectado antes de aceptar peticiones
    await check_db_connection()
    yield
    print("Apagando el servidor. Limpiando conexiones...")

# Instancia principal de FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Microservicio asíncrono para extracción OCR, procesamiento Gemini y dictado por voz.",
    version=settings.VERSION,
    lifespan=lifespan
)

# Configuración CORS (Vital para que tu frontend HTML/JS pueda comunicarse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Orígenes permitidos controlados por entorno
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],
)

# Ruta base de prueba (Health Check)
@app.get("/")
async def root():
    return {
        "status": "Online",
        "mensaje": "Bienvenido al Microservicio de IA Clínica",
        "motor": "FastAPI + MongoDB"
    }

from app.api import auth

# Aquí abajo registraremos los "routers" (endpoints)
app.include_router(auth_router)
app.include_router(recetas_router)
