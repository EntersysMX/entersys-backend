# app/main.py
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.api.v1.endpoints import health, auth
from app.core.config import settings

app = FastAPI(
    title="Entersys.mx API",
    description="Backend para la gestión de contenido de Entersys.mx con Analytics",
    version="1.0.0"
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