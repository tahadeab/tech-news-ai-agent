"""
telegram_sender.py
------------------
مرسل التقارير إلى Telegram عبر Bot API الرسمي.
- يتحقق من صلاحية التوكن قبل الإرسال
- يدعم إرسال التقارير متعددة الأجزاء (عند تجاوز حد 4096 رمز)
- يوفر أداة مساعدة لتعيين chat_id تلقائياً
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class TelegramSender:
    def __init__(self, bot_token: str, chat_id: str):
        self.base = f"{TELEGRAM_API}/bot{bot_token}"
        self.chat_id = chat_id

    # ---------- أدوات التحقق ----------

    def validate_token(self) -> dict:
        """التحقق من صلاحية التوكن وإرجاع معلومات البوت."""
        resp = requests.get(f"{self.base}/getMe", timeout=15)
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"التوكن غير صالح: {data}")
        bot = data["result"]
        return {
            "username": bot["username"],
            "name": bot.get("first_name", ""),
        }

    def get_updates(self, limit: int = 10) -> list[dict]:
        """جلب آخر الرسائل المرسلة للبوت (مفيدة لتعيين chat_id)."""
        resp = requests.get(f"{self.base}/getUpdates?limit={limit}", timeout=15)
        return resp.json().get("result", [])

    def find_my_chat_id(self) -> str | None:
        """إيجاد chat_id من آخر رسالة مرسلها المستخدم للبوت."""
        for update in reversed(self.get_updates()):
            msg = update.get("message", {})
            chat = msg.get("chat", {})
            if chat:
                return str(chat["id"])
        return None

    # ---------- الإرسال ----------

    def send_message(self, text: str, parse_mode: str = "MarkdownV2") -> bool:
        """إرسال رسالة واحدة إلى الدردشة."""
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False,
        }
        resp = requests.post(f"{self.base}/sendMessage", json=payload, timeout=30)
        data = resp.json()
        if data.get("ok"):
            logger.info("تم إرسال الرسالة بنجاح")
            return True
        logger.error(f"فشل الإرسال: {data.get('description', data)}")
        return False

    def send_report(self, parts: list[str]) -> dict:
        """إرسال جميع أجزاء التقرير بترتيب، مع إعادة المحاولة عند الفشل."""
        results = {"sent": 0, "failed": 0, "errors": []}
        for i, part in enumerate(parts, 1):
            ok = False
            for attempt in range(3):
                if self.send_message(part):
                    ok = True
                    break
                time.sleep(3)
            if ok:
                results["sent"] += 1
                logger.info(f"تم إرسال الجزء {i}/{len(parts)}")
                # احترام حدود_rate في Telegram
                time.sleep(1)
            else:
                results["failed"] += 1
                results["errors"].append(f"الجزء {i}")

        return results


def setup_assistant(bot_token: str):
    """مساعد تفاعلي لتعيين chat_id لأول مرة."""
    sender = TelegramSender(bot_token, "")
    info = sender.validate_token()
    print(f"✅ البوت صالح: @{info['username']} ({info['name']})")
    print("\n👉 افتح البوت @{username} في Telegram وأرسل له أي رسالة".format(**info))
    input("اضغط Enter بعد إرسال الرسالة...")
    chat_id = sender.find_my_chat_id()
    if chat_id:
        print(f"✅ chat_id الخاص بك: {chat_id}")
    else:
        print("⚠️ لم يتم العثور على رسالة. تأكد من إرسال رسالة للبوت ثم أعد المحاولة.")
    return chat_id


if __name__ == "__main__":
    import json
    config = json.load(open("config.json", encoding="utf-8"))
    token = config["telegram"].get("bot_token")
    chat = config["telegram"].get("chat_id")
    if not token:
        token = input("أدخل bot token: ").strip()
    if not chat:
        chat = setup_assistant(token)
    if chat:
        sender = TelegramSender(token, chat)
        sender.send_message("🤖 *وكيل الأخبار التقنية* جاهز للعمل\\!")
