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
| **Smartsheet Middleware** | `/smartsheet/*` | Integración con Smartsheet API |

### URLs Finales:
- `https://api.dev.entersys.mx/content/v1/health`
- `https://api.dev.entersys.mx/content/v1/posts`
- `https://api.dev.entersys.mx/users/v1/auth`
- `https://api.dev.entersys.mx/analytics/v1/stats`
- `https://api.dev.entersys.mx/smartsheet/v1/sheets/{id}/rows`

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

---

# 📊 Smartsheet Middleware Service

## 🎯 Objetivo
Middleware RESTful que simplifica y estandariza la comunicación con la API de Smartsheet, proporcionando capacidades de filtrado dinámico, paginación y selección de campos.

## 🛠️ Arquitectura del Servicio

### Stack Tecnológico
- **Python 3.11+** - Lenguaje base
- **FastAPI** - Framework web con validación Pydantic
- **Smartsheet Python SDK 3.0.3** - Cliente oficial de Smartsheet
- **Prometheus Client** - Métricas para monitoreo
- **Logging Estructurado** - Logs en JSON para integración con ELK/Grafana

### Estructura de Archivos
```
app/
├── api/v1/endpoints/
│   └── smartsheet.py          # Endpoints FastAPI
├── services/
│   └── smartsheet_service.py  # Lógica de negocio
├── models/
│   └── smartsheet.py          # Modelos Pydantic
├── utils/
│   └── query_parser.py        # Parser de filtros dinámicos
├── core/
│   ├── config.py             # Configuración (actualizada)
│   └── logging_config.py     # Sistema de logging
└── main.py                   # Aplicación principal (actualizada)
```

## 🌐 Endpoints Disponibles

### 1. Obtener Filas de Hoja
```http
GET /api/v1/smartsheet/sheets/{sheet_id}/rows
```

**Parámetros de Query:**
- `limit` (int): Máximo de filas a retornar (1-1000, default: 100)
- `offset` (int): Posición inicial para paginación (default: 0)
- `fields` (string): Columnas a incluir (separadas por comas)
- `includeAttachments` (bool): Incluir metadatos de adjuntos
- `q` (string): Cadena de filtrado dinámico

**Headers Requeridos:**
- `X-API-Key`: Clave de autenticación del middleware

### 2. Obtener Columnas de Hoja
```http
GET /api/v1/smartsheet/sheets/{sheet_id}/columns
```

### 3. Health Check
```http
GET /api/v1/smartsheet/health
```

## 🔍 Sistema de Filtrado Dinámico

### Sintaxis
```
[nombre_columna]:[operador]:[valor]
```

### Operadores Soportados
- `equals`: Coincidencia exacta (sensible a mayúsculas)
- `iequals`: Coincidencia exacta (insensible a mayúsculas)
- `contains`: Contiene texto
- `icontains`: Contiene texto (insensible a mayúsculas)
- `not_equals`: No es igual
- `is_empty`: Celda vacía
- `not_empty`: Celda no vacía
- `greater_than`: Mayor que (números/fechas)
- `less_than`: Menor que (números/fechas)

### Operadores Lógicos
Conectar múltiples condiciones con `AND`, `OR`:
```
Status:equals:Active,AND,Priority:equals:High
Name:contains:john,OR,Email:icontains:example.com
```

## 📊 Ejemplos de Uso

### Consulta Básica
```http
GET /api/v1/smartsheet/sheets/123456/rows?limit=50&offset=100
X-API-Key: your-middleware-api-key
```

### Filtrado por Estado
```http
GET /api/v1/smartsheet/sheets/123456/rows?q=Status:equals:Completed
X-API-Key: your-middleware-api-key
```

### Selección de Campos Específicos
```http
GET /api/v1/smartsheet/sheets/123456/rows?fields=Name,Status,Date&includeAttachments=true
X-API-Key: your-middleware-api-key
```

### Filtrado Complejo
```http
GET /api/v1/smartsheet/sheets/123456/rows?q=Status:equals:Active,AND,Priority:not_equals:Low,OR,Assignee:contains:admin
X-API-Key: your-middleware-api-key
```

## 📋 Formato de Respuesta

```json
{
  "success": true,
  "data": {
    "sheet_id": 123456,
    "total_rows": 250,
    "returned_rows": 50,
    "offset": 0,
    "limit": 50,
    "rows": [
      {
        "id": 987654321,
        "row_number": 1,
        "cells": {
          "Name": "John Doe",
          "Status": "Active",
          "Date": "2025-01-15"
        },
        "attachments": [],
        "created_at": "2025-01-01T10:00:00Z",
        "modified_at": "2025-01-15T14:30:00Z"
      }
    ]
  },
  "filters_applied": "Status:equals:Active",
  "execution_time_ms": 150
}
```

## 🔒 Seguridad

### Autenticación
- **X-API-Key Header**: Requerido para todos los endpoints
- **Token de Smartsheet**: Configurado via variable de entorno
- **Validación de Input**: Todos los parámetros validados con Pydantic

### Variables de Entorno
```bash
SMARTSHEET_ACCESS_TOKEN=VmwRrfCK736jp1j1MBiiFSPTRKVNlVJd5Dx6Y
SMARTSHEET_API_BASE_URL=https://api.smartsheet.com/2.0
MIDDLEWARE_API_KEY=generate_a_strong_secret_key_here
```

## 📊 Monitoreo y Logging

### Sistema de Logs
- **Logs Estructurados**: JSON format para parsing automático
- **Rotación Automática**: 10MB por archivo, 10 archivos de respaldo
- **Logs Específicos**:
  - `logs/app.log` - Logs generales
  - `logs/errors.log` - Solo errores
  - `logs/smartsheet.log` - Operaciones de Smartsheet
  - `logs/api.log` - Peticiones HTTP

### Métricas Prometheus
```
api_requests_total{method,endpoint,status}
api_request_duration_seconds{method,endpoint}
smartsheet_operations_total{operation,status}
smartsheet_active_connections
```

### Integración con Monitoring Stack
- **Prometheus**: Scraping de métricas
- **Grafana**: Dashboards y visualización
- **AlertManager**: Alertas basadas en métricas
- **Logs**: Integración con sistemas de log aggregation

## 🚀 URLs Finales del Servicio

```
GET https://api.dev.entersys.mx/api/v1/smartsheet/sheets/123456/rows
GET https://api.dev.entersys.mx/api/v1/smartsheet/sheets/123456/rows?limit=50&offset=100
GET https://api.dev.entersys.mx/api/v1/smartsheet/sheets/123456/rows?fields=Name,Status,Date
GET https://api.dev.entersys.mx/api/v1/smartsheet/sheets/123456/rows?q=Status:equals:Active
GET https://api.dev.entersys.mx/api/v1/smartsheet/health
GET https://api.dev.entersys.mx/docs (Documentación automática)
```

## 🎯 Consideraciones de Rendimiento

### Optimizaciones
- **Carga en Memoria**: Todas las filas se cargan para filtrado (optimizar para hojas <1000 filas)
- **Paginación Eficiente**: Aplicada después del filtrado
- **Cache de Columnas**: Mapeo de IDs a nombres cacheado
- **Logging Asíncrono**: No bloquea requests

### Limitaciones
- **Memoria**: 4GB RAM - optimizado para hojas medianas
- **Rate Limits**: Respeta límites de API de Smartsheet
- **Concurrent Requests**: Stateless design para múltiples instancias

## 🔧 Mantenimiento

### Health Checks
- Endpoint `/health` para verificar conectividad con Smartsheet
- Validación de tokens y permisos
- Métricas de tiempo de respuesta

### Actualizaciones
- SDK de Smartsheet actualizable independientemente
- Versionado de API mantenido
- Backward compatibility asegurada