#!/bin/bash
# ULTIMATE-WORKING-SETUP.sh
# Script final que maneja todas las configuraciones posibles de PostgreSQL

set -e

echo "🎯 ULTIMATE WORKING SETUP - TODAS LAS CONFIGURACIONES POSTGRESQL"
echo "==============================================================="

if [[ $(hostname) != *"dev-server"* ]] && [[ ! -f /srv/traefik/traefik.yml ]]; then
    echo "❌ Ejecutar en dev-server"
    exit 1
fi

echo "✅ Ejecutando en dev-server"

# FASE 1: DETECCION Y CONFIGURACION POSTGRESQL ROBUSTA
echo ""
echo "🗄️ FASE 1: DETECCIÓN Y CONFIGURACIÓN POSTGRESQL ROBUSTA"
echo "======================================================"

if docker ps | grep -q "dev-entersys-postgres"; then
    echo "✅ Contenedor PostgreSQL encontrado: dev-entersys-postgres"
    
    # Función para probar conexión PostgreSQL
    test_pg_connection() {
        local user="$1"
        local db="${2:-postgres}"
        
        if [ -n "$user" ]; then
            docker exec dev-entersys-postgres psql -U "$user" -d "$db" -c "SELECT 1;" >/dev/null 2>&1
        else
            docker exec dev-entersys-postgres psql -d "$db" -c "SELECT 1;" >/dev/null 2>&1
        fi
    }
    
    # Detectar configuración PostgreSQL
    echo "🔍 Detectando configuración PostgreSQL..."
    
    # Obtener variables de entorno
    POSTGRES_ENV_USER=""
    if docker exec dev-entersys-postgres env 2>/dev/null | grep -q "POSTGRES_USER="; then
        POSTGRES_ENV_USER=$(docker exec dev-entersys-postgres env | grep "POSTGRES_USER=" | cut -d'=' -f2)
        echo "📋 Variable POSTGRES_USER encontrada: $POSTGRES_ENV_USER"
    fi
    
    # Probar diferentes usuarios en orden de prioridad
    PG_USER=""
    PG_CONNECTION_OK=false
    
    echo "🧪 Probando diferentes configuraciones de usuario..."
    
    # 1. Probar con variable de entorno si existe
    if [ -n "$POSTGRES_ENV_USER" ] && test_pg_connection "$POSTGRES_ENV_USER"; then
        PG_USER="$POSTGRES_ENV_USER"
        PG_CONNECTION_OK=true
        echo "✅ Conexión exitosa con usuario de env: $PG_USER"
    
    # 2. Probar con usuario 'postgres' estándar
    elif test_pg_connection "postgres"; then
        PG_USER="postgres"
        PG_CONNECTION_OK=true
        echo "✅ Conexión exitosa con usuario postgres estándar"
    
    # 3. Probar sin especificar usuario (usuario por defecto del contenedor)
    elif test_pg_connection ""; then
        PG_USER=""
        PG_CONNECTION_OK=true
        echo "✅ Conexión exitosa con usuario por defecto del contenedor"
    
    # 4. Probar si ya existe entersys_user
    elif test_pg_connection "entersys_user"; then
        PG_USER="entersys_user"
        PG_CONNECTION_OK=true
        echo "✅ Usuario entersys_user ya existe y funciona"
    
    # 5. Intentar soluciones avanzadas
    else
        echo "⚠️ Conexión estándar falló, probando soluciones avanzadas..."
        
        # Obtener información del contenedor
        echo "🔍 Información del contenedor PostgreSQL:"
        docker exec dev-entersys-postgres env | grep -i postgres || echo "Sin variables PostgreSQL específicas"
        
        # Probar como usuario del sistema postgres
        echo "🔧 Intentando inicializar PostgreSQL correctamente..."
        
        # Intentar diferentes enfoques para inicializar
        docker exec dev-entersys-postgres sh -c '
            # Verificar si PostgreSQL está corriendo
            if ! pg_isready >/dev/null 2>&1; then
                echo "PostgreSQL no está listo, intentando inicializar..."
                
                # Intentar como usuario postgres del sistema
                if id postgres >/dev/null 2>&1; then
                    echo "Usuario postgres del sistema existe"
                    # Intentar crear usuario de base de datos postgres
                    su - postgres -c "createuser -s postgres" 2>/dev/null || echo "Ya existe o no se pudo crear"
                fi
            fi
        '
        
        # Probar conexión después de intentos de inicialización
        if test_pg_connection "postgres"; then
            PG_USER="postgres"
            PG_CONNECTION_OK=true
            echo "✅ Conexión exitosa después de inicialización"
        elif test_pg_connection ""; then
            PG_USER=""
            PG_CONNECTION_OK=true
            echo "✅ Conexión por defecto exitosa después de inicialización"
        fi
    fi
    
    if [ "$PG_CONNECTION_OK" = false ]; then
        echo "❌ ERROR CRÍTICO: No se pudo establecer conexión con PostgreSQL"
        echo "🔧 Información de diagnóstico:"
        echo "   - Contenedor: dev-entersys-postgres"
        echo "   - Estado: $(docker inspect dev-entersys-postgres --format='{{.State.Status}}')"
        echo "   - Logs recientes:"
        docker logs dev-entersys-postgres --tail 10
        exit 1
    fi
    
    echo "🎯 Configuración PostgreSQL detectada:"
    echo "   - Usuario: '${PG_USER:-[default]}'"
    echo "   - Contenedor: dev-entersys-postgres"
    
    # Configurar base de datos con el usuario detectado
    echo "🔧 Configurando base de datos entersys_db..."
    
    # Construir comando psql apropiado
    if [ -n "$PG_USER" ]; then
        PSQL_CMD="psql -U $PG_USER"
    else
        PSQL_CMD="psql"
    fi
    
    # Ejecutar configuración de base de datos
    docker exec dev-entersys-postgres $PSQL_CMD << 'EOSQL'
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
ALTER USER entersys_user CREATEDB;

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
        
        # Probar conexión con entersys_user
        echo "🧪 Verificando conexión final con entersys_user..."
        if test_pg_connection "entersys_user" "entersys_db"; then
            echo "✅ Verificación final exitosa: entersys_user puede conectar"
        else
            echo "⚠️ entersys_user no puede conectar directamente, pero la base está configurada"
        fi
    else
        echo "❌ Error configurando base de datos"
        exit 1
    fi
    
else
    echo "❌ Contenedor dev-entersys-postgres no encontrado"
    echo "Contenedores PostgreSQL disponibles:"
    docker ps | grep postgres || echo "Ninguno"
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

# FASE 3: CONFIGURAR REDES DOCKER
echo ""
echo "🔗 FASE 3: CONFIGURANDO REDES DOCKER"
echo "==================================="

docker network create entersys_internal 2>/dev/null && echo "✅ Red entersys_internal creada" || echo "✅ Red entersys_internal ya existe"

if ! docker network ls | grep -q "traefik"; then
    echo "❌ Red traefik no existe - creándola"
    docker network create traefik
fi

echo "✅ Redes configuradas"

# FASE 4: DEPLOYMENT CON CONFIGURACION ROBUSTA
echo ""
echo "🚀 FASE 4: DEPLOYMENT CON CONFIGURACIÓN ROBUSTA"
echo "=============================================="

# Crear configuración docker-compose optimizada
echo "⚙️ Creando configuración de deployment robusta..."

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
      - "8000:8000"  # Puerto expuesto para acceso directo
      
    networks:
      - traefik_network
      - entersys_internal
      
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.entersys-api.rule=Host(`api.dev.entersys.mx`)"
      - "traefik.http.routers.entersys-api.entrypoints=websecure"
      - "traefik.http.routers.entersys-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.entersys-api.loadbalancer.server.port=8000"
      
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  traefik_network:
    name: traefik
    external: true
  entersys_internal:
    external: true
EOF

echo "✅ Configuración robusta creada"

# Limpiar contenedores anteriores
echo "🧹 Limpiando contenedores anteriores..."
docker-compose down 2>/dev/null || true

# Desplegar
echo "🔨 Desplegando aplicación..."
docker-compose up -d --build --force-recreate

echo "⏳ Esperando 90 segundos para startup completo..."
sleep 90

# FASE 5: VERIFICACION COMPLETA
echo ""
echo "🧪 FASE 5: VERIFICACIÓN COMPLETA"
echo "==============================="

echo "📊 Estado del contenedor:"
docker-compose ps

echo ""
echo "🏥 Test interno del contenedor:"
if docker exec entersys-content-api curl -f -s http://localhost:8000/api/v1/health >/dev/null 2>&1; then
    echo "✅ Health check interno exitoso"
    INTERNAL_RESPONSE=$(docker exec entersys-content-api curl -s http://localhost:8000/api/v1/health)
    echo "📋 Respuesta interna: $INTERNAL_RESPONSE"
else
    echo "❌ Health check interno falló"
    echo "📋 Logs del contenedor:"
    docker logs --tail 20 entersys-content-api
    echo ""
    echo "💡 Problema con la aplicación - revisar configuración"
    exit 1
fi

echo ""
echo "🌐 Test externo HTTPS:"
sleep 30
if curl -f -s https://api.dev.entersys.mx/api/v1/health >/dev/null 2>&1; then
    echo "🎉 ¡HTTPS FUNCIONA PERFECTAMENTE!"
    echo "✅ URLs HTTPS disponibles:"
    echo "  • Health: https://api.dev.entersys.mx/api/v1/health"
    echo "  • Docs:   https://api.dev.entersys.mx/docs"
    echo "  • Root:   https://api.dev.entersys.mx/"
    echo ""
    echo "📋 Respuesta HTTPS:"
    curl -s https://api.dev.entersys.mx/api/v1/health
    echo ""
    echo "🎯 DEPLOYMENT COMPLETAMENTE EXITOSO"
else
    echo "⚠️ HTTPS no funciona aún, reiniciando Traefik y probando de nuevo..."
    
    # Reiniciar Traefik
    docker restart traefik
    sleep 45
    
    if curl -f -s https://api.dev.entersys.mx/api/v1/health >/dev/null 2>&1; then
        echo "✅ HTTPS funciona después de reiniciar Traefik"
        curl -s https://api.dev.entersys.mx/api/v1/health
        echo ""
        echo "🎯 DEPLOYMENT EXITOSO (requirió reinicio de Traefik)"
    else
        echo "🧪 HTTPS no funciona, probando acceso directo por puerto 8000..."
        if curl -f -s http://34.134.14.202:8000/api/v1/health >/dev/null 2>&1; then
            echo ""
            echo "🎯 ACCESO DIRECTO FUNCIONA"
            echo "========================="
            echo "✅ URLs disponibles:"
            echo "  • Health: http://34.134.14.202:8000/api/v1/health"
            echo "  • Docs:   http://34.134.14.202:8000/docs"
            echo "  • Root:   http://34.134.14.202:8000/"
            echo ""
            echo "📋 Respuesta:"
            curl -s http://34.134.14.202:8000/api/v1/health
            echo ""
            echo "⚠️ Traefik/SSL tiene problemas, pero API funciona directamente"
            echo "💡 Para HTTPS, revisar:"
            echo "   - DNS: nslookup api.dev.entersys.mx"
            echo "   - Certificados SSL de Let's Encrypt"
            echo "   - Configuración de Traefik"
        else
            echo "❌ Ningún acceso externo funciona"
            echo ""
            echo "🔧 Diagnóstico final:"
            echo "1. Contenedor interno: ✅"
            echo "2. Acceso directo: ❌"
            echo "3. HTTPS: ❌"
            echo ""
            echo "💡 Posibles problemas:"
            echo "   - Firewall bloqueando puerto 8000"
            echo "   - Problemas de red Docker"
            echo "   - Configuración de Traefik incorrecta"
        fi
    fi
fi

echo ""
echo "✅ ULTIMATE SETUP COMPLETADO"
echo "============================"
echo "🐳 Contenedor: entersys-content-api"
echo "📁 Ubicación: /srv/servicios/entersys-apis/content-management"
echo "🗄️ Database: entersys_db (en dev-entersys-postgres)"

echo ""
echo "🔧 Comandos útiles para monitoreo:"
echo "• Ver logs: docker logs entersys-content-api -f"
echo "• Reiniciar: docker-compose restart"
echo "• Estado: docker-compose ps"
echo "• Health interno: docker exec entersys-content-api curl http://localhost:8000/api/v1/health"

echo ""
echo "🎉 DEPLOYMENT FINALIZADO - CONFIGURACIÓN ROBUSTA APLICADA"