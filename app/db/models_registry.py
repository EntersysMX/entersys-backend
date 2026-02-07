# app/db/models_registry.py
# Este archivo importa todos los modelos para que Alembic pueda detectarlos
# Se importa en alembic/env.py

from app.db.base import Base
from app.models.blog import AdminUser, BlogPost
from app.models.exam import ExamCategory, ExamQuestion

# Exportar Base para uso en Alembic
__all__ = ["Base", "AdminUser", "BlogPost", "ExamCategory", "ExamQuestion"]