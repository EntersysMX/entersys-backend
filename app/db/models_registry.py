# app/db/models_registry.py
# Este archivo importa todos los modelos para que Alembic pueda detectarlos
# Se importa en alembic/env.py

from app.db.base import Base
from app.models.blog import AdminUser, BlogPost

# Exportar Base para uso en Alembic
__all__ = ["Base", "AdminUser", "BlogPost"]