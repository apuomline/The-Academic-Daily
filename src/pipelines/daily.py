"""Daily report pipeline implementation."""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from config import settings
from src.database import db_manager, PaperCRUD, SubscriptionCRUD, PushLogCRUD
from src.fetchers import ArXivFetcher, OpenAlexFetcher, SemanticScholarFetcher
from src.parsers import PaperParser, PDFParser
from src.summarizers import create_summarizer, SummaryResult
from src.pipelines.template_renderer import TemplateRenderer
from src.pushers import EmailPusher

logger = logging.getLogger(__name__)


class DailyReportPipeline:
    """Pipeline for generating and delivering daily paper reports."""

    def __init__(self):
        """Initialize the pipeline."""
        self.parser = PaperParser()
        self.renderer = TemplateRenderer()
        self.summarizer = create_summarizer(
            provider=settings.llm_provider,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.get_api_key(),
            base_url=settings.get_base_url(),
        )

        # Initialize fetchers
        self.fetchers = {
            "arxiv": ArXivFetcher(
                api_url=settings.arxiv_api_url,
                max_results=settings.arxiv_max_results,
            ),
            "openalex": OpenAlexFetcher(),
            "semantic_scholar": SemanticScholarFetcher(),
        }

        # Initialize email pusher
        self.email_pusher = None
        if settings.email_enabled:
            try:
                self.email_pusher = EmailPusher()
                logger.info("Email pusher initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize email pusher: {e}")

    def fetch_papers(
        self,
        keywords: List[str],
        exclude_keywords: Optional[List[str]] = None,
        session: Optional[Session] = None,
    ) -> List:
        """Fetch papers from all sources.

        Args:
            keywords: Keywords to search for
            exclude_keywords: Keywords to exclude
            session: Database session (optional)

        Returns:
            List of Paper objects
        """
        all_papers = []

        # Fetch from each source
        for source_name, fetcher in self.fetchers.items():
            try:
                logger.info(f"Fetching from {source_name}...")

                if source_name == "arxiv":
                    papers = fetcher.fetch(" ".join(keywords))
                elif source_name == "openalex":
                    # Use date filter for recent papers
                    papers = fetcher.fetch(" ".join(keywords))
                else:  # semantic_scholar
                    papers = fetcher.fetch(" ".join(keywords))

                logger.info(f"  Fetched {len(papers)} papers from {source_name}")
                all_papers.extend(papers)

            except Exception as e:
                logger.error(f"  Failed to fetch from {source_name}: {e}")

        # Process papers (deduplicate, filter, etc.)
        processed_papers = self.parser.parse_and_process(
            all_papers,
            merge_versions=True,
            filter_keywords=keywords,
            exclude_keywords=exclude_keywords,
        )

        logger.info(f"Total papers after processing: {len(processed_papers)}")

        # Save to database if session provided
        if session:
            self._save_papers_to_db(session, processed_papers)

        return processed_papers

    def _save_papers_to_db(self, session: Session, papers: List) -> None:
        """Save papers to database.

        Args:
            session: Database session
            papers: List of Paper objects
        """
        saved_count = 0
        for paper in papers:
            try:
                # Check if paper already exists
                existing = None
                if paper.arxiv_id:
                    existing = PaperCRUD.get_paper_by_arxiv_id(session, paper.arxiv_id)

                if not existing and paper.doi:
                    existing = PaperCRUD.get_paper_by_doi(session, paper.doi)

                if existing:
                    # Update existing paper
                    existing.title = paper.title
                    existing.abstract = paper.abstract
                    existing.updated_date = datetime.fromisoformat(paper.updated) if paper.updated else None
                else:
                    # Create new paper
                    PaperCRUD.create_paper(
                        session,
                        arxiv_id=paper.arxiv_id,
                        doi=getattr(paper, 'doi', None),
                        title=paper.title,
                        abstract=paper.abstract,
                        source=paper.source,
                        published_date=datetime.fromisoformat(paper.published) if paper.published else None,
                        updated_date=datetime.fromisoformat(paper.updated) if paper.updated else None,
                    )
                    saved_count += 1

            except Exception as e:
                logger.warning(f"Failed to save paper to DB: {e}")

        try:
            session.commit()
            logger.info(f"Saved {saved_count} new papers to database")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to commit papers to database: {e}")

    def generate_report(
        self,
        papers: List,
        keywords: List[str],
        report_date: Optional[str] = None,
    ) -> tuple:
        """Generate report in multiple formats.

        Args:
            papers: List of Paper objects
            keywords: Search keywords
            report_date: Report date string (defaults to today)

        Returns:
            Tuple of (markdown_content, html_content, text_content)
        """
        if not report_date:
            report_date = datetime.now().strftime("%Y-%m-%d")

        generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Generate summaries if papers don't have them
        papers_with_summaries = self._ensure_summaries(papers)

        # Render in different formats
        markdown = self.renderer.render_markdown(
            papers_with_summaries,
            keywords,
            report_date,
            generation_time,
        )

        html = self.renderer.render_html_email(
            papers_with_summaries,
            keywords,
            report_date,
            generation_time,
        )

        text = self.renderer.render_summary_text(
            papers_with_summaries,
            keywords,
        )

        return markdown, html, text

    def _ensure_summaries(self, papers: List) -> List:
        """Ensure all papers have summary content using structured LLM output.

        Args:
            papers: List of Paper objects

        Returns:
            List of papers with summaries
        """
        pdf_parser = PDFParser()
        papers_to_keep = []

        for paper in papers:
            # Skip if already has structured summary
            if hasattr(paper, 'summary_structured') and paper.summary_structured:
                papers_to_keep.append(paper)
                continue

            try:
                # Try to download and parse PDF for introduction
                intro_text = None
                if paper.pdf_url:
                    result = pdf_parser.parse_paper(paper.arxiv_id, paper.pdf_url)
                    intro_text = result.get("intro_text")

                    # Skip paper if PDF download failed
                    if not result.get("success"):
                        logger.warning(f"PDF download failed for {paper.arxiv_id}, skipping paper")
                        continue

                # Call LLM to generate structured summary
                summary_result = self.summarizer.summarize_structured(
                    title=paper.title,
                    abstract=paper.abstract,
                    intro_text=intro_text,
                )

                if summary_result.success:
                    paper.summary_structured = summary_result.summary
                    paper.summary_content = summary_result.summary.abstract_translation
                    papers_to_keep.append(paper)
                else:
                    logger.warning(f"Failed to summarize paper {paper.arxiv_id}: {summary_result.error}")

            except Exception as e:
                logger.warning(f"Error processing paper {paper.arxiv_id}: {e}")

        return papers_to_keep if papers_to_keep else papers

    def send_reports(
        self,
        html_content: str,
        text_content: str,
        subject: str,
        session: Optional[Session] = None,
    ) -> dict:
        """Send reports to all active subscribers.

        Args:
            html_content: HTML email content
            text_content: Plain text content
            subject: Email subject
            session: Database session

        Returns:
            Dictionary with send results
        """
        results = {"success": 0, "failed": 0, "details": []}

        if not self.email_pusher:
            logger.warning("Email pusher not configured, skipping email delivery")
            return results

        # Get active subscriptions
        if session:
            subscriptions = SubscriptionCRUD.get_active_subscriptions(session)
        else:
            logger.warning("No database session provided, using default email")
            # Use default email from settings
            subscriptions = []

        # If no subscriptions in DB, check for default email
        if not subscriptions and settings.smtp_from_email:
            # Send to the from_email as a test
            send_results = self.email_pusher.send_report(
                [settings.smtp_from_email],
                subject,
                html_content,
                text_content,
            )
            return self._process_send_results(send_results, results)

        for subscription in subscriptions:
            # Check if already sent today
            if session:
                report_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                if PushLogCRUD.was_pushed(
                    session,
                    subscription.id,
                    "email",
                    report_date,
                ):
                    logger.info(f"Already sent to {subscription.user_email} today, skipping")
                    continue

            # Send email
            send_results = self.email_pusher.send_report(
                [subscription.user_email],
                subject,
                html_content,
                text_content,
            )

            # Log results
            self._log_push_results(session, subscription.id, send_results, report_date)

            # Aggregate results
            send_summary = self._process_send_results(send_results, {})
            results["success"] += send_summary["success"]
            results["failed"] += send_summary["failed"]
            results["details"].extend(send_summary.get("details", []))

        return results

    def _process_send_results(self, send_results: dict, results: dict) -> dict:
        """Process send results from email pusher.

        Args:
            send_results: Results from EmailPusher.send_report
            results: Results dictionary to update

        Returns:
            Updated results dictionary
        """
        if "success" in send_results:
            results["success"] = len(send_results["success"])
        if "failed" in send_results:
            results["failed"] = len(send_results["failed"])

        details = []
        for email in send_results.get("success", []):
            details.append({"email": email, "status": "success"})
        for fail in send_results.get("failed", []):
            details.append({"email": fail.get("email"), "status": "failed", "error": fail.get("error")})

        if details:
            results["details"] = results.get("details", []) + details

        return results

    def _log_push_results(
        self,
        session: Session,
        subscription_id: int,
        send_results: dict,
        report_date: datetime,
    ) -> None:
        """Log push results to database.

        Args:
            session: Database session
            subscription_id: Subscription ID
            send_results: Results from EmailPusher.send_report
            report_date: Report date
        """
        if not session:
            return

        # Determine overall status
        if send_results.get("failed") and not send_results.get("success"):
            status = "failed"
            error_msg = str(send_results["failed"][0].get("error")) if send_results["failed"] else None
        else:
            status = "success"
            error_msg = None

        # Create log entry
        PushLogCRUD.create_log(
            session,
            subscription_id=subscription_id,
            channel="email",
            report_date=report_date,
            status=status,
            error_msg=error_msg,
        )

        try:
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log push results: {e}")

    def run_daily_pipeline(
        self,
        keywords: List[str],
        exclude_keywords: Optional[List[str]] = None,
        subject: Optional[str] = None,
    ) -> dict:
        """Run the complete daily pipeline.

        Args:
            keywords: Keywords to search for
            exclude_keywords: Keywords to exclude
            subject: Email subject (auto-generated if None)

        Returns:
            Pipeline results dictionary
        """
        logger.info("Starting daily pipeline...")
        start_time = datetime.now()

        results = {
            "papers_fetched": 0,
            "reports_generated": False,
            "emails_sent": 0,
            "emails_failed": 0,
            "errors": [],
        }

        # Create database session
        session = db_manager.get_session()

        try:
            # Fetch papers
            papers = self.fetch_papers(keywords, exclude_keywords, session)
            results["papers_fetched"] = len(papers)

            if not papers:
                logger.warning("No papers found, skipping report generation")
                return results

            # Generate report
            markdown, html, text = self.generate_report(papers, keywords)
            results["reports_generated"] = True

            # Generate subject if not provided
            if not subject:
                subject = f"学术日报 {datetime.now().strftime('%Y年%m月%d日')} - {keywords[0]}"

            # Send reports
            send_results = self.send_reports(html, text, subject, session)
            results["emails_sent"] = send_results.get("success", 0)
            results["emails_failed"] = send_results.get("failed", 0)

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results["errors"].append(str(e))

        finally:
            session.close()

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Pipeline completed in {duration:.2f}s")
        logger.info(f"Results: {results}")

        return results
