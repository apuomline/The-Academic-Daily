"""Tests for database models and CRUD operations."""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import Base, Paper, PaperVersion, Subscription, PushLog
from src.database.crud import PaperCRUD, SubscriptionCRUD, PushLogCRUD, db_manager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal


@pytest.fixture
def session(in_memory_db):
    """Get a database session for testing."""
    session = in_memory_db()
    try:
        yield session
    finally:
        session.close()


class TestPaperModel:
    """Test Paper model."""

    def test_create_paper(self, session):
        """Test creating a paper."""
        paper = Paper(
            arxiv_id="2304.12345v1",
            title="Test Paper",
            abstract="Test abstract",
            source="arxiv",
            published_date=datetime(2026, 4, 12, 10, 30),
        )
        session.add(paper)
        session.commit()

        retrieved = session.query(Paper).filter_by(arxiv_id="2304.12345v1").first()
        assert retrieved is not None
        assert retrieved.title == "Test Paper"


class TestPaperCRUD:
    """Test Paper CRUD operations."""

    def test_create_paper(self, session):
        """Test creating a paper via CRUD."""
        paper = PaperCRUD.create_paper(
            session,
            arxiv_id="2304.12345v1",
            title="Test Paper",
            abstract="Test abstract",
            source="arxiv",
        )
        session.commit()

        assert paper.id is not None
        assert paper.arxiv_id == "2304.12345v1"

    def test_get_paper_by_arxiv_id(self, session):
        """Test retrieving paper by arXiv ID."""
        paper = PaperCRUD.create_paper(
            session,
            arxiv_id="2304.12345v1",
            title="Test Paper",
            source="arxiv",
        )
        session.commit()

        retrieved = PaperCRUD.get_paper_by_arxiv_id(session, "2304.12345v1")
        assert retrieved is not None
        assert retrieved.title == "Test Paper"

    def test_upsert_paper_new(self, session):
        """Test upsert creates new paper."""
        paper = PaperCRUD.upsert_paper(
            session,
            arxiv_id="2304.12345v1",
            title="New Paper",
            source="arxiv",
        )
        session.commit()

        assert paper.id is not None
        assert paper.title == "New Paper"

    def test_upsert_paper_existing(self, session):
        """Test upsert updates existing paper."""
        # Create original paper
        paper = PaperCRUD.create_paper(
            session,
            arxiv_id="2304.12345v1",
            title="Original Title",
            source="arxiv",
        )
        session.commit()

        # Update with upsert
        updated = PaperCRUD.upsert_paper(
            session,
            arxiv_id="2304.12345v1",
            title="Updated Title",
            abstract="New abstract",
        )
        session.commit()

        assert updated.id == paper.id
        assert updated.title == "Updated Title"
        assert updated.abstract == "New abstract"


class TestSubscriptionModel:
    """Test Subscription model."""

    def test_create_subscription(self, session):
        """Test creating a subscription."""
        subscription = Subscription(
            user_email="test@example.com",
            keywords=["llm", "deep learning"],
            timezone="Asia/Shanghai",
        )
        session.add(subscription)
        session.commit()

        retrieved = session.query(Subscription).filter_by(user_email="test@example.com").first()
        assert retrieved is not None
        assert "llm" in retrieved.keywords


class TestSubscriptionCRUD:
    """Test Subscription CRUD operations."""

    def test_create_subscription(self, session):
        """Test creating a subscription via CRUD."""
        subscription = SubscriptionCRUD.create_subscription(
            session,
            user_email="test@example.com",
            keywords=["llm"],
        )
        session.commit()

        assert subscription.id is not None
        assert subscription.user_email == "test@example.com"

    def test_get_active_subscriptions(self, session):
        """Test retrieving active subscriptions."""
        SubscriptionCRUD.create_subscription(session, "active@example.com", ["llm"])
        inactive = SubscriptionCRUD.create_subscription(session, "inactive@example.com", ["cv"])
        inactive.is_active = False
        session.commit()

        active = SubscriptionCRUD.get_active_subscriptions(session)
        assert len(active) == 1
        assert active[0].user_email == "active@example.com"


class TestPushLogModel:
    """Test PushLog model."""

    def test_create_push_log(self, session):
        """Test creating a push log entry."""
        # Create subscription first
        subscription = SubscriptionCRUD.create_subscription(
            session,
            user_email="test@example.com",
            keywords=["llm"],
        )
        session.commit()

        # Create push log
        log = PushLog(
            subscription_id=subscription.id,
            channel="email",
            report_date=datetime(2026, 4, 12),
            status="success",
        )
        session.add(log)
        session.commit()

        assert log.id is not None


class TestPushLogCRUD:
    """Test PushLog CRUD operations."""

    def test_was_pushed(self, session):
        """Test checking if a report was already pushed."""
        # Create subscription
        subscription = SubscriptionCRUD.create_subscription(
            session,
            user_email="test@example.com",
            keywords=["llm"],
        )
        session.commit()

        report_date = datetime(2026, 4, 12, 0, 0, 0)

        # Not pushed yet
        assert not PushLogCRUD.was_pushed(session, subscription.id, "email", report_date)

        # Mark as pushed
        PushLogCRUD.create_log(
            session,
            subscription_id=subscription.id,
            channel="email",
            report_date=report_date,
            status="success",
        )
        session.commit()

        # Now should be pushed
        assert PushLogCRUD.was_pushed(session, subscription.id, "email", report_date)
