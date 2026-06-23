from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(50), default="")
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tasks.task_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    success: Mapped[bool] = mapped_column(default=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    files_generated: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
