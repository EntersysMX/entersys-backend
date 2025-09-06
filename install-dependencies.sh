#!/bin/bash
# install-dependencies.sh
# Instala todas las dependencias necesarias en el servidor

set -e

echo "🔧 INSTALANDO DEPENDENCIAS NECESARIAS EN DEV-SERVER"
echo "==================================================="

# Verificar que estamos en el servidor correcto
if [[ $(hostname) != *"dev-server"* ]]; then
    echo "❌ Este script debe ejecutarse en dev-server"
    echo "Ejecuta: gcloud compute ssh dev-server --zone=us-central1-c"
    exit 1
fi

echo "✅ Ejecutando en dev-server"

# Actualizar sistema
echo "📦 Actualizando sistema..."
sudo apt update -qq

# Instalar herramientas básicas si no están
echo "🛠️ Instalando herramientas básicas..."
sudo apt install -y curl wget git jq htop unzip > /dev/null 2>&1 || echo "Algunas herramientas ya están instaladas"

# Verificar Docker
echo "🐳 Verificando Docker..."
if ! command -v docker &> /dev/null; then
    echo "📦 Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh > /dev/null 2>&1
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Docker instalado"
else
    echo "✅ Docker ya está instalado"
fi

# Verificar Docker Compose
echo "📦 Verificando Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Instalando Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose instalado"
else
    echo "✅ Docker Compose ya está instalado"
fi

# Verificar que Docker está corriendo
echo "🔍 Verificando servicios Docker..."
if ! sudo systemctl is-active --quiet docker; then
    echo "🚀 Iniciando Docker..."
    sudo systemctl start docker
    sudo systemctl enable docker
fi

if sudo docker info > /dev/null 2>&1; then
    echo "✅ Docker funcionando correctamente"
else
    echo "❌ Problemas con Docker"
    exit 1
fi

# Verificar estructura de directorios
echo "📁 Verificando estructura de directorios..."
sudo mkdir -p /srv/servicios/entersys-apis
sudo mkdir -p /srv/traefik
sudo mkdir -p /srv/backups
sudo mkdir -p /srv/scripts

# Dar permisos al usuario actual
sudo chown -R $USER:$USER /srv/servicios/entersys-apis 2>/dev/null || true

echo "✅ Estructura de directorios configurada"

# Verificar redes Docker
echo "🔗 Configurando redes Docker..."
docker network create traefik 2>/dev/null && echo "✅ Red traefik creada" || echo "✅ Red traefik ya existe"
docker network create entersys_internal 2>/dev/null && echo "✅ Red entersys_internal creada" || echo "✅ Red entersys_internal ya existe"

# Verificar que Traefik está corriendo
echo "🚦 Verificando Traefik..."
if docker ps | grep -q "traefik"; then
    echo "✅ Traefik está corriendo"
else
    echo "⚠️ Traefik no está corriendo"
    echo "💡 Si necesitas iniciarlo: cd /srv/traefik && docker-compose up -d"
fi

# Verificar PostgreSQL
echo "🗄️ Verificando PostgreSQL..."
if docker ps | grep -q "dev-entersys-postgres"; then
    echo "✅ PostgreSQL está corriendo"
else
    echo "⚠️ PostgreSQL no está corriendo"
    echo "💡 Si necesitas iniciarlo: cd /srv/servicios/entersys-db && docker-compose up -d"
fi

# Instalar herramientas adicionales útiles
echo "🔧 Instalando herramientas adicionales..."
sudo apt install -y python3 python3-pip > /dev/null 2>&1 || true

# Verificar acceso a GitHub
echo "📡 Verificando conectividad..."
if curl -s https://api.github.com > /dev/null; then
    echo "✅ Conectividad a GitHub OK"
else
    echo "⚠️ Problemas de conectividad a GitHub"
fi

# Información del sistema
echo ""
echo "📊 INFORMACIÓN DEL SISTEMA"
echo "========================="
echo "🖥️ Hostname: $(hostname)"
echo "💾 Memoria: $(free -h | grep Mem | awk '{print $2 " total, " $3 " usado, " $7 " disponible"}')"
echo "💽 Disco: $(df -h / | tail -1 | awk '{print $2 " total, " $3 " usado, " $4 " disponible"}')"
echo "🐳 Docker: $(docker --version)"
echo "📦 Docker Compose: $(docker-compose --version)"
echo "🌐 IP Externa: $(curl -s ifconfig.me 2>/dev/null || echo "No disponible")"

echo ""
echo "📋 CONTENEDORES ACTUALES"
echo "======================="
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | head -10

echo ""
echo "🔗 REDES DOCKER"
echo "==============="
docker network ls | grep -E "(traefik|entersys)"

echo ""
echo "✅ INSTALACIÓN COMPLETADA"
echo "========================"
echo "🎯 El servidor está listo para deployment"
echo ""
echo "🚀 Para desplegar Entersys API:"
echo "curl -s https://raw.githubusercontent.com/EntersysMX/entersys-backend/main/ONE-COMMAND-DEPLOY.sh | bash"
echo ""
echo "🔗 URLs que estarán disponibles:"
echo "  • https://api.dev.entersys.mx/content/v1/health"
echo "  • https://api.dev.entersys.mx/content/docs"

echo ""
echo "🔧 PRÓXIMOS PASOS:"
echo "1. Ejecutar el deployment script"
echo "2. Verificar que funciona"
echo "3. Configurar GitHub Actions (opcional)"