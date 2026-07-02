"""
Performance checks. Load-time and page-size checks are derived from the
Playwright crawl itself, so they always run. If PAGESPEED_API_KEY is set
in .env, Core Web Vitals, the Lighthouse performance score, and Lighthouse
SEO best-practice audits are also pulled from Google's PageSpeed Insights
API. If no key is set, a single informational check explains that clearly
instead of silently omitting the section.
"""
import requests
from django.conf import settings

REQUEST_TIMEOUT = 20
PAGESPEED_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Individual Lighthouse "seo" category audits worth surfacing directly,
# beyond the single aggregate seo score.
SEO_AUDIT_IDS = [
    "meta-description",
    "document-title",
    "link-text",
    "is-crawlable",
    "hreflang",
    "canonical",
    "robots-txt",
]


def run_checks(crawl_result) -> list[dict]:
    checks = [
        _check_load_time(crawl_result.load_time_ms),
        _check_page_size(crawl_result.page_size_bytes),
    ]

    api_key = getattr(settings, "PAGESPEED_API_KEY", "")
    if not api_key:
        checks.append(_result(
            "Lighthouse SEO audit", "warn",
            "PAGESPEED_API_KEY is not set, so Core Web Vitals and Lighthouse's SEO best-practice audits were skipped.",
            "Get a free Google PageSpeed Insights API key and set PAGESPEED_API_KEY in .env to enable Core Web Vitals and Lighthouse SEO checks.",
        ))
    else:
        checks.extend(_check_pagespeed(crawl_result.final_url, api_key))

    return checks


def _result(name, status, detail, recommendation=""):
    return {
        "category": "performance",
        "name": name,
        "status": status,
        "detail": detail,
        "recommendation": recommendation,
    }


def _check_load_time(load_time_ms):
    seconds = load_time_ms / 1000
    if seconds <= 2.5:
        return _result("Page load time", "pass", f"{seconds:.2f}s to fully render.")
    if seconds <= 4:
        return _result(
            "Page load time", "warn",
            f"{seconds:.2f}s to fully render \u2014 aim for under 2.5s.",
            "Reduce render-blocking resources, compress images, and defer non-critical scripts to speed up initial render.",
        )
    return _result(
        "Page load time", "fail",
        f"{seconds:.2f}s to fully render \u2014 well above the 2.5s target.",
        "Investigate slow server response time, large uncompressed assets, and render-blocking scripts \u2014 this load time will hurt both rankings and users.",
    )


def _check_page_size(page_size_bytes):
    kb = page_size_bytes / 1024
    if kb <= 500:
        return _result("HTML page size", "pass", f"{kb:.0f} KB of HTML.")
    if kb <= 1000:
        return _result(
            "HTML page size", "warn",
            f"{kb:.0f} KB of HTML \u2014 consider trimming.",
            "Remove unused markup/inline scripts or split content across pages to reduce HTML payload size.",
        )
    return _result(
        "HTML page size", "fail",
        f"{kb:.0f} KB of HTML \u2014 significantly larger than typical.",
        "This page's HTML is unusually large \u2014 audit for excessive inline data, duplicated markup, or unminified content.",
    )


def _check_pagespeed(url, api_key):
    try:
        resp = requests.get(
            PAGESPEED_ENDPOINT,
            params=[
                ("url", url),
                ("key", api_key),
                ("strategy", "mobile"),
                ("category", "performance"),
                ("category", "seo"),
            ],
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        return [_result(
            "Lighthouse audit", "warn",
            f"PageSpeed Insights request failed: {exc}",
            "Verify the PAGESPEED_API_KEY is valid and the target URL is publicly reachable, then retry.",
        )]

    results = []
    lighthouse = data.get("lighthouseResult", {})
    categories = lighthouse.get("categories", {})
    audits = lighthouse.get("audits", {})

    results.extend(_score_check("Lighthouse performance score", categories.get("performance")))
    results.extend(_score_check("Lighthouse SEO score", categories.get("seo")))
    results.extend(_core_web_vitals(audits))
    results.extend(_seo_audit_details(audits))

    return results


def _score_check(name, category_data):
    if not category_data or category_data.get("score") is None:
        return []
    score = round(category_data["score"] * 100)
    status = "pass" if score >= 80 else "warn" if score >= 50 else "fail"
    recommendation = "" if status == "pass" else "Review the individual Lighthouse audits below for specific fixes."
    return [_result(name, status, f"{score} / 100", recommendation)]


def _core_web_vitals(audits):
    vitals = [
        ("largest-contentful-paint", "Largest Contentful Paint (LCP)"),
        ("cumulative-layout-shift", "Cumulative Layout Shift (CLS)"),
        ("interaction-to-next-paint", "Interaction to Next Paint (INP)"),
    ]
    results = []
    for audit_id, label in vitals:
        audit = audits.get(audit_id)
        if not audit or audit.get("score") is None:
            continue
        score = audit["score"]
        status = "pass" if score >= 0.9 else "warn" if score >= 0.5 else "fail"
        display_value = audit.get("displayValue", "")
        recommendation = "" if status == "pass" else f"Improve {label} \u2014 see Google's Core Web Vitals guidance for this metric."
        results.append(_result(label, status, display_value or "See PageSpeed Insights for details.", recommendation))
    return results


def _seo_audit_details(audits):
    results = []
    for audit_id in SEO_AUDIT_IDS:
        audit = audits.get(audit_id)
        if not audit or audit.get("score") is None:
            continue
        score = audit["score"]
        status = "pass" if score == 1 else "fail"
        title = audit.get("title", audit_id)
        description = audit.get("displayValue") or ("Passed" if status == "pass" else "Failed \u2014 see Lighthouse report for details.")
        recommendation = "" if status == "pass" else f"Address the \u201c{title}\u201d issue flagged by Lighthouse's SEO audit."
        results.append(_result(f"Lighthouse SEO: {title}", status, description, recommendation))
    return results
