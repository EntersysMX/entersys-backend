#!/bin/bash
# SETUP-POSTGRES.sh
# Script para configurar PostgreSQL correctamente

set -e

echo "🗄️ CONFIGURANDO POSTGRESQL PARA ENTERSYS"
echo "========================================"

# Verificar si hay PostgreSQL corriendo
echo "🔍 Verificando contenedores PostgreSQL existentes..."
if docker ps | grep -q postgres; then
    echo "✅ Encontrado contenedor PostgreSQL corriendo:"
    docker ps | grep postgres
    
    # Obtener nombre del contenedor
    POSTGRES_CONTAINER=$(docker ps --format "{{.Names}}" | grep postgres | head -1)
    echo "📝 Usando contenedor: $POSTGRES_CONTAINER"
    
    # Verificar que podemos conectar
    echo "🧪 Probando conexión..."
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U postgres >/dev/null 2>&1; then
        echo "✅ PostgreSQL está respondiendo"
        
        # Crear base de datos y usuario
        echo "🔧 Configurando base de datos para Entersys..."
        docker exec "$POSTGRES_CONTAINER" psql -U postgres << 'EOSQL'
-- Crear base de datos si no existe
SELECT 'CREATE DATABASE entersys_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'entersys_db')\gexec

-- Crear usuario si no existe  
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'entersys_user') THEN
        CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025';
    END IF;
END$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO entersys_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO entersys_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO entersys_user;

-- Conectar a la base de datos específica
\c entersys_db
GRANT ALL ON SCHEMA public TO entersys_user;
EOSQL
        
        if [ $? -eq 0 ]; then
            echo "✅ Base de datos configurada exitosamente"
            echo "📋 Detalles de conexión:"
            echo "  • Host: $POSTGRES_CONTAINER"  
            echo "  • Database: entersys_db"
            echo "  • User: entersys_user"
            echo "  • Password: entersys_dev_pass_2025"
        else
            echo "❌ Error configurando base de datos"
            exit 1
        fi
    else
        echo "❌ PostgreSQL no está respondiendo"
        docker logs "$POSTGRES_CONTAINER" --tail 10
        exit 1
    fi
    
elif docker ps -a | grep -q postgres; then
    echo "⚠️ Encontrado contenedor PostgreSQL parado"
    POSTGRES_CONTAINER=$(docker ps -a --format "{{.Names}}" | grep postgres | head -1)
    echo "🚀 Iniciando contenedor: $POSTGRES_CONTAINER"
    docker start "$POSTGRES_CONTAINER"
    
    echo "⏳ Esperando que PostgreSQL inicie..."
    sleep 15
    
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U postgres >/dev/null 2>&1; then
        echo "✅ PostgreSQL iniciado exitosamente"
        # Ejecutar configuración de base de datos (código de arriba)
        echo "🔧 Configurando base de datos..."
        docker exec "$POSTGRES_CONTAINER" psql -U postgres << 'EOSQL'
SELECT 'CREATE DATABASE entersys_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'entersys_db')\gexec
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'entersys_user') THEN
        CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025';
    END IF;
END$$;
GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;
\c entersys_db
GRANT ALL ON SCHEMA public TO entersys_user;
EOSQL
        echo "✅ Base de datos configurada"
    else
        echo "❌ PostgreSQL no pudo iniciar"
        exit 1
    fi
    
else
    echo "❌ No se encontró contenedor PostgreSQL"
    echo "🔧 Creando nuevo contenedor PostgreSQL..."
    
    # Crear directorio para el nuevo PostgreSQL
    mkdir -p /srv/servicios/entersys-database
    cd /srv/servicios/entersys-database
    
    # Crear docker-compose para PostgreSQL
    cat > docker-compose.yml << 'EOF'
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    container_name: dev-entersys-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres_admin_2025
      POSTGRES_DB: postgres
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data/pgdata
    ports:
      - "5432:5432"
    networks:
      - traefik
      - entersys_internal

volumes:
  postgres_data:

networks:
  traefik:
    external: true
  entersys_internal:
    driver: bridge
EOF
    
    # Crear redes si no existen
    docker network create traefik 2>/dev/null || true
    docker network create entersys_internal 2>/dev/null || true
    
    # Desplegar PostgreSQL
    docker-compose up -d
    
    echo "⏳ Esperando que PostgreSQL nuevo inicie..."
    sleep 30
    
    # Configurar base de datos en el nuevo contenedor
    if docker exec dev-entersys-postgres pg_isready -U postgres >/dev/null 2>&1; then
        echo "✅ Nuevo PostgreSQL iniciado"
        echo "🔧 Configurando base de datos inicial..."
        
        docker exec dev-entersys-postgres psql -U postgres << 'EOSQL'
CREATE DATABASE entersys_db;
CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025';
GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;
\c entersys_db
GRANT ALL ON SCHEMA public TO entersys_user;
EOSQL
        
        echo "✅ Nuevo PostgreSQL configurado completamente"
    else
        echo "❌ Nuevo PostgreSQL falló al iniciar"
        docker logs dev-entersys-postgres
        exit 1
    fi
fi

echo ""
echo "🎯 POSTGRESQL CONFIGURADO EXITOSAMENTE"
echo "====================================="

# Verificación final
POSTGRES_CONTAINER=$(docker ps --format "{{.Names}}" | grep postgres | head -1)
echo "📊 Información final:"
echo "  • Contenedor: $POSTGRES_CONTAINER"
echo "  • Estado: $(docker inspect $POSTGRES_CONTAINER --format='{{.State.Status}}')"
echo "  • Puerto: 5432"

# Test de conexión final
echo ""
echo "🧪 Test de conexión final:"
if docker exec "$POSTGRES_CONTAINER" psql -U entersys_user -d entersys_db -c "SELECT 'Connection OK' as status;" 2>/dev/null; then
    echo "✅ Conexión con entersys_user exitosa"
else
    echo "⚠️ Probando conexión como postgres..."
    docker exec "$POSTGRES_CONTAINER" psql -U postgres -c "SELECT 'Connection OK' as status;"
fi

echo ""
echo "✅ PostgreSQL listo para Entersys deployment"
echo ""
echo "🚀 Siguiente paso:"
echo "curl -s https://raw.githubusercontent.com/EntersysMX/entersys-backend/main/GUARANTEED-WORKING.sh | bash"