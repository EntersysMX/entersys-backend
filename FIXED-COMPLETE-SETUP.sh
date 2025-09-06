#!/bin/bash
# FIXED-COMPLETE-SETUP.sh
# Versión corregida que detecta automáticamente el usuario PostgreSQL

set -e

echo "🚀 SETUP COMPLETO CORREGIDO - DB + DEPLOYMENT"
echo "=============================================="

if [[ $(hostname) != *"dev-server"* ]] && [[ ! -f /srv/traefik/traefik.yml ]]; then
    echo "❌ Ejecutar en dev-server"
    exit 1
fi

echo "✅ Ejecutando en dev-server"

# FASE 1: DETECTAR Y CONFIGURAR POSTGRESQL
echo ""
echo "🗄️ FASE 1: DETECTANDO POSTGRESQL"
echo "==============================="

if docker ps | grep -q "dev-entersys-postgres"; then
    echo "✅ Contenedor PostgreSQL encontrado: dev-entersys-postgres"
    
    # Detectar usuario PostgreSQL automáticamente
    echo "🔍 Detectando usuario PostgreSQL..."
    
    # Obtener variables de entorno del contenedor
    PG_USER=""
    if docker exec dev-entersys-postgres env | grep -q "POSTGRES_USER="; then
        PG_USER=$(docker exec dev-entersys-postgres env | grep "POSTGRES_USER=" | cut -d'=' -f2)
        echo "📋 Usuario encontrado en variables: $PG_USER"
    fi
    
    # Si no hay usuario específico, probar usuarios comunes
    if [ -z "$PG_USER" ]; then
        echo "🧪 Probando usuarios comunes..."
        
        # Probar 'postgres'
        if docker exec dev-entersys-postgres psql -U postgres -c "SELECT 1;" >/dev/null 2>&1; then
            PG_USER="postgres"
            echo "✅ Usuario 'postgres' funciona"
        # Probar sin especificar usuario
        elif docker exec dev-entersys-postgres psql -c "SELECT 1;" >/dev/null 2>&1; then
            PG_USER=""
            echo "✅ Usuario por defecto funciona"
        # Probar 'entersys_user' si ya existe
        elif docker exec dev-entersys-postgres psql -U entersys_user -c "SELECT 1;" >/dev/null 2>&1; then
            PG_USER="entersys_user"
            echo "✅ Usuario 'entersys_user' ya existe y funciona"
        else
            echo "❌ No se pudo determinar usuario PostgreSQL"
            echo "🔍 Información del contenedor:"
            docker exec dev-entersys-postgres env | grep POSTGRES || echo "Sin variables POSTGRES"
            echo "🔧 Intentando crear usuario postgres..."
            
            # Último recurso: intentar como usuario root/default
            echo "🔧 Intentando conexión como usuario por defecto del sistema..."
            
            # Probar diferentes enfoques para crear el usuario postgres
            docker exec dev-entersys-postgres sh -c "
                # Intentar como usuario postgres del sistema
                su - postgres -c 'createuser -s postgres' 2>/dev/null || 
                # O como root creando directamente en PostgreSQL
                psql -U \$(whoami) -c 'CREATE USER postgres WITH SUPERUSER;' 2>/dev/null ||
                echo 'Intentos de crear usuario fallaron'
            " || echo "No se pudo crear usuario postgres"
            
            # Probar de nuevo
            if docker exec dev-entersys-postgres psql -U postgres -c "SELECT 1;" >/dev/null 2>&1; then
                PG_USER="postgres"
                echo "✅ Usuario postgres creado y funcionando"
            else
                echo "❌ Error crítico: No se puede conectar a PostgreSQL"
                exit 1
            fi
        fi
    fi
    
    echo "🎯 Usando usuario PostgreSQL: '$PG_USER'"
    
    # Configurar base de datos con el usuario detectado
    echo "🔧 Configurando base de datos entersys_db..."
    
    if [ -n "$PG_USER" ]; then
        PSQL_CMD="psql -U $PG_USER -d postgres"
    else
        PSQL_CMD="psql -d postgres"
    fi
    
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
        echo "🧪 Probando conexión con entersys_user..."
        if docker exec dev-entersys-postgres psql -U entersys_user -d entersys_db -c "SELECT 'Test OK' as status;" >/dev/null 2>&1; then
            echo "✅ Conexión de entersys_user exitosa"
        else
            echo "⚠️ entersys_user no puede conectar, pero base configurada"
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

# Limpiar completamente el directorio
echo "🧹 Limpiando deployment anterior..."
rm -rf * .* 2>/dev/null || true

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
echo "===================================="

docker network create entersys_internal 2>/dev/null && echo "✅ Red entersys_internal creada" || echo "✅ Red entersys_internal ya existe"

if ! docker network ls | grep -q "traefik"; then
    echo "❌ Red traefik no existe - creándola"
    docker network create traefik
fi

echo "✅ Redes configuradas"

# FASE 4: DEPLOYMENT SIMPLIFICADO
echo ""
echo "🚀 FASE 4: DEPLOYMENT SIMPLIFICADO"
echo "=================================="

# Crear docker-compose.yml simple que funcione
echo "⚙️ Creando configuración de deployment..."

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

networks:
  traefik_network:
    name: traefik
    external: true
  entersys_internal:
    external: true
EOF

echo "✅ Configuración creada"

# Limpiar contenedores anteriores
echo "🧹 Limpiando contenedores anteriores..."
docker-compose down 2>/dev/null || true

# Desplegar
echo "🔨 Desplegando aplicación..."
docker-compose up -d --build --force-recreate

echo "⏳ Esperando 60 segundos para startup completo..."
sleep 60

# FASE 5: VERIFICACION
echo ""
echo "🧪 FASE 5: VERIFICACION"
echo "======================"

echo "📊 Estado del contenedor:"
docker-compose ps

echo ""
echo "🏥 Test interno:"
if docker exec entersys-content-api curl -f -s http://localhost:8000/api/v1/health >/dev/null 2>&1; then
    echo "✅ Health check interno exitoso"
    INTERNAL_RESPONSE=$(docker exec entersys-content-api curl -s http://localhost:8000/api/v1/health)
    echo "📋 Respuesta interna: $INTERNAL_RESPONSE"
else
    echo "❌ Health check interno falló"
    echo "📋 Logs del contenedor:"
    docker logs --tail 15 entersys-content-api
    echo ""
    echo "💡 Revisar configuración de base de datos o aplicación"
    exit 1
fi

echo ""
echo "🌐 Test externo HTTPS:"
sleep 20
if curl -f -s https://api.dev.entersys.mx/api/v1/health >/dev/null 2>&1; then
    echo "🎉 ¡HTTPS FUNCIONA!"
    echo "✅ URLs HTTPS disponibles:"
    echo "  • Health: https://api.dev.entersys.mx/api/v1/health"
    echo "  • Docs:   https://api.dev.entersys.mx/docs"
    echo "  • Root:   https://api.dev.entersys.mx/"
    echo ""
    echo "📋 Respuesta HTTPS:"
    curl -s https://api.dev.entersys.mx/api/v1/health
else
    echo "⚠️ HTTPS no funciona aún, probando HTTP directo..."
    
    # Reiniciar Traefik y probar de nuevo
    docker restart traefik
    sleep 30
    
    if curl -f -s https://api.dev.entersys.mx/api/v1/health >/dev/null 2>&1; then
        echo "✅ HTTPS funciona después de reiniciar Traefik"
        curl -s https://api.dev.entersys.mx/api/v1/health
    else
        echo "🧪 Probando acceso directo por puerto 8000..."
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
            echo "⚠️ Traefik/SSL tiene problemas, pero API funciona"
            echo "💡 Revisar configuración DNS o certificados SSL"
        else
            echo "❌ Ningún acceso externo funciona"
        fi
    fi
fi

echo ""
echo "✅ SETUP COMPLETADO"
echo "==================="
echo "🐳 Contenedor: entersys-content-api"
echo "📁 Ubicación: /srv/servicios/entersys-apis/content-management"
echo "🗄️ Database: entersys_db (en dev-entersys-postgres)"

echo ""
echo "🔧 Comandos útiles:"
echo "• Ver logs: docker logs entersys-content-api"
echo "• Reiniciar: docker-compose restart"
echo "• Estado: docker-compose ps"
echo ""
echo "🎉 DEPLOYMENT FINALIZADO"