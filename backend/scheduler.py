"""
Scraping scheduler — runs the ScraperManager on a configurable interval.

Uses APScheduler's AsyncIOScheduler. If APScheduler is not installed the
application still starts; scheduling is simply disabled.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_scheduler: Optional[object] = None


async def _run_scraping_job() -> None:
    """Job callback: instantiate ScraperManager and run a full scan."""
    from backend.scraping.scraper_manager import ScraperManager

    logger.info("Scheduled scraping job started")
    try:
        manager = ScraperManager()
        oportunidades = await manager.run()
        logger.info(
            "Scheduled scraping job finished: %d opportunities found",
            len(oportunidades),
        )
    except Exception as exc:
        logger.error("Scheduled scraping job failed: %s", exc)


def start_scheduler() -> None:
    """Start the APScheduler background scheduler."""
    global _scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from backend.config.settings import settings

        _scheduler = AsyncIOScheduler()
        _scheduler.add_job(
            _run_scraping_job,
            "interval",
            minutes=settings.SCRAPING_INTERVAL_MINUTES,
            id="scraping_full_scan",
            replace_existing=True,
            name="Full scraping scan",
        )
        _scheduler.start()
        logger.info(
            "Scheduler started — scraping every %d minutes",
            settings.SCRAPING_INTERVAL_MINUTES,
        )
    except ImportError:
        logger.warning(
            "APScheduler not installed — scraping scheduler is disabled. "
            "Install with: pip install apscheduler"
        )
    except Exception as exc:
        logger.error("Failed to start scheduler: %s", exc)


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
        except Exception as exc:
            logger.error("Error stopping scheduler: %s", exc)
        _scheduler = None
