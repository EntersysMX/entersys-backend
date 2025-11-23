from typing import TYPE_CHECKING, Optional
from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password

if TYPE_CHECKING:
    from app.models.blog import AdminUser


def get_user_by_email(db: Session, email: str) -> Optional["AdminUser"]:
    """
    Obtiene un usuario por su email.
    """
    from app.models.blog import AdminUser
    return db.query(AdminUser).filter(AdminUser.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional["AdminUser"]:
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


def create_user(db: Session, email: str, password: str) -> "AdminUser":
    """
    Crea un nuevo usuario administrador.
    """
    from app.models.blog import AdminUser
    hashed_password = get_password_hash(password)
    db_user = AdminUser(
        email=email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_admin_user(db: Session, email: str, full_name: str = None, password: str = None, hashed_password: str = None):
    """
    Crear un nuevo usuario administrador.
    Puede aceptar password plano O hashed_password (no ambos).
    """
    from app.models.blog import AdminUser

    if hashed_password is None:
        if password is None:
            raise ValueError("Debe proporcionar password o hashed_password")
        hashed_password = get_password_hash(password)

    db_user = AdminUser(
        email=email,
        full_name=full_name or email.split('@')[0],  # Usar email como fallback
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user