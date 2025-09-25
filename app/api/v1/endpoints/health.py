# app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import SessionLocal
from datetime import datetime
import os

router = APIRouter()

def get_db():
    """
    Función de dependencia para obtener una sesión de base de datos.
    Asegura que la sesión se cierre siempre después de la petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_smartsheet_service():
    """
    Verifica el estado del servicio Smartsheet.
    """
    try:
        # Verificar que las variables de entorno están configuradas
        if not os.getenv("SMARTSHEET_ACCESS_TOKEN"):
            return {"status": "misconfigured", "message": "SMARTSHEET_ACCESS_TOKEN not found"}

        if not os.getenv("MIDDLEWARE_API_KEY"):
            return {"status": "misconfigured", "message": "MIDDLEWARE_API_KEY not found"}

        # Verificar que el módulo smartsheet se puede importar
        try:
            import smartsheet
            return {"status": "ready", "sdk_version": "3.0.3"}
        except ImportError:
            return {"status": "unavailable", "message": "Smartsheet SDK not installed"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/health", summary="Verifica el estado completo del servicio")
def check_health(db: Session = Depends(get_db)):
    """
    Endpoint de Health Check consolidado.
    Verifica que la API está activa, la conexión a base de datos y todos los servicios disponibles.
    """
    health_status = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "database": {"status": "unknown"},
            "smartsheet": {"status": "unknown"},
        }
    }

    # Verificar conexión a base de datos
    try:
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"

    # Verificar servicio Smartsheet
    smartsheet_status = check_smartsheet_service()
    health_status["services"]["smartsheet"] = smartsheet_status

    if smartsheet_status["status"] not in ["ready", "healthy"]:
        if health_status["status"] == "ok":
            health_status["status"] = "degraded"

    # Determinar status global
    if health_status["services"]["database"]["status"] == "unhealthy":
        health_status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=health_status)

    return health_status