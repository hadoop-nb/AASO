from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(
        String(50), default="created", index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    tasks = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )
    decisions = relationship(
        "Decision", back_populates="project", cascade="all, delete-orphan"
    )
    lessons = relationship(
        "Lesson", back_populates="project", cascade="all, delete-orphan"
    )
