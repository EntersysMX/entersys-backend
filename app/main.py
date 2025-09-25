# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.api.v1.endpoints import health, auth
from app.core.config import settings
from app.core.logging_config import setup_logging
import logging

# Configurar logging al inicio de la aplicación
setup_logging()
logger = logging.getLogger("app")

app = FastAPI(
    title="Entersys.mx API",
    description="""
    ## Backend API para Entersys.mx

    **Servicios Disponibles:**
    - 🏥 **Health Check**: Monitoreo de estado de servicios
    - 🔐 **Authentication**: Autenticación OAuth con Google
    - 📊 **Analytics**: Integración con Matomo para métricas
    - 📧 **CRM**: Integración con Mautic para gestión de leads
    - 🗂️ **Smartsheet Middleware**: API avanzada para consultas dinámicas a Smartsheet

    **Smartsheet API Features:**
    - Filtrado dinámico con 8 operadores (equals, contains, greater_than, etc.)
    - Operadores lógicos (AND, OR) para consultas complejas
    - Paginación y selección de campos
    - Monitoreo con métricas Prometheus
    - Logs estructurados para Six Sigma analytics

    **Documentación adicional:** [API-DOCUMENTATION.md](https://github.com/EntersysMX/entersys-backend/blob/main/API-DOCUMENTATION.md)
    """,
    version="1.0.0",
    contact={
        "name": "Entersys Development Team",
        "url": "https://entersys.mx",
        "email": "armandocortes@entersys.mx"
    },
    license_info={
        "name": "Proprietary License",
        "url": "https://entersys.mx/license"
    }
)

logger.info("Entersys.mx API starting up")

# Configuración de CORS para permitir acceso desde dominios específicos
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dev.entersys.mx",
        "https://entersys.mx",
        "http://localhost:3000",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Se necesita un middleware de sesión para que Authlib funcione
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Registra el cliente OAuth de Google
auth.oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.get("/", tags=["Root"])
def read_root():
    """
    Endpoint raíz para verificar que la API está en línea.
    """
    return {"message": "Welcome to the Entersys.mx API - Analytics Integrated"}

app.include_router(health.router, prefix="/api/v1", tags=["Health Check"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])

# Router de analytics - import con manejo de errores
try:
    from app.api.v1.endpoints.analytics import router as analytics_router
    app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
except ImportError as e:
    print(f"Warning: Could not import analytics router: {e}")

# Router de CRM - import con manejo de errores
try:
    from app.api.v1.endpoints.crm import router as crm_router
    app.include_router(crm_router, prefix="/api/v1/crm", tags=["CRM"])
except ImportError as e:
    print(f"Warning: Could not import CRM router: {e}")

# Router de Smartsheet - import con manejo de errores
try:
    from app.api.v1.endpoints.smartsheet import router as smartsheet_router
    app.include_router(smartsheet_router, prefix="/api/v1/smartsheet", tags=["Smartsheet"])
except ImportError as e:
    print(f"Warning: Could not import Smartsheet router: {e}")