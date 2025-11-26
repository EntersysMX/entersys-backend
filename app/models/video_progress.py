# app/models/video_progress.py
from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.db.base import Base


class UserVideoProgress(Base):
    """
    Modelo para el seguimiento del progreso de visualización de videos.
    Implementa la validación anti-skip según MD050.
    """
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    video_id = Column(String(50), nullable=False, index=True)
    seconds_accumulated = Column(Float, default=0.0, nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'video_id', name='uq_user_video'),
    )

    def __repr__(self):
        return f"<UserVideoProgress(user_id={self.user_id}, video_id='{self.video_id}', seconds={self.seconds_accumulated})>"
