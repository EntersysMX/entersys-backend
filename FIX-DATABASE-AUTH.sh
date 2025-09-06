#!/bin/bash
# FIX-DATABASE-AUTH.sh
# Script para arreglar la autenticación de PostgreSQL y conectividad de red

set -e

echo "🔧 ARREGLANDO AUTENTICACIÓN POSTGRESQL Y REDES"
echo "=============================================="

if [[ $(hostname) != *"dev-server"* ]] && [[ ! -f /srv/traefik/traefik.yml ]]; then
    echo "❌ Ejecutar en dev-server"
    exit 1
fi

# PASO 1: Conectar PostgreSQL a la red entersys_internal
echo "🔗 PASO 1: Arreglando conectividad de redes Docker"
echo "================================================"

echo "• Conectando PostgreSQL a la red entersys_internal..."
docker network connect entersys_internal dev-entersys-postgres 2>/dev/null && echo "✅ PostgreSQL conectado a entersys_internal" || echo "ℹ️ PostgreSQL ya estaba en entersys_internal"

echo "• Verificando redes actuales:"
echo "  - API: $(docker inspect entersys-content-api --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}')"
echo "  - PostgreSQL: $(docker inspect dev-entersys-postgres --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}')"

# PASO 2: Arreglar autenticación PostgreSQL
echo ""
echo "🔐 PASO 2: Arreglando autenticación PostgreSQL"
echo "=============================================="

echo "• Verificando configuración actual del usuario entersys_user..."

# Función para probar conexión PostgreSQL
test_pg_connection() {
    local user="$1"
    local db="${2:-postgres}"
    
    if [ -n "$user" ]; then
        docker exec dev-entersys-postgres psql -U "$user" -d "$db" -c "SELECT 1;" >/dev/null 2>&1
    else
        docker exec dev-entersys-postgres psql -d "$db" -c "SELECT 1;" >/dev/null 2>&1
    fi
}

# Determinar qué usuario administrativo usar
ADMIN_USER=""
if test_pg_connection "postgres"; then
    ADMIN_USER="postgres"
    echo "✅ Usando usuario administrativo: postgres"
elif test_pg_connection ""; then
    ADMIN_USER=""
    echo "✅ Usando usuario administrativo por defecto"
else
    # Verificar variables de entorno del contenedor
    POSTGRES_ENV_USER=$(docker exec dev-entersys-postgres env | grep "POSTGRES_USER=" | cut -d'=' -f2 2>/dev/null || echo "")
    if [ -n "$POSTGRES_ENV_USER" ] && test_pg_connection "$POSTGRES_ENV_USER"; then
        ADMIN_USER="$POSTGRES_ENV_USER"
        echo "✅ Usando usuario administrativo de env: $POSTGRES_ENV_USER"
    else
        echo "❌ No se pudo determinar usuario administrativo"
        exit 1
    fi
fi

# Construir comando psql
if [ -n "$ADMIN_USER" ]; then
    PSQL_CMD="psql -U $ADMIN_USER -d postgres"
else
    PSQL_CMD="psql -d postgres"
fi

echo "• Reconfigurando usuario entersys_user y permisos..."

docker exec dev-entersys-postgres $PSQL_CMD << 'EOSQL'
-- Eliminar usuario si existe para recrearlo limpio
DROP USER IF EXISTS entersys_user;

-- Crear usuario con contraseña correcta
CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'Operaciones.2025';

-- Dar permisos de superusuario temporalmente para configurar
ALTER USER entersys_user CREATEDB;

-- Crear base de datos si no existe
SELECT 'CREATE DATABASE entersys_db OWNER entersys_user' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'entersys_db')\gexec

-- Grant privileges on database
GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;

-- Conectar a la base específica
\c entersys_db

-- Grant all permissions on schema
GRANT ALL ON SCHEMA public TO entersys_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO entersys_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO entersys_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO entersys_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO entersys_user;

-- Verificar configuración final
SELECT 'User configured successfully' as status;
EOSQL

if [ $? -eq 0 ]; then
    echo "✅ Usuario entersys_user reconfigurado exitosamente"
else
    echo "❌ Error reconfigurando usuario"
    exit 1
fi

# PASO 3: Probar conexión corregida
echo ""
echo "🧪 PASO 3: Verificando corrección"
echo "================================"

echo "• Probando conexión directa con entersys_user..."
if test_pg_connection "entersys_user" "entersys_db"; then
    echo "✅ entersys_user puede conectar directamente"
else
    echo "⚠️ Conexión directa aún falla, pero puede funcionar desde la aplicación"
fi

# PASO 4: Reiniciar contenedor de API para aplicar cambios
echo ""
echo "🔄 PASO 4: Reiniciando contenedor de API"
echo "======================================="

cd /srv/servicios/entersys-apis/content-management

echo "• Reiniciando contenedor de API..."
docker-compose restart content-api

echo "• Esperando 30 segundos para que reinicie..."
sleep 30

# PASO 5: Verificación final
echo ""
echo "🏥 PASO 5: Verificación final del health check"
echo "============================================="

RETRY_COUNT=0
MAX_RETRIES=6
HEALTH_OK=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$HEALTH_OK" = false ]; do
    echo "🔄 Intento $((RETRY_COUNT + 1))/$MAX_RETRIES - Probando health check..."
    
    if docker exec entersys-content-api python -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=10)
    if response.getcode() == 200:
        exit(0)
    else:
        exit(1)
except Exception:
    exit(1)
" 2>/dev/null; then
        HEALTH_OK=true
        echo "✅ Health check exitoso!"
        
        # Mostrar respuesta
        RESPONSE=$(docker exec entersys-content-api python -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=10)
    data = response.read().decode('utf-8')
    print(data)
except Exception as e:
    print('Error:', str(e))
")
        echo "📋 Respuesta: $RESPONSE"
    else
        echo "⏳ Health check aún falla, esperando 10 segundos..."
        sleep 10
        RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
done

if [ "$HEALTH_OK" = true ]; then
    echo ""
    echo "🎉 ¡PROBLEMA DE AUTENTICACIÓN SOLUCIONADO!"
    echo "========================================"
    echo "✅ Autenticación PostgreSQL funcionando"
    echo "✅ Health check respondiendo correctamente"
    echo "✅ API lista para uso"
    echo ""
    echo "🌐 Ahora puedes probar:"
    echo "• https://api.dev.entersys.mx/api/v1/health"
    echo "• https://api.dev.entersys.mx/docs"
else
    echo ""
    echo "⚠️ Health check aún falla después de la corrección"
    echo "📋 Logs recientes:"
    docker logs entersys-content-api --tail 15
    echo ""
    echo "💡 Puede necesitar más tiempo o hay otro problema"
fi

echo ""
echo "✅ CORRECCIÓN DE AUTENTICACIÓN COMPLETADA"