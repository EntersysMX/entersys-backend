# app/models/email_service.py
import enum
from sqlalchemy import (
    Boolean, Column, Integer, String, Text, ForeignKey,
    TIMESTAMP, Enum as SAEnum, Index, func
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.db.base import Base


class EmailStatusEnum(enum.Enum):
    queued = "queued"
    sent = "sent"
    failed = "failed"


class EmailProject(Base):
    __tablename__ = 'email_projects'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    api_key_hash = Column(String(255), nullable=False)
    api_key_prefix = Column(String(12), nullable=False, index=True)
    api_key_expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, server_default='true', nullable=False)
    rate_limit_per_minute = Column(Integer, server_default='30', nullable=False)
    rate_limit_per_hour = Column(Integer, server_default='500', nullable=False)
    created_by = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    logs = relationship("EmailLog", back_populates="project", cascade="all, delete-orphan")
    escalation_contacts = relationship("EmailEscalationContact", back_populates="project", cascade="all, delete-orphan")


class EmailLog(Base):
    __tablename__ = 'email_logs'
    __table_args__ = (
        Index('ix_email_logs_project_status', 'project_id', 'status'),
        Index('ix_email_logs_created_at', 'created_at'),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('email_projects.id', ondelete='CASCADE'), nullable=False)
    to_emails = Column(ARRAY(String), nullable=False)
    cc = Column(ARRAY(String), nullable=True)
    bcc = Column(ARRAY(String), nullable=True)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    attachments_count = Column(Integer, server_default='0', nullable=False)
    attachment_names = Column(JSONB, nullable=True)
    status = Column(
        SAEnum(EmailStatusEnum, name='email_status_enum', create_type=True),
        nullable=False, server_default=EmailStatusEnum.queued.value
    )
    error_message = Column(Text, nullable=True)
    provider_message_id = Column(String(255), nullable=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("EmailProject", back_populates="logs")
    escalation_events = relationship("EmailEscalationEvent", back_populates="email_log", cascade="all, delete-orphan")


class EmailEscalationContact(Base):
    __tablename__ = 'email_escalation_contacts'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('email_projects.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    level = Column(Integer, nullable=False)  # 1, 2, or 3
    is_active = Column(Boolean, server_default='true', nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("EmailProject", back_populates="escalation_contacts")
    escalation_events = relationship("EmailEscalationEvent", back_populates="contact", cascade="all, delete-orphan")


class EmailEscalationEvent(Base):
    __tablename__ = 'email_escalation_events'

    id = Column(Integer, primary_key=True)
    email_log_id = Column(Integer, ForeignKey('email_logs.id', ondelete='CASCADE'), nullable=False)
    contact_id = Column(Integer, ForeignKey('email_escalation_contacts.id', ondelete='CASCADE'), nullable=False)
    level = Column(Integer, nullable=False)
    notified_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    acknowledged_at = Column(TIMESTAMP(timezone=True), nullable=True)

    email_log = relationship("EmailLog", back_populates="escalation_events")
    contact = relationship("EmailEscalationContact", back_populates="escalation_events")
