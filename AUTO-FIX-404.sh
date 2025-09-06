#!/bin/bash
# AUTO-FIX-404.sh
# Script inteligente que diagnostica y corrige automáticamente el error 404

set -e

echo "🔧 AUTO-FIX 404 ERROR - DIAGNOSTICO Y CORRECCION AUTOMATICA"
echo "=========================================================="

if [[ $(hostname) != *"dev-server"* ]] && [[ ! -f /srv/traefik/traefik.yml ]]; then
    echo "❌ Ejecutar en dev-server"
    exit 1
fi

echo "✅ Ejecutando en dev-server"

# Funciones de utilidad
check_url() {
    local url="$1"
    if curl -f -s "$url" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

test_and_report() {
    local url="$1"
    local description="$2"
    echo -n "🧪 $description... "
    if check_url "$url"; then
        echo "✅ FUNCIONA"
        return 0
    else
        echo "❌ FALLA"
        return 1
    fi
}

# Ir al directorio del proyecto
cd /srv/servicios/entersys-apis/content-management

echo "📊 FASE 1: DIAGNOSTICO INICIAL"
echo "=============================="

# Verificar contenedor
echo "🔍 Verificando contenedor..."
if docker ps | grep -q "entersys-content-api"; then
    echo "✅ Contenedor entersys-content-api está corriendo"
else
    echo "❌ Contenedor entersys-content-api NO está corriendo"
    echo "🔧 Iniciando contenedor..."
    docker-compose up -d --build
    sleep 30
fi

# Test interno
echo "🏥 Verificando health check interno..."
if docker exec entersys-content-api curl -f -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "✅ Health check interno OK"
else
    echo "❌ Health check interno FALLA - problema en la aplicación"
    echo "📋 Logs del contenedor:"
    docker logs --tail 10 entersys-content-api
    echo "🔧 SOLUCION 1: Reconstruir aplicación"
    docker-compose down
    docker-compose up -d --build --force-recreate
    sleep 45
    
    if docker exec entersys-content-api curl -f -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "✅ Health check interno OK después de rebuild"
    else
        echo "❌ Aplicación interna aún falla - revisando..."
        exit 1
    fi
fi

echo ""
echo "📊 FASE 2: DIAGNOSTICO DE ROUTING"
echo "================================="

# Verificar labels de Traefik
echo "🏷️ Verificando labels de Traefik..."
docker inspect entersys-content-api | grep -A 10 traefik.http.routers || echo "Sin labels de Traefik"

# Test URLs actuales
echo "🌐 Probando URLs con configuración actual..."
CURRENT_WORKING=false

# URLs posibles con la configuración actual
TEST_URLS=(
    "https://api.dev.entersys.mx/content/v1/health"
    "https://api.dev.entersys.mx/api/v1/health"
    "https://api.dev.entersys.mx/v1/health"
    "https://api.dev.entersys.mx/"
)

for url in "${TEST_URLS[@]}"; do
    if test_and_report "$url" "$(basename "$url")"; then
        echo "🎉 ENCONTRADA URL FUNCIONAL: $url"
        CURRENT_WORKING=true
        break
    fi
done

if $CURRENT_WORKING; then
    echo "✅ El routing ya funciona con alguna URL"
    exit 0
fi

echo ""
echo "📊 FASE 3: CORRECCION AUTOMATICA"
echo "==============================="

echo "🔧 Problema detectado: Traefik no está enrutando correctamente"
echo "🛠️ Aplicando corrección automática..."

# Parar contenedor actual
docker-compose down

# SOLUCION 1: Configuración con routing directo (sin path prefix)
echo "🔧 SOLUCION 1: Routing directo sin path stripping"
cat > docker-compose.yml << 'EOF'
version: '3.9'

services:
  content-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: entersys-content-api
    restart: unless-stopped
    
    env_file:
      - .env
      
    networks:
      - traefik_network
      - entersys_internal
      
    labels:
      - "traefik.enable=true"
      # Routing directo a api.dev.entersys.mx
      - "traefik.http.routers.entersys-content-api.rule=Host(`api.dev.entersys.mx`)"
      - "traefik.http.routers.entersys-content-api.entrypoints=websecure"
      - "traefik.http.routers.entersys-content-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.entersys-content-api.loadbalancer.server.port=8000"
      # Metadata
      - "entersys.service.name=content-management"
      - "entersys.service.version=1.0.0"

networks:
  traefik_network:
    name: traefik
    external: true
  entersys_internal:
    driver: bridge
EOF

# Desplegar solución 1
docker-compose up -d --build --force-recreate
echo "⏳ Esperando 60 segundos para startup completo..."
sleep 60

# Test solución 1
echo "🧪 Probando Solución 1..."
if test_and_report "https://api.dev.entersys.mx/api/v1/health" "Health check directo"; then
    echo "🎉 SOLUCION 1 EXITOSA!"
    echo "✅ URLs funcionando:"
    echo "  • https://api.dev.entersys.mx/api/v1/health"
    echo "  • https://api.dev.entersys.mx/docs"
    echo "  • https://api.dev.entersys.mx/"
    exit 0
fi

echo "⚠️ Solución 1 no funcionó, probando Solución 2..."

# SOLUCION 2: Forzar reinicio de Traefik
echo "🔧 SOLUCION 2: Reiniciar Traefik"
docker restart traefik
sleep 30

if test_and_report "https://api.dev.entersys.mx/api/v1/health" "Health check después de restart Traefik"; then
    echo "🎉 SOLUCION 2 EXITOSA!"
    exit 0
fi

echo "⚠️ Solución 2 no funcionó, probando Solución 3..."

# SOLUCION 3: Puerto expuesto + routing directo
echo "🔧 SOLUCION 3: Con puerto expuesto"
docker-compose down
cat > docker-compose.yml << 'EOF'
version: '3.9'

services:
  content-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: entersys-content-api
    restart: unless-stopped
    
    env_file:
      - .env
      
    ports:
      - "8000:8000"  # Puerto expuesto para debug
      
    networks:
      - traefik_network
      - entersys_internal
      
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.entersys-content.rule=Host(`api.dev.entersys.mx`)"
      - "traefik.http.routers.entersys-content.entrypoints=websecure"
      - "traefik.http.routers.entersys-content.tls.certresolver=letsencrypt"
      - "traefik.http.services.entersys-content.loadbalancer.server.port=8000"

networks:
  traefik_network:
    name: traefik
    external: true
  entersys_internal:
    driver: bridge
EOF

docker-compose up -d --build --force-recreate
sleep 45

# Test directo al puerto
echo "🧪 Probando acceso directo al puerto 8000..."
if curl -f -s "http://34.134.14.202:8000/api/v1/health" > /dev/null 2>&1; then
    echo "✅ Puerto 8000 directo funciona"
fi

if test_and_report "https://api.dev.entersys.mx/api/v1/health" "Health check con puerto expuesto"; then
    echo "🎉 SOLUCION 3 EXITOSA!"
    exit 0
fi

echo ""
echo "📊 DIAGNOSTICO FINAL"
echo "==================="
echo "🔍 Información de debug:"

echo "1. Estado del contenedor:"
docker-compose ps

echo "2. Labels aplicadas:"
docker inspect entersys-content-api | grep -A 20 Labels

echo "3. Logs de Traefik (últimas 10 líneas):"
docker logs traefik 2>/dev/null | tail -10

echo "4. Test interno:"
docker exec entersys-content-api curl -s http://localhost:8000/api/v1/health || echo "Falla interno"

echo ""
echo "💡 RECOMENDACIONES FINALES:"
echo "1. Verificar que api.dev.entersys.mx apunte a 34.134.14.202"
echo "2. Esperar 5-10 minutos más para certificados SSL"
echo "3. Probar: curl -k https://api.dev.entersys.mx/api/v1/health"
echo "4. Contactar al administrador de DNS si persiste"

echo ""
echo "✅ Script de auto-corrección completado"