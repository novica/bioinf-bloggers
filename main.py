import feedparser
from pathlib import Path
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader, select_autoescape

from helpers import extract_dt


# === Config ===
PAGE_SIZE = 10
OUTPUT_DIR = Path("public")
OUTPUT_DIR_STATIC = Path("public/static")
FEEDS_FILE = Path("feeds.txt")
TEMPLATES_DIR = Path("templates")


def main():
    # === Load feeds ===
    feeds = []
    for line in FEEDS_FILE.read_text(encoding="utf-8").splitlines():
        if "," in line:
            name, url = line.split(",", 1)
            feeds.append((name.strip(), url.strip()))
        else:
            feeds.append((line.strip(), line.strip()))

    # === Fetch feeds and items ===
    items = []
    feed_list = []

    for name, url in feeds:
        feed = feedparser.parse(url)
        
        raw_title = getattr(feed.feed, "title", "")
        raw_link = getattr(feed.feed, "link", "")

        title = name.strip() if name.strip() else raw_title.strip() or url
        link = raw_link.strip() or url

        feed_list.append((title, link))

        for entry in feed.entries[:5]:
            dt = extract_dt(entry)
            display_date = (
                entry.get("published")
                or entry.get("updated")
                or dt.strftime("%Y-%m-%d")
            )
            
            summary = getattr(entry, "summary", "") or ""
            summary = summary[:200]

            items.append(
                {
                    "title": entry.title,
                    "link": entry.link,
                    "source": title,
                    "published": display_date,
                    "summary": summary,
                    "dt": dt,
                }
            )

    # === Sort ===
    feed_list.sort(key=lambda x: x[0].lower())
    items.sort(key=lambda x: x["dt"], reverse=True)

    last_build = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    # === Jinja environment ===
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("index.html")
    rss_template = env.get_template("feed.xml")

    # === Ensure output dirs ===
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR_STATIC.mkdir(exist_ok=True)

    # === Pagination ===
    pages = [items[i : i + PAGE_SIZE] for i in range(0, len(items), PAGE_SIZE)]

    for i, page_items in enumerate(pages, start=1):
        prev_page = None
        next_page = None

        if i > 1:
            prev_page = "index.html" if i == 2 else f"page{i - 1}.html"
        if i < len(pages):
            next_page = f"page{i + 1}.html"

        html = template.render(
            items=page_items,
            feeds=feed_list,
            last_build=last_build,
            prev_page=prev_page,
            next_page=next_page,
        )

        filename = "index.html" if i == 1 else f"page{i}.html"
        (OUTPUT_DIR / filename).write_text(html, encoding="utf-8")

    # === Copy CSS ===
    (OUTPUT_DIR / "static/styles.css").write_text(
        Path("static/styles.css").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    # === Generate RSS via Jinja ===
    rss_xml = rss_template.render(
        items=items[:50],
        last_build=last_build,
    )

    (OUTPUT_DIR / "feed.xml").write_text(rss_xml, encoding="utf-8")


if __name__ == "__main__":
    main()
