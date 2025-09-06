#!/bin/bash
# FIX-404-DEPLOY.sh
# Script para solucionar el error 404 con configuración simplificada

set -e

echo "🔧 SOLUCIONANDO ERROR 404 - ROUTING SIMPLIFICADO"
echo "==============================================="

if [[ $(hostname) != *"dev-server"* ]] && [[ ! -f /srv/traefik/traefik.yml ]]; then
    echo "❌ Ejecutar en dev-server"
    exit 1
fi

echo "📍 Ubicación: /srv/servicios/entersys-apis/content-management"
cd /srv/servicios/entersys-apis/content-management

# Parar contenedores existentes
echo "🛑 Parando contenedores..."
docker-compose down 2>/dev/null || true

# Crear docker-compose.yml simplificado para solucionar 404
echo "⚙️ Creando configuración sin path stripping..."
cat > docker-compose.yml << 'EOF'
# docker-compose.yml - Configuración simplificada sin path stripping
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
      # Routing directo sin path stripping - más simple
      - "traefik.http.routers.entersys-content-api.rule=Host(`api.dev.entersys.mx`)"
      - "traefik.http.routers.entersys-content-api.entrypoints=websecure"
      - "traefik.http.routers.entersys-content-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.entersys-content-api.loadbalancer.server.port=8000"

networks:
  traefik_network:
    name: traefik
    external: true
  entersys_internal:
    driver: bridge
EOF

echo "✅ Configuración simplificada creada"

# Redesplegar con configuración simple
echo "🔨 Redesplegando con configuración simplificada..."
docker-compose up -d --build --force-recreate

echo "⏳ Esperando startup..."
sleep 45

# Verificar contenedor
echo "📊 Estado del contenedor:"
docker-compose ps

# Test interno
echo "🏥 Test interno:"
if docker exec entersys-content-api curl -f -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "✅ Health check interno OK"
    docker exec entersys-content-api curl -s http://localhost:8000/api/v1/health
else
    echo "❌ Health check interno falló"
    echo "Logs del contenedor:"
    docker logs --tail 20 entersys-content-api
    exit 1
fi

# Test externo con routing directo (sin /content/ path)
echo "🌐 Test externo con routing directo:"
sleep 15

# Probar URLs directas
TEST_URLS=(
    "https://api.dev.entersys.mx/api/v1/health"
    "https://api.dev.entersys.mx/"
    "https://api.dev.entersys.mx/docs"
)

for url in "${TEST_URLS[@]}"; do
    echo "🧪 Probando: $url"
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo "✅ $url - FUNCIONA"
        curl -s "$url" | head -3
    else
        echo "❌ $url - Falla"
    fi
    echo ""
done

echo "🔍 Diagnóstico adicional:"
echo "1. Labels del contenedor:"
docker inspect entersys-content-api | grep -A 15 '"Labels"' | head -20

echo ""
echo "2. Traefik logs recientes:"
docker logs traefik 2>/dev/null | grep -i "api.dev.entersys.mx\|entersys" | tail -10 || echo "Sin logs específicos"

echo ""
echo "🎯 URLS A PROBAR:"
echo "✅ Health check: https://api.dev.entersys.mx/api/v1/health"
echo "✅ Docs: https://api.dev.entersys.mx/docs"  
echo "✅ Root: https://api.dev.entersys.mx/"

echo ""
echo "💡 Si aún hay 404, ejecuta:"
echo "docker restart traefik"
echo "sleep 30"
echo "curl https://api.dev.entersys.mx/api/v1/health"
EOF