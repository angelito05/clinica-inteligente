from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# Inicializamos el cliente asíncrono
client = AsyncIOMotorClient(settings.MONGO_URI)

# Seleccionamos la base de datos (la misma que creaste en Compass)
db = client.clinica_inteligente

# Exportamos las referencias directas a las colecciones para usarlas en otros archivos
usuarios_col = db.get_collection("usuarios")
historial_col = db.get_collection("historial_clinico")
recetas_col = db.get_collection("recetas_inteligentes")
extracciones_col = db.get_collection("extracciones_ocr")

async def check_db_connection():
    """
    Función para probar la conexión a la base de datos al iniciar el servidor.
    """
    try:
        # Hacemos un 'ping' rápido a la base de datos
        await client.admin.command('ping')
        print("✅ ¡Conexión exitosa a MongoDB asíncrono!")
    except Exception as e:
        print(f"❌ Error crítico conectando a MongoDB: {e}")
