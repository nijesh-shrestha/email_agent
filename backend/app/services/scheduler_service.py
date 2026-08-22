"""Background scheduler service for sending scheduled emails."""

import asyncio
import logging
from datetime import timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.database.models import ScheduledEmail, ScheduledEmailStatus
from app.services.gmail_service import send_email
from app.utils.timezone import now_npt

logger = logging.getLogger(__name__)


class EmailScheduler:
    """Background scheduler that checks for and sends scheduled emails."""

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval = check_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Email scheduler started (checking every {self.check_interval} seconds)")

    async def stop(self):
        """Stop the background scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Email scheduler stopped")

    async def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_and_send_emails()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")

            await asyncio.sleep(self.check_interval)

    async def _check_and_send_emails(self):
        """Check for due scheduled emails and send them."""
        db = SessionLocal()
        try:
            now = now_npt()

            # Find all pending emails that are due
            # Database stores timezone-naive UTC values.
            now_naive = now.astimezone(timezone.utc).replace(tzinfo=None)

            due_emails = (
                db.query(ScheduledEmail)
                .filter(ScheduledEmail.status == ScheduledEmailStatus.PENDING.upper())
                .filter(ScheduledEmail.scheduled_date <= now_naive)
                .all()
            )

            if not due_emails:
                return

            logger.info(f"Found {len(due_emails)} scheduled email(s) to send")

            for email in due_emails:
                await self._send_scheduled_email(db, email)

        except Exception as e:
            logger.error(f"Error checking scheduled emails: {e}")
        finally:
            db.close()

    async def _send_scheduled_email(self, db: Session, email: ScheduledEmail):
        """Send a single scheduled email."""
        try:
            # Send the email
            ok, payload = send_email(
                db,
                email.user_id,
                email.recipient,
                email.subject,
                email.body,
            )


            if ok:
                email.status = ScheduledEmailStatus.SENT
                email.sent_at = now_npt()
                email.message_id = payload.get("message_id")
                logger.info(
                    f"Scheduled email {email.id} sent successfully to {email.recipient}"
                )
            else:
                email.status = ScheduledEmailStatus.FAILED
                email.error_message = payload.get("detail", "Unknown error")
                logger.error(
                    f"Failed to send scheduled email {email.id}: {email.error_message}"
                )

            db.commit()

        except Exception as e:
            logger.error(f"Exception sending scheduled email {email.id}: {e}")
            email.status = ScheduledEmailStatus.FAILED
            email.error_message = str(e)
            db.commit()


# Global scheduler instance
scheduler = EmailScheduler(check_interval_seconds=60)


async def start_scheduler():
    """Start the email scheduler."""
    await scheduler.start()


async def stop_scheduler():
    """Stop the email scheduler."""
    await scheduler.stop()