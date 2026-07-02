"""
Technical SEO checks: HTTPS, robots.txt (file), XML sitemap, mobile
viewport tag, structured data (Schema.org / JSON-LD). robots.txt/sitemap
use `requests` (simple GETs) rather than Playwright, since they don't need
a rendered browser.

Note: this is distinct from the page-level <meta name="robots"> tag, which
is checked in onpage_checks.py.
"""
import json
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 10


def run_checks(html: str, page_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        _check_https(page_url),
        _check_robots_txt(page_url),
        _check_sitemap(page_url),
        _check_viewport(soup),
        _check_structured_data(soup),
    ]


def _result(name, status, detail, recommendation=""):
    return {
        "category": "technical",
        "name": name,
        "status": status,
        "detail": detail,
        "recommendation": recommendation,
    }


def _check_https(page_url):
    if page_url.startswith("https://"):
        return _result("HTTPS", "pass", "The page is served over HTTPS.")
    return _result(
        "HTTPS", "fail",
        "The page is not served over HTTPS.",
        "Serve the site over HTTPS \u2014 it's a confirmed Google ranking signal and required for most modern browser features.",
    )


def _check_robots_txt(page_url):
    robots_url = urljoin(page_url, "/robots.txt")
    try:
        resp = requests.get(robots_url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return _result(
            "robots.txt", "warn",
            f"Could not fetch {robots_url}: {exc}",
            "Make sure /robots.txt is reachable so crawlers can read your crawl directives.",
        )

    if resp.status_code == 200 and resp.text.strip():
        return _result("robots.txt", "pass", f"{robots_url} \u2014 200 OK")
    return _result(
        "robots.txt", "fail",
        f"{robots_url} returned {resp.status_code}.",
        "Add a robots.txt file at the site root, even a permissive one, so crawlers get an explicit answer instead of a 404.",
    )


def _check_sitemap(page_url):
    sitemap_url = urljoin(page_url, "/sitemap.xml")
    try:
        resp = requests.get(sitemap_url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return _result(
            "XML sitemap", "warn",
            f"Could not fetch {sitemap_url}: {exc}",
            "Make sure /sitemap.xml is reachable so search engines can discover all your pages.",
        )

    if resp.status_code == 200:
        return _result("XML sitemap", "pass", f"{sitemap_url} \u2014 200 OK")
    return _result(
        "XML sitemap", "fail",
        f"{sitemap_url} returned {resp.status_code}.",
        "Generate an XML sitemap and publish it at /sitemap.xml (and reference it from robots.txt) to help search engines discover your pages.",
    )


def _check_viewport(soup):
    tag = soup.find("meta", attrs={"name": "viewport"})
    content = tag.get("content", "").strip() if tag else ""

    if not content:
        return _result(
            "Mobile viewport", "fail",
            "No mobile viewport meta tag found.",
            "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> so the page renders correctly on mobile \u2014 required for Google's mobile-first indexing.",
        )
    return _result("Mobile viewport", "pass", f"viewport content: {content}")


def _check_structured_data(soup):
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not scripts:
        return _result(
            "Structured data", "warn",
            "No JSON-LD structured data found.",
            "Add Schema.org structured data (JSON-LD) relevant to your content type (Article, Product, Organization, etc.) to become eligible for rich results.",
        )

    valid_types = []
    invalid_count = 0
    for script in scripts:
        raw = script.string or script.get_text() or ""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            invalid_count += 1
            continue

        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            if isinstance(entry, dict):
                schema_type = entry.get("@type")
                if schema_type:
                    valid_types.append(
                        schema_type if isinstance(schema_type, str) else ",".join(schema_type)
                    )
                elif "@context" not in entry:
                    invalid_count += 1

    if invalid_count and not valid_types:
        return _result(
            "Structured data", "fail",
            f"{len(scripts)} JSON-LD block(s) found, but {invalid_count} could not be parsed or are missing @type.",
            "Fix the malformed JSON-LD and make sure each block includes a valid @type (validate with Google's Rich Results Test).",
        )
    if invalid_count:
        return _result(
            "Structured data", "warn",
            f"Found valid types ({', '.join(valid_types[:5])}) but {invalid_count} block(s) had issues.",
            "Review the JSON-LD blocks that failed to parse and fix their @type/@context values.",
        )
    return _result(
        "Structured data", "pass",
        f"{len(scripts)} JSON-LD block(s) found with type(s): {', '.join(valid_types[:5]) or 'unspecified'}.",
    )
