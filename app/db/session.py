# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Se crea el motor (engine) de SQLAlchemy usando la URI de la configuración.
engine = create_engine(settings.DATABASE_URI)

# Se crea una fábrica de sesiones que se usará para crear sesiones individuales.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)