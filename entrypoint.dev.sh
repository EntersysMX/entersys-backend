#!/bin/sh
# entrypoint.dev.sh - Development version with hot-reload

set -ex

DB_HOST=${POSTGRES_SERVER:-database}
DB_PORT=${POSTGRES_PORT:-5432}

echo "🔧 [DEV MODE] Paso 1: Esperando a que PostgreSQL esté disponible..."

# Wait for database to be ready
while ! nc -z $DB_HOST $DB_PORT; do
  echo "Base de datos en $DB_HOST:$DB_PORT no está disponible. Reintentando en 2 segundos..."
  sleep 2
done

echo "✅ Paso 2: PostgreSQL está disponible. Verificando conexión completa..."

# Run prestart script (migrations, etc.)
python -m app.scripts.prestart

echo "✅ Paso 3: La conexión a la base de datos fue exitosa."
echo "🚀 [DEV MODE] Iniciando servidor con hot-reload..."

# Start uvicorn with hot-reload for development
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
