import calendar
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone


def extract_dt(entry) -> datetime:
    """Prefer parsed structs from feedparser"""
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
