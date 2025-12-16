#!/bin/sh
# entrypoint.sh (VERSIÓN FINAL Y ROBUSTA)

set -ex

DB_HOST=${POSTGRES_SERVER:-db}
DB_PORT=${POSTGRES_PORT:-5432}

echo "Paso 1: Esperando a que el servicio de red de la base de datos esté disponible..."

if ! command -v nc > /dev/null; then
    apt-get update > /dev/null && apt-get install -y netcat-openbsd > /dev/null
fi

while ! nc -z $DB_HOST $DB_PORT; do
  echo "Base de datos en $DB_HOST:$DB_PORT no está disponible. Reintentando en 2 segundos..."
  sleep 2
done

echo "✅ Paso 2: El puerto de la base de datos está abierto. Verificando conexión completa..."

# Ejecutamos el prestart como un módulo (-m)
python -m app.scripts.prestart

echo "✅ Paso 3: La conexión a la base de datos fue exitosa."
echo "Iniciando la aplicación Gunicorn..."

# Ejecutamos Gunicorn como un módulo (-m) y llamamos a la app como un módulo
# --timeout 120: Aumentado para operaciones largas como generacion de PDF/certificados
exec gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 120 app.main:app
