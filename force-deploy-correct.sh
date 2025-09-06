#!/bin/bash
# force-deploy-correct.sh
# Force deployment with correct configuration for api.dev.entersys.mx

set -e

echo "🚀 Force Deployment to api.dev.entersys.mx"
echo "==========================================="

# Navigate to the correct directory
cd /srv/servicios

# Ensure directory exists and get latest code
echo "📁 Setting up directory..."
mkdir -p entersys-backend
cd entersys-backend

echo "📥 Getting latest code..."
if [ -d ".git" ]; then
    git stash 2>/dev/null || true
    git pull origin main
else
    rm -rf * 2>/dev/null || true
    git clone https://github.com/EntersysMX/entersys-backend.git .
fi

echo "⚙️ Creating .env file with correct database settings..."
cat > .env << 'EOF'
# Correct database configuration for dev-entersys-postgres
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=entersys_dev_pass_2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
EOF

echo "✅ .env file created"

echo "🗄️ Setting up database (creating user and database if needed)..."
# Try to create database and user - ignore errors if they already exist
docker exec dev-entersys-postgres psql -U postgres -c "
SELECT 'CREATE DATABASE entersys_db' 
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'entersys_db')\gexec

DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'entersys_user') THEN
        CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025';
    END IF;
END\$\$;

GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;
" 2>/dev/null || echo "⚠️ Database setup completed (some commands may have been skipped if already configured)"

echo "🛑 Stopping any existing containers..."
docker-compose down 2>/dev/null || echo "No existing containers to stop"

echo "🗑️ Cleaning up any orphaned containers..."
docker container prune -f 2>/dev/null || true

echo "🔨 Building and starting containers with correct configuration..."
docker-compose up -d --build --force-recreate

echo "⏳ Waiting for application startup..."
sleep 45

echo "📊 Checking container status..."
docker-compose ps

echo "🏥 Testing internal health check..."
attempt=1
max_attempts=6
while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt/$max_attempts..."
    if docker exec dev-entersys-backend curl -f -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "✅ Internal health check PASSED!"
        
        echo "📋 Internal health check response:"
        docker exec dev-entersys-backend curl -s http://localhost:8000/api/v1/health | python3 -m json.tool 2>/dev/null || docker exec dev-entersys-backend curl -s http://localhost:8000/api/v1/health
        
        break
    else
        echo "❌ Internal health check failed, waiting..."
        if [ $attempt -eq $max_attempts ]; then
            echo "🔍 Showing container logs for debugging:"
            docker logs --tail 30 dev-entersys-backend
        else
            sleep 10
        fi
    fi
    ((attempt++))
done

echo ""
echo "🌐 Testing external access via api.dev.entersys.mx..."
sleep 15

if curl -f -s https://api.dev.entersys.mx/api/v1/health > /dev/null 2>&1; then
    echo "✅ SUCCESS! External access working!"
    echo "🎉 API is accessible at: https://api.dev.entersys.mx"
    
    echo ""
    echo "📋 Health check response:"
    curl -s https://api.dev.entersys.mx/api/v1/health | python3 -m json.tool 2>/dev/null || curl -s https://api.dev.entersys.mx/api/v1/health
    
    echo ""
    echo "🔗 Available endpoints:"
    echo "  • Health check: https://api.dev.entersys.mx/api/v1/health"
    echo "  • API docs: https://api.dev.entersys.mx/docs"
    echo "  • ReDoc: https://api.dev.entersys.mx/redoc"
    echo "  • Root endpoint: https://api.dev.entersys.mx/"
    
else
    echo "❌ External access still not working"
    echo ""
    echo "🔍 Debugging information:"
    echo "1. Container status:"
    docker-compose ps
    
    echo ""
    echo "2. Container logs (last 20 lines):"
    docker logs --tail 20 dev-entersys-backend
    
    echo ""
    echo "3. Traefik logs (last 10 lines, looking for entersys):"
    docker logs traefik 2>/dev/null | grep -i entersys | tail -10 || echo "No Traefik logs found"
    
    echo ""
    echo "4. Container labels:"
    docker inspect dev-entersys-backend | grep -A 15 '"Labels"' || echo "Cannot inspect container"
    
    echo ""
    echo "5. Manual debugging steps:"
    echo "   → Run debug script: ./debug-api-domain.sh"
    echo "   → Check Traefik: docker logs traefik | grep -i error"
    echo "   → Restart Traefik: docker restart traefik"
fi

echo ""
echo "✅ Deployment completed!"