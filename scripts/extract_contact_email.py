#!/usr/bin/env python3
"""Nutwood contact-page email extractor (Task B).

Usage:
  python scripts/extract_contact_email.py <base_url>
Ví dụ: python scripts/extract_contact_email.py https://nutwood.vn

Crawler tối đa 10 trang (trang chủ + /contact* /lien-he* /about*), regex
email, ưu tiên email công ty trùng domain. Không cần API key.
"""

import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)
SKIP_EXT = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".css", ".js", ".svg", ".ico")
MAX_PAGES = 10


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks = []

    def handle_data(self, data):
        self.chunks.append(data)


def fetch(url: str, timeout: int = 15) -> str | None:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (contact-scraper)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def extract_emails(html: str) -> set[str]:
    parser = TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    text = " ".join(parser.chunks) + " " + html  # cả raw html (mailto:)
    return set(e.lower().strip(".") for e in EMAIL_RE.findall(text))


def crawl_links(base_url: str, html: str) -> set[str]:
    links = set()
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html):
        full = urljoin(base_url, m.group(1).split("#")[0])
        if urlparse(full).netloc == urlparse(base_url).netloc and \
           not full.lower().endswith(SKIP_EXT):
            links.add(full)
    # Ưu tiên link chứa contact/lien-he/about
    priority = [l for l in links if re.search(
        r"contact|lien-?he|about|gioi-?thieu", l, re.I)]
    others = [l for l in links if l not in priority]
    return set(priority[:5] + others[:5])


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "https://nutwood.vn"
    domain = urlparse(base_url).netloc.replace("www.", "")
    to_visit = [base_url]
    seen = set()
    all_emails: dict[str, list[str]] = {}

    while to_visit and len(seen) < MAX_PAGES:
        url = to_visit.pop(0)
        if url in seen:
            continue
        seen.add(url)
        html = fetch(url)
        if not html:
            continue
        emails = extract_emails(html)
        if emails:
            all_emails[url] = sorted(emails)
        to_visit.extend(crawl_links(base_url, html) - seen)

    corporate = [e for es in all_emails.values() for e in es
                 if domain.split(".")[0] in e or not any(
                     e.endswith(x) for x in ("gmail.com", "yahoo.com",
                                             "hotmail.com", "outlook.com"))]
    report = {
        "base_url": base_url,
        "pages_crawled": sorted(seen),
        "emails_found": all_emails,
        "best_guess": corporate[0] if corporate else (
            next(iter({e for es in all_emails.values() for e in es}), None)),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["best_guess"] else 1


if __name__ == "__main__":
    sys.exit(main())