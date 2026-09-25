# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
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

# Configuración CORS (Estricta para Producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],  # Solo permite el frontend oficial
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
from app.api.pacientes import router as pacientes_router
from app.api.consultas import router as consultas_router
from app.api.estudios import router as estudios_router
# (Eliminado montaje estático /uploads por seguridad, usamos Cloudinary)

# Manejador Global de Excepciones No Controladas
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"🔥 ERROR GLOBAL NO CONTROLADO: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocurrió un error interno en el servidor. Por favor, intente más tarde."},
    )

# Aquí abajo registraremos los "routers" (endpoints)
app.include_router(auth_router)
app.include_router(recetas_router)
app.include_router(pacientes_router)
app.include_router(consultas_router)
app.include_router(estudios_router)

# --- SSR Endpoint Demonstration ---
templates = Jinja2Templates(directory="app/templates")

@app.get("/ssr/dashboard", response_class=HTMLResponse)
async def get_ssr_dashboard(request: Request):
    # En un caso real, estos datos vendrían de la base de datos MongoDB
    stats = {
        "total_pacientes": 145,
        "consultas_hoy": 12,
        "recetas_emitidas": 8
    }
    proximas_citas = [
        {"paciente": "Juan Pérez", "fecha": "2026-10-25", "hora": "10:00", "estado": "Confirmada"},
        {"paciente": "María García", "fecha": "2026-10-25", "hora": "11:30", "estado": "Pendiente"},
        {"paciente": "Carlos López", "fecha": "2026-10-25", "hora": "12:15", "estado": "Confirmada"},
    ]
    
    return templates.TemplateResponse(
        request=request, name="ssr_dashboard.html", context={"stats": stats, "proximas_citas": proximas_citas}
    )
# ----------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
