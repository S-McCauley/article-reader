#!/usr/bin/env python3
"""
extract_text.py - Fetch a URL and extract readable text.

Usage:
    python extract_text.py <url> [-o output.txt] [-w WIDTH]

Requires:
    pip install requests beautifulsoup4
"""

import argparse
import re
import sys
import textwrap

import requests
from bs4 import BeautifulSoup

# Tags whose content is never readable body text
NOISE_TAGS = [
    "script", "style", "noscript", "template", "svg", "iframe",
    "header", "footer", "nav", "aside", "form", "button",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}


def fetch(url: str, timeout: int = 15) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    # Let requests guess encoding from content if the header lies
    if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    return resp.text


def extract_text(html: str) -> tuple[str, str]:
    """Return (title, readable_text)."""
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else ""

    for tag in soup(NOISE_TAGS):
        tag.decompose()

    # Prefer the <main> or <article> region if the page has one
    root = soup.find("main") or soup.find("article") or soup.body or soup

    blocks = []
    for el in root.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre", "td"]
    ):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        # Add simple markers for headings and list items
        name = el.name
        if name.startswith("h"):
            text = f"\n{'#' * int(name[1])} {text}\n"
        elif name == "li":
            text = f"  - {text}"
        blocks.append(text)

    # Fallback: no structured blocks found, take all visible text
    if not blocks:
        blocks = [root.get_text(" ", strip=True)]

    text = "\n".join(blocks)
    text = re.sub(r"[ \t]+", " ", text)        # collapse runs of spaces
    text = re.sub(r"\n{3,}", "\n\n", text)     # collapse blank lines
    return title, text.strip()


def wrap(text: str, width: int) -> str:
    if width <= 0:
        return text
    out = []
    for line in text.splitlines():
        if len(line) <= width:
            out.append(line)
        else:
            out.append(textwrap.fill(line, width=width))
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract readable text from a URL.")
    parser.add_argument("url", help="The URL to fetch")
    parser.add_argument("-o", "--output", help="Write text to this file instead of stdout")
    parser.add_argument("-w", "--width", type=int, default=100,
                        help="Wrap lines at this width (0 = no wrapping, default 100)")
    args = parser.parse_args()

    url = args.url if re.match(r"^https?://", args.url) else "https://" + args.url

    try:
        html = fetch(url)
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return 1

    title, text = extract_text(html)
    output = (f"{title}\n{'=' * len(title)}\n\n" if title else "") + wrap(text, args.width)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print(f"Saved {len(output):,} characters to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
