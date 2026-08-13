"""
scheduler.py
--------------
جدولة الإرسال اليومي للتقرير.
- يستخدم APScheduler (جدولة قائمة على الذاكرة — مناسبة للتشغيل المستمر على سيرفر)
- يدعم تحديد الوقت والمنطقة الزمنية من config.json
- بديل خفيف بدون مكتبات خارجية: وضع loop داخل main.py
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from main import run_daily_report

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def start_scheduler(config: dict):
    """تشغيل الجدولة اليومية وفقاً لإعدادات config."""
    sched_cfg = config.get("schedule", {})
    if not sched_cfg.get("enabled", True):
        logger.info("الجدولة معطلة — سيعمل الوكيل في وضع التشغيل اليدوي فقط")
        return

    hour, minute = sched_cfg.get("time", "08:00").split(":")
    timezone = sched_cfg.get("timezone", "Asia/Riyadh")

    scheduler.add_job(
        run_daily_report,
        trigger=CronTrigger(hour=int(hour), minute=int(minute), timezone=timezone),
        id="daily_tech_report",
        name="Tech Report Daily Job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"✅ تم تفعيل الجدولة: تقرير يومي الساعة {hour}:{minute} ({timezone})"
    )
    print(f"📅 الجدولة نشطة: سيتم إرسال التقرير يومياً الساعة {hour}:{minute} ({timezone})")
    print("⏳ الوكيل يعمل الآن في الخلفية... اضغط Ctrl+C للإيقاف")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
