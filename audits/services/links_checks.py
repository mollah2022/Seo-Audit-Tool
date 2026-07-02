"""
Link checks: counts internal vs. external links, and (optionally, capped)
checks a sample of links for broken status codes. Broken-link checking is
network-heavy, so it's capped at MAX_LINKS_TO_VERIFY to keep audit time
reasonable — this mirrors the assignment's "broken links (optional)" item.
"""
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 6
MAX_LINKS_TO_VERIFY = 15
SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "#")


def run_checks(html: str, page_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    page_domain = urlparse(page_url).netloc.lower()

    internal, external = _collect_links(soup, page_url, page_domain)

    checks = [
        _check_link_counts(internal, external),
    ]
    checks.append(_check_broken_links(internal, external))
    return checks


def _result(name, status, detail, recommendation=""):
    return {
        "category": "links",
        "name": name,
        "status": status,
        "detail": detail,
        "recommendation": recommendation,
    }


def _collect_links(soup, page_url, page_domain):
    internal, external = [], []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(SKIP_SCHEMES):
            continue

        absolute = urljoin(page_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)

        link_domain = urlparse(absolute).netloc.lower()
        if link_domain == page_domain or not link_domain:
            internal.append(absolute)
        else:
            external.append(absolute)

    return internal, external


def _check_link_counts(internal, external):
    total = len(internal) + len(external)

    if total == 0:
        return _result(
            "Internal & external links", "warn",
            "No links found on the page.",
            "Add internal links to related pages to help both users and search engines discover more of your content.",
        )

    detail = f"{len(internal)} internal link(s), {len(external)} external link(s)."
    if len(internal) == 0:
        return _result(
            "Internal & external links", "warn",
            detail,
            "Add internal links to other pages on your site \u2014 this helps search engines crawl and understand your site structure.",
        )
    return _result("Internal & external links", "pass", detail)


def _check_broken_links(internal, external):
    candidates = (internal + external)[:MAX_LINKS_TO_VERIFY]
    if not candidates:
        return _result(
            "Broken links", "pass",
            "No links to verify.",
        )

    broken = []
    checked = 0
    for link in candidates:
        checked += 1
        status_code = _fetch_status(link)
        if status_code is None or status_code >= 400:
            broken.append((link, status_code))

    skipped_note = ""
    total_links = len(internal) + len(external)
    if total_links > MAX_LINKS_TO_VERIFY:
        skipped_note = f" (checked the first {MAX_LINKS_TO_VERIFY} of {total_links} links)"

    if not broken:
        return _result(
            "Broken links", "pass",
            f"All {checked} checked link(s) responded successfully{skipped_note}.",
        )

    sample = "; ".join(
        f"{url} \u2192 {code if code else 'no response'}" for url, code in broken[:5]
    )
    status = "fail" if len(broken) > 2 else "warn"
    return _result(
        "Broken links", status,
        f"{len(broken)} of {checked} checked link(s) appear broken{skipped_note}: {sample}",
        "Fix or remove the broken links listed above \u2014 broken links hurt both user experience and crawl efficiency.",
    )


def _fetch_status(url):
    try:
        resp = requests.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code == 405:
            # Some servers reject HEAD; fall back to a lightweight GET.
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True, stream=True)
        return resp.status_code
    except requests.RequestException:
        return None
