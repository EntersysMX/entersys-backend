## 🤖 Prompt para Claude Code - Middleware Smartsheet (Versión Final)

```
Eres un desarrollador experto en Python/FastAPI. Crea un servicio web middleware para la API de Smartsheet siguiendo esta especificación técnica detallada:

## 📋 CONTEXTO Y OBJETIVOS

Desarrollar un middleware RESTful que simplifique y estandarice la comunicación con la API de Smartsheet, integrándose con la infraestructura existente en Google Cloud Platform usando Traefik como proxy reverso.

**Objetivos principales:**
- Simplificar consultas dinámicas a hojas de Smartsheet
- Optimizar rendimiento mediante paginación y selección de campos
- Centralizar la lógica de acceso a Smartsheet
- Integración nativa con arquitectura de contenedores Docker existente

## 🏗️ ARQUITECTURA Y STACK

**Stack Tecnológico:**
- Python 3.11+
- FastAPI (con Pydantic para validación)
- Uvicorn + Gunicorn para producción
- smartsheet-python-sdk (SDK oficial)
- Docker + Docker Compose

**Estructura del Proyecto en el Repositorio:**
```
C:\Web_Entersys\entersys-backend\
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── __init__.py
│   │       │   ├── smartsheet.py          # Endpoints de Smartsheet
│   │       │   └── ...
│   │       ├── __init__.py
│   │       └── api.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── smartsheet_service.py          # Lógica de negocio Smartsheet
│   ├── models/
│   │   ├── __init__.py
│   │   └── smartsheet.py                  # Modelos Pydantic
│   ├── utils/
│   │   ├── __init__.py
│   │   └── query_parser.py                # Parser para filtrado dinámico
│   ├── __init__.py
│   └── main.py
├── requirements.txt (actualizar con nuevas dependencias)
├── docker-compose.yml (actualizar)
└── .env.example (actualizar)
```

## 🛠️ REQUERIMIENTOS FUNCIONALES

### Endpoint Principal
**GET /api/v1/smartsheet/sheets/{sheet_id}/rows**

**IMPORTANTE: La URL completa debe ser `https://api.dev.entersys.mx/api/v1/smartsheet/sheets/{sheet_id}/rows` - NO crear subdominio nuevo**

**Parámetros:**
- `sheet_id` (path, int, requerido): ID de la hoja de Smartsheet
- `limit` (query, int, opcional, default=100): Número máximo de registros
- `offset` (query, int, opcional, default=0): Posición inicial para paginación
- `fields` (query, string, opcional): Columnas a retornar (separadas por comas)
- `includeAttachments` (query, bool, opcional, default=false): Incluir metadatos de adjuntos
- `q` (query, string, opcional): Cadena de filtrado dinámico

### Query Language para Filtrado (parámetro `q`)

**Sintaxis:** `[nombre_columna]:[operador]:[valor]`
**Encadenamiento:** `condición1,LOGICO,condición2,LOGICO,condición3`

**Operadores soportados:**
- `equals`: Coincidencia exacta (sensible a mayúsculas)
- `iequals`: Coincidencia exacta (insensible a mayúsculas)
- `contains`: Contiene el texto
- `icontains`: Contiene el texto (insensible a mayúsculas)
- `not_equals`: No es igual a
- `is_empty`: Celda vacía
- `not_empty`: Celda no vacía
- `greater_than`: Mayor que (números/fechas)
- `less_than`: Menor que (números/fechas)

**Operadores lógicos:** `AND`, `OR`

### Ejemplos de Uso
```
GET /api/v1/smartsheet/sheets/82829292/rows?limit=20
GET /api/v1/smartsheet/sheets/82829292/rows?offset=50&limit=25&fields=Subject,Status
GET /api/v1/smartsheet/sheets/82829292/rows?q=Status:equals:Completed,AND,Priority:equals:High
GET /api/v1/smartsheet/sheets/82829292/rows?q=Assignee:contains:john.doe&includeAttachments=true
```

## 🔧 REQUERIMIENTOS TÉCNICOS

### 1. Integración con Infraestructura Existente
- **URL Base Específica**: `https://api.dev.entersys.mx/api/v1/smartsheet/sheets/{sheet_id}/rows`
- Integrar con la estructura existente del repositorio `entersys-backend`
- Mantener compatibilidad con Traefik y Docker Compose existente
- Variables de entorno para tokens (SMARTSHEET_ACCESS_TOKEN, MIDDLEWARE_API_KEY)
- Autenticación mediante header `X-API-Key` (compatible con sistema existente)

### 2. Actualización de Docker Configuration
**Actualizar docker-compose.yml existente:**
```
# Agregar a los labels de Traefik existentes:
- "traefik.http.routers.entersys-api.rule=Host(`api.dev.entersys.mx`) && PathPrefix(`/api/v1/smartsheet`)"
```

### 3. Variables de Entorno (.env)
Agregar al .env existente:
```
# Smartsheet Configuration
SMARTSHEET_ACCESS_TOKEN=tu_token_secreto_de_smartsheet
SMARTSHEET_API_BASE_URL=https://api.smartsheet.com/2.0
MIDDLEWARE_API_KEY=un_token_secreto_fuerte_para_proteger_el_middleware
```

### 4. Lógica de Procesamiento
1. Conectar con Smartsheet API usando el SDK oficial
2. Obtener todas las filas de la hoja específica (`GET /sheets/{sheetId}`)
3. Aplicar filtros del parámetro `q` en memoria usando el query parser
4. Seleccionar campos específicos (parámetro `fields`)
5. Aplicar paginación (`offset` y `limit`)
6. Incluir metadatos de adjuntos si `includeAttachments=true`

## 📦 DELIVERABLES REQUERIDOS

Actualiza/crea estos archivos siguiendo la estructura existente:

1. **app/api/v1/endpoints/smartsheet.py** - Endpoints FastAPI para Smartsheet
2. **app/services/smartsheet_service.py** - Lógica de negocio y cliente Smartsheet
3. **app/models/smartsheet.py** - Modelos Pydantic para validación
4. **app/utils/query_parser.py** - Parser para el sistema de filtrado dinámico
5. **app/core/config.py** - Actualizar con configuración de Smartsheet
6. **requirements.txt** - Agregar nuevas dependencias (smartsheet-python-sdk)
7. **app/api/v1/api.py** - Incluir los nuevos endpoints
8. **.env.example** - Actualizar con variables de Smartsheet

### Nuevas Dependencias para requirements.txt:
```
smartsheet-python-sdk==3.0.3
```

## 🔧 CONFIGURACIÓN ESPECÍFICA

### Integración con FastAPI existente
```
# En app/api/v1/api.py agregar:
from app.api.v1.endpoints import smartsheet

api_router.include_router(
    smartsheet.router, 
    prefix="/smartsheet", 
    tags=["smartsheet"]
)
```

### Configuración en app/core/config.py
```
# Agregar a la clase Settings:
SMARTSHEET_ACCESS_TOKEN: str = Field(..., env="SMARTSHEET_ACCESS_TOKEN")
SMARTSHEET_API_BASE_URL: str = Field("https://api.smartsheet.com/2.0", env="SMARTSHEET_API_BASE_URL")
MIDDLEWARE_API_KEY: str = Field(..., env="MIDDLEWARE_API_KEY")
```

### Estructura del Endpoint Principal
```
# En app/api/v1/endpoints/smartsheet.py
@router.get("/sheets/{sheet_id}/rows", response_model=SmartsheetRowsResponse)
async def get_sheet_rows(
    sheet_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    fields: Optional[str] = Query(None, description="Comma-separated column names"),
    includeAttachments: bool = Query(False),
    q: Optional[str] = Query(None, description="Query filter string"),
    x_api_key: str = Header(..., alias="X-API-Key"),
    smartsheet_service: SmartsheetService = Depends()
):
    # Implementación aquí
```

## 🎯 CONSIDERACIONES IMPORTANTES

- **URL Routing Específica**: Usar `/api/v1/smartsheet/sheets/{sheet_id}/rows` como endpoint exacto
- **Estructura Existente**: Respetar la arquitectura modular ya implementada
- **Rendimiento**: El middleware carga todas las filas en memoria para filtrado
- **Hardware**: Servidor con 4GB RAM - optimizar uso de memoria para hojas grandes
- **Integración**: Compatible con proxy reverso Traefik existente
- **Escalabilidad**: Diseño stateless para múltiples instancias
- **Logging**: Usar el sistema de logging ya configurado en el proyecto
- **Error Handling**: Manejar errores de Smartsheet API (rate limits, permisos, etc.)

## ✅ CRITERIOS DE ÉXITO

- Endpoint `/sheets/{sheet_id}/rows` integrado correctamente en la estructura FastAPI existente
- Sistema de filtrado dinámico operativo con todos los operadores especificados
- Paginación y selección de campos implementada y funcional
- Autenticación por API Key funcional y compatible con sistema existente
- Integración transparente con Docker Compose existente
- URLs funcionando en `https://api.dev.entersys.mx/api/v1/smartsheet/sheets/{sheet_id}/rows`
- Logging estructurado usando el sistema existente
- Documentación automática de FastAPI disponible en `/docs`
- Manejo robusto de errores y rate limits de Smartsheet API

## 🚀 URLs FINALES ESPERADAS

```
GET https://api.dev.entersys.mx/api/v1/smartsheet/sheets/123456/rows
GET https://api.dev.entersys.mx/api/v1/smartsheet/sheets/123456/rows?limit=50&offset=100
GET https://api.dev.entersys.mx/api/v1/smartsheet/sheets/123456/rows?fields=Name,Status,Date
GET https://api.dev.entersys.mx/api/v1/smartsheet/sheets/123456/rows?q=Status:equals:Active
GET https://api.dev.entersys.mx/docs (documentación actualizada con endpoints de Smartsheet)
```

## 📋 RESPUESTA ESPERADA DEL ENDPOINT

```
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
                "rowNumber": 1,
                "cells": {
                    "Name": "John Doe",
                    "Status": "Active",
                    "Date": "2025-01-15"
                },
                "attachments": [] // solo si includeAttachments=true
            }
        ]
    },
    "filters_applied": "Status:equals:Active",
    "execution_time_ms": 150
}

este es el apikey de smartsheet: VmwRrfCK736jp1j1MBiiFSPTRKVNlVJd5Dx6Y.
agrega los de errores y consultas exitosas en logs de todos los servicios con rotacion de forma que podamos integrarlo a los monitoreos que tiene el servidor con alertmanager, Prometheus y grafana y podmaos crear unos dashboard para obtener sixsigma.
procura no afectar los servicios actuales, solo mejoralos para los logs si crees necesario pero las rutas deben ser las mismas.
Revisa que todos los servicios tengan la seguridad necesaria para sus consumos.
tienes que mantener siempre actualizado el repositorio de github antes de subir al servidor los cambios
documenta esta api para su consumo y modificame el archivo "ARCHITECTURE.md" con esto nuevo.