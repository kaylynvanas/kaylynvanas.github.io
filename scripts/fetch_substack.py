"""Save the latest Substack posts to _data/substack.json for the Writing section.

Reads the Substack address from _config.yml. Run it by hand after publishing a post,
then commit _data/substack.json. Standard library only.

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
INTRO_CHARS = 280
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"
CREATOR = "{http://purl.org/dc/elements/1.1/}creator"


def substack_url():
    match = re.search(r'^substack:\s*"?([^"\n]*)"?', (ROOT / "_config.yml").read_text(), re.M)
    return match.group(1).strip().rstrip("/") if match else ""


def excerpt(raw, limit=EXCERPT_CHARS):
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))
    # Tags become spaces so words don't merge; then drop the gap that leaves before punctuation.
    text = re.sub(r"\s+([.,;:!?])", r"\1", " ".join(text.split()))
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def first_paragraph(body):
    match = re.search(r"<p[^>]*>(.*?)</p>", body or "", re.S)
    return excerpt(match.group(1), INTRO_CHARS) if match else ""


def parse(feed_xml):
    posts = []
    for item in ET.fromstring(feed_xml).iter("item"):
        published = parsedate_to_datetime(item.findtext("pubDate"))
        posts.append({
            "title": (item.findtext("title") or "").strip(),
            "url": (item.findtext("link") or "").strip(),
            "date": published.strftime("%b %-d, %Y"),
            "author": (item.findtext(CREATOR) or "").strip(),
            "subtitle": excerpt(item.findtext("description")),
            "intro": first_paragraph(item.findtext(CONTENT)),
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
