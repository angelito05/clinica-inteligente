# Usa una imagen oficial y ligera de Python
FROM python:3.10-slim

# Evita que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE 1
# Evita que Python guarde en buffer la salida estándar (para ver logs en tiempo real)
ENV PYTHONUNBUFFERED 1

# Instala dependencias del sistema operativo (Tesseract OCR y librerías necesarias para pdfplumber)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    libgl1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Configura el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia primero el archivo de requerimientos para aprovechar la caché de Docker
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código del backend al contenedor
COPY . .

# Expone el puerto 8000
EXPOSE 8000

# Comando para iniciar la aplicación (Uvicorn)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
