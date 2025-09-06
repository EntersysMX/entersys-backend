#!/bin/bash
# FORCE-REBUILD.sh
# Script para forzar rebuild completo de la imagen Docker con curl

set -e

echo "🔄 FORCE REBUILD - RECONSTRUIR IMAGEN CON CURL"
echo "=============================================="

if [[ $(hostname) != *"dev-server"* ]] && [[ ! -f /srv/traefik/traefik.yml ]]; then
    echo "❌ Ejecutar en dev-server"
    exit 1
fi

cd /srv/servicios/entersys-apis/content-management

echo "🛑 Parando contenedores existentes..."
docker-compose down

echo "🧹 Limpiando imágenes Docker para forzar rebuild completo..."
# Eliminar imagen específica del proyecto
docker rmi content-management-content-api 2>/dev/null && echo "✅ Imagen anterior eliminada" || echo "ℹ️ No había imagen anterior"

# Eliminar imágenes huérfanas
docker image prune -f >/dev/null 2>&1 && echo "✅ Imágenes huérfanas limpiadas"

echo "🔨 Reconstruyendo imagen desde cero (sin cache)..."
docker-compose build --no-cache --pull

echo "🚀 Iniciando con imagen nueva..."
docker-compose up -d

echo "⏳ Esperando 60 segundos para que inicie completamente..."
sleep 60

echo "🧪 Verificando que curl esté disponible en el contenedor..."
if docker exec entersys-content-api which curl >/dev/null 2>&1; then
    echo "✅ curl está disponible en el contenedor"
    
    echo "🏥 Probando health check con curl..."
    if docker exec entersys-content-api curl -f -s http://localhost:8000/api/v1/health >/dev/null 2>&1; then
        echo "🎉 ¡Health check exitoso con curl!"
        echo "📋 Respuesta:"
        docker exec entersys-content-api curl -s http://localhost:8000/api/v1/health
    else
        echo "⚠️ curl funciona pero la aplicación aún no responde"
        echo "🔍 Logs recientes:"
        docker logs entersys-content-api --tail 15
    fi
else
    echo "❌ curl aún no está disponible - problema con el Dockerfile"
    echo "🔍 Verificando contenido del contenedor..."
    docker exec entersys-content-api ls -la /usr/bin/ | grep curl || echo "curl no encontrado"
fi

echo ""
echo "📊 Estado final:"
docker-compose ps

echo ""
echo "✅ FORCE REBUILD COMPLETADO"
echo ""
echo "🔧 Si curl funciona, ejecuta el deployment completo:"
echo "curl -s https://raw.githubusercontent.com/EntersysMX/entersys-backend/main/ULTIMATE-WORKING-SETUP.sh | bash"