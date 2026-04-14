"""Scheduler for automated paper pipeline execution."""

import logging
import sys
from datetime import datetime, time
from typing import Callable, Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('paper_pusher.log'),
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


class PaperPipelineScheduler:
    """Scheduler for running the paper pipeline on a schedule."""

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BlockingScheduler()
        logger.info("Scheduler initialized")

    def add_daily_job(
        self,
        job_func: Callable,
        hour: int = 2,
        minute: int = 0,
        job_id: str = "daily_paper_fetch",
    ) -> None:
        """Add a daily job to run at a specific time.

        Args:
            job_func: Function to execute
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            job_id: Unique job identifier
        """
        trigger = CronTrigger(hour=hour, minute=minute)
        self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name="Daily Paper Fetch Job",
            replace_existing=True,
        )
        logger.info(f"Added daily job '{job_id}' to run at {hour:02d}:{minute:02d}")

    def add_interval_job(
        self,
        job_func: Callable,
        minutes: int = 60,
        job_id: str = "interval_fetch",
    ) -> None:
        """Add an interval job to run periodically.

        Args:
            job_func: Function to execute
            minutes: Interval in minutes
            job_id: Unique job identifier
        """
        self.scheduler.add_job(
            job_func,
            'interval',
            minutes=minutes,
            id=job_id,
            name=f"Interval Job ({minutes} min)",
            replace_existing=True,
        )
        logger.info(f"Added interval job '{job_id}' to run every {minutes} minutes")

    def add_cron_job(
        self,
        job_func: Callable,
        cron_expression: str,
        job_id: str = "cron_fetch",
    ) -> None:
        """Add a cron job with custom expression.

        Args:
            job_func: Function to execute
            cron_expression: Cron expression (e.g., "0 */2 * * *" for every 2 hours)
            job_id: Unique job identifier
        """
        # Parse cron expression (simple format: "min hour day month dow")
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        minute, hour, day, month, day_of_week = parts

        trigger = CronTrigger(
            minute=int(minute) if minute != '*' else None,
            hour=int(hour) if hour != '*' else None,
            day=int(day) if day != '*' else None,
            month=int(month) if month != '*' else None,
            day_of_week=int(day_of_week) if day_of_week != '*' else None,
        )

        self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=f"Cron Job ({cron_expression})",
            replace_existing=True,
        )
        logger.info(f"Added cron job '{job_id}' with expression '{cron_expression}'")

    def remove_job(self, job_id: str) -> None:
        """Remove a job by ID.

        Args:
            job_id: Job identifier to remove
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job '{job_id}'")
        except Exception as e:
            logger.warning(f"Failed to remove job '{job_id}': {e}")

    def list_jobs(self) -> list:
        """List all scheduled jobs.

        Returns:
            List of job information dictionaries
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time,
            })
        return jobs

    def start(self) -> None:
        """Start the scheduler (blocking)."""
        logger.info("Starting scheduler...")
        logger.info(f"Scheduled jobs: {len(self.scheduler.get_jobs())}")

        for job in self.scheduler.get_jobs():
            logger.info(f"  - {job.id}: {job.name} (next: {job.next_run_time})")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            raise

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler.

        Args:
            wait: Wait for jobs to complete
        """
        logger.info("Shutting down scheduler...")
        self.scheduler.shutdown(wait=wait)


def create_scheduler(
    daily_hour: int = 2,
    daily_minute: int = 0,
) -> PaperPipelineScheduler:
    """Create and configure a scheduler with default daily job.

    Args:
        daily_hour: Hour for daily job (default: 2 AM)
        daily_minute: Minute for daily job (default: 0)

    Returns:
        Configured PaperPipelineScheduler instance
    """
    scheduler = PaperPipelineScheduler()

    # Note: Jobs need to be added separately with add_daily_job()
    # This function just creates and returns the configured scheduler

    return scheduler
