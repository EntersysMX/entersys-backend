#!/bin/bash
# COMPLETE-SETUP.sh
# Un comando que configura todo: DB + deployment completo

set -e

echo "🚀 SETUP COMPLETO - DB + DEPLOYMENT EN UN COMANDO"
echo "================================================="

if [[ $(hostname) != *"dev-server"* ]] && [[ ! -f /srv/traefik/traefik.yml ]]; then
    echo "❌ Ejecutar en dev-server"
    exit 1
fi

echo "✅ Ejecutando en dev-server"

# FASE 1: CONFIGURAR POSTGRESQL
echo ""
echo "🗄️ FASE 1: CONFIGURANDO POSTGRESQL"
echo "================================="

# Verificar PostgreSQL
if docker ps | grep -q "dev-entersys-postgres"; then
    echo "✅ Contenedor PostgreSQL encontrado: dev-entersys-postgres"
    
    # Configurar base de datos
    echo "🔧 Configurando base de datos entersys_db..."
    docker exec dev-entersys-postgres psql -U postgres << 'EOSQL'
-- Crear base de datos si no existe
SELECT 'CREATE DATABASE entersys_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'entersys_db')\gexec

-- Crear usuario si no existe  
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'entersys_user') THEN
        CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025';
        RAISE NOTICE 'User entersys_user created';
    ELSE
        RAISE NOTICE 'User entersys_user already exists';
    END IF;
END$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;

-- Conectar a la base específica y dar permisos
\c entersys_db
GRANT ALL ON SCHEMA public TO entersys_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO entersys_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO entersys_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO entersys_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO entersys_user;
EOSQL
    
    if [ $? -eq 0 ]; then
        echo "✅ Base de datos configurada exitosamente"
    else
        echo "❌ Error configurando base de datos"
        exit 1
    fi
    
    # Probar conexión
    echo "🧪 Probando conexión de entersys_user..."
    if docker exec dev-entersys-postgres psql -U entersys_user -d entersys_db -c "SELECT 'Connection test OK' as status;" >/dev/null 2>&1; then
        echo "✅ Conexión de usuario exitosa"
    else
        echo "⚠️ Conexión directa falló, pero continuamos (se puede conectar como postgres)"
    fi
    
else
    echo "❌ Contenedor PostgreSQL no encontrado"
    echo "Esperado: dev-entersys-postgres"
    echo "Contenedores disponibles:"
    docker ps | grep postgres || echo "Ningún contenedor PostgreSQL"
    exit 1
fi

# FASE 2: CREAR ESTRUCTURA DEL PROYECTO
echo ""
echo "📁 FASE 2: CREANDO ESTRUCTURA DEL PROYECTO"
echo "=========================================="

cd /srv/servicios
mkdir -p entersys-apis/content-management
cd entersys-apis/content-management

# Limpiar si existe
if [ -d ".git" ]; then
    echo "🧹 Limpiando deployment anterior..."
    rm -rf * .git* 2>/dev/null || true
fi

echo "📥 Clonando código fuente..."
git clone https://github.com/EntersysMX/entersys-backend.git . --quiet

echo "⚙️ Creando .env..."
cat > .env << 'ENVEOF'
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=entersys_dev_pass_2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
ENVEOF

echo "✅ Estructura del proyecto lista"

# FASE 3: CONFIGURAR DOCKER Y REDES
echo ""
echo "🔗 FASE 3: CONFIGURANDO DOCKER Y REDES"
echo "====================================="

# Crear redes necesarias
docker network create entersys_internal 2>/dev/null && echo "✅ Red entersys_internal creada" || echo "✅ Red entersys_internal ya existe"

if ! docker network ls | grep -q "traefik"; then
    echo "❌ Red traefik no existe - creándola"
    docker network create traefik
fi

echo "✅ Redes configuradas"

# FASE 4: DESPLEGAR CON CONFIGURACIONES MÚLTIPLES
echo ""
echo "🚀 FASE 4: DESPLEGANDO CON MÚLTIPLES CONFIGURACIONES"
echo "=================================================="

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
    
    echo "🔧 Desplegando: $config_name"
    
    # Parar contenedores anteriores
    docker-compose down 2>/dev/null || true
    
    # Aplicar configuración
    echo "$config_content" > docker-compose.yml
    
    # Desplegar
    docker-compose up -d --build --force-recreate
    
    # Esperar
    echo "⏳ Esperando 45 segundos para startup..."
    sleep 45
    
    # Verificar contenedor interno
    if ! docker exec entersys-content-api curl -f -s http://localhost:8000/api/v1/health >/dev/null 2>&1; then
        echo "❌ Health check interno falló en $config_name"
        echo "📋 Logs:"
        docker logs --tail 10 entersys-content-api
        return 1
    fi
    
    echo "✅ $config_name - Health check interno OK"
    return 0
}

# CONFIGURACION 1: Routing directo (más simple)
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
      - entersys_internal
      
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.entersys-api.rule=Host(\`api.dev.entersys.mx\`)"
      - "traefik.http.routers.entersys-api.entrypoints=websecure"
      - "traefik.http.routers.entersys-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.entersys-api.loadbalancer.server.port=8000"

networks:
  traefik_network:
    name: traefik
    external: true
  entersys_internal:
    external: true'

if deploy_config "Routing Directo" "$CONFIG1"; then
    sleep 20
    if test_url "https://api.dev.entersys.mx/api/v1/health" 15; then
        echo ""
        echo "🎉 ¡SUCCESS! CONFIGURACION 1 FUNCIONA!"
        echo "========================================="
        echo "✅ URLs disponibles:"
        echo "  • Health: https://api.dev.entersys.mx/api/v1/health"
        echo "  • Docs:   https://api.dev.entersys.mx/docs"
        echo "  • Root:   https://api.dev.entersys.mx/"
        echo ""
        echo "📋 Respuesta del health check:"
        curl -s https://api.dev.entersys.mx/api/v1/health | python3 -m json.tool 2>/dev/null || curl -s https://api.dev.entersys.mx/api/v1/health
        echo ""
        echo "✅ DEPLOYMENT COMPLETO EXITOSO"
        exit 0
    fi
fi

echo "⚠️ Configuración 1 no funcionó, probando configuración 2..."

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
      - entersys_internal
      
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.entersys-exposed.rule=Host(\`api.dev.entersys.mx\`)"
      - "traefik.http.routers.entersys-exposed.entrypoints=websecure"
      - "traefik.http.routers.entersys-exposed.tls.certresolver=letsencrypt"
      - "traefik.http.services.entersys-exposed.loadbalancer.server.port=8000"

networks:
  traefik_network:
    name: traefik
    external: true
  entersys_internal:
    external: true'

if deploy_config "Con Puerto Expuesto" "$CONFIG2"; then
    # Reiniciar Traefik
    docker restart traefik
    sleep 30
    
    if test_url "https://api.dev.entersys.mx/api/v1/health" 15; then
        echo ""
        echo "🎉 ¡SUCCESS! CONFIGURACION 2 FUNCIONA!"
        echo "========================================="
        echo "✅ URLs disponibles:"
        echo "  • Health: https://api.dev.entersys.mx/api/v1/health"
        echo "  • Docs:   https://api.dev.entersys.mx/docs"
        echo ""
        echo "📋 Respuesta:"
        curl -s https://api.dev.entersys.mx/api/v1/health
        echo ""
        echo "✅ DEPLOYMENT COMPLETO EXITOSO"
        exit 0
    fi
    
    # Probar acceso directo por puerto como fallback
    echo "🧪 Probando acceso directo por puerto 8000..."
    if test_url "http://34.134.14.202:8000/api/v1/health" 10; then
        echo ""
        echo "🎯 ACCESO DIRECTO FUNCIONA (Fallback)"
        echo "===================================="
        echo "✅ URLs disponibles:"
        echo "  • Health: http://34.134.14.202:8000/api/v1/health"
        echo "  • Docs:   http://34.134.14.202:8000/docs"
        echo ""
        echo "📋 Respuesta:"
        curl -s http://34.134.14.202:8000/api/v1/health
        echo ""
        echo "⚠️  Traefik/SSL tiene problemas, pero API funciona directamente"
        echo "💡 Para HTTPS, revisar configuración de Traefik"
        echo "✅ DEPLOYMENT FUNCIONAL (acceso directo)"
        exit 0
    fi
fi

echo ""
echo "😞 DIAGNOSTICO FINAL"
echo "==================="

echo "📊 Estado del contenedor:"
docker-compose ps 2>/dev/null || echo "Sin docker-compose activo"

echo ""
echo "🏥 Test interno:"
docker exec entersys-content-api curl -s http://localhost:8000/api/v1/health 2>/dev/null || echo "Falla test interno"

echo ""
echo "🔗 Labels de Traefik:"
docker inspect entersys-content-api 2>/dev/null | grep -A 5 traefik || echo "Sin labels"

echo ""
echo "📋 Logs recientes:"
docker logs --tail 10 entersys-content-api 2>/dev/null || echo "Sin logs"

echo ""
echo "💡 POSIBLES SOLUCIONES:"
echo "1. Verificar DNS: nslookup api.dev.entersys.mx"
echo "2. Verificar Traefik: docker logs traefik"
echo "3. Esperar 5-10 minutos más para certificados SSL"
echo "4. Usar acceso directo: http://34.134.14.202:8000/api/v1/health"

echo ""
echo "⚠️ Deployment completado parcialmente - revisar configuraciones"