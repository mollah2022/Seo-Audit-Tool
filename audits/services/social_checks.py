"""
Social metadata checks: Open Graph (Facebook/LinkedIn/etc.) and Twitter
Card tags. These control how a page looks when shared on social platforms
and are a common SEO-audit ask even though they're not a direct Google
ranking factor.
"""
from bs4 import BeautifulSoup

REQUIRED_OG_TAGS = ["og:title", "og:description", "og:image", "og:url"]


def run_checks(html: str, page_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        _check_open_graph(soup),
        _check_twitter_card(soup),
    ]


def _result(name, status, detail, recommendation=""):
    return {
        "category": "social",
        "name": name,
        "status": status,
        "detail": detail,
        "recommendation": recommendation,
    }


def _meta_content(soup, attr, value):
    tag = soup.find("meta", attrs={attr: value})
    return tag.get("content", "").strip() if tag else ""


def _check_open_graph(soup):
    found = {}
    missing = []
    for prop in REQUIRED_OG_TAGS:
        content = _meta_content(soup, "property", prop)
        if content:
            found[prop] = content
        else:
            missing.append(prop)

    if not found:
        return _result(
            "Open Graph tags", "fail",
            "No Open Graph tags found (og:title, og:description, og:image, og:url).",
            "Add Open Graph meta tags in <head> so links to this page render properly when shared on Facebook, LinkedIn, etc.",
        )
    if missing:
        return _result(
            "Open Graph tags", "warn",
            f"Missing: {', '.join(missing)}. Present: {', '.join(f'{k}=\"{v[:40]}\"' for k, v in found.items())}",
            f"Add the missing Open Graph tag(s): {', '.join(missing)}.",
        )
    preview = ", ".join(f'{k}="{v[:40]}"' for k, v in found.items())
    return _result("Open Graph tags", "pass", f"All required tags present \u2014 {preview}")


def _check_twitter_card(soup):
    card_type = _meta_content(soup, "name", "twitter:card")
    title = _meta_content(soup, "name", "twitter:title")
    description = _meta_content(soup, "name", "twitter:description")

    if not card_type:
        return _result(
            "Twitter Card tags", "warn",
            "No twitter:card meta tag found.",
            "Add <meta name=\"twitter:card\" content=\"summary_large_image\"> (plus twitter:title/description) so shares on X/Twitter render with a rich preview.",
        )

    missing = []
    if not title:
        missing.append("twitter:title")
    if not description:
        missing.append("twitter:description")

    if missing:
        return _result(
            "Twitter Card tags", "warn",
            f"twitter:card=\"{card_type}\" is set, but missing: {', '.join(missing)}.",
            f"Add the missing tag(s): {', '.join(missing)}.",
        )
    return _result(
        "Twitter Card tags", "pass",
        f"twitter:card=\"{card_type}\" with title and description present.",
    )
