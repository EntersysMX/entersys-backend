# app/schemas/onboarding_schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class OnboardingGenerateRequest(BaseModel):
    """
    Schema para la solicitud de generación de QR desde Smartsheet Bridge.
    """
    row_id: int = Field(..., description="ID de la fila en Smartsheet", gt=0)
    full_name: str = Field(..., description="Nombre completo del usuario", min_length=1, max_length=255)
    email: EmailStr = Field(..., description="Correo electrónico del usuario")
    score: float = Field(..., description="Puntaje de evaluación del usuario", ge=0, le=100)

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Valida y limpia el nombre completo"""
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "row_id": 123456789,
                "full_name": "Juan Pérez García",
                "email": "juan.perez@empresa.com",
                "score": 85.5
            }
        }


class OnboardingGenerateResponse(BaseModel):
    """
    Schema para la respuesta de generación de QR exitosa.
    """
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo del resultado")
    data: Optional["OnboardingGenerateData"] = Field(None, description="Datos de la generación")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "QR code generated and sent successfully",
                "data": {
                    "cert_uuid": "550e8400-e29b-41d4-a716-446655440000",
                    "expiration_date": "2026-01-15",
                    "email_sent": True,
                    "smartsheet_updated": True
                }
            }
        }


class OnboardingGenerateData(BaseModel):
    """
    Datos específicos de la generación de QR.
    """
    cert_uuid: str = Field(..., description="UUID del certificado generado")
    expiration_date: str = Field(..., description="Fecha de vencimiento del certificado")
    email_sent: bool = Field(..., description="Indica si el email fue enviado")
    smartsheet_updated: bool = Field(..., description="Indica si Smartsheet fue actualizado")


class OnboardingValidateResponse(BaseModel):
    """
    Schema para la respuesta de validación de QR (principalmente para documentación).
    En la práctica, este endpoint redirige al usuario.
    """
    valid: bool = Field(..., description="Indica si el certificado es válido")
    message: str = Field(..., description="Mensaje descriptivo del resultado")
    redirect_url: str = Field(..., description="URL a la que se redirige")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "message": "Certificate is valid",
                "redirect_url": "https://entersys.mx/certificacion-seguridad/550e8400-e29b-41d4-a716-446655440000"
            }
        }


class CertificateInfo(BaseModel):
    """
    Información del certificado almacenada en Smartsheet.
    """
    row_id: int = Field(..., description="ID de la fila en Smartsheet")
    cert_uuid: str = Field(..., description="UUID del certificado")
    full_name: str = Field(..., description="Nombre completo del titular")
    email: str = Field(..., description="Correo electrónico del titular")
    score: float = Field(..., description="Puntaje de evaluación")
    expiration_date: datetime = Field(..., description="Fecha de vencimiento")
    qr_sent: bool = Field(False, description="Indica si el QR fue enviado")
    last_validation: Optional[datetime] = Field(None, description="Última fecha de validación")


class OnboardingErrorResponse(BaseModel):
    """
    Schema para respuestas de error.
    """
    success: bool = Field(False, description="Siempre False para errores")
    error: str = Field(..., description="Código de error")
    message: str = Field(..., description="Mensaje descriptivo del error")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "SCORE_TOO_LOW",
                "message": "Score must be >= 80 to generate certificate. Current score: 75.0"
            }
        }


# Rebuild models to handle forward references
OnboardingGenerateResponse.model_rebuild()
