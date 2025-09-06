# 🏗️ Arquitectura de Servicios Entersys

## 🎯 Visión General

Esta arquitectura está diseñada para escalar múltiples servicios de API organizados por función, usando `api.dev.entersys.mx` como punto de entrada único con routing basado en paths.

## 📁 Estructura Propuesta

```
/srv/servicios/entersys-apis/
├── content-management/          # Gestión de contenido (este proyecto)
│   ├── docker-compose.yml      # Backend FastAPI principal
│   ├── .env
│   └── app/
├── user-management/             # Futuro: Gestión de usuarios
│   ├── docker-compose.yml
│   └── app/
├── analytics/                   # Futuro: Analytics y reportes
│   ├── docker-compose.yml
│   └── app/
├── file-storage/               # Futuro: Gestión de archivos
│   ├── docker-compose.yml
│   └── app/
└── shared/                     # Servicios compartidos
    ├── databases/
    └── redis/
```

## 🌐 Routing Strategy

### Dominio Base: `api.dev.entersys.mx`

| Servicio | Path | Descripción |
|----------|------|-------------|
| **Content Management** | `/content/*` | Blog, posts, páginas |
| **User Management** | `/users/*` | Autenticación, perfiles |
| **Analytics** | `/analytics/*` | Métricas, reportes |
| **File Storage** | `/files/*` | Upload, gestión archivos |

### URLs Finales:
- `https://api.dev.entersys.mx/content/v1/health`
- `https://api.dev.entersys.mx/content/v1/posts`
- `https://api.dev.entersys.mx/users/v1/auth`
- `https://api.dev.entersys.mx/analytics/v1/stats`

## 🐳 Configuración de Contenedores

### Estrategia de Naming:
- **Content Management**: `entersys-content-api`
- **User Management**: `entersys-users-api`
- **Analytics**: `entersys-analytics-api`

### Networks:
- **traefik** - Red externa para routing
- **entersys-internal** - Red interna para comunicación entre servicios

## 📊 Base de Datos Strategy

### Opción 1: Base de Datos por Servicio (Microservicios)
```
dev-entersys-content-db    # PostgreSQL para content
dev-entersys-users-db      # PostgreSQL para users
dev-entersys-analytics-db  # PostgreSQL para analytics
```

### Opción 2: Base de Datos Compartida con Schemas
```
dev-entersys-postgres:
  ├── content_schema
  ├── users_schema
  └── analytics_schema
```

## 🔄 Deployment Strategy

### 1. Deployment Individual por Servicio
Cada servicio puede desplegarse independientemente:
```bash
cd /srv/servicios/entersys-apis/content-management
docker-compose up -d --build
```

### 2. Deployment Orquestado
Script maestro que despliega todos los servicios:
```bash
./deploy-all-services.sh
```

### 3. Service Discovery
Traefik automáticamente detecta nuevos servicios por labels.

## 🚀 Migration Path

### Fase 1: Content Management (Actual)
- ✅ Desplegar content-management en `/content/*`
- ✅ Migrar health check a `/content/v1/health`

### Fase 2: Expandir Servicios
- 🔄 Agregar user-management en `/users/*`
- 🔄 Agregar analytics en `/analytics/*`

### Fase 3: Optimización
- 🔄 Service mesh si es necesario
- 🔄 Load balancing por servicio
- 🔄 Monitoring centralizado

## 🎯 Beneficios de esta Arquitectura

1. **Escalabilidad**: Cada servicio escala independientemente
2. **Mantenimiento**: Equipos pueden trabajar en servicios específicos
3. **Deployment**: Zero-downtime deployments por servicio
4. **Desarrollo**: Tecnologías diferentes por servicio si es necesario
5. **Organización**: Clara separación de responsabilidades

## 🔧 Configuración Actual vs Nueva

### Antes:
```
api.dev.entersys.mx/api/v1/health  ❌ Genérico
```

### Después:
```
api.dev.entersys.mx/content/v1/health  ✅ Específico por función
api.dev.entersys.mx/users/v1/health    ✅ Futuro
api.dev.entersys.mx/analytics/v1/stats ✅ Futuro
```