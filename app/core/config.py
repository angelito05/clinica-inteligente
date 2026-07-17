from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Configuración global de la aplicación.
    Valida las variables de entorno necesarias para la ejecución.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", frozen=True)

    PROJECT_NAME: str = Field(
        default="API de IA Clínica y Recetas por Voz",
        description="Nombre del proyecto"
    )
    VERSION: str = Field(
        default="2.0.0",
        description="Versión del microservicio"
    )
    MONGO_URI: str = Field(
        default="MONGO_URI",
        description="URI de conexión a MongoDB"
    )
    GEMINI_API_KEY: str = Field(
        default="",
        description="Llave de API para Google Gemini"
    )
    GROQ_API_KEY: str
    CORS_ORIGINS: list[str] = Field(
        default=["*"],
        description="Orígenes permitidos para CORS (permite Vercel y Localhost)"
    )
    SECRET_KEY: str = Field(
        default="SECRET_KEY",
        description="Clave secreta para firmar los tokens JWT"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        description="Minutos de expiración del token JWT"
    )
    JWT_SECRET: str = Field(
        default="SUPER_SECRET_KEY"
    )
    FRONTEND_URL: str = Field(
        default="http://127.0.0.1:5500"
    )
    CLOUDINARY_URL: str = Field(
        default="",
        description="URL de conexión a Cloudinary"
    )

# Instancia global de configuración
settings = Settings()

# Configuración automática de Cloudinary si la URL está presente
if settings.CLOUDINARY_URL:
    import os
    import cloudinary
    # Pydantic carga el .env internamente, por lo que debemos forzarlo en el SO para que Cloudinary lo vea
    os.environ['CLOUDINARY_URL'] = settings.CLOUDINARY_URL
    cloudinary.reset_config()
    cloudinary.config(secure=True)
