INICIO DEL PROMPT
Rol: Actúa como un Desarrollador Backend Senior experto en FastAPI, SQLAlchemy y sistemas de autenticación OAuth 2.0.
Contexto:
Estás finalizando el Sprint 1 para el proyecto entersys-backend. La base de la aplicación (BD, migraciones, CI/CD) ya está configurada y funcionando. Tu tarea es completar los dos issues de autenticación restantes, basándote en la arquitectura del MD070. 
revisa los archivos que explican como funciona el servidor en la ruta C:\Documentacion Infraestructura.

Ya disponemos de las credenciales de Google OAuth:
GOOGLE_CLIENT_ID: 96894495492-npdg8c8eeh6oqpgkug2vaalle8krm0so.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET: 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
Objetivo Principal:
Implementar la lógica de negocio completa para los dos flujos de autenticación requeridos:
Issue #11: Un login funcional con email/contraseña que devuelve un token JWT.
Issue #12: Un flujo de login con Google (OAuth 2.0) que crea o autentica a un usuario y devuelve un token JWT.
Requerimientos Detallados:
Sigue los siguientes pasos en orden. Iniciaremos creando una nueva rama de Git para encapsular todo el trabajo. El código debe ser de calidad de producción, robusto y seguro.
Fase 0: Preparación del Entorno de Desarrollo
Acción 0.1: Sincronizar y Crear una Nueva Rama
Ejecuta los siguientes comandos en la terminal, en la raíz de tu repositorio local.
# Asegúrate de estar en la rama principal y tener los últimos cambios
git checkout main
git pull origin main

# Crea y cambia a una nueva rama para las funcionalidades del Sprint 1
git checkout -b feature/sprint-1-auth-completion


Issue #11: Completar la Autenticación con JWT (Email/Contraseña)
Paso 11.1: Crear la Capa de Acceso a Datos para Usuarios (CRUD)
Crea un nuevo archivo app/crud/crud_user.py con el siguiente contenido.
# app/crud/crud_user.py
from sqlalchemy.orm import Session
from app.models.blog import AdminUser
from app.core.security import get_password_hash

def get_user_by_email(db: Session, email: str):
    return db.query(AdminUser).filter(AdminUser.email == email).first()

def create_admin_user(db: Session, email: str, password: str):
    hashed_password = get_password_hash(password)
    db_user = AdminUser(email=email, hashed_password=hashed_password, is_active=True)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


Paso 11.2: Crear un Script para el Primer Usuario Administrador
Crea un nuevo archivo app/scripts/create_admin.py.
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


Paso 11.3: Completar la Lógica del Endpoint de Autenticación
Reemplaza el contenido del archivo app/api/v1/endpoints/auth.py con esta versión completa.
# app/api/v1/endpoints/auth.py
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core import security
from app.crud import crud_user
from app.schemas.token import Token
from app.core.config import settings
from authlib.integrations.starlette_client import OAuth

router = APIRouter()
oauth = OAuth()

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
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


Issue #12: Completar la Autenticación con Google (OAuth 2.0)
Paso 12.1: Añadir Dependencia y Actualizar Configuración
Añade Authlib a tu requirements.txt.
Añade las credenciales de Google a tu .env.example.
# .env.example
# ... (JWT Settings) ...

# --- Google OAuth Settings ---
GOOGLE_CLIENT_ID=96894495492-npdg8c8eeh6oqpgkug2vaalle8krm0so.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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


Añade las variables a app/core/config.py.
# app/core/config.py
# ...
class Settings(BaseSettings):
    # ... (JWT Settings) ...

    # --- Google OAuth Settings ---
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
# ...


Paso 12.2: Configurar el Cliente OAuth en main.py
Modifica tu app/main.py para registrar el cliente de Google al iniciar la aplicación.
# app/main.py
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.api.v1.endpoints import health, auth
from app.core.config import settings

app = FastAPI(title="Entersys.mx API")

# Se necesita un middleware de sesión para que Authlib funcione
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Registra el cliente OAuth de Google
auth.oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='[https://accounts.google.com/.well-known/openid-configuration](https://accounts.google.com/.well-known/openid-configuration)',
    client_kwargs={'scope': 'openid email profile'}
)

# ... (resto de main.py) ...
app.include_router(health.router, prefix="/api/v1", tags=["Health Check"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])


Paso 12.3: Implementar las Rutas de Google en auth.py
Añade el siguiente código al final de tu archivo app/api/v1/endpoints/auth.py.
# app/api/v1/endpoints/auth.py
# ... (código anterior) ...

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
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


Fase Final: Guardar, Sincronizar y Verificar
Acción Final.1: Hacer Commit de los Cambios
# Instala las nuevas dependencias en tu entorno local
pip install -r requirements.txt

# Añade todos los archivos nuevos y modificados
git add .

# Crea un commit con un mensaje descriptivo
git commit -m "feat(auth): Complete Sprint 1 - JWT and Google OAuth login"


Acción Final.2: Subir la Nueva Rama a GitHub
# Sube tu nueva rama a GitHub
git push origin feature/sprint-1-auth-completion


Acción Final.3: Crear un Pull Request
Ve a tu repositorio en GitHub, crea un Pull Request desde feature/sprint-1-auth-completion hacia main, y fusiónalo.
Acción Final.4: Verificar en el Servidor de Desarrollo
Una vez que el despliegue automático de CI/CD termine, ejecuta los siguientes pasos para verificar:
Crea el usuario administrador en el servidor:
ssh ajcortest@34.134.14.202 "docker exec entersys-content-api python -m app.scripts.create_admin"


Prueba el login con email/contraseña:
curl -X POST -d "username=admin@entersys.mx&password=admin123" [https://api.dev.entersys.mx/api/v1/auth/token](https://api.dev.entersys.mx/api/v1/auth/token)


Prueba el login con Google: Abre https://api.dev.entersys.mx/api/v1/login/google en tu navegador y completa el flujo de autenticación de Google.
FIN DEL PROMPT MEJORADO
