#!/bin/bash

# 🚀 DEPLOYMENT DE SMARTSHEET MIDDLEWARE - v1.0
# Script de deployment actualizado para incluir el servicio de Smartsheet

echo "🔄 Starting Smartsheet Middleware Deployment..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones auxiliares
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Directorio de trabajo
WORK_DIR="/srv/servicios/entersys-apis/content-management"

log_info "Updating repository with latest Smartsheet service..."

# Ir al directorio y actualizar
cd "$WORK_DIR" || {
    log_error "Cannot access directory: $WORK_DIR"
    exit 1
}

# Actualizar código desde GitHub
log_info "Pulling latest code from GitHub..."
git pull origin main

if [ $? -ne 0 ]; then
    log_error "Failed to pull code from GitHub"
    exit 1
fi

log_success "Code updated successfully"

# Verificar que los archivos de Smartsheet existen
log_info "Verifying Smartsheet service files..."

REQUIRED_FILES=(
    "app/api/v1/endpoints/smartsheet.py"
    "app/services/smartsheet_service.py"
    "app/models/smartsheet.py"
    "app/utils/query_parser.py"
    "app/core/logging_config.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        log_error "Missing required file: $file"
        exit 1
    fi
done

log_success "All Smartsheet service files present"

# Verificar configuración de entorno
log_info "Checking Smartsheet environment variables..."

if ! grep -q "SMARTSHEET_ACCESS_TOKEN" .env; then
    log_error "Missing SMARTSHEET_ACCESS_TOKEN in .env"
    log_warning "Please add Smartsheet configuration to .env file"
    exit 1
fi

log_success "Environment configuration verified"

# Crear directorio de logs si no existe
log_info "Creating logs directory..."
mkdir -p logs
chmod 755 logs

# Parar servicios
log_info "Stopping current services..."
docker-compose down

# Rebuild y restart
log_info "Building and starting services with Smartsheet support..."
docker-compose up -d --build

# Esperar a que los servicios inicien
log_info "Waiting for services to start..."
sleep 30

# Health checks
log_info "Performing health checks..."

# Test interno básico
if docker exec entersys-content-api curl -f http://localhost:8000/api/v1/health >/dev/null 2>&1; then
    log_success "Basic API health check passed"
else
    log_error "Basic API health check failed"
fi

# Test interno de Smartsheet
if docker exec entersys-content-api curl -f -H "X-API-Key: smartsheet_production_api_key_2025_secure" http://localhost:8000/api/v1/smartsheet/health >/dev/null 2>&1; then
    log_success "Smartsheet API health check passed"
else
    log_error "Smartsheet API health check failed"
    log_info "Checking Smartsheet service logs..."
    docker exec entersys-content-api tail -20 logs/smartsheet.log 2>/dev/null || log_warning "No Smartsheet logs yet"
fi

# Test externo
log_info "Testing external connectivity..."
if curl -f https://api.dev.entersys.mx/api/v1/health >/dev/null 2>&1; then
    log_success "External API access working"
else
    log_warning "External API access may have issues"
fi

# Estado final
log_info "Final service status:"
docker-compose ps

# URLs de prueba
echo ""
log_info "🔗 Test URLs:"
echo "  Basic Health: https://api.dev.entersys.mx/api/v1/health"
echo "  Smartsheet Health: https://api.dev.entersys.mx/api/v1/smartsheet/health"
echo "  Smartsheet Data: https://api.dev.entersys.mx/api/v1/smartsheet/sheets/1837320408878980/rows?limit=3"
echo "  Documentation: https://api.dev.entersys.mx/docs"
echo ""
echo "  🔑 Remember to use header: X-API-Key: smartsheet_production_api_key_2025_secure"
echo ""

# Comandos de testing
echo ""
log_info "🧪 Quick tests you can run:"
echo 'curl -H "X-API-Key: smartsheet_production_api_key_2025_secure" https://api.dev.entersys.mx/api/v1/smartsheet/health'
echo 'curl -H "X-API-Key: smartsheet_production_api_key_2025_secure" "https://api.dev.entersys.mx/api/v1/smartsheet/sheets/1837320408878980/rows?limit=2"'
echo ""

log_success "🎉 Smartsheet Middleware deployment completed!"
log_info "Check logs with: docker logs entersys-content-api"
log_info "Check Smartsheet logs with: docker exec entersys-content-api tail -f logs/smartsheet.log"

echo ""
echo "📊 Monitoring Integration Ready:"
echo "  - Structured JSON logs in logs/ directory"
echo "  - Prometheus metrics available"
echo "  - Six Sigma dashboard compatible"