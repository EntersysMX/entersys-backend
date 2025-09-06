#!/bin/bash
# FORCE-ENV-RELOAD.sh
# Forzar recarga completa de variables de entorno

echo "🔄 FORZANDO RECARGA DE VARIABLES DE ENTORNO"
echo "=========================================="

cd /srv/servicios/entersys-apis/content-management

echo "• Verificando .env actual:"
cat .env

echo ""
echo "• Creando .env con contraseña correcta:"
cat > .env << 'EOF'
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=Operaciones.2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
EOF

echo "• .env actualizado:"
cat .env

echo ""
echo "• Parando contenedor completamente:"
docker-compose down

echo "• Esperando 5 segundos..."
sleep 5

echo "• Iniciando contenedor con variables nuevas:"
docker-compose up -d

echo "• Esperando 45 segundos para inicio completo..."
sleep 45

echo ""
echo "• Verificando variables de entorno cargadas:"
docker exec entersys-content-api env | grep -E "(POSTGRES|DATABASE)" || echo "❌ Sin variables PostgreSQL"

echo ""
echo "• Test de conexión con nuevas variables:"
docker exec entersys-content-api python -c "
import os
print('Variables leídas por Python:')
print('POSTGRES_USER:', os.getenv('POSTGRES_USER', 'NO_SET'))
print('POSTGRES_PASSWORD:', os.getenv('POSTGRES_PASSWORD', 'NO_SET')[:5] + '...')
print('POSTGRES_SERVER:', os.getenv('POSTGRES_SERVER', 'NO_SET'))
print('POSTGRES_DB:', os.getenv('POSTGRES_DB', 'NO_SET'))

print('\\nProbando conexión con variables de entorno:')
try:
    import psycopg2
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_SERVER'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        database=os.getenv('POSTGRES_DB'),
        port=os.getenv('POSTGRES_PORT', '5432')
    )
    cursor = conn.cursor()
    cursor.execute('SELECT 1;')
    result = cursor.fetchone()
    print('✅ Conexión con variables ENV exitosa:', result)
    cursor.close()
    conn.close()
except Exception as e:
    print('❌ Error con variables ENV:', str(e))
"

echo ""
echo "• Test del health endpoint después de recarga:"
sleep 10

HEALTH_RETRY=0
MAX_HEALTH_RETRIES=5

while [ $HEALTH_RETRY -lt $MAX_HEALTH_RETRIES ]; do
    echo "🔄 Intento health check $((HEALTH_RETRY + 1))/$MAX_HEALTH_RETRIES"
    
    HEALTH_RESULT=$(docker exec entersys-content-api python -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=10)
    data = response.read().decode('utf-8')
    print('SUCCESS:' + data)
except urllib.error.HTTPError as e:
    error_data = e.read().decode('utf-8')
    print('HTTP_ERROR:' + str(e.code) + ':' + error_data)
except Exception as e:
    print('ERROR:' + str(e))
" 2>/dev/null)

    if echo "$HEALTH_RESULT" | grep -q "SUCCESS:"; then
        echo "🎉 ¡HEALTH CHECK EXITOSO!"
        echo "$HEALTH_RESULT" | sed 's/SUCCESS:/📋 Respuesta: /'
        break
    else
        echo "❌ Health check falló: $HEALTH_RESULT"
        if [ $HEALTH_RETRY -lt $((MAX_HEALTH_RETRIES - 1)) ]; then
            echo "⏳ Esperando 15 segundos antes del siguiente intento..."
            sleep 15
        fi
    fi
    
    HEALTH_RETRY=$((HEALTH_RETRY + 1))
done

if [ $HEALTH_RETRY -eq $MAX_HEALTH_RETRIES ]; then
    echo ""
    echo "⚠️ Health check aún falla después de recargar variables"
    echo "📋 Logs recientes:"
    docker logs entersys-content-api --tail 15
else
    echo ""
    echo "🌐 Probando acceso externo:"
    if curl -f -s https://api.dev.entersys.mx/api/v1/health >/dev/null 2>&1; then
        echo "🎉 ¡ACCESO HTTPS FUNCIONA!"
        curl -s https://api.dev.entersys.mx/api/v1/health
    else
        echo "⚠️ HTTPS no funciona, probando acceso directo:"
        curl -f -s http://34.134.14.202:8000/api/v1/health 2>/dev/null || echo "Acceso directo tampoco funciona"
    fi
fi

echo ""
echo "✅ RECARGA DE VARIABLES COMPLETADA"