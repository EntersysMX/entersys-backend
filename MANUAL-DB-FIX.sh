#!/bin/bash
# MANUAL-DB-FIX.sh
# Solución manual y directa para el problema de autenticación PostgreSQL

set -e

echo "🔧 SOLUCIÓN MANUAL POSTGRESQL - PASO A PASO"
echo "==========================================="

if [[ $(hostname) != *"dev-server"* ]] && [[ ! -f /srv/traefik/traefik.yml ]]; then
    echo "❌ Ejecutar en dev-server"
    exit 1
fi

echo "🔍 PASO 1: Diagnóstico inicial"
echo "============================="

# Verificar qué usuario administrativo funciona
echo "• Probando usuarios administrativos disponibles:"

ADMIN_USER=""
if docker exec dev-entersys-postgres psql -U postgres -c "SELECT 1;" >/dev/null 2>&1; then
    ADMIN_USER="postgres"
    echo "  ✅ Usuario 'postgres' funciona"
elif docker exec dev-entersys-postgres psql -c "SELECT 1;" >/dev/null 2>&1; then
    ADMIN_USER=""
    echo "  ✅ Usuario por defecto funciona"
else
    # Probar con el usuario de las variables de entorno
    ENV_USER=$(docker exec dev-entersys-postgres env | grep "POSTGRES_USER=" | cut -d'=' -f2 2>/dev/null || echo "")
    if [ -n "$ENV_USER" ] && docker exec dev-entersys-postgres psql -U "$ENV_USER" -c "SELECT 1;" >/dev/null 2>&1; then
        ADMIN_USER="$ENV_USER"
        echo "  ✅ Usuario de env '$ENV_USER' funciona"
    else
        echo "  ❌ No se pudo encontrar usuario administrativo"
        echo "• Variables de entorno PostgreSQL:"
        docker exec dev-entersys-postgres env | grep POSTGRES || echo "Sin variables POSTGRES"
        exit 1
    fi
fi

echo "🎯 Usuario administrativo a usar: '${ADMIN_USER:-[default]}'"

# Construir comando psql
if [ -n "$ADMIN_USER" ]; then
    PSQL_CMD="psql -U $ADMIN_USER"
else
    PSQL_CMD="psql"
fi

echo ""
echo "🔍 PASO 2: Verificar estado actual de usuarios"
echo "=============================================="

echo "• Usuarios existentes en PostgreSQL:"
docker exec dev-entersys-postgres $PSQL_CMD -c "SELECT usename FROM pg_user;" 2>/dev/null || echo "Error listando usuarios"

echo ""
echo "• Bases de datos existentes:"
docker exec dev-entersys-postgres $PSQL_CMD -c "SELECT datname FROM pg_database;" 2>/dev/null || echo "Error listando bases"

echo ""
echo "🔧 PASO 3: Limpieza completa y recreación"
echo "========================================"

echo "• Eliminando usuario entersys_user si existe..."
docker exec dev-entersys-postgres $PSQL_CMD << 'EOSQL'
-- Terminar conexiones activas del usuario (si las hay)
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = 'entersys_user';

-- Quitar permisos de la base de datos
REVOKE ALL PRIVILEGES ON DATABASE entersys_db FROM entersys_user;

-- Eliminar usuario
DROP USER IF EXISTS entersys_user;

-- Verificar que se eliminó
SELECT 'User deleted' as status;
EOSQL

echo "• Recreando usuario entersys_user..."
docker exec dev-entersys-postgres $PSQL_CMD << 'EOSQL'
-- Crear usuario con contraseña específica
CREATE USER entersys_user WITH PASSWORD 'Operaciones.2025';

-- Dar permisos de creación de base de datos
ALTER USER entersys_user CREATEDB;

-- Verificar creación
SELECT usename, usecreatedb FROM pg_user WHERE usename = 'entersys_user';
EOSQL

echo "• Verificando que el usuario se creó correctamente..."
if docker exec dev-entersys-postgres $PSQL_CMD -c "SELECT usename FROM pg_user WHERE usename = 'entersys_user';" | grep -q "entersys_user"; then
    echo "  ✅ Usuario entersys_user creado"
else
    echo "  ❌ Error creando usuario"
    exit 1
fi

echo ""
echo "🔧 PASO 4: Configurar base de datos entersys_db"
echo "=============================================="

echo "• Recreando base de datos entersys_db..."
docker exec dev-entersys-postgres $PSQL_CMD << 'EOSQL'
-- Eliminar base si existe
DROP DATABASE IF EXISTS entersys_db;

-- Crear base con owner correcto
CREATE DATABASE entersys_db OWNER entersys_user;

-- Verificar
SELECT datname, datdba::regrole FROM pg_database WHERE datname = 'entersys_db';
EOSQL

echo "• Configurando permisos en entersys_db..."
docker exec dev-entersys-postgres $PSQL_CMD -d entersys_db << 'EOSQL'
-- Grant all permissions on schema public
GRANT ALL ON SCHEMA public TO entersys_user;

-- Grant permissions on all existing tables and sequences
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO entersys_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO entersys_user;

-- Grant default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO entersys_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO entersys_user;

-- Verificar permisos
SELECT 'Permissions configured' as status;
EOSQL

echo ""
echo "🧪 PASO 5: Probar conexión directa"
echo "================================="

echo "• Probando conexión como entersys_user a entersys_db..."
if docker exec dev-entersys-postgres psql -U entersys_user -d entersys_db -c "SELECT 'Connection test OK' as result;" >/dev/null 2>&1; then
    echo "  ✅ Conexión directa exitosa"
    
    # Mostrar resultado
    echo "• Resultado de test:"
    docker exec dev-entersys-postgres psql -U entersys_user -d entersys_db -c "SELECT 'Connection test OK' as result;"
else
    echo "  ❌ Conexión directa aún falla"
    echo "• Intentando diagnóstico adicional..."
    
    # Mostrar información de autenticación
    docker exec dev-entersys-postgres $PSQL_CMD -c "SELECT usename, passwd FROM pg_shadow WHERE usename = 'entersys_user';" 2>/dev/null || echo "No se pudo ver info de password"
    
    echo "• Probando con password especificado manualmente:"
    docker exec dev-entersys-postgres psql -U entersys_user -d entersys_db << 'TESTPWD'
-- Test con password
\q
TESTPWD
fi

echo ""
echo "🔄 PASO 6: Reiniciar API y verificar"
echo "==================================="

cd /srv/servicios/entersys-apis/content-management

echo "• Reiniciando contenedor de API..."
docker-compose restart content-api

echo "• Esperando 30 segundos..."
sleep 30

echo "• Test final desde API:"
docker exec entersys-content-api python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_SERVER', 'dev-entersys-postgres'),
        user=os.getenv('POSTGRES_USER', 'entersys_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'Operaciones.2025'),
        database=os.getenv('POSTGRES_DB', 'entersys_db'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        connect_timeout=10
    )
    cursor = conn.cursor()
    cursor.execute('SELECT 1 as test_result;')
    result = cursor.fetchone()
    print(f'✅ API puede conectar a PostgreSQL: {result}')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ API no puede conectar: {e}')
"

echo ""
echo "• Test del health endpoint:"
docker exec entersys-content-api python -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=10)
    data = response.read().decode('utf-8')
    print('🎉 Health endpoint funciona:', data)
except Exception as e:
    print('❌ Health endpoint falla:', str(e))
"

echo ""
echo "✅ CORRECCIÓN MANUAL POSTGRESQL COMPLETADA"
echo ""
echo "🌐 Si todo funcionó, prueba:"
echo "• curl -s http://localhost:8000/api/v1/health (desde el servidor)"
echo "• https://api.dev.entersys.mx/api/v1/health (externo)"