import feedparser
from pathlib import Path

feeds = Path("feeds.txt").read_text().splitlines()
items = []
feed_list = []  # for sidebar

for url in feeds:
    feed = feedparser.parse(url)
    title = feed.feed.get("title", url)
    feed_list.append((title, feed.feed.get("link", url)))
    for entry in feed.entries[:5]:
        items.append({
            "title": entry.title,
            "link": entry.link,
            "source": title,
            "published": entry.get("published", ""),
            "summary": entry.get("summary", "")[:200]
        })

# Sort newest first
items.sort(key=lambda x: x["published"], reverse=True)

# Build post cards
entry_html = []
for item in items:
    entry_html.append(f"""
    <article>
      <h2><a href="{item['link']}">{item['title']}</a></h2>
      <p class="meta">From <strong>{item['source']}</strong> – {item['published']}</p>
      <p>{item['summary']}...</p>
    </article>
    """)

# Build sidebar list
sidebar_html = "\n".join(
    f'<li><a href="{link}">{name}</a></li>' for name, link in feed_list
)

# Insert into template
template = Path("template.html").read_text(encoding="utf-8")
html = (template
        .replace("{{ content }}", "\n".join(entry_html))
        .replace("{{ sidebar }}", sidebar_html))

Path("index.html").write_text(html, encoding="utf-8")
