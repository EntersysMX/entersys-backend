# app/api/v1/endpoints/video_security.py
"""
Endpoints para el módulo de validación de seguridad de video (MD050).
Implementa el sistema Heartbeat anti-skipping.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import logging

from app.db.session import get_db
from app.models.video_progress import UserVideoProgress
from app.schemas.video_security import (
    HeartbeatRequest,
    HeartbeatResponse,
    ValidationRequest,
    ValidationResponse,
    ProgressResponse
)

router = APIRouter()
logger = logging.getLogger('app.video_security')

# Configuración del módulo
COMPLETION_THRESHOLD = 0.90  # 90% del video debe ser visualizado
EXAM_URL = "https://forms.entersys.mx/examen-seguridad"


@router.post(
    "/video-heartbeat",
    response_model=HeartbeatResponse,
    summary="Registrar heartbeat de video",
    description="Registra el progreso incremental de visualización del video cada 5 segundos."
)
async def register_heartbeat(
    request: HeartbeatRequest,
    db: Session = Depends(get_db)
):
    """
    Registra el progreso de visualización del video.

    - **user_id**: ID del usuario
    - **video_id**: Identificador del video
    - **seconds_watched**: Segundos visualizados desde el último heartbeat
    """
    try:
        # Buscar progreso existente
        progress = db.query(UserVideoProgress).filter(
            and_(
                UserVideoProgress.user_id == request.user_id,
                UserVideoProgress.video_id == request.video_id
            )
        ).first()

        if progress:
            # Actualizar progreso existente
            progress.seconds_accumulated += request.seconds_watched
            progress.last_updated = datetime.utcnow()
        else:
            # Crear nuevo registro de progreso
            progress = UserVideoProgress(
                user_id=request.user_id,
                video_id=request.video_id,
                seconds_accumulated=request.seconds_watched
            )
            db.add(progress)

        db.commit()
        db.refresh(progress)

        logger.info(
            f"Heartbeat registrado: user={request.user_id}, "
            f"video={request.video_id}, total={progress.seconds_accumulated}s"
        )

        return HeartbeatResponse(
            success=True,
            total_seconds=progress.seconds_accumulated,
            message="Progreso registrado correctamente"
        )

    except Exception as e:
        logger.error(f"Error registrando heartbeat: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar progreso: {str(e)}"
        )


@router.post(
    "/validate-completion",
    response_model=ValidationResponse,
    summary="Validar completitud del video",
    description="Verifica si el usuario ha visualizado al menos el 90% del video para desbloquear el examen."
)
async def validate_completion(
    request: ValidationRequest,
    db: Session = Depends(get_db)
):
    """
    Valida si el usuario puede acceder al examen.

    - **user_id**: ID del usuario
    - **video_id**: Identificador del video
    - **video_duration**: Duración total del video en segundos
    """
    try:
        # Buscar progreso del usuario
        progress = db.query(UserVideoProgress).filter(
            and_(
                UserVideoProgress.user_id == request.user_id,
                UserVideoProgress.video_id == request.video_id
            )
        ).first()

        if not progress:
            logger.warning(
                f"Intento de validación sin progreso: user={request.user_id}, video={request.video_id}"
            )
            return ValidationResponse(
                authorized=False,
                exam_url=None,
                progress_percentage=0.0,
                message="No se encontró progreso de visualización. Por favor, vea el video completo."
            )

        # Calcular porcentaje de completitud
        progress_percentage = (progress.seconds_accumulated / request.video_duration) * 100

        # Verificar si cumple el umbral
        is_authorized = progress_percentage >= (COMPLETION_THRESHOLD * 100)

        if is_authorized:
            logger.info(
                f"Acceso autorizado: user={request.user_id}, "
                f"video={request.video_id}, progress={progress_percentage:.1f}%"
            )
            return ValidationResponse(
                authorized=True,
                exam_url=EXAM_URL,
                progress_percentage=round(progress_percentage, 2),
                message="Acceso autorizado al examen. ¡Buena suerte!"
            )
        else:
            logger.info(
                f"Acceso denegado: user={request.user_id}, "
                f"video={request.video_id}, progress={progress_percentage:.1f}%"
            )
            return ValidationResponse(
                authorized=False,
                exam_url=None,
                progress_percentage=round(progress_percentage, 2),
                message=f"Debe visualizar al menos el 90% del video. Progreso actual: {progress_percentage:.1f}%"
            )

    except Exception as e:
        logger.error(f"Error validando completitud: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al validar completitud: {str(e)}"
        )


@router.get(
    "/progress/{user_id}/{video_id}",
    response_model=ProgressResponse,
    summary="Consultar progreso actual",
    description="Obtiene el progreso de visualización actual de un usuario para un video específico."
)
async def get_progress(
    user_id: int,
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    Consulta el progreso actual del usuario.

    - **user_id**: ID del usuario
    - **video_id**: Identificador del video
    """
    progress = db.query(UserVideoProgress).filter(
        and_(
            UserVideoProgress.user_id == user_id,
            UserVideoProgress.video_id == video_id
        )
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró progreso para este usuario y video"
        )

    return ProgressResponse(
        user_id=progress.user_id,
        video_id=progress.video_id,
        seconds_accumulated=progress.seconds_accumulated,
        last_updated=progress.last_updated
    )


@router.delete(
    "/progress/{user_id}/{video_id}",
    summary="Resetear progreso",
    description="Elimina el progreso de un usuario para un video específico (uso administrativo)."
)
async def reset_progress(
    user_id: int,
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    Resetea el progreso del usuario (uso administrativo).

    - **user_id**: ID del usuario
    - **video_id**: Identificador del video
    """
    progress = db.query(UserVideoProgress).filter(
        and_(
            UserVideoProgress.user_id == user_id,
            UserVideoProgress.video_id == video_id
        )
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró progreso para eliminar"
        )

    db.delete(progress)
    db.commit()

    logger.info(f"Progreso eliminado: user={user_id}, video={video_id}")

    return {"message": "Progreso eliminado correctamente", "user_id": user_id, "video_id": video_id}
