# app/main.py
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.api.v1.endpoints import health, smartsheet, analytics, crm, metrics, six_sigma_metrics, auth, posts, seo, onboarding, qr, video_security, support
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
    - **Authentication**: Sistema completo de autenticacion (JWT + OAuth Google)
    - **Posts Management**: CRUD de posts y contenido del blog
    - **Smartsheet**: Middleware para API de Smartsheet con filtrado avanzado
    - **Analytics**: Integracion con Matomo para tracking
    - **CRM**: Integracion con Mautic CRM  
    - **Metrics**: Metricas de rendimiento y monitoreo
    - **Six Sigma**: Metricas de calidad empresarial y compliance
    - **Onboarding**: Sistema de validacion QR para certificaciones de seguridad
    - **Support**: Portal de soporte y chatbot inteligente (MD070)
    
    **Authentication Features:**
    - Login tradicional con email/password
    - OAuth 2.0 con Google
    - JWT tokens seguros
    - Sesiones protegidas
    
    **Six Sigma Features:**
    - Monitoreo 99.99966% disponibilidad
    - Alertas proactivas de calidad
    - Reportes ejecutivos de compliance
    - Metricas en tiempo real
    ''',
    version='1.0.0',
    contact={
        'name': 'Entersys Development Team',
        'url': 'https://entersys.mx',
        'email': 'armandocortes@entersys.mx'
    },
    license_info={
        'name': 'Proprietary License',
        'url': 'https://entersys.mx/license'
    },
    openapi_url='/openapi.json',
    docs_url='/docs',
    redoc_url='/redoc'
)

logger.info('Entersys.mx API starting up with complete services suite')

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'https://entersys.mx',
        'https://www.entersys.mx',
        'https://admin.entersys.mx',
        'http://localhost:3000',
        'http://localhost:5173'
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Configurar middleware de sesion (requerido para OAuth)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Six Sigma logging middleware para capturar todas las requests
app.add_middleware(SixSigmaLoggingMiddleware)

# Registrar OAuth Google para autenticacion
auth.oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Incluir rutas - Todos los endpoints disponibles
app.include_router(health.router, prefix='/api/v1', tags=['Health Check'])
app.include_router(auth.router, prefix='/api/v1', tags=['Authentication'])
app.include_router(posts.router, prefix='/api/v1/posts', tags=['Posts Management'])
app.include_router(seo.router, prefix='/api/v1/seo', tags=['SEO & Feeds'])
app.include_router(smartsheet.router, prefix='/api/v1/smartsheet', tags=['Smartsheet'])
app.include_router(analytics.router, prefix='/api/v1/analytics', tags=['Analytics'])
app.include_router(crm.router, prefix='/api/v1/crm', tags=['CRM'])
app.include_router(metrics.router, prefix='/api/v1/metrics', tags=['Metrics'])
app.include_router(six_sigma_metrics.router, prefix='/api/v1', tags=['Six Sigma Quality'])
app.include_router(onboarding.router, prefix='/api/v1/onboarding', tags=['Onboarding Validation'])
app.include_router(qr.router, prefix='/api/v1/qr', tags=['QR Code Generator'])
app.include_router(video_security.router, prefix='/api', tags=['Video Security'])
app.include_router(support.router, prefix='/api/v1/support', tags=['Support & Chatbot'])

@app.get('/')
async def root():
    return {
        'message': 'Bienvenido al Backend de Entersys.mx',
        'status': 'operativo',
        'version': '1.0.0',
        'quality_level': 'six_sigma_enabled',
        'authentication': 'jwt_oauth_enabled',
        'docs': '/docs',
        'available_services': [
            'health', 'auth', 'posts', 'smartsheet', 'analytics', 'crm', 'metrics', 'six-sigma', 'support'
        ],
        'authentication_endpoints': {
            'login_email': '/api/v1/auth/token',
            'login_google': '/api/v1/login/google',
            'google_callback': '/api/v1/auth/google'
        },
        'six_sigma_features': {
            'real_time_metrics': '/api/v1/six-sigma/metrics/current',
            'compliance_report': '/api/v1/six-sigma/compliance/report',
            'active_alerts': '/api/v1/six-sigma/alerts/active'
        }
    }

@app.get('/metrics', include_in_schema=False)
async def prometheus_metrics():
    """Endpoint de metricas para Prometheus"""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
