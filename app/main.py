# app/main.py
from fastapi import FastAPI
from app.api.v1.endpoints import health, auth, posts

app = FastAPI(
    title="Entersys.mx API",
    description="Backend para la gestión de contenido de Entersys.mx",
    version="1.0.0"
)

@app.get("/", tags=["Root"])
def read_root():
    """
    Endpoint raíz para verificar que la API está en línea.
    """
    return {"message": "Welcome to the Entersys.mx API - JWT Auth Ready"}

# Se incluye el router de health check bajo el prefijo /api/v1
app.include_router(health.router, prefix="/api/v1", tags=["Health Check"])

# Router de autenticación
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

# Router de posts del blog
app.include_router(posts.router, prefix="/api/v1/posts", tags=["Blog Posts"])