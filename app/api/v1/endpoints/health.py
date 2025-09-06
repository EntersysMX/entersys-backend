# app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import SessionLocal

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

@router.get("/health", summary="Verifica el estado del servicio y la base de datos")
def check_health(db: Session = Depends(get_db)):
    """
    Endpoint de Health Check.
    Verifica que la API está activa y que puede conectarse a la base de datos.
    """
    try:
        # Ejecuta una consulta simple para verificar la conexión a la BD
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database_connection": "ok"}
    except Exception:
        # Si la conexión a la BD falla, devuelve un error 503 Service Unavailable
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "database_connection": "failed"}
        )