# app/services/email_sending_service.py
"""
Core service for the centralized email system.
Handles API key management, email sending with logging, escalation, and dashboard stats.
"""
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.email_service import (
    EmailProject, EmailLog, EmailStatusEnum,
    EmailEscalationContact, EmailEscalationEvent,
)
from app.services.gmail_service import gmail_service

logger = logging.getLogger(__name__)

API_KEY_PREFIX = "esp_"
API_KEY_LENGTH = 48


class EmailSendingService:
    """Centralized email sending service with logging and escalation."""

    # ── API Key Management ──

    @staticmethod
    def generate_api_key() -> Tuple[str, str, str]:
        """
        Generate a new API key.
        Returns: (raw_key, prefix_for_lookup, bcrypt_hash)
        """
        random_part = secrets.token_urlsafe(API_KEY_LENGTH)
        raw_key = f"{API_KEY_PREFIX}{random_part}"
        prefix = raw_key[:12]
        key_hash = get_password_hash(raw_key)
        return raw_key, prefix, key_hash

    @staticmethod
    def validate_api_key(db: Session, raw_key: str) -> Optional[EmailProject]:
        """
        Validate an API key and return the associated project.
        Looks up by prefix, then verifies hash and checks expiration.
        """
        if not raw_key or not raw_key.startswith(API_KEY_PREFIX):
            return None

        prefix = raw_key[:12]
        project = db.query(EmailProject).filter(
            EmailProject.api_key_prefix == prefix,
            EmailProject.is_active == True,
        ).first()

        if not project:
            return None

        if not verify_password(raw_key, project.api_key_hash):
            return None

        if project.api_key_expires_at and project.api_key_expires_at < datetime.now(timezone.utc):
            return None

        return project

    @staticmethod
    def rotate_api_key(db: Session, project: EmailProject) -> str:
        """Rotate the API key for a project. Returns the new raw key."""
        raw_key, prefix, key_hash = EmailSendingService.generate_api_key()
        project.api_key_hash = key_hash
        project.api_key_prefix = prefix
        db.commit()
        db.refresh(project)
        return raw_key

    # ── Email Sending ──

    @staticmethod
    def send_email(
        db: Session,
        project: EmailProject,
        to_emails: list[str],
        subject: str,
        html_content: str,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
        attachments: Optional[list[dict]] = None,
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Send an email: create log → send via Gmail → update log → trigger escalation if failed.
        Returns: (success, log_id, provider_message_id)
        """
        # Create log entry (queued)
        attachment_names = [a["filename"] for a in attachments] if attachments else None
        log = EmailLog(
            project_id=project.id,
            to_emails=to_emails,
            cc=cc,
            bcc=bcc,
            subject=subject,
            body_html=html_content,
            attachments_count=len(attachments) if attachments else 0,
            attachment_names=attachment_names,
            status=EmailStatusEnum.queued,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        # Send via Gmail
        success, message_id, error = gmail_service.send_email(
            to_emails=to_emails,
            subject=subject,
            html_content=html_content,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
        )

        # Update log
        if success:
            log.status = EmailStatusEnum.sent
            log.provider_message_id = message_id
            log.sent_at = datetime.now(timezone.utc)
        else:
            log.status = EmailStatusEnum.failed
            log.error_message = error

        db.commit()
        db.refresh(log)

        # Trigger escalation on failure
        if not success:
            EmailSendingService._trigger_escalation(db, project, log)

        return success, log.id, message_id

    # ── Escalation ──

    @staticmethod
    def _trigger_escalation(db: Session, project: EmailProject, failed_log: EmailLog):
        """
        Escalation matrix:
        - L1: always on first failure
        - L2: ≥3 failures in last hour
        - L3: ≥10 failures in last hour
        """
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        failures_last_hour = db.query(func.count(EmailLog.id)).filter(
            EmailLog.project_id == project.id,
            EmailLog.status == EmailStatusEnum.failed,
            EmailLog.created_at >= one_hour_ago,
        ).scalar() or 0

        # Determine max escalation level to trigger
        max_level = 1
        if failures_last_hour >= 10:
            max_level = 3
        elif failures_last_hour >= 3:
            max_level = 2

        # Get active contacts for levels up to max_level
        contacts = db.query(EmailEscalationContact).filter(
            EmailEscalationContact.project_id == project.id,
            EmailEscalationContact.is_active == True,
            EmailEscalationContact.level <= max_level,
        ).all()

        for contact in contacts:
            # Create escalation event
            event = EmailEscalationEvent(
                email_log_id=failed_log.id,
                contact_id=contact.id,
                level=contact.level,
            )
            db.add(event)

            # Send alert email (best-effort, don't fail the whole flow)
            try:
                alert_html = f"""
                <h2>⚠️ Email Service Alert — {project.name}</h2>
                <p><strong>Level:</strong> L{contact.level}</p>
                <p><strong>Project:</strong> {project.name}</p>
                <p><strong>Failed email subject:</strong> {failed_log.subject}</p>
                <p><strong>Recipients:</strong> {', '.join(failed_log.to_emails)}</p>
                <p><strong>Error:</strong> {failed_log.error_message}</p>
                <p><strong>Failures in last hour:</strong> {failures_last_hour}</p>
                <p><strong>Time:</strong> {datetime.now(timezone.utc).isoformat()}</p>
                """
                gmail_service.send_email(
                    to_emails=[contact.email],
                    subject=f"[L{contact.level}] Email Service Alert — {project.name}",
                    html_content=alert_html,
                )
            except Exception as e:
                logger.error(f"Failed to send escalation alert to {contact.email}: {e}")

        db.commit()

    # ── Dashboard Stats ──

    @staticmethod
    def get_dashboard_stats(db: Session) -> dict:
        """Get aggregated stats for the email dashboard."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        # Counts by period
        def count_by_status(since: datetime, status: EmailStatusEnum) -> int:
            return db.query(func.count(EmailLog.id)).filter(
                EmailLog.created_at >= since,
                EmailLog.status == status,
            ).scalar() or 0

        sent_today = count_by_status(today_start, EmailStatusEnum.sent)
        sent_week = count_by_status(week_start, EmailStatusEnum.sent)
        sent_month = count_by_status(month_start, EmailStatusEnum.sent)
        failed_today = count_by_status(today_start, EmailStatusEnum.failed)
        failed_week = count_by_status(week_start, EmailStatusEnum.failed)

        total_week = sent_week + failed_week
        failure_rate = (failed_week / total_week * 100) if total_week > 0 else 0.0

        # Project counts
        total_projects = db.query(func.count(EmailProject.id)).scalar() or 0
        active_projects = db.query(func.count(EmailProject.id)).filter(
            EmailProject.is_active == True,
        ).scalar() or 0

        # Pending escalations (not acknowledged)
        pending_escalations = db.query(func.count(EmailEscalationEvent.id)).filter(
            EmailEscalationEvent.acknowledged_at == None,
        ).scalar() or 0

        # Top projects by volume this month
        top_projects_q = db.query(
            EmailProject.name,
            func.count(EmailLog.id).label('total'),
            func.count(case((EmailLog.status == EmailStatusEnum.sent, 1))).label('sent'),
            func.count(case((EmailLog.status == EmailStatusEnum.failed, 1))).label('failed'),
        ).join(EmailLog, EmailProject.id == EmailLog.project_id).filter(
            EmailLog.created_at >= month_start,
        ).group_by(EmailProject.name).order_by(func.count(EmailLog.id).desc()).limit(5).all()

        top_projects = [
            {"name": r.name, "total": r.total, "sent": r.sent, "failed": r.failed}
            for r in top_projects_q
        ]

        # Recent failures
        recent_failures_q = db.query(EmailLog).filter(
            EmailLog.status == EmailStatusEnum.failed,
        ).order_by(EmailLog.created_at.desc()).limit(10).all()

        recent_failures = [
            {
                "id": r.id,
                "project_id": r.project_id,
                "subject": r.subject,
                "to_emails": r.to_emails,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent_failures_q
        ]

        return {
            "sent_today": sent_today,
            "sent_this_week": sent_week,
            "sent_this_month": sent_month,
            "failed_today": failed_today,
            "failed_this_week": failed_week,
            "failure_rate_percent": round(failure_rate, 2),
            "total_projects": total_projects,
            "active_projects": active_projects,
            "pending_escalations": pending_escalations,
            "top_projects": top_projects,
            "recent_failures": recent_failures,
        }
