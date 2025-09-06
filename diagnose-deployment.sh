#!/bin/bash
# diagnose-deployment.sh
# Script to diagnose deployment issues on dev-server

echo "🔍 Diagnosing Entersys Backend Deployment..."
echo "=================================================="

echo "📊 1. Checking if entersys-backend is deployed..."
if [ -d "/srv/servicios/entersys-backend" ]; then
    echo "✅ Directory exists: /srv/servicios/entersys-backend"
    cd /srv/servicios/entersys-backend
else
    echo "❌ Directory missing: /srv/servicios/entersys-backend"
    echo "🚨 Need to deploy first!"
    exit 1
fi

echo ""
echo "📊 2. Checking Docker containers..."
echo "All containers:"
docker ps -a | grep -E "(CONTAINER|entersys-backend|traefik)"

echo ""
echo "Docker compose status:"
docker-compose ps || echo "❌ No docker-compose found or not running"

echo ""
echo "📊 3. Checking container logs..."
if docker ps | grep -q "dev-entersys-backend"; then
    echo "✅ Container dev-entersys-backend is running"
    echo "Recent logs:"
    docker logs --tail 20 dev-entersys-backend
else
    echo "❌ Container dev-entersys-backend is NOT running"
    echo "Checking why it failed:"
    docker logs dev-entersys-backend 2>/dev/null || echo "No container logs found"
fi

echo ""
echo "📊 4. Checking Traefik routing..."
docker logs traefik 2>/dev/null | grep -i entersys | tail -10 || echo "No Traefik logs found for entersys"

echo ""
echo "📊 5. Checking networks..."
echo "Traefik network:"
docker network ls | grep traefik || echo "❌ Traefik network not found"

echo ""
echo "Container network connections:"
docker inspect dev-entersys-backend 2>/dev/null | grep -A 10 "Networks" || echo "Container not found"

echo ""
echo "📊 6. Checking internal connectivity..."
if docker ps | grep -q "dev-entersys-backend"; then
    echo "Testing internal health check:"
    docker exec dev-entersys-backend curl -f http://localhost:8000/api/v1/health 2>/dev/null && echo "✅ Internal health check OK" || echo "❌ Internal health check failed"
fi

echo ""
echo "📊 7. Checking DNS resolution..."
nslookup api.dev.entersys.mx || echo "❌ DNS resolution failed for api.dev.entersys.mx"

echo ""
echo "📊 8. Checking database connectivity..."
echo "PostgreSQL container status:"
docker ps | grep postgres | grep entersys || echo "❌ Entersys PostgreSQL container not found"

if docker ps | grep -q "dev-entersys-postgres"; then
    echo "✅ Database container is running"
    echo "Testing database connection:"
    docker exec dev-entersys-postgres pg_isready -U entersys_user || echo "❌ Database not ready"
else
    echo "❌ Database container dev-entersys-postgres not running"
fi

echo ""
echo "=================================================="
echo "🔍 Diagnosis complete!"
echo "Next steps based on findings above:"
echo "- If container not running: check docker-compose up -d --build"
echo "- If Traefik not routing: check labels and network"
echo "- If DNS fails: verify domain configuration"
echo "- If database fails: check dev-entersys-postgres container"