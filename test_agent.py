"""
test_agent.py
-------------
سكربت اختبار شامل: يحاكي دورة التشغيل الكاملة للوكيل
(جمع → تصفية → تلخيص LLM ثنائي اللغة → مقدمة تحليلية → تنسيق → حفظ)
دون إرسال فعلي عبر Telegram.
يختبر الأوضاع الثلاثة: Arabic / English / both
"""

import json
import sys

sys.path.insert(0, ".")

from rss_collector import collect_articles, load_config
from report_formatter import (
    generate_full_report,
    build_report_markdown,
    build_report_telegram,
)


def run_test(language: str, tag: str):
    print("\n" + "=" * 60)
    print(f"🧪 اختبار وضع اللغة: {tag}")
    print("=" * 60)

    config = load_config()
    config["language"] = language

    print("\n1️⃣  جمع المقالات من RSS")
    articles = collect_articles(config, hours=24)
    print(f"✅ تم جمع {len(articles)} مقالة")
    if not articles:
        print("⚠️ لا توجد مقالات جديدة")
        return False

    print("\n2️⃣  توليد التقرير مع تلخيص LLM ثنائي اللغة")
    report = generate_full_report(config, articles)
    intro = report["intro"]
    if isinstance(intro, dict):
        print(f"   🇸🇦 مقدمة عربية: {intro.get('Arabic', '')[:80]}...")
        print(f"   🇬🇧 English intro: {intro.get('English', '')[:80]}...")
    else:
        print(f"   مقدمة: {intro[:80]}...")

    print("\n3️⃣  التحقق من تنسيق Telegram MarkdownV2")
    tg_parts = report["telegram"]
    for i, part in enumerate(tg_parts, 1):
        assert len(part) <= 4096, f"الجزء {i} تجاوز 4096 رمز!"
    print(f"✅ {len(tg_parts)} جزء، جميعها ضمن حد Telegram")

    print("\n4️⃣  حفظ التقارير محلياً")
    for fmt, path in report["files"].items():
        print(f"✅ حُفظ: {path}")

    print(f"\n✅ نجح اختبار وضع {tag}!\n")
    return True


def main():
    print("🧪 بداية الاختبار الشامل — Tech News AI Agent (Bilingual)")
    print("=" * 60)

    # التحقق من صحة بناء الجملة لكل الوحدات
    print("\n📋 0️⃣  فحص استيراد الوحدات...")
    import rss_collector
    import llm_summarizer
    import report_formatter
    import telegram_sender
    import scheduler
    import main as agent_main
    print("✅ جميع الوحدات تستورد بنجاح")

    # 1) اختبار وضع both (ثنائي اللغة)
    ok1 = run_test("both", "Arabic + English (both)")
    # 2) اختبار وضع English فقط
    ok2 = run_test("English", "English only")
    # 3) اختبار وضع Arabic فقط
    ok3 = run_test("Arabic", "Arabic only")

    # 4) فحص أن جميع الملخصات تحتوي على اللغتين في وضع both
    print("=" * 60)
    print("🔎 فحص جودة المخرجات...")
    config = load_config()
    config["language"] = "both"
    articles = collect_articles(config, hours=24)
    from llm_summarizer import LLMSummarizer, summarize_all
    articles = summarize_all(LLMSummarizer(config["llm"], language="both"), articles, workers=6)
    for a in articles:
        s = a.get("summary", {})
        assert isinstance(s, dict), "الملخص يجب أن يكون قاموس لغتين!"
        assert s.get("Arabic"), f"ملخص عربي مفقود: {a['title']}"
        assert s.get("English"), f"English summary missing: {a['title']}"
    print(f"✅ جميع {len(articles)} مقالة تملك ملخصات باللغتين")

    # 5) فحص محتوى ملف HTML العربي (RTL)
    import glob
    ar_files = glob.glob("reports/report_*_ar.html")
    en_files = glob.glob("reports/report_*_en.html")
    if ar_files:
        content = open(ar_files[-1], encoding="utf-8").read()
        assert 'dir="rtl"' in content, "HTML العربي يجب أن يكون RTL"
        assert 'lang="ar"' in content, "HTML العربي يجب أن يكون lang=ar"
        print("✅ HTML العربي: RTL + lang=ar صحيح")
    if en_files:
        content = open(en_files[-1], encoding="utf-8").read()
        assert 'dir="ltr"' in content, "HTML الإنجليزي يجب أن يكون LTR"
        assert 'lang="en"' in content, "HTML الإنجليزي يجب أن يكون lang=en"
        print("✅ HTML الإنجليزي: LTR + lang=en صحيح")

    if ok1 and ok2 and ok3:
        print("\n🎉 جميع اختبارات الوكيل باللغتين نجحت!")
        sys.exit(0)
    else:
        print("\n❌ فشل أحد اختبارات الأوضاع!")
        sys.exit(1)


if __name__ == "__main__":
    main()
