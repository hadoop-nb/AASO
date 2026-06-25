from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class ProjectPlan(Base, TimestampMixin):
    __tablename__ = "project_plans"

    plan_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    overall_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    tasks = relationship(
        "PlanTask", back_populates="plan", cascade="all, delete-orphan"
    )


class PlanTask(Base, TimestampMixin):
    __tablename__ = "plan_tasks"

    task_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_plans.plan_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("plan_tasks.task_id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_factors: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    dependencies: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_agent_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    plan = relationship("ProjectPlan", back_populates="tasks")
