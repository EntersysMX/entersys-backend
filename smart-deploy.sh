#!/bin/bash
# smart-deploy.sh
# Intelligent deployment script that tries multiple configurations

set -e

echo "🚀 Smart Deployment for Entersys Backend"
echo "========================================"

# Navigate to services directory
cd /srv/servicios
mkdir -p entersys-backend
cd entersys-backend

echo "📥 Getting latest code..."
if [ -d ".git" ]; then
    git pull origin main
else
    git clone https://github.com/EntersysMX/entersys-backend.git .
fi

echo "⚙️ Setting up environment..."
cat > .env << 'EOF'
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=entersys_dev_pass_2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
EOF

echo "🗄️ Setting up database..."
docker exec dev-entersys-postgres psql -U postgres -c "
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'entersys_user') THEN
      CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025';
   END IF;
END
\$\$;

DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'entersys_db') THEN
      CREATE DATABASE entersys_db OWNER entersys_user;
   END IF;
END
\$\$;

GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;
" 2>/dev/null || echo "⚠️ Database setup may have had warnings"

echo "🐳 Stopping any existing containers..."
docker-compose down 2>/dev/null || echo "No existing containers"

echo "🔨 Building and deploying with subdomain routing (api.entersys.mx)..."
docker-compose up -d --build

echo "⏳ Waiting for application to start..."
sleep 30

echo "🏥 Testing deployment..."
if docker exec dev-entersys-backend curl -f -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "✅ Internal health check passed"
    
    # Test external access
    if curl -f -s https://api.entersys.mx/api/v1/health > /dev/null 2>&1; then
        echo "✅ External access via api.entersys.mx working!"
        echo "🌐 SUCCESS! API accessible at: https://api.entersys.mx"
        echo "🏥 Health check: https://api.entersys.mx/api/v1/health"
        echo "📚 Documentation: https://api.entersys.mx/docs"
        exit 0
    else
        echo "⚠️ Subdomain routing not working, trying path-based routing..."
    fi
else
    echo "❌ Internal health check failed"
    echo "🔍 Container logs:"
    docker logs --tail 20 dev-entersys-backend
fi

echo "🔄 Trying path-based routing on dev.scram2k.com..."
docker-compose down
docker-compose -f docker-compose-path-routing.yml up -d --build

sleep 30

echo "🏥 Testing path-based routing..."
if curl -f -s https://dev.scram2k.com/api/v1/health > /dev/null 2>&1; then
    echo "✅ Path-based routing working!"
    echo "🌐 SUCCESS! API accessible at: https://dev.scram2k.com/api/"
    echo "🏥 Health check: https://dev.scram2k.com/api/v1/health"
    echo "📚 Documentation: https://dev.scram2k.com/api/docs"
else
    echo "❌ Path-based routing also failed"
    echo "🔍 Debug information:"
    echo "Container status:"
    docker-compose -f docker-compose-path-routing.yml ps
    echo "Container logs:"
    docker logs --tail 20 dev-entersys-backend
    echo "Traefik logs (last 10 lines):"
    docker logs --tail 10 traefik | grep -i entersys || echo "No Traefik logs found"
fi

echo ""
echo "🔍 Final status check:"
docker-compose -f docker-compose-path-routing.yml ps
echo ""
echo "📋 Manual testing commands:"
echo "- Internal: docker exec dev-entersys-backend curl http://localhost:8000/api/v1/health"
echo "- External: curl https://dev.scram2k.com/api/v1/health"
echo "- Traefik: docker logs traefik | grep entersys"