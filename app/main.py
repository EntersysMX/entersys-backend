# app/main.py
from fastapi import FastAPI
from app.api.v1.endpoints import health

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
    return {"message": "Welcome to the Entersys.mx API"}

# Se incluye el router de health check bajo el prefijo /api/v1
app.include_router(health.router, prefix="/api/v1", tags=["Health Check"])

# Aquí se añadirán los futuros routers para posts, autenticación, etc.