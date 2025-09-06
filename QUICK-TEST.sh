#!/bin/bash
# QUICK-TEST.sh
# Test rápido del estado actual

echo "🧪 TEST RÁPIDO POST-CORRECCIÓN"
echo "============================"

cd /srv/servicios/entersys-apis/content-management

echo "• Esperando 15 segundos adicionales..."
sleep 15

echo "• Estado del contenedor:"
docker-compose ps

echo ""
echo "• Test de conectividad PostgreSQL desde la API:"
docker exec entersys-content-api python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_SERVER'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        database=os.getenv('POSTGRES_DB'),
        port=os.getenv('POSTGRES_PORT')
    )
    cursor = conn.cursor()
    cursor.execute('SELECT 1;')
    print('✅ PostgreSQL conecta desde la API')
    cursor.close()
    conn.close()
except Exception as e:
    print('❌ Error PostgreSQL:', str(e))
"

echo ""
echo "• Test del health endpoint:"
docker exec entersys-content-api python -c "
import urllib.request
import json
try:
    response = urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=15)
    data = response.read().decode('utf-8')
    print('✅ Health endpoint OK:', data)
except urllib.error.HTTPError as e:
    error_data = e.read().decode('utf-8') if hasattr(e, 'read') else 'No error details'
    print(f'❌ HTTP Error {e.code}:', error_data)
except Exception as e:
    print('❌ Error:', str(e))
"

echo ""
echo "• Test del endpoint raíz:"
docker exec entersys-content-api python -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8000/', timeout=10)
    data = response.read().decode('utf-8')
    print('✅ Root endpoint OK:', data[:100] + '...' if len(data) > 100 else data)
except Exception as e:
    print('❌ Root endpoint error:', str(e))
"

echo ""
echo "• Test externo HTTPS:"
sleep 5
if curl -f -s https://api.dev.entersys.mx/api/v1/health >/dev/null 2>&1; then
    echo "🎉 HTTPS funciona!"
    curl -s https://api.dev.entersys.mx/api/v1/health
else
    echo "⚠️ HTTPS aún no funciona, probando acceso directo:"
    curl -f -s http://34.134.14.202:8000/api/v1/health || echo "Acceso directo también falla"
fi