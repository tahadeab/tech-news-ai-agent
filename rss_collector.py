"""
rss_collector.py
----------------
وحدة جمع المقالات التقنية من مصادر RSS Feeds.
- تقرأ المصادر من config.json
- تجلب المقالات من كل مصدر خلال آخر N ساعة (افتراضياً 24 ساعة)
- تطبّق فلاتر الكلمات المفتاحية (شامل/مستبعد) من config.json
- تزيل المقالات المكررة وتعيد قائمة مقالات منظمة
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests as _requests

logger = logging.getLogger(__name__)

# ترويسات طلبات HTTP تحاكي متصفحاً (بعض المصادر ترفض وكلاء بايثون الافتراضيين)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def _fetch_feed(url: str, timeout: int = 20) -> str:
    """جلب محتوى RSS يدوياً (أكثر موثوقية من التحميل الداخلي في feedparser)."""
    resp = _requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text

ARTICLE_TEMPLATE = (
    "المصدر: {source}\n"
    "العنوان: {title}\n"
    "الوصف: {description}\n"
    "الرابط: {link}\n"
    "تاريخ النشر: {published}"
)


def load_config(path: str = "config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    """إزالة الوسوم HTML من النص المختصر."""
    if not text:
        return ""
    text = text.replace("<br>", " ").replace("<br/>", " ")
    parts = [p for p in text.split("<") if False]
    import re
    return re.sub(r"<[^>]+>", " ", text)


def parse_article_date(entry: dict) -> datetime:
    """استخراج تاريخ النشر من المدخل (قد يختلف بين المصادر)."""
    for attr in ("published_parsed", "updated_parsed"):
        parsed = entry.get(attr)
        if parsed and hasattr(parsed, "tm_year"):
            try:
                import calendar
                return datetime.fromtimestamp(calendar.timegm(parsed[:6]), tz=timezone.utc)
            except Exception:
                pass
    return datetime.now(tz=timezone.utc)


def matches_filters(article: dict, keywords: dict) -> bool:
    """
    تطبيق فلاتر الكلمات المفتاحية:
    - إذا كانت قائمة include غير فارغة، يجب أن يظهر أحد الكلمات في العنوان أو الوصف
    - يستبعد المقال إذا ظهر أي من كلمات exclude في العنوان
    """
    text = (article["title"] + " " + article["description"]).lower()
    include = [k.lower() for k in keywords.get("include", [])]
    exclude = [k.lower() for k in keywords.get("exclude", [])]

    if include and not any(k in text for k in include):
        return False
    if exclude and any(k in text for k in exclude):
        return False
    return True


def collect_articles(config: dict, hours: int = 24) -> list[dict]:
    """
    جلب المقالات من جميع المصادر المحددة في config.
    يعيد قائمة مقالات فريدة مرتبة تنازلياً حسب تاريخ النشر.
    """
    feeds = config.get("rss_feeds", [])
    keywords = config.get("keywords", {})
    limits = config.get("limits", {})
    max_per_feed = limits.get("max_articles_per_feed", 10)
    max_total = limits.get("max_articles_in_report", 20)

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    all_articles = []
    seen_urls = set()

    for feed in feeds:
        name, url = feed["name"], feed["url"]
        logger.info(f"جلب المقالات من: {name} ({url})")
        try:
            content = _fetch_feed(url)
            parsed = feedparser.parse(content)
        except Exception as e:
            logger.error(f"فشل جلب {name}: {e}")
            continue

        count = 0
        for entry in parsed.entries:
            if count >= max_per_feed:
                break
            article_date = parse_article_date(entry)
            # إذا لم نستطع استخراج التاريخ، نقبل المقال (بعض المصادر لا توفره)
            if article_date < cutoff and article_date.tzinfo is not None:
                continue

            link = entry.get("link", "")
            if link in seen_urls:
                continue
            seen_urls.add(link)

            article = {
                "source": name,
                "title": entry.get("title", "بدون عنوان"),
                "description": normalize_text(
                    entry.get("summary") or entry.get("description") or ""
                )[:600],
                "link": link,
                "published": article_date.strftime("%Y-%m-%d %H:%M"),
            }

            if matches_filters(article, keywords):
                all_articles.append(article)
                count += 1

        logger.info(f"تم جمع {count} مقالة من {name}")

    # ترتيب تنازلي حسب تاريخ النشر وإزالة التكرار النهائي
    all_articles.sort(key=lambda a: a["published"], reverse=True)
    return all_articles[:max_total]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    articles = collect_articles(config)
    print(f"إجمالي المقالات المجمعة: {len(articles)}")
    for a in articles[:5]:
        print("-", a["title"], "|", a["source"])
