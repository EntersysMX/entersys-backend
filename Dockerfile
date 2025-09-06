# Dockerfile
# Etapa 1: Imagen base de Python, optimizada y segura.
FROM python:3.11-slim

# Establecer variables de entorno para buenas prácticas en producción.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalar curl para health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Crear y establecer el directorio de trabajo.
WORKDIR /app

# Copiar el archivo de dependencias primero para aprovechar el cache de Docker.
COPY requirements.txt .

# Instalar las dependencias de Python.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar todo el código de la aplicación (la carpeta 'app').
COPY ./app /app/app

# Comando para ejecutar la aplicación en producción.
# Gunicorn gestiona los workers de Uvicorn para un rendimiento robusto.
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "app.main:app"]