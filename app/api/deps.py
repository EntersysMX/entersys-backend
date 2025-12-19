from typing import Generator
from app.db.session import SessionLocal

def get_db() -> Generator:
    """
    Dependency para obtener la sesión de base de datos.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
