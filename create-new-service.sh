#!/bin/bash
# create-new-service.sh
# Script para crear un nuevo servicio en la arquitectura modular

SERVICE_NAME="$1"
SERVICE_PATH="$2"
SERVICE_PORT="${3:-8000}"

if [ -z "$SERVICE_NAME" ] || [ -z "$SERVICE_PATH" ]; then
    echo "Usage: $0 <service-name> <service-path> [port]"
    echo ""
    echo "Examples:"
    echo "  $0 user-management users 8001"
    echo "  $0 analytics analytics 8002" 
    echo "  $0 file-storage files 8003"
    echo ""
    echo "This will create:"
    echo "  • /srv/servicios/entersys-apis/<service-name>/"
    echo "  • https://api.dev.entersys.mx/<service-path>/*"
    exit 1
fi

SERVICE_SLUG=$(echo "$SERVICE_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g')

echo "🔧 Creating new Entersys service: $SERVICE_NAME"
echo "=============================================="
echo "Service Name: $SERVICE_NAME"
echo "Service Slug: $SERVICE_SLUG" 
echo "Service Path: /$SERVICE_PATH"
echo "Service Port: $SERVICE_PORT"
echo ""

# Create service directory structure
echo "📁 Creating service directory structure..."
mkdir -p "/srv/servicios/entersys-apis/$SERVICE_NAME"
cd "/srv/servicios/entersys-apis/$SERVICE_NAME"

echo "⚙️ Creating docker-compose.yml from template..."
sed -e "s/SERVICE_NAME/$SERVICE_NAME/g" \
    -e "s/SERVICE_SLUG/$SERVICE_SLUG/g" \
    -e "s/SERVICE_PATH/$SERVICE_PATH/g" \
    -e "s/8000/$SERVICE_PORT/g" \
    /srv/servicios/entersys-apis/content-management/templates/docker-compose.service-template.yml > docker-compose.yml

echo "⚙️ Creating environment file..."
cat > .env << EOF
# Environment for $SERVICE_NAME service
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=entersys_dev_pass_2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_${SERVICE_SLUG//-/_}_db
POSTGRES_PORT=5432

# Service configuration
SERVICE_NAME=$SERVICE_NAME
SERVICE_PATH=$SERVICE_PATH
SERVICE_PORT=$SERVICE_PORT
EOF

echo "📚 Creating service documentation..."
cat > README.md << EOF
# $SERVICE_NAME Service

Part of the Entersys modular API architecture.

## Service Information
- **Name**: $SERVICE_NAME
- **Path**: https://api.dev.entersys.mx/$SERVICE_PATH/
- **Port**: $SERVICE_PORT
- **Container**: entersys-$SERVICE_SLUG-api
- **Database**: entersys_${SERVICE_SLUG//-/_}_db

## Endpoints
- Health Check: https://api.dev.entersys.mx/$SERVICE_PATH/v1/health
- Documentation: https://api.dev.entersys.mx/$SERVICE_PATH/docs
- ReDoc: https://api.dev.entersys.mx/$SERVICE_PATH/redoc

## Development

### Local Development
\`\`\`bash
# Start service
docker-compose up -d --build

# View logs
docker logs entersys-$SERVICE_SLUG-api

# Stop service  
docker-compose down
\`\`\`

### Database
- **Database**: entersys_${SERVICE_SLUG//-/_}_db
- **User**: entersys_user
- **Connection**: Via dev-entersys-postgres container

## Architecture
This service follows the Entersys modular architecture pattern:
- Path-based routing via Traefik
- Shared PostgreSQL instance with service-specific database
- Internal network for service-to-service communication
- Auto SSL certificate generation
EOF

echo "📝 Creating basic FastAPI application structure..."
mkdir -p app/api/v1/endpoints app/core app/db app/models

# Create basic main.py
cat > app/main.py << EOF
from fastapi import FastAPI

app = FastAPI(
    title="$SERVICE_NAME API",
    description="$SERVICE_NAME service for Entersys.mx",
    version="1.0.0"
)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the $SERVICE_NAME API", "service": "$SERVICE_NAME"}

@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "$SERVICE_NAME", "version": "1.0.0"}
EOF

# Create basic Dockerfile
cat > Dockerfile << EOF
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Basic requirements for new service
RUN pip install fastapi uvicorn

COPY ./app /app/app

EXPOSE $SERVICE_PORT

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$SERVICE_PORT"]
EOF

echo "🗄️ Setting up database..."
DB_NAME="entersys_${SERVICE_SLUG//-/_}_db"

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

echo "✅ Service $SERVICE_NAME created successfully!"
echo ""
echo "📁 Service location: /srv/servicios/entersys-apis/$SERVICE_NAME"
echo "🌐 Future URL: https://api.dev.entersys.mx/$SERVICE_PATH/"
echo ""
echo "🚀 To deploy this service:"
echo "  cd /srv/servicios/entersys-apis/$SERVICE_NAME"
echo "  docker-compose up -d --build"
echo ""
echo "🔧 To develop this service:"
echo "  1. Add your application code to app/"
echo "  2. Update requirements in Dockerfile or add requirements.txt"
echo "  3. Deploy with docker-compose"
echo ""
echo "📊 Service will be available at:"
echo "  • Health: https://api.dev.entersys.mx/$SERVICE_PATH/v1/health"
echo "  • Docs: https://api.dev.entersys.mx/$SERVICE_PATH/docs"