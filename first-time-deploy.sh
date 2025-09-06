#!/bin/bash
# first-time-deploy.sh
# First time deployment of entersys-backend to api.dev.entersys.mx

echo "🚀 FIRST TIME DEPLOYMENT - Entersys Backend API"
echo "==============================================="
echo "Target: https://api.dev.entersys.mx"
echo ""

# Navigate to services directory (following infrastructure pattern)
echo "📁 Setting up directory structure..."
cd /srv/servicios

# Create the project directory
echo "Creating entersys-backend directory..."
mkdir -p entersys-backend
cd entersys-backend

echo "📥 Cloning repository for first time..."
git clone https://github.com/EntersysMX/entersys-backend.git .

echo "⚙️ Creating production environment configuration..."
cat > .env << 'EOF'
# Production environment for api.dev.entersys.mx
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=entersys_dev_pass_2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
EOF

echo "✅ Environment file created"

echo ""
echo "🗄️ Setting up database..."
echo "Checking if PostgreSQL container is running..."
if docker ps | grep -q "dev-entersys-postgres"; then
    echo "✅ PostgreSQL container is running"
    
    echo "Creating database and user..."
    docker exec dev-entersys-postgres psql -U postgres << 'EOSQL'
-- Create database if it doesn't exist
SELECT 'CREATE DATABASE entersys_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'entersys_db')\gexec

-- Create user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'entersys_user') THEN
        CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025';
    END IF;
END$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;

-- Connect to the database and set up permissions
\c entersys_db
GRANT ALL ON SCHEMA public TO entersys_user;
EOSQL

    echo "✅ Database setup completed"
else
    echo "❌ PostgreSQL container 'dev-entersys-postgres' is not running!"
    echo "Please start it first with:"
    echo "cd /srv/servicios/entersys-db && docker-compose up -d"
    exit 1
fi

echo ""
echo "🔗 Checking Traefik network..."
if docker network ls | grep -q "traefik"; then
    echo "✅ Traefik network exists"
else
    echo "❌ Traefik network not found!"
    echo "Creating traefik network..."
    docker network create traefik
fi

echo ""
echo "🐳 First time deployment with Docker Compose..."
echo "Building and starting containers..."
docker-compose up -d --build

echo ""
echo "⏳ Waiting for application to fully start..."
echo "This may take a few minutes for first-time setup..."

# Wait and check multiple times
for i in {1..12}; do
    echo "Checking startup progress... ($i/12)"
    sleep 15
    
    if docker ps | grep -q "dev-entersys-backend"; then
        echo "✅ Container is running"
        
        # Test internal connectivity
        if docker exec dev-entersys-backend curl -f -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
            echo "✅ Application is responding internally"
            break
        else
            echo "⏳ Application still starting up..."
        fi
    else
        echo "⏳ Container still starting..."
    fi
    
    if [ $i -eq 12 ]; then
        echo "❌ Application took too long to start"
        echo "Let's check what's happening..."
        docker-compose ps
        docker logs dev-entersys-backend
        exit 1
    fi
done

echo ""
echo "🏥 Testing internal health check..."
internal_health=$(docker exec dev-entersys-backend curl -s http://localhost:8000/api/v1/health)
if [ $? -eq 0 ]; then
    echo "✅ Internal health check successful:"
    echo "$internal_health"
else
    echo "❌ Internal health check failed"
    echo "Container logs:"
    docker logs --tail 20 dev-entersys-backend
    exit 1
fi

echo ""
echo "🌐 Waiting for Traefik SSL certificate generation..."
echo "This may take a few minutes for Let's Encrypt certificate..."
sleep 30

echo ""
echo "🔍 Testing external access via https://api.dev.entersys.mx..."

# Try multiple times as SSL certificate might be generating
for i in {1..6}; do
    echo "Testing external access... ($i/6)"
    
    # Test HTTPS first
    if curl -f -s https://api.dev.entersys.mx/api/v1/health > /dev/null 2>&1; then
        echo "🎉 SUCCESS! HTTPS access working!"
        external_health=$(curl -s https://api.dev.entersys.mx/api/v1/health)
        echo "Health check response:"
        echo "$external_health"
        break
    fi
    
    # Test HTTP as fallback
    if curl -f -s http://api.dev.entersys.mx/api/v1/health > /dev/null 2>&1; then
        echo "⚠️  HTTP access working (HTTPS certificate may still be generating)"
        external_health=$(curl -s http://api.dev.entersys.mx/api/v1/health)
        echo "Health check response:"
        echo "$external_health"
        break
    fi
    
    if [ $i -eq 6 ]; then
        echo "❌ External access not working yet"
        echo ""
        echo "🔍 Debugging information:"
        echo "1. Container status:"
        docker-compose ps
        
        echo ""
        echo "2. Traefik logs (looking for api.dev.entersys.mx):"
        docker logs traefik 2>/dev/null | grep -i "api.dev.entersys.mx\|entersys" | tail -10 || echo "No relevant Traefik logs found"
        
        echo ""
        echo "3. Container labels check:"
        docker inspect dev-entersys-backend | grep -A 10 '"Labels"'
        
        echo ""
        echo "🔧 Try these manual steps:"
        echo "1. Wait a few more minutes for SSL certificate"
        echo "2. Check Traefik dashboard if available"
        echo "3. Restart Traefik: docker restart traefik"
        echo "4. Test again: curl https://api.dev.entersys.mx/api/v1/health"
    else
        echo "Waiting for certificate generation and routing setup..."
        sleep 30
    fi
done

echo ""
echo "📊 Final deployment status:"
docker-compose ps

echo ""
echo "🎯 Summary:"
echo "==========="
if curl -f -s https://api.dev.entersys.mx/api/v1/health > /dev/null 2>&1; then
    echo "✅ DEPLOYMENT SUCCESSFUL!"
    echo ""
    echo "🌐 API is now accessible at:"
    echo "  • Health Check: https://api.dev.entersys.mx/api/v1/health"
    echo "  • API Documentation: https://api.dev.entersys.mx/docs"
    echo "  • ReDoc: https://api.dev.entersys.mx/redoc"
    echo "  • Root endpoint: https://api.dev.entersys.mx/"
else
    echo "⚠️  DEPLOYMENT COMPLETED but external access needs verification"
    echo ""
    echo "The application is running internally. External access may need:"
    echo "• A few more minutes for SSL certificate generation"
    echo "• DNS propagation (if recently configured)"
    echo "• Traefik restart: docker restart traefik"
fi

echo ""
echo "🔧 Useful commands for monitoring:"
echo "• Check logs: docker logs dev-entersys-backend"
echo "• Check status: docker-compose ps"
echo "• Restart app: docker-compose restart backend"
echo "• View Traefik: docker logs traefik | grep entersys"

echo ""
echo "🎉 First deployment completed!"