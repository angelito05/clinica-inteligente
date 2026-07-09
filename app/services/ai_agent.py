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