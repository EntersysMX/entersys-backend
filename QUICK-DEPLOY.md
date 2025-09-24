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

# JWT Security Configuration
SECRET_KEY=dev-secret-key-for-testing-only-2025
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth Settings
GOOGLE_CLIENT_ID=96894495492-npdg8c8eeh6oqpgkug2vaalle8krm0so.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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

# Mautic OAuth2 Configuration
MAUTIC_BASE_URL=https://crm.entersys.mx
MAUTIC_CLIENT_ID=1_2psjjg30m7s4ogs8goswsksos0s8scgk0k8wc484gwoww8sw4c
MAUTIC_CLIENT_SECRET=1_2psjjg30m7s4ogs8goswsksos0s8scgk0k8wc484gwoww8sw4c
MAUTIC_TOKEN_CACHE_TTL=3300

# Smartsheet Configuration
SMARTSHEET_ACCESS_TOKEN=VmwRrfCK736jp1j1MBiiFSPTRKVNlVJd5Dx6Y
SMARTSHEET_API_BASE_URL=https://api.smartsheet.com/2.0
MIDDLEWARE_API_KEY=smartsheet_production_api_key_2025_secure
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

**APIs Generales:**
- https://api.dev.entersys.mx/api/v1/health

**Smartsheet Middleware (requiere X-API-Key: smartsheet_production_api_key_2025_secure):**
- https://api.dev.entersys.mx/api/v1/smartsheet/health
- https://api.dev.entersys.mx/api/v1/smartsheet/sheets/1837320408878980/rows?limit=3
- https://api.dev.entersys.mx/api/v1/smartsheet/sheets/1837320408878980/columns

**Documentación:**
- https://api.dev.entersys.mx/docs

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

# Test Smartsheet interno
docker exec entersys-content-api curl -H "X-API-Key: smartsheet_production_api_key_2025_secure" http://localhost:8000/api/v1/smartsheet/health

# Ver logs estructurados de Smartsheet
docker exec entersys-content-api tail -f logs/smartsheet.log
```

### 5. Test completo de Smartsheet desde servidor:
```bash
# Test health check de Smartsheet
curl -H "X-API-Key: smartsheet_production_api_key_2025_secure" https://api.dev.entersys.mx/api/v1/smartsheet/health

# Test datos reales con filtrado
curl -H "X-API-Key: smartsheet_production_api_key_2025_secure" "https://api.dev.entersys.mx/api/v1/smartsheet/sheets/1837320408878980/rows?q=Cliente:equals:AWALAB&limit=2"

# Test selección de campos
curl -H "X-API-Key: smartsheet_production_api_key_2025_secure" "https://api.dev.entersys.mx/api/v1/smartsheet/sheets/1837320408878980/rows?fields=ID,Cliente,ERP&limit=2"
```

## ¡Ejecuta esto y dime qué resultado obtienes!