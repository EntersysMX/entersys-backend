# app/schemas/email_service.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ── Email Projects ──

class EmailProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    api_key_expires_at: Optional[datetime] = None
    rate_limit_per_minute: int = 30
    rate_limit_per_hour: int = 500
    created_by: Optional[str] = None


class EmailProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    api_key_expires_at: Optional[datetime] = None
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None


class EmailProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    api_key_prefix: str
    api_key_expires_at: Optional[datetime] = None
    is_active: bool
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmailProjectCreateResponse(EmailProjectResponse):
    """Response when creating a project — includes the raw API key (shown only once)."""
    api_key_raw: str


class ApiKeyRotateResponse(BaseModel):
    api_key_raw: str
    api_key_prefix: str
    message: str = "API key rotated successfully. Store it securely — it won't be shown again."


# ── Email Send ──

class EmailAttachment(BaseModel):
    filename: str
    content: str  # base64 encoded


class EmailSendRequest(BaseModel):
    to: List[EmailStr]
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    subject: str = Field(..., max_length=500)
    html_content: str
    attachments: Optional[List[EmailAttachment]] = None


class EmailSendResponse(BaseModel):
    success: bool
    message: str
    log_id: Optional[int] = None
    provider_message_id: Optional[str] = None


# ── Email Logs ──

class EmailLogResponse(BaseModel):
    id: int
    project_id: int
    project_name: Optional[str] = None
    to_emails: List[str]
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    subject: str
    body_html: str
    attachments_count: int
    attachment_names: Optional[list] = None
    status: str
    error_message: Optional[str] = None
    provider_message_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EmailLogListResponse(BaseModel):
    items: List[EmailLogResponse]
    total: int
    page: int
    page_size: int


# ── Escalation Contacts ──

class EscalationContactCreate(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    level: int = Field(..., ge=1, le=3)


class EscalationContactUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    level: Optional[int] = Field(None, ge=1, le=3)
    is_active: Optional[bool] = None


class EscalationContactResponse(BaseModel):
    id: int
    project_id: int
    name: str
    email: str
    level: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Escalation Events ──

class EscalationEventResponse(BaseModel):
    id: int
    email_log_id: int
    contact_id: int
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    level: int
    notified_at: datetime
    acknowledged_at: Optional[datetime] = None
    # joined fields
    project_name: Optional[str] = None
    email_subject: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class EscalationEventListResponse(BaseModel):
    items: List[EscalationEventResponse]
    total: int
    page: int
    page_size: int


# ── Dashboard Stats ──

class EmailDashboardStats(BaseModel):
    sent_today: int = 0
    sent_this_week: int = 0
    sent_this_month: int = 0
    failed_today: int = 0
    failed_this_week: int = 0
    failure_rate_percent: float = 0.0
    total_projects: int = 0
    active_projects: int = 0
    pending_escalations: int = 0
    top_projects: List[dict] = []
    recent_failures: List[dict] = []
