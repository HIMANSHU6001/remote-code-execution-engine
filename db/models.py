"""SQLAlchemy ORM models — single source of truth for table definitions."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="user")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin', 'problem_setter')", name="chk_user_role"),
    )


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    base_time_limit_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    base_memory_limit_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))

    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="problem", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("base_time_limit_ms > 0", name="chk_time_limit_positive"),
        CheckConstraint("base_memory_limit_mb > 0", name="chk_memory_limit_positive"),
    )


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    ordering: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))

    problem: Mapped["Problem"] = relationship(back_populates="test_cases")

    __table_args__ = (
        CheckConstraint("octet_length(input_data) <= 1048576", name="chk_input_size"),
        CheckConstraint("octet_length(expected_output) <= 1048576", name="chk_expected_size"),
        Index("idx_test_cases_problem", "problem_id", "ordering"),
    )


class Submission(Base):
    __tablename__ = "submissions"

    # id is server-generated before insert; never client-supplied
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    problem_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False)          # language_enum value
    code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")  # submission_status
    verdict: Mapped[str | None] = mapped_column(Text, nullable=True)     # verdict_enum; NULL until completed
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_used_mb: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    stdout_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)  # first 1 KB
    stderr_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)  # first 512 B
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (
        CheckConstraint("octet_length(code) <= 65536", name="chk_code_size"),
        Index("idx_submissions_user", "user_id", "created_at"),
        Index("idx_submissions_problem", "problem_id", "created_at"),
    )
