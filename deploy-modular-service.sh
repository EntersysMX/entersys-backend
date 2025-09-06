#!/bin/bash
# deploy-modular-service.sh
# Deployment script for modular Entersys API architecture

set -e

SERVICE_NAME="${1:-content-management}"
SERVICE_PATH="${2:-content}"

echo "🚀 Deploying Entersys Service: $SERVICE_NAME"
echo "============================================="
echo "Service Path: /srv/servicios/entersys-apis/$SERVICE_NAME"
echo "API Path: https://api.dev.entersys.mx/$SERVICE_PATH/"
echo ""

# Navigate to services directory
echo "📁 Setting up modular directory structure..."
cd /srv/servicios

# Create the modular structure
mkdir -p entersys-apis
cd entersys-apis

# Create service-specific directory
echo "Creating service directory: $SERVICE_NAME"
mkdir -p "$SERVICE_NAME"
cd "$SERVICE_NAME"

echo "📥 Cloning/updating $SERVICE_NAME service..."
if [ -d ".git" ]; then
    git stash 2>/dev/null || true
    git pull origin main
else
    if [ "$SERVICE_NAME" == "content-management" ]; then
        git clone https://github.com/EntersysMX/entersys-backend.git .
    else
        echo "❌ Repository for $SERVICE_NAME not configured yet"
        echo "Please provide repository URL for this service"
        exit 1
    fi
fi

echo "⚙️ Setting up environment for $SERVICE_NAME..."
cat > .env << EOF
# Environment for $SERVICE_NAME service
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=entersys_dev_pass_2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_${SERVICE_NAME//-/_}_db
POSTGRES_PORT=5432

# Service metadata
SERVICE_NAME=$SERVICE_NAME
SERVICE_PATH=$SERVICE_PATH
EOF

echo "✅ Environment configured for $SERVICE_PATH path"

echo "🗄️ Setting up database for $SERVICE_NAME..."
DB_NAME="entersys_${SERVICE_NAME//-/_}_db"

docker exec dev-entersys-postgres psql -U postgres << EOSQL
-- Create service-specific database
SELECT 'CREATE DATABASE $DB_NAME'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Ensure user exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'entersys_user') THEN
        CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025';
    END IF;
END\$\$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO entersys_user;

-- Connect and set permissions
\\c $DB_NAME
GRANT ALL ON SCHEMA public TO entersys_user;
EOSQL

echo "✅ Database $DB_NAME configured"

echo "🔗 Checking networks..."
if ! docker network ls | grep -q "entersys_internal"; then
    echo "Creating entersys internal network..."
    docker network create entersys_internal
fi

echo "🛑 Stopping existing $SERVICE_NAME containers..."
docker-compose down 2>/dev/null || echo "No existing containers"

# Clean up old containers with different names if they exist
docker container prune -f 2>/dev/null || true

echo "🔨 Building and deploying $SERVICE_NAME service..."
docker-compose up -d --build --force-recreate

echo "⏳ Waiting for $SERVICE_NAME service to start..."
CONTAINER_NAME="entersys-${SERVICE_NAME}-api"
if [ "$SERVICE_NAME" == "content-management" ]; then
    CONTAINER_NAME="entersys-content-api"
fi

sleep 30

# Wait for service to be healthy
echo "🏥 Testing internal health check..."
attempt=1
max_attempts=8
while [ $attempt -le $max_attempts ]; do
    echo "Health check attempt $attempt/$max_attempts..."
    
    if docker exec "$CONTAINER_NAME" curl -f -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "✅ $SERVICE_NAME internal health check passed!"
        break
    else
        if [ $attempt -eq $max_attempts ]; then
            echo "❌ Health check failed after $max_attempts attempts"
            echo "Container logs:"
            docker logs --tail 20 "$CONTAINER_NAME"
            exit 1
        fi
        echo "⏳ Service still starting up..."
        sleep 15
    fi
    ((attempt++))
done

echo "🌐 Testing external access..."
sleep 20

HEALTH_URL="https://api.dev.entersys.mx/$SERVICE_PATH/v1/health"
echo "Testing: $HEALTH_URL"

if curl -f -s "$HEALTH_URL" > /dev/null 2>&1; then
    echo "✅ SUCCESS! $SERVICE_NAME is accessible externally"
    echo ""
    echo "🎉 Service URLs:"
    echo "  • Health: https://api.dev.entersys.mx/$SERVICE_PATH/v1/health"
    echo "  • Docs: https://api.dev.entersys.mx/$SERVICE_PATH/docs"
    echo "  • Root: https://api.dev.entersys.mx/$SERVICE_PATH/"
    
    echo ""
    echo "📋 Health Check Response:"
    curl -s "$HEALTH_URL" | python3 -m json.tool 2>/dev/null || curl -s "$HEALTH_URL"
    
else
    echo "⚠️ External access pending (SSL certificate may still be generating)"
    echo ""
    echo "🔍 Debug information:"
    docker-compose ps
    echo ""
    echo "Container logs (last 10 lines):"
    docker logs --tail 10 "$CONTAINER_NAME"
    echo ""
    echo "Traefik routing logs:"
    docker logs traefik 2>/dev/null | grep -i "$SERVICE_PATH\|$SERVICE_NAME" | tail -5 || echo "No Traefik logs found"
    echo ""
    echo "Manual test: curl https://api.dev.entersys.mx/$SERVICE_PATH/v1/health"
fi

echo ""
echo "📊 Service deployment summary:"
echo "============================="
echo "Service: $SERVICE_NAME"
echo "Container: $CONTAINER_NAME"
echo "Path: /$SERVICE_PATH/*"
echo "Database: $DB_NAME"
echo "Status: $(docker inspect $CONTAINER_NAME --format='{{.State.Status}}' 2>/dev/null || echo 'Unknown')"

echo ""
echo "🔧 Management commands:"
echo "• Logs: docker logs $CONTAINER_NAME"
echo "• Status: docker-compose ps"
echo "• Restart: docker-compose restart"
echo "• Stop: docker-compose down"

echo ""
echo "✅ $SERVICE_NAME deployment completed!"