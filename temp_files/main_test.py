#!/usr/bin/env python3
"""
Test version of main.py for local development with SQLite
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from datetime import datetime, timedelta
import logging

# Import our auth modules
from app.core.config_test import test_settings
from app.core import security
from app.schemas.token import Token

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Entersys.mx API - Test Version", version="1.0.0-test")

# Configuración de CORS para permitir acceso desde cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=test_settings.SECRET_KEY)

# OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=test_settings.GOOGLE_CLIENT_ID,
    client_secret=test_settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Database setup for testing
TestBase = declarative_base()

class TestAdminUser(TestBase):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

engine = create_engine(test_settings.DATABASE_URI, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
TestBase.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_by_email(db: Session, email: str):
    return db.query(TestAdminUser).filter(TestAdminUser.email == email).first()

def create_admin_user_if_not_exists():
    """Create admin user if it doesn't exist"""
    db = SessionLocal()
    try:
        admin_email = "admin@entersys.mx"
        user = get_user_by_email(db, admin_email)
        if not user:
            logger.info(f"Creating admin user: {admin_email}")
            hashed_password = security.get_password_hash("admin123")
            db_user = TestAdminUser(
                email=admin_email,
                hashed_password=hashed_password,
                is_active=True
            )
            db.add(db_user)
            db.commit()
            logger.info("Admin user created successfully!")
    finally:
        db.close()

# Create admin user on startup
create_admin_user_if_not_exists()

@app.get("/", tags=["Root"])
def read_root():
    """Root endpoint"""
    return {"message": "Entersys.mx Test API - Authentication Ready", "version": "1.0.0-test"}

@app.get("/api/v1/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/v1/auth/token", response_model=Token, tags=["Authentication"])
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """JWT Authentication with email and password"""
    user = get_user_by_email(db, email=form_data.username)
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    access_token_expires = timedelta(minutes=test_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get('/api/v1/login/google', tags=["Authentication"])
async def login_via_google(request: Request):
    """Redirect to Google OAuth"""
    redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, str(redirect_uri))

@app.get('/api/v1/auth/google', response_model=Token, tags=["Authentication"])
async def auth_via_google(request: Request, db: Session = Depends(get_db)):
    """Google OAuth callback"""
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
    
    user = get_user_by_email(db, email=user_data['email'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"El usuario con email {user_data['email']} no está autorizado."
        )

    access_token_expires = timedelta(minutes=test_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting test server on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")