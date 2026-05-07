"""SQLAlchemy ORM models — single source of truth for table definitions."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from shared.enums import Difficulty, Language, SubmissionStatus, SupportedLanguage, Verdict


def _enum_values(enum_cls: type[PyEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    verification_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_token_expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="user")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin', 'problem_setter')", name="chk_user_role"),
        Index("idx_users_verification_token_hash", "verification_token_hash"),
    )


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_account_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    user: Mapped[User] = relationship(back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_account_id", name="uq_oauth_provider_account"),
        UniqueConstraint("user_id", "provider", name="uq_oauth_user_provider"),
        Index("idx_oauth_user_id", "user_id"),
    )


problem_topics = Table(
    "problem_topics",
    Base.metadata,
    Column(
        "problem_id",
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("topic_id", Integer, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
)


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        SAEnum(Difficulty, name="difficulty_enum", create_type=False, values_callable=_enum_values),
        nullable=False,
        server_default=text("'medium'"),
    )
    base_time_limit_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    base_memory_limit_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="problem", cascade="all, delete-orphan"
    )
    topics: Mapped[list["Topic"]] = relationship("Topic", secondary=problem_topics, lazy="joined")
    language_configs: Mapped[list["ProblemLanguageConfig"]] = relationship(
        "ProblemLanguageConfig", back_populates="problem", cascade="all, delete-orphan"
    )
    hints: Mapped[list[str]] = mapped_column(ARRAY(String), server_default="{}")

    __table_args__ = (
        CheckConstraint("base_time_limit_ms > 0", name="chk_time_limit_positive"),
        CheckConstraint("base_memory_limit_mb > 0", name="chk_memory_limit_positive"),
        CheckConstraint("array_length(hints, 1) <= 4", name="max_four_hints"),
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
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    problem: Mapped["Problem"] = relationship(back_populates="test_cases")

    __table_args__ = (
        CheckConstraint("octet_length(input_data) <= 1048576", name="chk_input_size"),
        CheckConstraint("octet_length(expected_output) <= 1048576", name="chk_expected_size"),
        Index("idx_test_cases_problem", "problem_id", "ordering"),
    )


class ProblemLanguageConfig(Base):
    __tablename__ = "problem_language_configs"

    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True
    )
    language: Mapped[SupportedLanguage] = mapped_column(
        SAEnum(
            SupportedLanguage,
            name="supported_language_enum",
            create_type=False,
            values_callable=_enum_values,
        ),
        primary_key=True,
    )
    boilerplate: Mapped[str] = mapped_column(Text, nullable=False)
    driver_code: Mapped[str] = mapped_column(Text, nullable=False)

    problem: Mapped["Problem"] = relationship(back_populates="language_configs")


class Submission(Base):
    __tablename__ = "submissions"

    # id is server-generated before insert; never client-supplied
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False
    )
    language: Mapped[Language] = mapped_column(
        SAEnum(Language, name="language_enum", create_type=False, values_callable=_enum_values),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        SAEnum(
            SubmissionStatus,
            name="submission_status",
            create_type=False,
            values_callable=_enum_values,
        ),
        nullable=False,
        server_default=text("'pending'"),
    )
    verdict: Mapped[Verdict | None] = mapped_column(
        SAEnum(Verdict, name="verdict_enum", create_type=False, values_callable=_enum_values),
        nullable=True,
    )
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_used_mb: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    stdout_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)  # first 1 KB
    stderr_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)  # first 512 B
    actual_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_submit: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    passed_test_cases: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    total_test_cases: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    failed_test_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True
    )
    failed_test_case: Mapped["TestCase | None"] = relationship(
        "TestCase", foreign_keys=[failed_test_case_id]
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")
    )

    __table_args__ = (
        CheckConstraint("octet_length(code) <= 65536", name="chk_code_size"),
        Index("idx_submissions_user", "user_id", "created_at"),
        Index("idx_submissions_problem", "problem_id", "created_at"),
    )
