#!/bin/bash
# debug-api-domain.sh
# Specific debugging for api.dev.entersys.mx domain

echo "🔍 Debugging api.dev.entersys.mx - Entersys Backend"
echo "=================================================="

echo "1. 🌐 Testing DNS resolution..."
echo "Local DNS lookup:"
nslookup api.dev.entersys.mx
echo ""
echo "External DNS lookup:"
dig api.dev.entersys.mx +short || echo "dig command not available"

echo ""
echo "2. 📡 Testing direct connectivity..."
echo "Ping test:"
ping -c 3 api.dev.entersys.mx || echo "Ping failed or not available"

echo "HTTP/HTTPS connectivity test:"
curl -I -m 10 http://api.dev.entersys.mx 2>/dev/null && echo "✅ HTTP responds" || echo "❌ HTTP failed"
curl -I -m 10 https://api.dev.entersys.mx 2>/dev/null && echo "✅ HTTPS responds" || echo "❌ HTTPS failed"

echo ""
echo "3. 🐳 Checking if entersys-backend container exists and is running..."
if docker ps | grep -q "dev-entersys-backend"; then
    echo "✅ Container dev-entersys-backend is RUNNING"
    
    echo ""
    echo "Container details:"
    docker ps | grep dev-entersys-backend
    
    echo ""
    echo "Container networks:"
    docker inspect dev-entersys-backend | grep -A 10 '"Networks"' | head -15
    
    echo ""
    echo "4. 🏥 Testing internal health check..."
    echo "Internal health check (direct to container):"
    if docker exec dev-entersys-backend curl -f http://localhost:8000/api/v1/health 2>/dev/null; then
        echo "✅ Internal health check PASSED"
    else
        echo "❌ Internal health check FAILED"
        echo "Container logs (last 20 lines):"
        docker logs --tail 20 dev-entersys-backend
    fi
    
else
    echo "❌ Container dev-entersys-backend is NOT RUNNING"
    
    echo ""
    echo "Checking if container exists but stopped:"
    docker ps -a | grep dev-entersys-backend || echo "Container doesn't exist at all"
    
    echo ""
    echo "Checking docker-compose status:"
    if [ -f "/srv/servicios/entersys-backend/docker-compose.yml" ]; then
        cd /srv/servicios/entersys-backend
        docker-compose ps
    else
        echo "❌ docker-compose.yml not found in expected location"
    fi
fi

echo ""
echo "5. 🚦 Checking Traefik configuration..."
echo "Traefik container status:"
docker ps | grep traefik || echo "❌ Traefik container not found"

echo ""
echo "Traefik logs for entersys (last 20 lines):"
docker logs traefik 2>/dev/null | grep -i entersys | tail -20 || echo "No Traefik logs found for 'entersys'"

echo ""
echo "All Traefik recent logs (last 10 lines):"
docker logs --tail 10 traefik 2>/dev/null || echo "Cannot access Traefik logs"

echo ""
echo "6. 🔗 Checking Traefik networks..."
echo "Available Docker networks:"
docker network ls | grep traefik

echo ""
echo "Containers connected to traefik network:"
docker network inspect traefik 2>/dev/null | grep -A 5 '"Containers"' | head -20 || echo "Cannot inspect traefik network"

echo ""
echo "7. 🎯 Summary & Next Steps:"
echo "==========================================="
echo "If container is not running:"
echo "  → cd /srv/servicios/entersys-backend && docker-compose up -d --build"
echo ""
echo "If container is running but health check fails:"
echo "  → Check application logs: docker logs dev-entersys-backend"
echo "  → Check database connectivity: docker exec dev-entersys-backend env"
echo ""
echo "If Traefik not routing:"
echo "  → Check container labels: docker inspect dev-entersys-backend | grep -A 20 Labels"
echo "  → Restart Traefik: docker restart traefik"
echo ""
echo "Manual test commands:"
echo "  → Internal: docker exec dev-entersys-backend curl http://localhost:8000/api/v1/health"
echo "  → External: curl https://api.dev.entersys.mx/api/v1/health"