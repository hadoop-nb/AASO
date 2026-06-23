from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Lesson(Base, TimestampMixin):
    __tablename__ = "lessons"

    lesson_id: Mapped[str] = mapped_column(
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
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    solution: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, default="")

    project = relationship("Project", back_populates="lessons")
