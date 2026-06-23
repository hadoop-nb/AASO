from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Decision(Base, TimestampMixin):
    __tablename__ = "decisions"

    decision_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
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
    question: Mapped[str] = mapped_column(Text, nullable=False)
    alternatives: Mapped[list] = mapped_column(JSON, default=list)
    selected: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")

    project = relationship("Project", back_populates="decisions")
