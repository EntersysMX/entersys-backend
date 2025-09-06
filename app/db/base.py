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