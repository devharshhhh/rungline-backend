import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime, JSON, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LanguagePref(str, enum.Enum):
    python = "python"
    cpp = "cpp"


class MasteryBucket(str, enum.Enum):
    struggling = "struggling"
    on_track = "on_track"
    ready_to_advance = "ready_to_advance"


class ErrorType(str, enum.Enum):
    none = "none"
    syntax_error = "syntax_error"
    wrong_output = "wrong_output"
    runtime_error = "runtime_error"
    timeout = "timeout"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    language_pref: Mapped[LanguagePref] = mapped_column(Enum(LanguagePref), default=LanguagePref.python)
    plan: Mapped[str] = mapped_column(String, default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    attempts: Mapped[list["Attempt"]] = relationship(back_populates="user")
    mastery_records: Mapped[list["Mastery"]] = relationship(back_populates="user")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    problems: Mapped[list["Problem"]] = relationship(back_populates="topic")


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    topic_id: Mapped[str] = mapped_column(String, ForeignKey("topics.id"), nullable=False)
    sub_topic: Mapped[str] = mapped_column(String, nullable=True)  # e.g. "Loop-based min/max finding"
    grade: Mapped[str] = mapped_column(String, nullable=False)     # "A" / "B" / "C"
    rank: Mapped[int] = mapped_column(Integer, nullable=False)     # 1-10 within the grade
    language: Mapped[LanguagePref] = mapped_column(Enum(LanguagePref), default=LanguagePref.python)

    title: Mapped[str] = mapped_column(String, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    starter_code: Mapped[str] = mapped_column(Text, default="")
    test_cases: Mapped[list] = mapped_column(JSON, nullable=False)   # [{"input":..., "expected_output":...}]
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=2000)

    edge_case_notes: Mapped[str] = mapped_column(Text, default="")   # internal only
    common_mistakes: Mapped[str] = mapped_column(Text, default="")   # internal only, feeds AI tutor
    tags: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    topic: Mapped["Topic"] = relationship(back_populates="problems")
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="problem")


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    problem_id: Mapped[str] = mapped_column(String, ForeignKey("problems.id"), nullable=False)

    code_submitted: Mapped[str] = mapped_column(Text, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    error_type: Mapped[ErrorType] = mapped_column(Enum(ErrorType), default=ErrorType.none)
    time_taken_ms: Mapped[int] = mapped_column(Integer, default=0)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)

    test_results: Mapped[list] = mapped_column(JSON, default=list)  # per-test-case pass/fail detail
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped["User"] = relationship(back_populates="attempts")
    problem: Mapped["Problem"] = relationship(back_populates="attempts")


class Mastery(Base):
    __tablename__ = "mastery"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    topic_id: Mapped[str] = mapped_column(String, ForeignKey("topics.id"), nullable=False)

    score: Mapped[float] = mapped_column(Float, default=0.0)
    bucket: Mapped[MasteryBucket] = mapped_column(Enum(MasteryBucket), default=MasteryBucket.on_track)
    current_grade: Mapped[str] = mapped_column(String, default="A")
    current_rank: Mapped[int] = mapped_column(Integer, default=1)
    consecutive_good_results: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="mastery_records")


class Hint(Base):
    __tablename__ = "hints"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    attempt_id: Mapped[str] = mapped_column(String, ForeignKey("attempts.id"), nullable=False)
    hint_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, or 3
    prompt_sent: Mapped[str] = mapped_column(Text, default="")
    response_text: Mapped[str] = mapped_column(Text, default="")
    leaked_flag: Mapped[bool] = mapped_column(Boolean, default=False)  # set during manual audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
