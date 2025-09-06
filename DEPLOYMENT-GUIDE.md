# 🚀 Guía de Deployment - Arquitectura Modular Entersys

## 📋 Overview

Esta guía describe cómo desplegar y gestionar múltiples servicios API organizados por función usando la arquitectura modular de Entersys.

## 🎯 Servicio Actual: Content Management

### 📍 URLs del Content Management Service
- **Health Check**: https://api.dev.entersys.mx/content/v1/health
- **Documentación**: https://api.dev.entersys.mx/content/docs
- **ReDoc**: https://api.dev.entersys.mx/content/redoc
- **Root**: https://api.dev.entersys.mx/content/

## 🚀 Primer Deployment

### Paso 1: Desplegar Content Management
```bash
# Conectar al servidor
gcloud compute ssh dev-server --zone=us-central1-c

# Ejecutar el primer deployment
cd /srv/servicios
git clone https://github.com/EntersysMX/entersys-backend.git temp-clone
cd temp-clone
chmod +x first-time-deploy.sh
./first-time-deploy.sh

# Esto creará la estructura:
# /srv/servicios/entersys-apis/content-management/
```

### Resultado Esperado
```bash
✅ Content Management API is now accessible at:
  • Health Check: https://api.dev.entersys.mx/content/v1/health
  • API Documentation: https://api.dev.entersys.mx/content/docs
  • ReDoc: https://api.dev.entersys.mx/content/redoc
  • Root endpoint: https://api.dev.entersys.mx/content/
```

## 🏗️ Estructura Final en el Servidor

```
/srv/servicios/entersys-apis/
├── content-management/          # ✅ Este deployment
│   ├── app/                     # Código FastAPI
│   ├── docker-compose.yml       # Configuración Traefik
│   ├── .env                     # Variables de entorno
│   └── templates/               # Templates para futuros servicios
├── user-management/             # 🔄 Futuro
├── analytics/                   # 🔄 Futuro
└── file-storage/               # 🔄 Futuro
```

## 🔄 Agregar Futuros Servicios

### Crear un Nuevo Servicio
```bash
cd /srv/servicios/entersys-apis/content-management
chmod +x create-new-service.sh

# Ejemplos:
./create-new-service.sh user-management users 8001
./create-new-service.sh analytics analytics 8002
./create-new-service.sh file-storage files 8003
```

### URLs Futuras Automáticas
- **Users**: https://api.dev.entersys.mx/users/v1/health
- **Analytics**: https://api.dev.entersys.mx/analytics/v1/stats  
- **Files**: https://api.dev.entersys.mx/files/v1/upload

## 🐳 Gestión de Contenedores

### Estado Actual
```bash
# Ver contenedores Entersys
docker ps | grep entersys

# Contenedor actual:
entersys-content-api           # Content Management
```

### Estado Futuro
```bash
# Contenedores futuros:
entersys-content-api           # Content Management
entersys-users-api             # User Management  
entersys-analytics-api         # Analytics
entersys-files-api             # File Storage
```

## 🗄️ Estrategia de Base de Datos

### Configuración Actual
- **Contenedor**: `dev-entersys-postgres`
- **Database**: `entersys_db` (content management)
- **Usuario**: `entersys_user`

### Configuración Futura (Auto-creada)
```sql
entersys_db                    -- Content Management
entersys_user_management_db    -- User Management
entersys_analytics_db          -- Analytics  
entersys_file_storage_db       -- File Storage
```

## 🔧 Comandos de Gestión

### Content Management Service
```bash
cd /srv/servicios/entersys-apis/content-management

# Ver estado
docker-compose ps

# Ver logs
docker logs entersys-content-api

# Reiniciar
docker-compose restart

# Actualizar código
git pull origin main
docker-compose up -d --build

# Parar servicio
docker-compose down
```

### Gestión Multi-Servicio
```bash
# Ver todos los servicios Entersys
docker ps | grep entersys-

# Ver logs de Traefik (routing)
docker logs traefik | grep entersys

# Reiniciar Traefik si hay problemas de routing
docker restart traefik
```

## 🌐 Routing y SSL

### Configuración Automática
- **Dominio Base**: `api.dev.entersys.mx`
- **SSL**: Let's Encrypt automático
- **Routing**: Path-based por Traefik

### Patrón de URLs
```
https://api.dev.entersys.mx/[service-path]/[endpoint]

Ejemplos:
https://api.dev.entersys.mx/content/v1/health
https://api.dev.entersys.mx/users/v1/auth
https://api.dev.entersys.mx/analytics/v1/stats
```

## 🔍 Troubleshooting

### Si un servicio no responde:
```bash
# 1. Verificar contenedor
docker ps | grep [service-name]

# 2. Ver logs
docker logs entersys-[service]-api

# 3. Verificar routing
docker logs traefik | grep [service-name]

# 4. Test interno
docker exec entersys-[service]-api curl localhost:8000/api/v1/health
```

### Si Traefik no routing correctamente:
```bash
# Reiniciar Traefik
docker restart traefik

# Verificar labels del contenedor
docker inspect entersys-content-api | grep -A 20 Labels

# Verificar red traefik
docker network inspect traefik
```

## 📊 Monitoreo

### Health Checks
```bash
# Content Management
curl https://api.dev.entersys.mx/content/v1/health

# Futuros servicios
curl https://api.dev.entersys.mx/users/v1/health
curl https://api.dev.entersys.mx/analytics/v1/health
```

### Métricas de Estado
```bash
# Todos los contenedores Entersys
docker stats $(docker ps --format "{{.Names}}" | grep entersys)

# Estado de servicios
for service in content users analytics files; do
    echo "Testing $service..."
    curl -s https://api.dev.entersys.mx/$service/v1/health | jq .status || echo "Service not deployed"
done
```

## 🎯 Beneficios de esta Arquitectura

1. **Escalabilidad Independiente**: Cada servicio escala por separado
2. **Deployment Zero-Downtime**: Actualiza servicios sin afectar otros
3. **Desarrollo Paralelo**: Equipos trabajan en servicios específicos
4. **Mantenimiento Simplificado**: Problemas aislados por servicio
5. **Tecnologías Flexibles**: Cada servicio puede usar diferente stack

## ✅ Checklist de Deployment

- [x] Content Management desplegado en `/content/*`
- [ ] User Management en `/users/*`
- [ ] Analytics en `/analytics/*`  
- [ ] File Storage en `/files/*`
- [x] SSL automático funcionando
- [x] Health checks configurados
- [x] Logging centralizado via Docker
- [x] Base de datos configurada

## 🔄 Próximos Pasos

1. **Verificar Content Management**: https://api.dev.entersys.mx/content/v1/health
2. **Desarrollar User Management**: Usar `create-new-service.sh`
3. **Implementar Analytics**: Métricas y reportes
4. **Agregar File Storage**: Upload y gestión de archivos