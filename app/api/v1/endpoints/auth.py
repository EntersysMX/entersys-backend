# app/api/v1/endpoints/auth.py
from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import secrets

from app.db.session import SessionLocal
from app.core import security
from app.crud import crud_user
from app.schemas.token import Token
from app.core.config import settings
from app.core.email import send_password_reset_email
from authlib.integrations.starlette_client import OAuth

router = APIRouter()
oauth = OAuth()

# Schemas para registro y recuperación
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/auth/token", response_model=Token, summary="Autenticación con Email y Contraseña")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = crud_user.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get('/login/google', summary="Iniciar login con Google")
async def login_via_google(request: Request):
    redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, str(redirect_uri))

@router.get('/auth/google', response_model=Token, summary="Callback de autenticación de Google")
async def auth_via_google(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'No se pudo obtener el token de acceso de Google: {e}',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    
    user_data = token.get('userinfo')
    if not user_data or not user_data.get('email'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No se pudo obtener la información del usuario de Google',
        )
    
    user = crud_user.get_user_by_email(db, email=user_data['email'])
    if not user:
        # Por ahora, solo permitimos el login de usuarios administradores ya existentes.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"El usuario con email {user_data['email']} no está autorizado."
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/register", summary="Registrar nuevo usuario")
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Crear un nuevo usuario administrador.
    """
    # Verificar si el usuario ya existe
    existing_user = crud_user.get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado",
        )

    # Validar contraseña
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 8 caracteres",
        )

    # Crear usuario
    try:
        hashed_password = security.get_password_hash(user_data.password)
        new_user = crud_user.create_admin_user(
            db,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password
        )
        return {
            "message": "Usuario creado exitosamente",
            "email": new_user.email,
            "full_name": new_user.full_name
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear usuario: {str(e)}",
        )


@router.post("/auth/forgot-password", summary="Solicitar restablecimiento de contraseña")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Enviar email para restablecer contraseña.
    Genera un token de recuperación y envía email con el enlace.
    """
    user = crud_user.get_user_by_email(db, email=request.email)

    # Por seguridad, siempre retornamos éxito aunque el usuario no exista
    # Esto previene que se pueda enumerar usuarios válidos
    if not user:
        return {"message": "Si el email existe, recibirás instrucciones para restablecer tu contraseña"}

    # Generar token seguro
    reset_token = secrets.token_urlsafe(32)
    
    # Establecer expiración del token (24 horas)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    # Guardar token en la base de datos
    user.reset_token = reset_token
    user.reset_token_expires = expires_at
    db.commit()
    
    # Enviar email
    try:
        send_password_reset_email(email_to=user.email, token=reset_token)
    except Exception as e:
        # Log el error pero no revelamos al usuario que falló
        print(f"Error al enviar email: {e}")
    
    return {"message": "Si el email existe, recibirás instrucciones para restablecer tu contraseña"}


@router.post("/auth/reset-password", summary="Restablecer contraseña con token")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Restablecer contraseña usando token de recuperación.
    """
    # Buscar usuario por token
    from app.models.blog import AdminUser
    user = db.query(AdminUser).filter(AdminUser.reset_token == request.token).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado",
        )
    
    # Verificar si el token ha expirado
    if not user.reset_token_expires or user.reset_token_expires < datetime.now(timezone.utc):
        # Limpiar token expirado
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado",
        )
    
    # Validar nueva contraseña
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 8 caracteres",
        )
    
    # Actualizar contraseña
    user.hashed_password = security.get_password_hash(request.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return {"message": "Contraseña restablecida exitosamente"}
