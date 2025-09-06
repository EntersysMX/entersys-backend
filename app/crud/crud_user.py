from sqlalchemy.orm import Session
from app.models.blog import AdminUser
from app.core.security import get_password_hash, verify_password


def get_user_by_email(db: Session, email: str) -> AdminUser:
    """
    Obtiene un usuario por su email.
    """
    return db.query(AdminUser).filter(AdminUser.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> AdminUser:
    """
    Autentica un usuario verificando email y contraseña.
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def create_user(db: Session, email: str, password: str) -> AdminUser:
    """
    Crea un nuevo usuario administrador.
    """
    hashed_password = get_password_hash(password)
    db_user = AdminUser(
        email=email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user