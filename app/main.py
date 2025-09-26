# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.api.v1.endpoints import health, smartsheet, analytics, crm, metrics, six_sigma_metrics
from app.core.config import settings
from app.core.logging_config import setup_logging
from middleware.request_logging import SixSigmaLoggingMiddleware
import logging

# Configurar logging al inicio de la aplicacion
setup_logging()
logger = logging.getLogger('app')

app = FastAPI(
    title='Entersys.mx API',
    description='''
    ## Backend API para Entersys.mx
    
    **Servicios Disponibles:**
    - **Health Check**: Monitoreo de estado de servicios
    - **Smartsheet**: Middleware para API de Smartsheet con filtrado avanzado
    - **Analytics**: Integracion con Matomo para tracking
    - **CRM**: Integracion con Mautic CRM  
    - **Metrics**: Metricas de rendimiento y monitoreo
    - **Six Sigma**: Metricas de calidad empresarial y compliance
    
    **Six Sigma Features:**
    - Monitoreo 99.99966% disponibilidad
    - Alertas proactivas de calidad
    - Reportes ejecutivos de compliance
    - Metricas en tiempo real
    ''',
    version='1.0.0',
    openapi_url='/openapi.json',
    docs_url='/docs',
    redoc_url='/redoc'
)

logger.info('Entersys.mx API starting up with Six Sigma monitoring')

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Configurar middleware de sesion (requerido para OAuth)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Six Sigma logging middleware para capturar todas las requests
app.add_middleware(SixSigmaLoggingMiddleware)

# Incluir rutas - Todos los endpoints disponibles
app.include_router(health.router, prefix='/api/v1', tags=['Health Check'])
app.include_router(smartsheet.router, prefix='/api/v1/smartsheet', tags=['Smartsheet'])
app.include_router(analytics.router, prefix='/api/v1/analytics', tags=['Analytics'])
app.include_router(crm.router, prefix='/api/v1/crm', tags=['CRM'])
app.include_router(metrics.router, prefix='/api/v1/metrics', tags=['Metrics'])
app.include_router(six_sigma_metrics.router, prefix='/api/v1', tags=['Six Sigma Quality'])

@app.get('/')
async def root():
    return {
        'message': 'Bienvenido al Backend de Entersys.mx',
        'status': 'operativo',
        'version': '1.0.0',
        'quality_level': 'six_sigma_enabled',
        'docs': '/docs',
        'available_services': [
            'health', 'smartsheet', 'analytics', 'crm', 'metrics', 'six-sigma'
        ],
        'six_sigma_features': {
            'real_time_metrics': '/api/v1/six-sigma/metrics/current',
            'compliance_report': '/api/v1/six-sigma/compliance/report',
            'active_alerts': '/api/v1/six-sigma/alerts/active'
        }
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
