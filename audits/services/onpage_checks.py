"""
On-page SEO checks: title tag, meta description, headings, alt text,
canonical tag, robots meta tag, word count. Pure HTML parsing, no network
calls — this is the easiest module to unit test directly.
"""
from bs4 import BeautifulSoup


def run_checks(html: str, page_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        _check_title(soup),
        _check_meta_description(soup),
        _check_h1(soup),
        _check_heading_hierarchy(soup),
        _check_alt_text(soup),
        _check_word_count(soup),
        _check_canonical(soup),
        _check_robots_meta(soup),
        _check_lang_attribute(soup),
    ]


def _result(name, status, detail, recommendation=""):
    return {
        "category": "on_page",
        "name": name,
        "status": status,
        "detail": detail,
        "recommendation": recommendation,
    }


def _check_title(soup):
    tag = soup.find("title")
    text = tag.get_text(strip=True) if tag else ""
    length = len(text)

    if not text:
        return _result(
            "Title tag", "fail",
            "No <title> tag found on the page.",
            "Add a <title> tag inside <head> with a unique, descriptive page title, ideally 50-60 characters.",
        )
    if length < 30:
        return _result(
            "Title tag", "warn",
            f"\u201c{text}\u201d \u2014 {length} characters, shorter than the recommended 50-60.",
            "Expand the title to better describe the page's content and target keywords, aiming for 50-60 characters.",
        )
    if length > 60:
        return _result(
            "Title tag", "warn",
            f"\u201c{text}\u201d \u2014 {length} characters, longer than the recommended 50-60.",
            "Shorten the title so it doesn't get truncated in search results \u2014 aim for 50-60 characters.",
        )
    return _result("Title tag", "pass", f"\u201c{text}\u201d \u2014 {length} characters, within range.")


def _check_meta_description(soup):
    tag = soup.find("meta", attrs={"name": "description"})
    content = tag.get("content", "").strip() if tag else ""
    length = len(content)

    if not content:
        return _result(
            "Meta description", "fail",
            "No meta description found.",
            "Add <meta name=\"description\" content=\"...\"> in <head> with a 150-160 character summary of the page.",
        )
    if length < 120:
        return _result(
            "Meta description", "warn",
            f"{length} characters, shorter than the recommended 150-160.",
            "Expand the meta description to make better use of the search snippet space, aiming for 150-160 characters.",
        )
    if length > 160:
        return _result(
            "Meta description", "warn",
            f"{length} characters, longer than the recommended 150-160.",
            "Trim the meta description so it isn't cut off in search results \u2014 aim for 150-160 characters.",
        )
    return _result("Meta description", "pass", f"{length} characters, within the 150-160 range.")


def _check_h1(soup):
    h1s = soup.find_all("h1")
    count = len(h1s)

    if count == 0:
        return _result(
            "H1 tag", "fail",
            "No H1 tag found on the page.",
            "Add a single <h1> that clearly states the page's main topic.",
        )
    if count > 1:
        sample = ", ".join(f"\u201c{h.get_text(strip=True)[:40]}\u201d" for h in h1s[:3])
        return _result(
            "H1 tag", "warn",
            f"{count} H1 tags found \u2014 only one is recommended. Found: {sample}",
            "Keep only one <h1> per page and demote the others to <h2>/<h3> as appropriate.",
        )
    return _result("H1 tag", "pass", f"Exactly one H1: \u201c{h1s[0].get_text(strip=True)}\u201d")


def _check_heading_hierarchy(soup):
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    levels = [int(h.name[1]) for h in headings]

    if not levels:
        return _result(
            "Heading hierarchy", "warn",
            "No headings found on the page.",
            "Structure the content with headings (H1 for the main title, H2/H3 for sections) to help both users and search engines parse the page.",
        )

    skipped_at = None
    for a, b, heading in zip(levels, levels[1:], headings[1:]):
        if b - a > 1:
            skipped_at = (a, b, heading.get_text(strip=True)[:40])
            break

    if skipped_at:
        prev_level, next_level, text = skipped_at
        return _result(
            "Heading hierarchy", "warn",
            f"Heading level jumps from H{prev_level} to H{next_level} at \u201c{text}\u201d.",
            "Don't skip heading levels (e.g. H2 straight to H4) \u2014 it breaks the document outline for screen readers and search engines.",
        )
    return _result("Heading hierarchy", "pass", f"{len(levels)} headings found in a logical order.")


def _check_alt_text(soup):
    images = soup.find_all("img")
    total = len(images)
    missing_imgs = [img for img in images if not img.get("alt", "").strip()]
    missing = len(missing_imgs)

    if total == 0:
        return _result("Image alt text", "pass", "No images found on the page.")
    if missing == 0:
        return _result("Image alt text", "pass", f"All {total} images have alt text.")

    sample_srcs = [img.get("src", "unknown-src")[:60] for img in missing_imgs[:3]]
    sample_text = "; ".join(sample_srcs)
    if missing == total:
        return _result(
            "Image alt text", "fail",
            f"None of the {total} images have alt text. Examples: {sample_text}",
            "Add a descriptive alt attribute to every <img> tag \u2014 use alt=\"\" only for purely decorative images.",
        )
    return _result(
        "Image alt text", "warn",
        f"{missing} of {total} images are missing alt text. Examples: {sample_text}",
        "Add descriptive alt attributes to the images listed above.",
    )


def _check_word_count(soup):
    soup_copy = BeautifulSoup(str(soup), "html.parser")
    for tag in soup_copy(["script", "style", "noscript"]):
        tag.decompose()
    text = soup_copy.get_text(separator=" ", strip=True)
    word_count = len(text.split())

    if word_count < 300:
        return _result(
            "Content length", "warn",
            f"{word_count} words \u2014 may be considered thin content (under 300).",
            "Add more substantive, unique content to the page \u2014 aim for at least 300 words where relevant.",
        )
    return _result("Content length", "pass", f"{word_count} words on the page.")


def _check_canonical(soup):
    tags = soup.find_all("link", attrs={"rel": "canonical"})
    if not tags:
        return _result(
            "Canonical tag", "warn",
            "No canonical tag found.",
            "Add <link rel=\"canonical\" href=\"...\"> in <head> pointing to the preferred URL for this content.",
        )
    if len(tags) > 1:
        hrefs = ", ".join(t.get("href", "") for t in tags[:3])
        return _result(
            "Canonical tag", "fail",
            f"{len(tags)} canonical tags found on one page: {hrefs}",
            "Keep only one <link rel=\"canonical\"> tag per page \u2014 multiple canonicals confuse search engines.",
        )
    href = tags[0].get("href", "").strip()
    if not href:
        return _result(
            "Canonical tag", "fail",
            "Canonical tag present but has no href value.",
            "Set the href attribute on the canonical tag to the page's preferred URL.",
        )
    return _result("Canonical tag", "pass", f"Canonical points to {href}")


def _check_robots_meta(soup):
    tag = soup.find("meta", attrs={"name": "robots"})
    content = tag.get("content", "").strip().lower() if tag else ""

    if not tag:
        return _result(
            "Robots meta tag", "pass",
            "No robots meta tag found \u2014 defaults to indexing and following links.",
        )

    directives = [d.strip() for d in content.split(",")]
    blocking = {"noindex", "nofollow"} & set(directives)

    if "noindex" in directives:
        return _result(
            "Robots meta tag", "fail",
            f"<meta name=\"robots\" content=\"{content}\"> \u2014 this page is blocked from search indexing.",
            "Remove \"noindex\" from the robots meta tag if you want this page to appear in search results.",
        )
    if "nofollow" in directives:
        return _result(
            "Robots meta tag", "warn",
            f"<meta name=\"robots\" content=\"{content}\"> \u2014 links on this page won't be followed by crawlers.",
            "Remove \"nofollow\" from the robots meta tag unless you specifically want to prevent link equity from passing through this page.",
        )
    return _result("Robots meta tag", "pass", f"<meta name=\"robots\" content=\"{content}\"> \u2014 indexing is allowed.")


def _check_lang_attribute(soup):
    html_tag = soup.find("html")
    lang = html_tag.get("lang", "").strip() if html_tag else ""

    if not lang:
        return _result(
            "HTML lang attribute", "warn",
            "The <html> tag has no lang attribute.",
            "Add a lang attribute to the <html> tag (e.g. <html lang=\"en\">) so search engines and screen readers know the page's language.",
        )
    return _result("HTML lang attribute", "pass", f"<html lang=\"{lang}\">")
