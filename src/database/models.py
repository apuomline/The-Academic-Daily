"""Database models for Academic Paper Pusher."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Table,
    Column,
    Index,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Paper(Base):
    """Represents an academic paper from any source."""

    __tablename__ = "papers"
    __table_args__ = (
        Index("ix_papers_source_date", "source", "published_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    arxiv_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="arxiv")
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    versions: Mapped[list["PaperVersion"]] = relationship(
        "PaperVersion",
        back_populates="paper",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Paper(id={self.id}, title='{self.title[:50]}...', source={self.source})>"


class PaperVersion(Base):
    """Stores different versions/summaries of a paper."""

    __tablename__ = "paper_versions"
    __table_args__ = (
        UniqueConstraint("paper_id", "version", name="uq_paper_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., "v1", "v2"
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # LLM summary
    model_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "gpt-4o"
    prompt_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="versions")

    def __repr__(self) -> str:
        return f"<PaperVersion(id={self.id}, paper_id={self.paper_id}, version={self.version})>"


class Subscription(Base):
    """User subscription preferences."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    exclude_keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    push_time: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # HH:MM format
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Shanghai")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, email='{self.user_email}', active={self.is_active})>"


class PushLog(Base):
    """Log of push delivery attempts for idempotency."""

    __tablename__ = "push_logs"
    __table_args__ = (
        UniqueConstraint("subscription_id", "channel", "report_date", name="uq_push_idempotency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)  # 'email', 'wework', 'telegram'
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # Date of the report
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 'success', 'failed'
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    subscription: Mapped["Subscription"] = relationship("Subscription")

    def __repr__(self) -> str:
        return f"<PushLog(id={self.id}, channel={self.channel}, status={self.status})>"
