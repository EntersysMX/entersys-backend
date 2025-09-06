# Server Deployment Commands

## Connect to dev-server
```bash
gcloud compute ssh dev-server --zone=us-central1-c
```

## Manual Deployment Steps

### 1. Deploy the application
```bash
# Navigate to services directory
cd /srv/servicios

# Run deployment script
chmod +x entersys-backend/deploy-to-dev-server.sh
./entersys-backend/deploy-to-dev-server.sh
```

### 2. Alternative manual deployment
```bash
# Create directory and navigate
mkdir -p /srv/servicios/entersys-backend
cd /srv/servicios/entersys-backend

# Clone repository
git clone https://github.com/EntersysMX/entersys-backend.git .

# Create .env file
cp .env.example .env
echo "POSTGRES_PASSWORD=entersys_dev_pass_2025" >> .env

# Deploy with Docker Compose
docker-compose up -d --build
```

## Monitoring Commands

### Check container status
```bash
cd /srv/servicios/entersys-backend
docker-compose ps
docker-compose logs -f backend
```

### Check Traefik routing
```bash
cd /srv/traefik
docker logs traefik | grep entersys-backend
```

### Test endpoints
```bash
# Health check (internal)
curl http://localhost:8000/api/v1/health

# Health check (via Traefik)
curl https://api.dev.entersys.mx/api/v1/health

# API documentation
curl https://api.dev.entersys.mx/docs
```

### Database connection test
```bash
# Connect to PostgreSQL container
docker exec -it dev-entersys-postgres psql -U entersys_user -d entersys_db

# Create tables if needed (run inside PostgreSQL)
\d # List tables
```

## Troubleshooting

### If containers fail to start
```bash
# Check logs
docker-compose logs backend

# Check database connectivity
docker exec -it dev-entersys-postgres psql -U postgres -c "SELECT 1"

# Recreate containers
docker-compose down
docker-compose up -d --build --force-recreate
```

### If Traefik routing doesn't work
```bash
# Check if traefik network exists
docker network ls | grep traefik

# Check Traefik configuration
docker logs traefik | tail -50

# Verify labels
docker inspect dev-entersys-backend | grep -A 10 Labels
```

## URLs after deployment
- **API Base**: https://api.dev.entersys.mx
- **Health Check**: https://api.dev.entersys.mx/api/v1/health  
- **API Docs**: https://api.dev.entersys.mx/docs
- **ReDoc**: https://api.dev.entersys.mx/redoc