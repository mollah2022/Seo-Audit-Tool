"""
Ties the crawler and all check modules together, then saves everything to
the database. Called synchronously from the view for v1 — a single-page
audit completes in a few seconds, which is fine for a request/response
cycle. If you later add Celery, this function's signature can stay mostly
the same; you'd just call it from a task instead of the view.
"""
import logging
from urllib.parse import urlparse

from django.db import transaction

from ..models import Audit, CheckResult
from . import (
    links_checks,
    onpage_checks,
    performance_checks,
    scoring,
    social_checks,
    technical_checks,
)
from .crawler import CrawlError, crawl

logger = logging.getLogger(__name__)


def run_audit(audit: Audit) -> Audit:
    audit.status = Audit.Status.RUNNING
    audit.save(update_fields=["status", "updated_at"])

    try:
        crawl_result = crawl(audit.url)
    except CrawlError as exc:
        logger.warning("Crawl failed for %s: %s", audit.url, exc)
        audit.status = Audit.Status.FAILED
        audit.error_message = str(exc)
        audit.save(update_fields=["status", "error_message", "updated_at"])
        return audit

    check_dicts = []
    check_dicts.extend(onpage_checks.run_checks(crawl_result.html, crawl_result.final_url))
    check_dicts.extend(technical_checks.run_checks(crawl_result.html, crawl_result.final_url))
    check_dicts.extend(social_checks.run_checks(crawl_result.html, crawl_result.final_url))
    check_dicts.extend(links_checks.run_checks(crawl_result.html, crawl_result.final_url))
    check_dicts.extend(performance_checks.run_checks(crawl_result))

    overall_score = scoring.compute_overall_score(check_dicts)
    band, label = scoring.score_band(overall_score)

    with transaction.atomic():
        audit.domain = urlparse(crawl_result.final_url).hostname or audit.domain
        audit.overall_score = overall_score
        audit.score_band = band
        audit.score_label = label
        audit.status = Audit.Status.DONE
        audit.save()

        CheckResult.objects.bulk_create(
            [
                CheckResult(
                    audit=audit,
                    category=c["category"],
                    name=c["name"],
                    status=c["status"],
                    detail=c["detail"],
                    recommendation=c.get("recommendation", ""),
                )
                for c in check_dicts
            ]
        )

    return audit
