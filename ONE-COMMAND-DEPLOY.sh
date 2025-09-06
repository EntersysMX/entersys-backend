#!/bin/bash
# ONE-COMMAND-DEPLOY.sh
# Script que ejecuta TODO en un solo comando

set -e
trap 'echo "❌ Error en línea $LINENO"' ERR

echo "🚀 ENTERSYS CONTENT API - DEPLOYMENT AUTOMATICO"
echo "==============================================="

# Verificar que estamos en el servidor
if [[ $(hostname) != *"dev-server"* ]] && [[ ! -f /srv/traefik/traefik.yml ]]; then
    echo "❌ Este script debe ejecutarse en dev-server"
    echo "Ejecuta: gcloud compute ssh dev-server --zone=us-central1-c"
    echo "Luego: curl -s https://raw.githubusercontent.com/EntersysMX/entersys-backend/main/ONE-COMMAND-DEPLOY.sh | bash"
    exit 1
fi

echo "✅ Ejecutando en dev-server"

# Navegar y crear estructura
echo "📁 Creando estructura de directorios..."
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

# Crear .env
echo "⚙️ Configurando variables de entorno..."
cat > .env << 'ENVEOF'
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=entersys_dev_pass_2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
ENVEOF

echo "✅ .env creado"

# Verificar PostgreSQL
echo "🔍 Verificando PostgreSQL container..."
if ! docker ps | grep -q "dev-entersys-postgres"; then
    echo "❌ Container dev-entersys-postgres no está corriendo"
    echo "Inicia primero: cd /srv/servicios/entersys-db && docker-compose up -d"
    exit 1
fi

echo "✅ PostgreSQL container activo"

# Configurar base de datos
echo "🗄️ Configurando base de datos..."
docker exec dev-entersys-postgres psql -U postgres -v ON_ERROR_STOP=1 << 'SQLEOF'
-- Crear database si no existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'entersys_db') THEN
        CREATE DATABASE entersys_db;
        RAISE NOTICE 'Database entersys_db created';
    ELSE
        RAISE NOTICE 'Database entersys_db already exists';
    END IF;
END
$$;

-- Crear usuario si no existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'entersys_user') THEN
        CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025';
        RAISE NOTICE 'User entersys_user created';
    ELSE
        RAISE NOTICE 'User entersys_user already exists';
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;

-- Connect to database and grant schema permissions
\c entersys_db
GRANT ALL ON SCHEMA public TO entersys_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO entersys_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO entersys_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO entersys_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO entersys_user;
SQLEOF

if [ $? -eq 0 ]; then
    echo "✅ Base de datos configurada correctamente"
else
    echo "❌ Error configurando base de datos"
    exit 1
fi

# Crear redes Docker
echo "🔗 Configurando redes Docker..."
docker network create entersys_internal 2>/dev/null && echo "✅ Red entersys_internal creada" || echo "✅ Red entersys_internal ya existe"

# Verificar red traefik
if ! docker network ls | grep -q "traefik"; then
    echo "❌ Red traefik no existe"
    exit 1
fi

echo "✅ Redes configuradas"

# Limpiar contenedores anteriores
echo "🧹 Limpiando contenedores anteriores..."
docker-compose down --remove-orphans 2>/dev/null || true
docker container prune -f 2>/dev/null || true

# Construir y desplegar
echo "🔨 Construyendo y desplegando..."
docker-compose up -d --build --force-recreate

if [ $? -ne 0 ]; then
    echo "❌ Error en docker-compose up"
    exit 1
fi

echo "✅ Contenedor desplegado"

# Esperar startup
echo "⏳ Esperando startup de la aplicación..."
CONTAINER_NAME="entersys-content-api"

for i in {1..30}; do
    if docker ps | grep -q "$CONTAINER_NAME"; then
        echo "✅ Contenedor $CONTAINER_NAME está corriendo"
        break
    fi
    echo "⏳ Esperando contenedor... ($i/30)"
    sleep 2
done

if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ Contenedor no se inició correctamente"
    echo "📋 Logs del contenedor:"
    docker logs "$CONTAINER_NAME" 2>/dev/null || echo "No se pudieron obtener logs"
    exit 1
fi

# Test de salud interno
echo "🏥 Probando health check interno..."
for i in {1..20}; do
    if docker exec "$CONTAINER_NAME" curl -f -s http://localhost:8000/api/v1/health >/dev/null 2>&1; then
        echo "✅ Health check interno exitoso"
        INTERNAL_RESPONSE=$(docker exec "$CONTAINER_NAME" curl -s http://localhost:8000/api/v1/health)
        echo "📋 Respuesta: $INTERNAL_RESPONSE"
        break
    fi
    echo "⏳ Esperando health check interno... ($i/20)"
    sleep 3
done

# Test de acceso externo
echo "🌐 Probando acceso externo..."
sleep 10

EXTERNAL_URL="https://api.dev.entersys.mx/content/v1/health"
echo "🔗 Probando: $EXTERNAL_URL"

for i in {1..10}; do
    if curl -f -s "$EXTERNAL_URL" >/dev/null 2>&1; then
        echo "🎉 ¡ACCESO EXTERNO EXITOSO!"
        EXTERNAL_RESPONSE=$(curl -s "$EXTERNAL_URL")
        echo "📋 Respuesta externa: $EXTERNAL_RESPONSE"
        break
    fi
    echo "⏳ Esperando acceso externo... ($i/10)"
    sleep 5
done

# Estado final
echo ""
echo "📊 ESTADO FINAL DEL DEPLOYMENT"
echo "=============================="
echo "📍 Ubicación: /srv/servicios/entersys-apis/content-management"
echo "🐳 Contenedor: $CONTAINER_NAME"
echo ""

echo "📊 Estado de contenedores:"
docker-compose ps

echo ""
echo "🔗 URLs disponibles:"
echo "  • Health Check: https://api.dev.entersys.mx/content/v1/health"
echo "  • Documentación: https://api.dev.entersys.mx/content/docs"
echo "  • Root: https://api.dev.entersys.mx/content/"

echo ""
echo "🧪 Tests rápidos:"
echo "  curl https://api.dev.entersys.mx/content/v1/health"
echo "  curl https://api.dev.entersys.mx/content/docs"

echo ""
echo "🔧 Comandos útiles:"
echo "  • Ver logs: docker logs $CONTAINER_NAME"
echo "  • Reiniciar: docker-compose restart"
echo "  • Parar: docker-compose down"

# Test final
echo ""
echo "🧪 TEST FINAL:"
if curl -f -s https://api.dev.entersys.mx/content/v1/health >/dev/null 2>&1; then
    echo "🎉 ¡DEPLOYMENT COMPLETADO EXITOSAMENTE!"
    echo "✅ API funcionando en: https://api.dev.entersys.mx/content/"
else
    echo "⚠️ Deployment completado pero acceso externo aún no disponible"
    echo "💡 Puede tomar unos minutos más para la generación de certificados SSL"
    echo "🔧 Para debug: docker logs traefik | grep entersys"
fi

echo ""
echo "✅ Deployment script completado"