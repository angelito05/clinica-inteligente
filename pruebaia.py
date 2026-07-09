import google.generativeai as genai

# Pon tu llave real aquí
MI_LLAVE = "AQ.Ab8RN6If2TBJG_byOHml_PBUURzkdci-l48wnDvqa_YhCbk9wA"

genai.configure(api_key=MI_LLAVE)

print("🔍 Buscando modelos disponibles...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Modelo compatible encontrado: {m.name}")
except Exception as e:
    print(f"❌ Error al conectar: {e}")