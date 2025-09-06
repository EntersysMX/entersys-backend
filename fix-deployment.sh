#!/bin/bash
# fix-deployment.sh
# Script to fix deployment issues and ensure proper configuration

set -e

echo "🔧 Fixing Entersys Backend Deployment..."
echo "========================================"

# Navigate to services directory
cd /srv/servicios

# Create entersys-backend directory if needed
mkdir -p entersys-backend
cd entersys-backend

echo "📥 Cloning/updating repository..."
if [ -d ".git" ]; then
    git pull origin main
else
    git clone https://github.com/EntersysMX/entersys-backend.git .
fi

echo "⚙️ Setting up environment..."
# Create .env file with correct database settings
cat > .env << 'EOF'
# Database configuration for existing dev-entersys-postgres container
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=entersys_dev_pass_2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
EOF

echo "✅ .env file created"

echo "🗄️ Setting up database..."
# Create database and user if they don't exist
docker exec dev-entersys-postgres psql -U postgres -c "
CREATE DATABASE entersys_db;
CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025';
GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;
" 2>/dev/null || echo "Database/user may already exist"

echo "🐳 Stopping old containers..."
docker-compose down 2>/dev/null || echo "No existing containers"

echo "🔨 Building and starting containers..."
docker-compose up -d --build

echo "⏳ Waiting for application to start..."
sleep 45

echo "📊 Checking deployment status..."
docker-compose ps

echo "🏥 Testing health check..."
sleep 15

# Test internal connectivity first
echo "Internal health check:"
docker exec dev-entersys-backend curl -f http://localhost:8000/api/v1/health || echo "❌ Internal health check failed"

# Test external connectivity
echo "External health check via Traefik:"
curl -f https://api.dev.entersys.mx/api/v1/health || curl -f http://api.dev.entersys.mx/api/v1/health || echo "❌ External access failed"

echo "🔍 Container logs (last 10 lines):"
docker logs --tail 10 dev-entersys-backend

echo "✅ Deployment fix complete!"
echo ""
echo "🌐 URLs to test:"
echo "- https://api.dev.entersys.mx/api/v1/health"
echo "- https://api.dev.entersys.mx/docs"
echo "- https://api.dev.entersys.mx/"