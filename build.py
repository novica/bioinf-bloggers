import feedparser
import datetime
from pathlib import Path
from xml.sax.saxutils import escape

# === Config ===
PAGE_SIZE = 20
OUTPUT_DIR = Path("public")
FEEDS_FILE = Path("feeds.txt")

# === Load feeds ===
feeds = FEEDS_FILE.read_text().splitlines()
items = []
feed_list = []

for url in feeds:
    feed = feedparser.parse(url)
    title = feed.feed.get("title", url)
    link = feed.feed.get("link", url)
    feed_list.append((title, link))

    for entry in feed.entries[:5]:
        items.append(
            {
                "title": entry.title,
                "link": entry.link,
                "source": title,
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")[:500],
            }
        )

# Sort newest first
items.sort(key=lambda x: x["published"], reverse=True)

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

rss_feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>Bioinformatics Blogs</title>
  <link>https://bioinf-bloggers.com/</link>
  <description>A feed of the latest posts of Bioinformatics blogs around the world</description>
  <lastBuildDate>{datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
  {"".join(rss_items)}
</channel>
</rss>
"""

(OUTPUT_DIR / "feed.xml").write_text(rss_feed, encoding="utf-8")
