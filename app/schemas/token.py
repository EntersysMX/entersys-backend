from pydantic import BaseModel


class Token(BaseModel):
    """
    Schema para el token de acceso devuelto por la API.
    """
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """
    Schema para el payload del token JWT.
    """
    sub: str = None


class UserLogin(BaseModel):
    """
    Schema para el login del usuario.
    """
    email: str
    password: str