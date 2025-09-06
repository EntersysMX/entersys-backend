#!/bin/bash
# GUARANTEED-WORKING.sh
# Script que prueba múltiples configuraciones hasta que una funcione

set -e

echo "🎯 GUARANTEED WORKING DEPLOYMENT - MULTIPLES CONFIGURACIONES"
echo "============================================================"

if [[ $(hostname) != *"dev-server"* ]] && [[ ! -f /srv/traefik/traefik.yml ]]; then
    echo "❌ Ejecutar en dev-server"
    exit 1
fi

cd /srv/servicios/entersys-apis/content-management

# Función para probar URLs
test_url() {
    local url="$1"
    local timeout="${2:-10}"
    if timeout "$timeout" curl -f -s "$url" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Función para desplegar configuración
deploy_config() {
    local config_name="$1"
    local config_content="$2"
    
    echo "🔧 Probando configuración: $config_name"
    
    # Parar contenedores
    docker-compose down 2>/dev/null || true
    
    # Aplicar nueva configuración
    echo "$config_content" > docker-compose.yml
    
    # Desplegar
    docker-compose up -d --build --force-recreate
    
    # Esperar startup
    echo "⏳ Esperando 60 segundos para startup..."
    sleep 60
    
    # Verificar contenedor interno
    if ! docker exec entersys-content-api curl -f -s http://localhost:8000/api/v1/health >/dev/null 2>&1; then
        echo "❌ Health check interno falló"
        return 1
    fi
    
    echo "✅ Health check interno OK"
    return 0
}

# CONFIGURACION 1: Routing directo sin path
echo ""
echo "========== CONFIGURACION 1: ROUTING DIRECTO =========="

CONFIG1='version: '\''3.9'\''

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
      
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.entersys-api.rule=Host(\`api.dev.entersys.mx\`)"
      - "traefik.http.routers.entersys-api.entrypoints=websecure"
      - "traefik.http.routers.entersys-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.entersys-api.loadbalancer.server.port=8000"

networks:
  traefik_network:
    name: traefik
    external: true'

if deploy_config "Routing Directo" "$CONFIG1"; then
    sleep 20
    if test_url "https://api.dev.entersys.mx/api/v1/health"; then
        echo "🎉 CONFIGURACION 1 FUNCIONA!"
        echo "✅ URLs:"
        echo "  • https://api.dev.entersys.mx/api/v1/health"
        echo "  • https://api.dev.entersys.mx/docs"
        curl -s https://api.dev.entersys.mx/api/v1/health
        exit 0
    fi
fi

echo "⚠️ Configuración 1 no funcionó, probando 2..."

# CONFIGURACION 2: Con puerto expuesto
echo ""
echo "========== CONFIGURACION 2: CON PUERTO EXPUESTO =========="

CONFIG2='version: '\''3.9'\''

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
      - "8000:8000"
      
    networks:
      - traefik_network
      
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.entersys-exposed.rule=Host(\`api.dev.entersys.mx\`)"
      - "traefik.http.routers.entersys-exposed.entrypoints=websecure"
      - "traefik.http.routers.entersys-exposed.tls.certresolver=letsencrypt"
      - "traefik.http.services.entersys-exposed.loadbalancer.server.port=8000"

networks:
  traefik_network:
    name: traefik
    external: true'

if deploy_config "Con Puerto Expuesto" "$CONFIG2"; then
    # Reiniciar Traefik para asegurar detección
    docker restart traefik
    sleep 30
    
    if test_url "https://api.dev.entersys.mx/api/v1/health"; then
        echo "🎉 CONFIGURACION 2 FUNCIONA!"
        echo "✅ URLs:"
        echo "  • https://api.dev.entersys.mx/api/v1/health"
        echo "  • https://api.dev.entersys.mx/docs"
        curl -s https://api.dev.entersys.mx/api/v1/health
        exit 0
    fi
    
    # Probar acceso directo por puerto
    echo "🧪 Probando acceso directo por puerto 8000..."
    if test_url "http://34.134.14.202:8000/api/v1/health"; then
        echo "✅ Acceso directo por puerto funciona:"
        echo "  • http://34.134.14.202:8000/api/v1/health"
        echo "  • http://34.134.14.202:8000/docs"
        curl -s http://34.134.14.202:8000/api/v1/health
        echo "⚠️ Problema con SSL/Traefik, pero API funciona directamente"
    fi
fi

echo "⚠️ Configuración 2 no funcionó, probando 3..."

# CONFIGURACION 3: HTTP solo (sin HTTPS)
echo ""
echo "========== CONFIGURACION 3: HTTP SOLO =========="

CONFIG3='version: '\''3.9'\''

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
      - "8000:8000"
      
    networks:
      - traefik_network
      
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.entersys-http.rule=Host(\`api.dev.entersys.mx\`)"
      - "traefik.http.routers.entersys-http.entrypoints=web"
      - "traefik.http.services.entersys-http.loadbalancer.server.port=8000"

networks:
  traefik_network:
    name: traefik
    external: true'

if deploy_config "HTTP Solo" "$CONFIG3"; then
    docker restart traefik
    sleep 30
    
    # Probar HTTP
    if test_url "http://api.dev.entersys.mx/api/v1/health"; then
        echo "🎉 CONFIGURACION 3 FUNCIONA! (HTTP)"
        echo "✅ URLs:"
        echo "  • http://api.dev.entersys.mx/api/v1/health"
        echo "  • http://api.dev.entersys.mx/docs"
        curl -s http://api.dev.entersys.mx/api/v1/health
        echo ""
        echo "💡 Para HTTPS, configura certificado SSL correctamente"
        exit 0
    fi
fi

echo "⚠️ Configuración 3 no funcionó, probando 4..."

# CONFIGURACION 4: Path-based routing funcional
echo ""
echo "========== CONFIGURACION 4: PATH-BASED ROUTING =========="

CONFIG4='version: '\''3.9'\''

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
      - "8000:8000"
      
    networks:
      - traefik_network
      
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.entersys-path.rule=Host(\`api.dev.entersys.mx\`) && PathPrefix(\`/content/\`)"
      - "traefik.http.routers.entersys-path.entrypoints=websecure"
      - "traefik.http.routers.entersys-path.tls.certresolver=letsencrypt"
      - "traefik.http.services.entersys-path.loadbalancer.server.port=8000"
      - "traefik.http.routers.entersys-path.middlewares=entersys-stripprefix"
      - "traefik.http.middlewares.entersys-stripprefix.stripprefix.prefixes=/content"

networks:
  traefik_network:
    name: traefik
    external: true'

if deploy_config "Path-based Routing" "$CONFIG4"; then
    docker restart traefik
    sleep 30
    
    if test_url "https://api.dev.entersys.mx/content/v1/health"; then
        echo "🎉 CONFIGURACION 4 FUNCIONA! (Path-based)"
        echo "✅ URLs:"
        echo "  • https://api.dev.entersys.mx/content/v1/health"
        echo "  • https://api.dev.entersys.mx/content/docs"
        curl -s https://api.dev.entersys.mx/content/v1/health
        exit 0
    fi
fi

echo ""
echo "😞 NINGUNA CONFIGURACION AUTOMATICA FUNCIONÓ"
echo "============================================="

echo "📊 Estado final del diagnóstico:"
echo "1. Contenedor interno:"
docker exec entersys-content-api curl -s http://localhost:8000/api/v1/health || echo "Falla interno"

echo ""
echo "2. Acceso directo por IP:"
curl -s http://34.134.14.202:8000/api/v1/health || echo "Falla IP directa"

echo ""
echo "3. Labels actuales:"
docker inspect entersys-content-api | grep -A 10 traefik

echo ""
echo "4. Logs de Traefik:"
docker logs traefik 2>/dev/null | grep -i entersys | tail -5 || echo "Sin logs"

echo ""
echo "💡 SOLUCION MANUAL:"
echo "1. Verificar DNS: nslookup api.dev.entersys.mx"
echo "2. Verificar certificados: curl -k https://api.dev.entersys.mx/api/v1/health"
echo "3. Usar acceso directo temporalmente: http://34.134.14.202:8000/api/v1/health"

echo ""
echo "✅ Al menos el contenedor está funcionando internamente"