INICIO DEL PROMPT

Rol: Actúa como un Arquitecto de Software y Desarrollador Backend Senior con experiencia en arquitecturas modernas basadas en contenedores y microservicios.

Contexto: Estás a cargo de iniciar el desarrollo del nuevo backend para Entersys.mx. La arquitectura técnica ya ha sido definida en el documento MD070 y se alinea con el manual de infraestructura SCRAM-Infrastructure-Manual.md. El stack tecnológico principal es FastAPI, SQLAlchemy 2.0, PostgreSQL, Docker y Traefik. Ya existe un repositorio en GitHub para este proyecto: https://github.com/EntersysMX/entersys-backend.

Objetivo Principal: Generar la estructura completa de directorios, el código fuente fundacional y los archivos de configuración de despliegue para la aplicación entersys-backend. El resultado final debe ser un conjunto de archivos listos para ser subidos (commit y push) al repositorio de GitHub.

Requerimientos Detallados:

Debes crear todos los archivos que se especifican a continuación, con el contenido exacto proporcionado. La estructura debe ser modular, escalable y seguir las mejores prácticas de la industria.

Fase 1: Estructura de Directorios y Código Fuente
1.1. Crea la siguiente estructura de directorios en la raíz del proyecto:

entersys-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   ├── core/
│   ├── db/
│   ├── models/
└── .github/
    └── workflows/
1.2. Genera los siguientes archivos de código fuente:

Archivo: app/core/config.py

Propósito: Gestionar la configuración de la aplicación desde variables de entorno usando Pydantic, asegurando una configuración robusta y validada.

Python

# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, computed_field

class Settings(BaseSettings):
    """
    Gestiona la configuración de la aplicación cargando variables de entorno.
    Utiliza Pydantic para la validación de tipos.
    """
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_case=True, extra="ignore"
    )

    # Variables de la base de datos leídas desde el archivo .env
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @computed_field
    @property
    def DATABASE_URI(self) -> str:
        """
        Genera la URI de conexión a la base de datos en formato SQLAlchemy.
        Pydantic validará que la URI construida sea correcta.
        """
        dsn = PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=f"/{self.POSTGRES_DB}",
        )
        return str(dsn)

# Instancia única de la configuración que será usada en toda la aplicación.
settings = Settings()
Archivo: app/db/session.py

Propósito: Centralizar la creación del motor (engine) y la fábrica de sesiones (SessionLocal) de SQLAlchemy para toda la aplicación.

Python

# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Se crea el motor (engine) de SQLAlchemy usando la URI de la configuración.
engine = create_engine(settings.DATABASE_URI)

# Se crea una fábrica de sesiones que se usará para crear sesiones individuales.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Archivo: app/db/base.py

Propósito: Definir la clase Base declarativa de la cual heredarán todos los modelos. Es el punto de entrada para que Alembic descubra los modelos.

Python

# app/db/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Clase base declarativa de la cual heredarán todos los modelos de la base de datos.
    """
    pass

# Es crucial importar todos los modelos aquí para que la clase Base
# los registre y Alembic pueda detectarlos automáticamente.
from app.models.blog import AdminUser, BlogPost
Archivo: app/models/blog.py

Propósito: Definir los modelos de SQLAlchemy que se mapean a las tablas admin_users y blog_posts según la arquitectura MD070.

Python

# app/models/blog.py
import enum
from sqlalchemy import (
    Boolean, Column, Integer, String, Text, ForeignKey,
    TIMESTAMP, Enum as SAEnum, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base

class PostStatusEnum(enum.Enum):
    draft = "draft"
    published = "published"

class AdminUser(Base):
    __tablename__ = 'admin_users'
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, server_default='true', nullable=False)
    posts = relationship("BlogPost", back_populates="author", cascade="all, delete-orphan")

class BlogPost(Base):
    __tablename__ = 'blog_posts'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    content = Column(Text)
    author_id = Column(Integer, ForeignKey('admin_users.id', ondelete='RESTRICT'), nullable=False)
    status = Column(
        SAEnum(PostStatusEnum, name='post_status_enum', create_type=False),
        nullable=False, server_default=PostStatusEnum.draft.value
    )
    published_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
    meta_description = Column(String(300))
    faq_json = Column(JSONB)
    author = relationship("AdminUser", back_populates="posts")
Archivo: app/api/v1/endpoints/health.py

Propósito: Implementar un endpoint de health check que verifique la conectividad con la base de datos, esencial para el monitoreo.

Python

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
Archivo: app/main.py

Propósito: El punto de entrada de la aplicación FastAPI. Configura la app e incluye los routers de la API.

Python

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
Fase 2: Archivos de Configuración y Despliegue
Archivo: requirements.txt

Propósito: Definir explícitamente todas las dependencias de Python para asegurar builds consistentes.

Plaintext

# requirements.txt
# FastAPI y Servidores
fastapi
uvicorn
gunicorn

# Base de Datos y ORM
sqlalchemy==2.0.31
psycopg2-binary
alembic

# Configuración
pydantic-settings
python-dotenv
Archivo: .env.example

Propósito: Servir como plantilla para las variables de entorno, evitando subir secretos al repositorio.

Fragmento de código

# .env.example
# Este archivo es una plantilla. Copiar a .env y rellenar los valores.
# NO subir el archivo .env a Git.

# --- Configuración de la Base de Datos ---
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
Archivo: Dockerfile

Propósito: La "receta" para construir una imagen de contenedor optimizada y reproducible para la aplicación.

Dockerfile

# Dockerfile
# Etapa 1: Imagen base de Python, optimizada y segura.
FROM python:3.11-slim

# Establecer variables de entorno para buenas prácticas en producción.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Crear y establecer el directorio de trabajo.
WORKDIR /app

# Copiar el archivo de dependencias primero para aprovechar el cache de Docker.
COPY requirements.txt .

# Instalar las dependencias de Python.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar todo el código de la aplicación (la carpeta 'app').
COPY ./app /app/app

# Comando para ejecutar la aplicación en producción.
# Gunicorn gestiona los workers de Uvicorn para un rendimiento robusto.
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "app.main:app"]
Archivo: docker-compose.yml

Propósito: Orquestar el despliegue del contenedor y configurarlo para que sea descubierto automáticamente por Traefik.

YAML

# docker-compose.yml
version: '3.9'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: dev-entersys-backend
    restart: unless-stopped
    
    # Cargar variables de entorno desde el archivo .env
    env_file:
      - .env
      
    # Conectar a la red externa de Traefik
    networks:
      - traefik_network
      
    # Etiquetas para la auto-configuración de Traefik (Descubrimiento de servicios)
    labels:
      - "traefik.enable=true"
      # Regla: Enrutar si el Host es api.dev.entersys.mx
      - "traefik.http.routers.entersys-backend-dev.rule=Host(`api.dev.entersys.mx`)"
      # Punto de entrada: usar el puerto 443 (HTTPS)
      - "traefik.http.routers.entersys-backend-dev.entrypoints=websecure"
      # Certificado SSL: Usar Let's Encrypt para obtenerlo
      - "traefik.http.routers.entersys-backend-dev.tls.certresolver=letsencrypt"
      # Servicio: Indicar a Traefik que el puerto interno de la app es 8000
      - "traefik.http.services.entersys-backend-dev.loadbalancer.server.port=8000"

networks:
  # Definir que usaremos la red 'traefik' que ya existe en el host
  traefik_network:
    name: traefik
    external: true
Conclusión de la Tarea:

Una vez generados todos estos archivos, el repositorio contendrá una base de código FastAPI completa, profesional y lista para el despliegue. El siguiente paso será subir estos archivos a GitHub.

FIN DEL PROMPT