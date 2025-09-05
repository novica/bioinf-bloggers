import feedparser
from pathlib import Path
from xml.sax.saxutils import escape
import calendar
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone


def extract_dt(entry) -> datetime:
    # Prefer parsed structs from feedparser
    for attr in ("published_parsed", "updated_parsed"):
        t = entry.get(attr)
        if t:
            # t is time.struct_time (UTC). Make it aware.
            return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
    # Fallback: try RFC2822/ISO-ish strings
    for attr in ("published", "updated"):
        s = entry.get(attr)
        if s:
            try:
                return parsedate_to_datetime(s).astimezone(timezone.utc)
            except Exception:
                pass
    # No date at all → push to the end
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


# === Config ===
PAGE_SIZE = 10
OUTPUT_DIR = Path("public")
FEEDS_FILE = Path("feeds.txt")

# === Load feeds ===
feeds = []
for line in FEEDS_FILE.read_text().splitlines():
    if "," in line:
        name, url = line.split(",", 1)
        feeds.append((name.strip(), url.strip()))
    else:
        # fallback: no name given, use URL
        feeds.append((line.strip(), line.strip()))


# Fetch feeds and items
items = []
feed_list = []

for name, url in feeds:
    feed = feedparser.parse(url)
    title = name or feed.feed.get("title", url)
    link = feed.feed.get("link", url)
    feed_list.append((title, link))

    for entry in feed.entries[:5]:
        dt = extract_dt(entry)
        display_date = (
            entry.get("published") or entry.get("updated") or dt.strftime("%Y-%m-%d")
        )

        items.append(
            {
                "title": entry.title,
                "link": entry.link,
                "source": title,
                "published": display_date,
                "summary": entry.get("summary", "")[:200],
                "dt": dt,  # for sorting
            }
        )

# Sort feed list alphabetically
feed_list.sort(key=lambda x: x[0].lower())

# Sort newest first
items.sort(key=lambda x: x["dt"], reverse=True)

# === Sidebar ===
sidebar_html = "\n".join(
    f'<li><a href="{link}">{name}</a></li>' for name, link in feed_list
)

# === Load template ===
template = Path("template.html").read_text(encoding="utf-8")

# Ensure output dir exists
OUTPUT_DIR.mkdir(exist_ok=True)

# === Pagination ===
pages = [items[i : i + PAGE_SIZE] for i in range(0, len(items), PAGE_SIZE)]

for i, page_items in enumerate(pages, start=1):
    entry_html = []
    for item in page_items:
        entry_html.append(f"""
        <article>
          <h2><a href="{item["link"]}">{item["title"]}</a></h2>
          <p class="meta">From <strong>{item["source"]}</strong> – {item["published"]}</p>
          <p>{item["summary"]}...</p>
        </article>
        """)

    # Add pagination links
    nav_links = []
    if i > 1:
        if i == 2:
            nav_links.append('<a href="index.html">← Previous</a>')
        else:
            nav_links.append(f'<a href="page{i - 1}.html">← Previous</a>')
    if i < len(pages):
        nav_links.append(f'<a href="page{i + 1}.html">Next →</a>')

    html = (
        template.replace("{{ content }}", "\n".join(entry_html))
        .replace("{{ sidebar }}", sidebar_html)
        .replace("{{ pagination }}", " ".join(nav_links))
    )

    filename = "index.html" if i == 1 else f"page{i}.html"
    (OUTPUT_DIR / filename).write_text(html, encoding="utf-8")

# === Copy CSS ===
(OUTPUT_DIR / "style.css").write_text(
    Path("style.css").read_text(encoding="utf-8"), encoding="utf-8"
)

# === Generate RSS ===
rss_items = []
for item in items[:50]:  # latest 50
    rss_items.append(f"""
    <item>
      <title>{escape(item["title"])}</title>
      <link>{escape(item["link"])}</link>
      <description>{escape(item["summary"])}</description>
      <pubDate>{escape(item["published"])}</pubDate>
      <source>{escape(item["source"])}</source>
      <guid>{escape(item["link"])}</guid>
    </item>
    """)

last_build = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

rss_feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>Bioinformatics Blogs</title>
  <link>https://bioinf-bloggers.com/</link>
  <description>A feed of the latest posts of Bioinformatics blogs around the world</description>
  <lastBuildDate>{last_build}</lastBuildDate>
  {"".join(rss_items)}
</channel>
</rss>
"""

(OUTPUT_DIR / "feed.xml").write_text(rss_feed, encoding="utf-8")
