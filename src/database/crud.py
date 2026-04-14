"""Database CRUD operations."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine, select, and_, or_
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from .models import Base, Paper, PaperVersion, Subscription, PushLog


class DatabaseManager:
    """Manages database connection and session creation."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager.

        Args:
            database_url: Database connection string. Defaults to settings.DATABASE_URL
        """
        self.database_url = database_url or getattr(settings, "database_url", "sqlite:///papers.db")
        self.engine = create_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

    def create_tables(self) -> None:
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self) -> None:
        """Drop all tables from the database."""
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            SQLAlchemy Session object
        """
        return self.SessionLocal()


# Global database manager instance
db_manager = DatabaseManager()


class PaperCRUD:
    """CRUD operations for Paper model."""

    @staticmethod
    def create_paper(
        session: Session,
        arxiv_id: Optional[str] = None,
        doi: Optional[str] = None,
        title: str = "",
        abstract: Optional[str] = None,
        source: str = "arxiv",
        published_date: Optional[datetime] = None,
        updated_date: Optional[datetime] = None,
    ) -> Paper:
        """Create a new paper.

        Args:
            session: Database session
            arxiv_id: arXiv ID
            doi: DOI
            title: Paper title
            abstract: Paper abstract
            source: Data source
            published_date: Publication date
            updated_date: Last update date

        Returns:
            Created Paper object
        """
        paper = Paper(
            arxiv_id=arxiv_id,
            doi=doi,
            title=title,
            abstract=abstract,
            source=source,
            published_date=published_date,
            updated_date=updated_date,
        )
        session.add(paper)
        session.flush()
        return paper

    @staticmethod
    def get_paper_by_id(session: Session, paper_id: int) -> Optional[Paper]:
        """Get paper by ID.

        Args:
            session: Database session
            paper_id: Paper ID

        Returns:
            Paper object or None
        """
        return session.execute(
            select(Paper).where(Paper.id == paper_id)
        ).scalar_one_or_none()

    @staticmethod
    def get_paper_by_arxiv_id(session: Session, arxiv_id: str) -> Optional[Paper]:
        """Get paper by arXiv ID.

        Args:
            session: Database session
            arxiv_id: arXiv ID

        Returns:
            Paper object or None
        """
        return session.execute(
            select(Paper).where(Paper.arxiv_id == arxiv_id)
        ).scalar_one_or_none()

    @staticmethod
    def get_paper_by_doi(session: Session, doi: str) -> Optional[Paper]:
        """Get paper by DOI.

        Args:
            session: Database session
            doi: DOI

        Returns:
            Paper object or None
        """
        return session.execute(
            select(Paper).where(Paper.doi == doi)
        ).scalar_one_or_none()

    @staticmethod
    def get_papers_by_date_range(
        session: Session,
        start_date: datetime,
        end_date: datetime,
        source: Optional[str] = None,
    ) -> List[Paper]:
        """Get papers within a date range.

        Args:
            session: Database session
            start_date: Start date
            end_date: End date
            source: Optional source filter

        Returns:
            List of Paper objects
        """
        query = select(Paper).where(
            and_(
                Paper.published_date >= start_date,
                Paper.published_date <= end_date,
            )
        )

        if source:
            query = query.where(Paper.source == source)

        return list(session.execute(query).scalars().all())

    @staticmethod
    def get_recent_papers(
        session: Session,
        limit: int = 20,
        source: Optional[str] = None,
    ) -> List[Paper]:
        """Get recent papers ordered by published date.

        Args:
            session: Database session
            limit: Max results
            source: Optional source filter

        Returns:
            List of Paper objects
        """
        query = select(Paper).order_by(Paper.published_date.desc())

        if source:
            query = query.where(Paper.source == source)

        query = query.limit(limit)
        return list(session.execute(query).scalars().all())

    @staticmethod
    def search_papers(
        session: Session,
        keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[Paper]:
        """Search papers by keywords using AND logic.

        All keywords must be present in either title or abstract.

        Args:
            session: Database session
            keywords: Include keywords (must ALL match)
            exclude_keywords: Exclude keywords
            source: Optional source filter
            limit: Max results

        Returns:
            List of Paper objects
        """
        query = select(Paper).order_by(Paper.published_date.desc())

        if source:
            query = query.where(Paper.source == source)

        # Keyword filtering using AND logic - all keywords must match
        if keywords:
            # For each keyword, the paper must match in title OR abstract
            keyword_conditions = []
            for keyword in keywords:
                keyword_conditions.append(
                    or_(
                        Paper.title.ilike(f"%{keyword}%"),
                        Paper.abstract.ilike(f"%{keyword}%"),
                    )
                )
            # All keyword conditions must be true (AND logic)
            query = query.where(and_(*keyword_conditions))

        if exclude_keywords:
            for keyword in exclude_keywords:
                query = query.where(
                    and_(
                        ~Paper.title.ilike(f"%{keyword}%"),
                        ~Paper.abstract.ilike(f"%{keyword}%"),
                    )
                )

        query = query.limit(limit)
        return list(session.execute(query).scalars().all())

    @staticmethod
    def upsert_paper(session: Session, **kwargs) -> Paper:
        """Insert or update a paper.

        Args:
            session: Database session
            **kwargs: Paper fields

        Returns:
            Paper object
        """
        arxiv_id = kwargs.get("arxiv_id")
        doi = kwargs.get("doi")

        # Try to find existing paper
        paper = None
        if arxiv_id:
            paper = PaperCRUD.get_paper_by_arxiv_id(session, arxiv_id)
        elif doi:
            paper = PaperCRUD.get_paper_by_doi(session, doi)

        if paper:
            # Update existing paper
            for key, value in kwargs.items():
                if hasattr(paper, key) and value is not None:
                    setattr(paper, key, value)
        else:
            # Create new paper
            paper = PaperCRUD.create_paper(session, **kwargs)

        return paper


class PaperVersionCRUD:
    """CRUD operations for PaperVersion model."""

    @staticmethod
    def create_version(
        session: Session,
        paper_id: int,
        version: str,
        content: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt_id: Optional[str] = None,
    ) -> PaperVersion:
        """Create a new paper version.

        Args:
            session: Database session
            paper_id: Paper ID
            version: Version string (e.g., "v1")
            content: Summary content
            model_name: LLM model used
            prompt_id: Prompt template ID

        Returns:
            Created PaperVersion object
        """
        version = PaperVersion(
            paper_id=paper_id,
            version=version,
            content=content,
            model_name=model_name,
            prompt_id=prompt_id,
        )
        session.add(version)
        session.flush()
        return version

    @staticmethod
    def get_latest_version(session: Session, paper_id: int) -> Optional[PaperVersion]:
        """Get latest version of a paper.

        Args:
            session: Database session
            paper_id: Paper ID

        Returns:
            Latest PaperVersion or None
        """
        return session.execute(
            select(PaperVersion)
            .where(PaperVersion.paper_id == paper_id)
            .order_by(PaperVersion.created_at.desc())
        ).scalar_one_or_none()


class SubscriptionCRUD:
    """CRUD operations for Subscription model."""

    @staticmethod
    def create_subscription(
        session: Session,
        user_email: str,
        keywords: List[str],
        exclude_keywords: Optional[List[str]] = None,
        push_time: Optional[str] = None,
        timezone: str = "Asia/Shanghai",
    ) -> Subscription:
        """Create a new subscription.

        Args:
            session: Database session
            user_email: User email address
            keywords: Keywords to track
            exclude_keywords: Keywords to exclude
            push_time: Push time in HH:MM format
            timezone: User timezone

        Returns:
            Created Subscription object
        """
        subscription = Subscription(
            user_email=user_email,
            keywords=keywords,
            exclude_keywords=exclude_keywords or [],
            push_time=push_time,
            timezone=timezone,
        )
        session.add(subscription)
        session.flush()
        return subscription

    @staticmethod
    def get_active_subscriptions(session: Session) -> List[Subscription]:
        """Get all active subscriptions.

        Args:
            session: Database session

        Returns:
            List of active Subscription objects
        """
        return list(session.execute(
            select(Subscription).where(Subscription.is_active == True)
        ).scalars().all())

    @staticmethod
    def get_subscription_by_email(session: Session, email: str) -> Optional[Subscription]:
        """Get subscription by email.

        Args:
            session: Database session
            email: Email address

        Returns:
            Subscription object or None
        """
        return session.execute(
            select(Subscription).where(Subscription.user_email == email)
        ).scalar_one_or_none()

    @staticmethod
    def update_subscription(
        session: Session,
        subscription_id: int,
        **kwargs,
    ) -> Optional[Subscription]:
        """Update a subscription.

        Args:
            session: Database session
            subscription_id: Subscription ID
            **kwargs: Fields to update

        Returns:
            Updated Subscription or None
        """
        subscription = session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        ).scalar_one_or_none()

        if subscription:
            for key, value in kwargs.items():
                if hasattr(subscription, key):
                    setattr(subscription, key, value)

        return subscription


class PushLogCRUD:
    """CRUD operations for PushLog model."""

    @staticmethod
    def create_log(
        session: Session,
        subscription_id: int,
        channel: str,
        report_date: datetime,
        status: str,
        error_msg: Optional[str] = None,
    ) -> PushLog:
        """Create a push log entry.

        Args:
            session: Database session
            subscription_id: Subscription ID
            channel: Push channel
            report_date: Report date
            status: Status ('success' or 'failed')
            error_msg: Error message if failed

        Returns:
            Created PushLog object
        """
        log = PushLog(
            subscription_id=subscription_id,
            channel=channel,
            report_date=report_date,
            status=status,
            error_msg=error_msg,
        )
        session.add(log)
        session.flush()
        return log

    @staticmethod
    def was_pushed(
        session: Session,
        subscription_id: int,
        channel: str,
        report_date: datetime,
    ) -> bool:
        """Check if a report was already pushed.

        Args:
            session: Database session
            subscription_id: Subscription ID
            channel: Push channel
            report_date: Report date

        Returns:
            True if already pushed successfully
        """
        log = session.execute(
            select(PushLog).where(
                and_(
                    PushLog.subscription_id == subscription_id,
                    PushLog.channel == channel,
                    PushLog.report_date == report_date,
                    PushLog.status == "success",
                )
            )
        ).scalar_one_or_none()

        return log is not None

    @staticmethod
    def get_recent_pushes(
        session: Session,
        limit: int = 50,
    ) -> List[PushLog]:
        """Get recent push logs.

        Args:
            session: Database session
            limit: Max results

        Returns:
            List of PushLog objects
        """
        return list(session.execute(
            select(PushLog)
            .order_by(PushLog.created_at.desc())
            .limit(limit)
        ).scalars().all())
