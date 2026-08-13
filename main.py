"""
main.py — Tech News AI Agent
=============================
الوكيل المتكامل للأخبار التقنية.

أوضاع التشغيل:
  python main.py              → وضع مجدول (يُشغّل التقرير يومياً حسب config)
  python main.py --once       → تشغيل واحد (تقرير فوري ثم خروج)
  python main.py --setup-bot  → مساعد تفاعلي لتعيين chat_id

يقرأ جميع الإعدادات من config.json:
  - rss_feeds   : مصادر RSS
  - keywords    : الكلمات المفتاحية الشاملة/المستبعدة
  - llm         : إعدادات LLM API
  - telegram    : بيانات بوت Telegram
  - schedule    : إعدادات الجدولة
"""

import argparse
import json
import logging
import sys

from rss_collector import collect_articles, load_config
from llm_summarizer import LLMSummarizer
from report_formatter import generate_full_report
from telegram_sender import TelegramSender, setup_assistant


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def validate_config(config: dict) -> list[str]:
    """التحقق من صحة الإعدادات الأساسية."""
    errors = []
    if not config.get("rss_feeds"):
        errors.append("قائمة rss_feeds فارغة — أضف مصدراً واحداً على الأقل")
    # ملاحظة: telegram.bot_token وchat_id غير إلزاميين للتشغيل المحلي؛
    # يتم التحقق منهما عند الإرسال الفعلي ويتم تخطي الإرسال إن لم يُعبّآ
    if not config.get("llm", {}).get("api_key"):
        errors.append("llm.api_key غير مضبوط")
    return errors


def run_daily_report():
    """الدالة الرئيسية للوكيل: جمع → تلخيص → تنسيق → إرسال."""
    logger = logging.getLogger("main")
    config = load_config()

    # 1) التحقق من الإعدادات
    errors = validate_config(config)
    if errors:
        for e in errors:
            logger.error(e)
        return False

    language = config.get("language", "both")
    LANG_HINT = {
        "Arabic": "[🇸🇦 Arabic]",
        "English": "[🇬🇧 English]",
        "both": "[🇸🇦 Arabic + 🇬🇧 English]",
    }.get(language, "")

    print(f"\n🚀 Starting Tech News AI Agent {LANG_HINT}...\n")
    print(f"🚀 بدء تشغيل Tech News AI Agent {LANG_HINT}...\n")

    # 2) جمع المقالات من RSS
    try:
        articles = collect_articles(config, hours=24)
        print(f"📥 تم جمع {len(articles)} مقالة تقنية")
        print(f"📥 Collected {len(articles)} technical articles")
    except Exception as e:
        logger.error(f"فشل جمع المقالات / Failed to collect articles: {e}")
        return False

    if not articles:
        logger.info("لا توجد مقالات جديدة اليوم ضمن الفلاتر المحددة")
        return True

    # 3) توليد التقرير (تلخيص LLM + مقدمة + تنسيق)
    try:
        report = generate_full_report(config, articles)
        print(f"📝 تم توليد التقرير ({len(articles)} مقالة)")
        print(f"📝 Report generated ({len(articles)} articles)")
    except Exception as e:
        logger.error(f"فشل توليد التقرير / Failed to generate report: {e}")
        return False

    # 4) الإرسال عبر Telegram
    tg = config["telegram"]
    if not tg.get("bot_token") or not tg.get("chat_id"):
        logger.warning("telegram.bot_token/chat_id غير مضبوط — تم تخطي الإرسال إلى Telegram")
        logger.warning("telegram.bot_token/chat_id not configured — Telegram delivery skipped")
        if report["files"]:
            for fmt, path in report["files"].items():
                print(f"💾 Saved report ({fmt}): {path}")
                print(f"💾 حُفظ التقرير ({fmt}): {path}")
        return True
    try:
        sender = TelegramSender(tg["bot_token"], tg["chat_id"])
        sender.validate_token()
        results = sender.send_report(report["telegram"])
        print(f"📤 نتائج الإرسال: نجح {results['sent']}، فشل {results['failed']}")
        print(f"📤 Telegram delivery: {results['sent']} sent, {results['failed']} failed")

        if report["files"]:
            for fmt, path in report["files"].items():
                print(f"💾 Saved report ({fmt}): {path}")
                print(f"💾 حُفظ التقرير ({fmt}): {path}")
        return results["failed"] == 0
    except Exception as e:
        logger.error(f"فشل الإرسال إلى Telegram: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Tech News AI Agent")
    parser.add_argument(
        "--once", action="store_true",
        help="تشغيل واحد: يولّد التقرير ويرسله ثم يخرج",
    )
    parser.add_argument(
        "--setup-bot", action="store_true",
        help="مساعد تفاعلي لتعيين chat_id لأول مرة",
    )
    args = parser.parse_args()

    setup_logging()
    config = load_config()

    if args.setup_bot:
        token = config["telegram"].get("bot_token", "")
        if not token:
            token = input("أدخل bot token: ").strip()
        chat_id = setup_assistant(token)
        if chat_id:
            print(f"\n💡 أضف هذا chat_id إلى config.json:")
            print(json.dumps({"telegram": {"bot_token": token, "chat_id": chat_id}},
                             ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.once:
        ok = run_daily_report()
        sys.exit(0 if ok else 1)

    # الوضع الافتراضي: تشغيل مجدول
    from scheduler import start_scheduler, stop_scheduler
    try:
        start_scheduler(config)
        # تشغيل التقرير الأول فورياً ثم الالتزام بالجدولة
        run_daily_report()
        while True:
            import time
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 إيقاف الوكيل...")
        stop_scheduler()


if __name__ == "__main__":
    main()
