import os
from pydantic import BaseModel, Field, ConfigDict
from dotenv import load_dotenv

# Cargar variables desde el archivo .env
load_dotenv()

class Settings(BaseModel):
    """
    Configuración global de la aplicación.
    Valida las variables de entorno necesarias para la ejecución.
    """
    model_config = ConfigDict(frozen=True)

    PROJECT_NAME: str = Field(
        default="API de IA Clínica y Recetas por Voz",
        description="Nombre del proyecto"
    )
    VERSION: str = Field(
        default="2.0.0",
        description="Versión del microservicio"
    )
    MONGO_URI: str = Field(
        default=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        description="URI de conexión a MongoDB"
    )
    GEMINI_API_KEY: str = Field(
        default=os.getenv("GEMINI_API_KEY", ""),
        description="Llave de API para Google Gemini"
    )

# Instancia global de configuración
settings = Settings()
