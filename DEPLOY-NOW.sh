#!/bin/bash
# DEPLOY-NOW.sh
# Script directo para desplegar AHORA el servicio

echo "🚀 DESPLEGANDO ENTERSYS CONTENT API AHORA"
echo "========================================"

echo "📍 Ejecuta estos comandos EN EL SERVIDOR:"
echo ""
echo "# 1. CONECTAR AL SERVIDOR"
echo "gcloud compute ssh dev-server --zone=us-central1-c"
echo ""
echo "# 2. DEPLOYMENT DIRECTO"
cat << 'EOF'
cd /srv/servicios
mkdir -p entersys-apis/content-management
cd entersys-apis/content-management
git clone https://github.com/EntersysMX/entersys-backend.git .

# Crear .env
cat > .env << 'ENVEOF'
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=entersys_dev_pass_2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
ENVEOF

# Setup database
docker exec dev-entersys-postgres psql -U postgres -c "
CREATE DATABASE IF NOT EXISTS entersys_db;
CREATE USER IF NOT EXISTS entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025';
GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;
" || docker exec dev-entersys-postgres psql -U postgres -c "
SELECT 'CREATE DATABASE entersys_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'entersys_db');
DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'entersys_user') THEN CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025'; END IF; END\$\$;
GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;
"

# Deploy
docker-compose down 2>/dev/null || true
docker-compose up -d --build

echo "⏳ Esperando 60 segundos para startup..."
sleep 60

echo "🏥 Probando health check interno..."
docker exec entersys-content-api curl -f http://localhost:8000/api/v1/health || echo "Health check interno falló"

echo "🌐 Probando acceso externo..."
curl -f https://api.dev.entersys.mx/content/v1/health || curl -f http://api.dev.entersys.mx/content/v1/health || echo "Acceso externo falló"

echo "📊 Estado final:"
docker-compose ps
docker logs --tail 10 entersys-content-api

echo "✅ Deployment completado"
echo "🌐 Probar: https://api.dev.entersys.mx/content/v1/health"
EOF