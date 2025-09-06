#!/bin/bash
# DEBUG-DATABASE.sh
# Script para diagnosticar problemas de conexión de base de datos

set -e

echo "🔍 DIAGNÓSTICO DE BASE DE DATOS"
echo "=============================="

if [[ $(hostname) != *"dev-server"* ]] && [[ ! -f /srv/traefik/traefik.yml ]]; then
    echo "❌ Ejecutar en dev-server"
    exit 1
fi

cd /srv/servicios/entersys-apis/content-management

echo "📋 Variables de entorno en el contenedor:"
docker exec entersys-content-api env | grep -E "(POSTGRES|DATABASE)" || echo "No se encontraron variables POSTGRES"

echo ""
echo "🗄️ Estado del contenedor PostgreSQL:"
docker ps | grep postgres || echo "❌ No hay contenedores PostgreSQL corriendo"

echo ""
echo "🔌 Conectividad desde el contenedor de la API a PostgreSQL:"

# Verificar si puede resolver el hostname
echo "• Resolviendo hostname 'dev-entersys-postgres':"
docker exec entersys-content-api nslookup dev-entersys-postgres 2>/dev/null || echo "❌ No puede resolver hostname"

# Verificar conectividad de red al puerto
echo "• Probando conectividad al puerto 5432:"
docker exec entersys-content-api timeout 5 bash -c "</dev/tcp/dev-entersys-postgres/5432 && echo '✅ Puerto 5432 accesible'" || echo "❌ Puerto 5432 no accesible"

echo ""
echo "🔧 Probando conexión directa con Python:"
docker exec entersys-content-api python -c "
import os
import sys
try:
    import psycopg2
    
    # Obtener variables de entorno
    host = os.getenv('POSTGRES_SERVER', 'localhost')
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', '')
    database = os.getenv('POSTGRES_DB', 'postgres')
    port = os.getenv('POSTGRES_PORT', '5432')
    
    print(f'Intentando conectar a: {user}@{host}:{port}/{database}')
    
    # Intentar conexión
    conn = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        connect_timeout=10
    )
    
    cursor = conn.cursor()
    cursor.execute('SELECT 1;')
    result = cursor.fetchone()
    
    print('✅ Conexión PostgreSQL exitosa!')
    print(f'Resultado de SELECT 1: {result}')
    
    cursor.close()
    conn.close()
    
except ImportError as e:
    print('❌ psycopg2 no está instalado:', str(e))
except Exception as e:
    print('❌ Error de conexión PostgreSQL:', str(e))
"

echo ""
echo "🏥 Probando endpoint de health específicamente:"
docker exec entersys-content-api python -c "
import urllib.request
import json
try:
    response = urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=10)
    data = response.read().decode('utf-8')
    print('✅ Health endpoint responde:')
    print(data)
except urllib.error.HTTPError as e:
    print(f'❌ Health endpoint falló con código {e.code}:')
    error_data = e.read().decode('utf-8')
    print(error_data)
except Exception as e:
    print('❌ Error accediendo health endpoint:', str(e))
"

echo ""
echo "📊 Resumen de diagnóstico:"
echo "========================"

# Verificar si el problema es la red Docker
echo "• Redes Docker del contenedor de API:"
docker inspect entersys-content-api --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' || echo "Error inspeccionando redes"

echo "• Redes Docker del contenedor PostgreSQL:"
docker inspect dev-entersys-postgres --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || echo "Error inspeccionando redes PostgreSQL"

echo ""
echo "💡 Si la API no puede conectar a PostgreSQL:"
echo "1. Verificar que ambos contenedores estén en la misma red Docker"
echo "2. Verificar variables de entorno en .env"
echo "3. Verificar que el usuario 'entersys_user' tenga permisos"
echo "4. Considerar reiniciar ambos contenedores"