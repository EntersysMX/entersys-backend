# app/schemas/video_security.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class HeartbeatRequest(BaseModel):
    """Schema para el registro de heartbeat de video."""
    user_id: int = Field(..., description="ID del usuario que está viendo el video")
    video_id: str = Field(..., max_length=50, description="Identificador único del video")
    seconds_watched: float = Field(..., ge=0, description="Segundos acumulados desde el último heartbeat")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "video_id": "seguridad-2024",
                "seconds_watched": 5.0
            }
        }


class HeartbeatResponse(BaseModel):
    """Schema para la respuesta del heartbeat."""
    success: bool
    total_seconds: float = Field(..., description="Total de segundos acumulados")
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_seconds": 125.5,
                "message": "Progreso registrado correctamente"
            }
        }


class ValidationRequest(BaseModel):
    """Schema para la solicitud de validación de completitud."""
    user_id: int = Field(..., description="ID del usuario")
    video_id: str = Field(..., max_length=50, description="Identificador único del video")
    video_duration: float = Field(..., gt=0, description="Duración total del video en segundos")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "video_id": "seguridad-2024",
                "video_duration": 600.0
            }
        }


class ValidationResponse(BaseModel):
    """Schema para la respuesta de validación de completitud."""
    authorized: bool = Field(..., description="Si el usuario está autorizado para acceder al examen")
    exam_url: Optional[str] = Field(None, description="URL del examen si está autorizado")
    progress_percentage: float = Field(..., description="Porcentaje de video visualizado")
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "authorized": True,
                "exam_url": "https://forms.entersys.mx/examen-seguridad",
                "progress_percentage": 95.5,
                "message": "Acceso autorizado al examen"
            }
        }


class ProgressResponse(BaseModel):
    """Schema para consultar el progreso actual."""
    user_id: int
    video_id: str
    seconds_accumulated: float
    last_updated: Optional[datetime]

    class Config:
        from_attributes = True
