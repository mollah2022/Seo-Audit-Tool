"""
Wraps Playwright: launches a headless Chromium browser, navigates to the
target URL, and returns the rendered HTML plus basic timing/response info
that the checks modules need.

NOTE: this uses Playwright's sync API, which is fine to call directly from
a Django view for a single-page audit (a full audit takes a few seconds).
If you later move audit execution into a Celery task, this function's
signature doesn't need to change.
"""
import time
from dataclasses import dataclass

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


class CrawlError(Exception):
    """Raised when the target page can't be fetched or rendered."""


@dataclass
class CrawlResult:
    url: str
    final_url: str
    html: str
    status_code: int | None
    load_time_ms: int
    page_size_bytes: int
    is_https: bool


def _launch_browser(playwright):
    """
    Prefer a system-installed Chrome/Chromium (via Playwright's "channel"
    option) so we don't depend on downloading Playwright's own browser
    build, which some networks block. Falls back to the bundled Chromium
    if no system browser/channel is available.
    """
    for channel in ("chrome", "chromium"):
        try:
            return playwright.chromium.launch(headless=True, channel=channel)
        except Exception:
            continue
    return playwright.chromium.launch(headless=True)


def crawl(url: str, timeout_ms: int = 45000) -> CrawlResult:
    start = time.monotonic()

    try:
        with sync_playwright() as p:
            browser = _launch_browser(p)
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (compatible; SEOAuditTool/1.0; "
                        "+https://example.com/bot)"
                    ),
                )
                page = context.new_page()
                try:
                    response = page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                except PlaywrightTimeoutError:
                    # Some large or highly dynamic sites never reach a full
                    # network idle state. Fall back to DOM content loaded so
                    # the audit can still inspect the page.
                    response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                html = page.content()
                final_url = page.url
                status_code = response.status if response else None
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise CrawlError(f"Timed out loading {url}") from exc
    except Exception as exc:  # noqa: BLE001 - surface any launch/navigation failure clearly
        raise CrawlError(f"Could not load {url}: {exc}") from exc

    load_time_ms = int((time.monotonic() - start) * 1000)

    return CrawlResult(
        url=url,
        final_url=final_url,
        html=html,
        status_code=status_code,
        load_time_ms=load_time_ms,
        page_size_bytes=len(html.encode("utf-8")),
        is_https=final_url.startswith("https://"),
    )
