# app/main.py
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.api.v1.endpoints import health, auth
from app.core.config import settings

app = FastAPI(title="Entersys.mx API")

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

app.include_router(health.router, prefix="/api/v1", tags=["Health Check"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])