# Dockerfile (VERSIÓN FINAL Y ROBUSTA)

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Añadimos /app al PYTHONPATH. Esto es crucial.
ENV PYTHONPATH /app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el proyecto.
COPY . .

# Damos permisos de ejecución al script de arranque.
RUN chmod +x ./entrypoint.sh

# El ENTRYPOINT ejecuta nuestro script de arranque.
ENTRYPOINT ["./entrypoint.sh"]
