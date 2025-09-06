#!/bin/bash
# SIMPLE-FIX.sh
# Solución simple usando las credenciales que sabemos que funcionan

echo "🔧 SOLUCIÓN SIMPLE - USANDO CREDENCIALES EXISTENTES"
echo "=================================================="

cd /srv/servicios/entersys-apis/content-management

echo "• Actualizando .env con configuración correcta..."
cat > .env << 'EOF'
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=Operaciones.2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
EOF

echo "✅ .env actualizado:"
cat .env

echo ""
echo "• Reiniciando contenedor de API..."
docker-compose restart content-api

echo "• Esperando 30 segundos para reinicio completo..."
sleep 30

echo ""
echo "• Test de conexión PostgreSQL desde la API:"
docker exec entersys-content-api python -c "
import os
import psycopg2
try:
    # Usar exactamente las mismas credenciales del .env
    conn = psycopg2.connect(
        host='dev-entersys-postgres',
        user='entersys_user', 
        password='Operaciones.2025',
        database='entersys_db',
        port='5432',
        connect_timeout=10
    )
    cursor = conn.cursor()
    cursor.execute('SELECT 1 as test;')
    result = cursor.fetchone()
    print('✅ Conexión PostgreSQL exitosa:', result)
    cursor.close()
    conn.close()
except Exception as e:
    print('❌ Error de conexión:', str(e))
    
    # Si falla con entersys_db, probar con main_db
    print('• Probando con main_db como fallback...')
    try:
        conn = psycopg2.connect(
            host='dev-entersys-postgres',
            user='entersys_user',
            password='Operaciones.2025', 
            database='main_db',
            port='5432',
            connect_timeout=10
        )
        cursor = conn.cursor()
        cursor.execute('SELECT 1 as test;')
        result = cursor.fetchone()
        print('✅ Conexión con main_db exitosa:', result)
        cursor.close()
        conn.close()
        print('💡 Sugerencia: Cambiar .env para usar main_db en lugar de entersys_db')
    except Exception as e2:
        print('❌ Error también con main_db:', str(e2))
"

echo ""
echo "• Test del health endpoint:"
docker exec entersys-content-api python -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=15)
    data = response.read().decode('utf-8')
    print('🎉 Health endpoint funciona:', data)
except urllib.error.HTTPError as e:
    error_data = e.read().decode('utf-8')
    print(f'❌ Health endpoint error {e.code}:', error_data)
except Exception as e:
    print('❌ Health endpoint error:', str(e))
"

echo ""
echo "• Si el health check funciona, probando acceso externo:"
sleep 5

if docker exec entersys-content-api python -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=10)
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
    echo "✅ API funciona internamente, probando HTTPS externo:"
    
    if curl -f -s https://api.dev.entersys.mx/api/v1/health >/dev/null 2>&1; then
        echo "🎉 ¡HTTPS FUNCIONA!"
        curl -s https://api.dev.entersys.mx/api/v1/health
    else
        echo "⚠️ HTTPS no funciona, probando acceso directo:"
        curl -f -s http://34.134.14.202:8000/api/v1/health 2>/dev/null || echo "Acceso directo tampoco funciona"
    fi
else
    echo "❌ API no funciona internamente aún"
fi

echo ""
echo "✅ SOLUCIÓN SIMPLE COMPLETADA"