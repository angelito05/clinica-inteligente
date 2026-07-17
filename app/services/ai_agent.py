import os
import json
import tempfile
from groq import AsyncGroq
from app.core.config import settings

# Iniciamos el cliente de Groq
client = AsyncGroq(api_key=settings.GROQ_API_KEY)

async def procesar_audio_receta(audio_bytes: bytes) -> dict:
    """
    Pipeline Open-Source:
    1. Whisper-large-v3 convierte el Audio a Texto.
    2. Llama-3 convierte el Texto al JSON estandarizado.
    """
    
    # Whisper necesita un archivo físico, así que lo guardamos temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    try:
        print("🎙️ 1. Enviando a Whisper para transcripción...")
        with open(temp_audio_path, "rb") as file:
            transcripcion = await client.audio.transcriptions.create(
                file=("dictado.webm", file.read()),
                model="whisper-large-v3", # Modelo Open Source de transcripción
                response_format="text",
                language="es" # Forzamos el español
            )
        
        texto_dictado = transcripcion
        print(f"📝 Texto detectado: {texto_dictado}")

        print("🧠 2. Enviando a Llama 3 para estructurar el JSON...")
        prompt = f"""
        Eres un asistente médico experto. Extrae la información médica del siguiente texto y devuélvela EXACTAMENTE como un JSON válido.
        No agregues texto fuera del JSON. Si un dato no se menciona en el texto, pon "No especificado".

        TEXTO DEL DOCTOR: "{texto_dictado}"

        ESTRUCTURA JSON REQUERIDA:
        {{
            "paciente_nombre": "Nombre del paciente",
            "edad": "Edad",
            "peso": "Peso en kg",
            "talla": "Estatura",
            "temperatura": "Temperatura",
            "presion_arterial": "Presión",
            "diagnostico": "Diagnóstico principal",
            "medicamentos": [
                {{
                    "nombre": "Nombre del medicamento",
                    "dosis": "Dosis",
                    "frecuencia": "Frecuencia",
                    "duracion": "Duración del tratamiento"
                }}
            ],
            "indicaciones_adicionales": "Cualquier otra indicación"
        }}
        """

        # Llama 3 es rapidísimo para procesar texto
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a machine that only outputs valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant", # Modelo Open Source de Meta
            temperature=0, # 0 = Respuestas estrictas y directas
            response_format={"type": "json_object"} # Forzamos que la salida sea JSON real
        )

        # Borramos el archivo temporal
        os.remove(temp_audio_path)

        # Retornamos el JSON parseado a Python
        return json.loads(chat_completion.choices[0].message.content)

    except Exception as e:
        print(f"🔥 ERROR EN GROQ: {str(e)}")
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        raise e

import pdfplumber
import pytesseract
from PIL import Image
import httpx
import os

# Configurar la ruta de Tesseract en Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

async def analizar_estudio_ia(file_url: str) -> str:
    """
    Descarga un archivo PDF o Imagen de Cloudinary (o disco local), extrae su texto (OCR) y lo analiza con Groq.
    """
    print(f"🧠 Extrayendo texto para análisis con Groq: {file_url}")
    ext = os.path.splitext(file_url)[1].lower()
    # Limpiar parámetros de URL en la extensión si los hay (e.g. .jpg?v=123)
    ext = ext.split('?')[0]
    
    texto_extraido = ""

    # Set TESSDATA_PREFIX environment variable to point to the local tessdata dir
    tessdata_dir = os.path.join(os.getcwd(), 'tessdata')
    os.environ['TESSDATA_PREFIX'] = tessdata_dir

    # Obtener el contenido del archivo (nube o local)
    file_bytes = None
    if file_url.startswith("http"):
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(file_url)
            response.raise_for_status()
            file_bytes = response.content
    else:
        # Es un archivo local viejo
        local_path = os.path.join(os.getcwd(), file_url.lstrip("/"))
        with open(local_path, "rb") as f:
            file_bytes = f.read()

    import io
    file_stream = io.BytesIO(file_bytes)

    if ext == ".pdf":
        try:
            with pdfplumber.open(file_stream) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        texto_extraido += text + "\n"
                    else:
                        # Si no hay texto, intentar OCR en la imagen renderizada
                        img = page.to_image(resolution=150).original
                        texto_extraido += pytesseract.image_to_string(img, lang='spa') + "\n"
        except Exception as e:
            raise ValueError(f"Error procesando el PDF: {str(e)}")
            
    elif ext in [".jpg", ".jpeg", ".png"]:
        try:
            img = Image.open(file_stream)
            texto_extraido = pytesseract.image_to_string(img, lang='spa')
        except Exception as e:
            raise ValueError(f"Error procesando la imagen con OCR: {str(e)}")
    else:
        raise ValueError("Formato no soportado para análisis.")

    if not texto_extraido.strip():
        raise ValueError("No se pudo extraer texto legible del documento o imagen.")

    prompt = f"""
    Eres un asistente médico experto. Analiza el siguiente TEXTO extraído de un documento de laboratorio o reporte médico mediante OCR.
    
    TEXTO DEL DOCUMENTO:
    \"\"\"
    {texto_extraido}
    \"\"\"
    
    Tus tareas:
    1. Identifica qué tipo de estudio es.
    2. Extrae los resultados más relevantes.
    3. Si es un examen de sangre/orina, resalta claramente cualquier valor que esté fuera de los rangos de referencia normales.
    4. Proporciona un breve resumen en español con lenguaje profesional pero claro, advirtiendo que esto es un análisis asistido por IA y el diagnóstico final es del médico.
    Devuelve la respuesta en formato Markdown limpio, sin bloques de código ```markdown.
    """
    
    print("🧠 Enviando texto a llama-3.1-8b-instant en Groq...")
    
    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.2, 
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"🔥 ERROR EN GROQ TEXT: {str(e)}")
        raise ValueError(f"Error en el análisis de IA: {str(e)}")