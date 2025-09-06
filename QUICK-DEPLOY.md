# 🚀 DEPLOYMENT INMEDIATO

## Ejecuta EXACTAMENTE estos comandos:

### 1. Conectar al servidor
```bash
gcloud compute ssh dev-server --zone=us-central1-c
```

### 2. Deployment directo (copia y pega todo):
```bash
cd /srv/servicios
mkdir -p entersys-apis/content-management
cd entersys-apis/content-management
git clone https://github.com/EntersysMX/entersys-backend.git .

# Crear .env
cat > .env << 'EOF'
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=entersys_dev_pass_2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
EOF

# Configurar base de datos
docker exec dev-entersys-postgres psql -U postgres << 'SQLEOF'
SELECT 'CREATE DATABASE entersys_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'entersys_db')\gexec
DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'entersys_user') THEN CREATE USER entersys_user WITH ENCRYPTED PASSWORD 'entersys_dev_pass_2025'; END IF; END$$;
GRANT ALL PRIVILEGES ON DATABASE entersys_db TO entersys_user;
\c entersys_db
GRANT ALL ON SCHEMA public TO entersys_user;
SQLEOF

# Crear red si no existe
docker network create entersys_internal 2>/dev/null || true

# Deploy
docker-compose down 2>/dev/null || true
docker-compose up -d --build

echo "⏳ Esperando 60 segundos..."
sleep 60

echo "🏥 Test interno:"
docker exec entersys-content-api curl -f http://localhost:8000/api/v1/health 2>/dev/null && echo "✅ Interno OK" || echo "❌ Interno FALLO"

echo "🌐 Test externo:"
curl -f https://api.dev.entersys.mx/content/v1/health 2>/dev/null && echo "✅ Externo OK" || echo "❌ Externo FALLO"

echo "📊 Estado:"
docker-compose ps
docker logs --tail 20 entersys-content-api
```

### 3. URLs a probar:
- https://api.dev.entersys.mx/content/v1/health
- https://api.dev.entersys.mx/content/docs  
- https://api.dev.entersys.mx/content/

### 4. Si hay problemas:
```bash
# Ver logs
docker logs entersys-content-api

# Ver logs de Traefik
docker logs traefik | grep entersys

# Reiniciar Traefik
docker restart traefik

# Test manual interno
docker exec entersys-content-api curl http://localhost:8000/api/v1/health
```

## ¡Ejecuta esto y dime qué resultado obtienes!