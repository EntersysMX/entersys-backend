# app/api/v1/endpoints/email_send.py
"""
Public endpoint for sending emails via API key authentication.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.email_service import EmailProject
from app.schemas.email_service import EmailSendRequest, EmailSendResponse
from app.services.email_sending_service import EmailSendingService

router = APIRouter()


def get_project_from_api_key(
    x_api_key: str = Header(..., description="Project API key (esp_...)"),
    db: Session = Depends(get_db),
) -> EmailProject:
    """Dependency: validate X-API-Key header and return the project."""
    project = EmailSendingService.validate_api_key(db, x_api_key)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )
    return project


@router.post("/send", response_model=EmailSendResponse)
def send_email(
    payload: EmailSendRequest,
    project: EmailProject = Depends(get_project_from_api_key),
    db: Session = Depends(get_db),
):
    """
    Send an email through the centralized email service.
    Requires a valid project API key in the X-API-Key header.
    """
    attachments = None
    if payload.attachments:
        attachments = [
            {"filename": a.filename, "content": a.content}
            for a in payload.attachments
        ]

    success, log_id, provider_message_id = EmailSendingService.send_email(
        db=db,
        project=project,
        to_emails=[str(e) for e in payload.to],
        subject=payload.subject,
        html_content=payload.html_content,
        cc=[str(e) for e in payload.cc] if payload.cc else None,
        bcc=[str(e) for e in payload.bcc] if payload.bcc else None,
        attachments=attachments,
    )

    if success:
        return EmailSendResponse(
            success=True,
            message="Email sent successfully",
            log_id=log_id,
            provider_message_id=provider_message_id,
        )
    else:
        return EmailSendResponse(
            success=False,
            message="Email delivery failed. The error has been logged and escalation triggered.",
            log_id=log_id,
        )
