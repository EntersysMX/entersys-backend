# app/api/v1/endpoints/email_admin.py
"""
Admin endpoints for the centralized email service.
All routes require JWT authentication (admin user).
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.blog import AdminUser
from app.models.email_service import (
    EmailProject, EmailLog, EmailStatusEnum,
    EmailEscalationContact, EmailEscalationEvent,
)
from app.schemas.email_service import (
    EmailProjectCreate, EmailProjectUpdate, EmailProjectResponse, EmailProjectCreateResponse,
    ApiKeyRotateResponse,
    EmailLogResponse, EmailLogListResponse,
    EscalationContactCreate, EscalationContactUpdate, EscalationContactResponse,
    EscalationEventResponse, EscalationEventListResponse,
    EmailDashboardStats,
)
from app.services.email_sending_service import EmailSendingService

router = APIRouter()


# ── Dashboard ──

@router.get("/stats", response_model=EmailDashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Get email service dashboard statistics."""
    return EmailSendingService.get_dashboard_stats(db)


# ── Projects CRUD ──

@router.get("/projects", response_model=list[EmailProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """List all email projects."""
    projects = db.query(EmailProject).order_by(EmailProject.created_at.desc()).all()
    return projects


@router.post("/projects", response_model=EmailProjectCreateResponse, status_code=201)
def create_project(
    payload: EmailProjectCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Create a new email project. Returns the API key (shown only once)."""
    raw_key, prefix, key_hash = EmailSendingService.generate_api_key()

    project = EmailProject(
        name=payload.name,
        description=payload.description,
        api_key_hash=key_hash,
        api_key_prefix=prefix,
        api_key_expires_at=payload.api_key_expires_at,
        rate_limit_per_minute=payload.rate_limit_per_minute,
        rate_limit_per_hour=payload.rate_limit_per_hour,
        created_by=payload.created_by or current_user.email,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    response = EmailProjectCreateResponse.model_validate(project)
    response.api_key_raw = raw_key
    return response


@router.get("/projects/{project_id}", response_model=EmailProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Get project details."""
    project = db.query(EmailProject).filter(EmailProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=EmailProjectResponse)
def update_project(
    project_id: int,
    payload: EmailProjectUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Update a project."""
    project = db.query(EmailProject).filter(EmailProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Delete a project and all its related data."""
    project = db.query(EmailProject).filter(EmailProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()


@router.post("/projects/{project_id}/rotate-key", response_model=ApiKeyRotateResponse)
def rotate_api_key(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Rotate the API key for a project."""
    project = db.query(EmailProject).filter(EmailProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    raw_key = EmailSendingService.rotate_api_key(db, project)
    return ApiKeyRotateResponse(
        api_key_raw=raw_key,
        api_key_prefix=project.api_key_prefix,
    )


# ── Logs ──

@router.get("/logs", response_model=EmailLogListResponse)
def list_logs(
    project_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """List email logs with filters and pagination."""
    query = db.query(EmailLog)

    if project_id:
        query = query.filter(EmailLog.project_id == project_id)
    if status_filter:
        query = query.filter(EmailLog.status == EmailStatusEnum(status_filter))
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (EmailLog.subject.ilike(search_term)) |
            (EmailLog.error_message.ilike(search_term))
        )

    total = query.count()
    logs = query.order_by(EmailLog.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # Enrich with project name
    project_names = {}
    project_ids = {log.project_id for log in logs}
    if project_ids:
        projects = db.query(EmailProject.id, EmailProject.name).filter(
            EmailProject.id.in_(project_ids)
        ).all()
        project_names = {p.id: p.name for p in projects}

    items = []
    for log in logs:
        item = EmailLogResponse.model_validate(log)
        item.project_name = project_names.get(log.project_id)
        items.append(item)

    return EmailLogListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/logs/{log_id}", response_model=EmailLogResponse)
def get_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Get email log details."""
    log = db.query(EmailLog).filter(EmailLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    item = EmailLogResponse.model_validate(log)
    project = db.query(EmailProject).filter(EmailProject.id == log.project_id).first()
    if project:
        item.project_name = project.name
    return item


# ── Escalation Contacts ──

@router.get("/projects/{project_id}/escalation-contacts", response_model=list[EscalationContactResponse])
def list_escalation_contacts(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """List escalation contacts for a project."""
    return db.query(EmailEscalationContact).filter(
        EmailEscalationContact.project_id == project_id
    ).order_by(EmailEscalationContact.level, EmailEscalationContact.name).all()


@router.post("/projects/{project_id}/escalation-contacts", response_model=EscalationContactResponse, status_code=201)
def create_escalation_contact(
    project_id: int,
    payload: EscalationContactCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Add an escalation contact to a project."""
    project = db.query(EmailProject).filter(EmailProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    contact = EmailEscalationContact(
        project_id=project_id,
        name=payload.name,
        email=payload.email,
        level=payload.level,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.put("/escalation-contacts/{contact_id}", response_model=EscalationContactResponse)
def update_escalation_contact(
    contact_id: int,
    payload: EscalationContactUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Update an escalation contact."""
    contact = db.query(EmailEscalationContact).filter(EmailEscalationContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/escalation-contacts/{contact_id}", status_code=204)
def delete_escalation_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Delete an escalation contact."""
    contact = db.query(EmailEscalationContact).filter(EmailEscalationContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()


# ── Escalation Events ──

@router.get("/escalation-events", response_model=EscalationEventListResponse)
def list_escalation_events(
    project_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """List escalation events with optional project filter."""
    query = db.query(EmailEscalationEvent)

    if project_id:
        # Join through email_log to filter by project
        query = query.join(EmailLog, EmailEscalationEvent.email_log_id == EmailLog.id).filter(
            EmailLog.project_id == project_id
        )

    total = query.count()
    events = query.order_by(EmailEscalationEvent.notified_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = []
    for event in events:
        item = EscalationEventResponse.model_validate(event)
        # Enrich with contact and log details
        if event.contact:
            item.contact_name = event.contact.name
            item.contact_email = event.contact.email
        if event.email_log:
            item.email_subject = event.email_log.subject
            item.error_message = event.email_log.error_message
            project = db.query(EmailProject).filter(
                EmailProject.id == event.email_log.project_id
            ).first()
            if project:
                item.project_name = project.name
        items.append(item)

    return EscalationEventListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/escalation-events/{event_id}/acknowledge")
def acknowledge_escalation_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """Acknowledge an escalation event."""
    event = db.query(EmailEscalationEvent).filter(EmailEscalationEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.acknowledged_at:
        raise HTTPException(status_code=400, detail="Event already acknowledged")

    event.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Escalation event acknowledged", "acknowledged_at": event.acknowledged_at.isoformat()}
