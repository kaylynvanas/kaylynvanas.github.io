"""Save the latest Substack posts to _data/substack.json for the Writing section.

Reads the Substack address from _config.yml. Run by .github/workflows/substack.yml;
standard library only so the workflow needs no installs.

usage: python scripts/fetch_substack.py [feed_url] [out_path]
"""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_POSTS = 5
EXCERPT_CHARS = 200


def substack_url():
    match = re.search(r'^substack:\s*"?([^"\n]*)"?', (ROOT / "_config.yml").read_text(), re.M)
    return match.group(1).strip().rstrip("/") if match else ""


def excerpt(raw):
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))
    text = " ".join(text.split())
    return text if len(text) <= EXCERPT_CHARS else text[:EXCERPT_CHARS].rsplit(" ", 1)[0] + "…"


def parse(feed_xml):
    posts = []
    for item in ET.fromstring(feed_xml).iter("item"):
        published = parsedate_to_datetime(item.findtext("pubDate"))
        posts.append({
            "title": (item.findtext("title") or "").strip(),
            "url": (item.findtext("link") or "").strip(),
            "date": published.strftime("%-d %b %Y"),
            "excerpt": excerpt(item.findtext("description")),
        })
    return posts[:MAX_POSTS]


def main():
    feed = sys.argv[1] if len(sys.argv) > 1 else (substack_url() + "/feed" if substack_url() else "")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "_data" / "substack.json"
    if not feed:
        print("No substack address in _config.yml; nothing to fetch.")
        return
    request = urllib.request.Request(feed, headers={"User-Agent": "kaylynvanas.github.io feed fetcher"})
    with urllib.request.urlopen(request, timeout=30) as response:
        posts = parse(response.read())
    # A failed or empty fetch keeps the posts already saved rather than blanking the section.
    if not posts:
        print("Feed had no posts; leaving existing file alone.")
        return
    out.write_text(json.dumps(posts, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved {len(posts)} posts to {out}")


if __name__ == "__main__":
    main()
