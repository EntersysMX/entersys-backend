# app/scripts/create_admin.py
import logging
from app.db.session import SessionLocal
from app.crud.crud_user import get_user_by_email, create_admin_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Iniciando creación de usuario administrador...")
    db = SessionLocal()
    admin_email = "admin@entersys.mx"
    admin_password = "admin123"

    user = get_user_by_email(db, email=admin_email)
    if not user:
        create_admin_user(db, email=admin_email, password=admin_password)
        logger.info(f"Usuario administrador '{admin_email}' creado exitosamente.")
    else:
        logger.info(f"El usuario administrador '{admin_email}' ya existe.")
    db.close()

if __name__ == "__main__":
    main()