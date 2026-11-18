
import os
import re
import hmac
import logging
import requests

from urllib.parse import urlsplit
from flask import Flask, request, jsonify

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إعدادات البوت
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

app = Flask(__name__)


# إرسال رسالة للمستخدم
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text
        },
        timeout=20
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError("Telegram message failed")


# إعداد Webhook
def setup_webhook():
    if not BOT_TOKEN or not WEBHOOK_URL or not WEBHOOK_SECRET:
        raise RuntimeError("Missing environment variables")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"

    response = requests.post(
        url,
        json={
            "url": WEBHOOK_URL + "/webhook",
            "secret_token": WEBHOOK_SECRET,
            "allowed_updates": ["message"]
        },
        timeout=20
    )

    response.raise_for_status()

    if not response.json().get("ok"):
        raise RuntimeError("Webhook setup failed")


# الصفحة الرئيسية
@app.route("/", methods=["GET"])
def home():
    try:
        setup_webhook()

        return jsonify({
            "status": "online",
            "bot": "Phopia",
            "webhook": "configured"
        })

    except Exception:
        logger.exception("Setup failed")
        return jsonify({"status": "setup_error"}), 503


# استقبال رسائل تيليجرام
@app.route("/webhook", methods=["POST"])
def webhook():

    received_secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token", ""
    )

    if not WEBHOOK_SECRET or not hmac.compare_digest(
        received_secret, WEBHOOK_SECRET
    ):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json(silent=True) or {}

    message = data.get("message") or {}
    chat = message.get("chat") or {}

    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return jsonify({"ok": True})

    command = text.split()[0].split("@")[0].lower()

    # أمر البداية
    if command == "/start":
        reply = (
            "👋 أهلاً بيك في Phopia Bot!\n\n"
            "🎬 بوتك لتحميل الفيديوهات.\n\n"
            "📥 أرسل رابط الفيديو للبدء."
        )

    # المساعدة
    elif command == "/help":
        reply = (
            "📖 أوامر Phopia:\n\n"
            "/start - تشغيل البوت\n"
            "/help - المساعدة\n"
            "/about - معلومات البوت"
        )

    # معلومات البوت
    elif command == "/about":
        reply = (
            "🔥 Phopia Bot\n"
            "Social Media Video Downloader\n\n"
            "Powered by Phopia."
        )

    # استقبال الروابط
    else:
        candidate = text

        if not re.match(r"^https?://", candidate, re.I):
            candidate = "https://" + candidate

        try:
            parsed = urlsplit(candidate)

            valid = (
                parsed.scheme in ("http", "https")
                and parsed.hostname is not None
                and "." in parsed.hostname
            )

        except ValueError:
            valid = False

        if valid:
            reply = (
                "✅ تم استلام الرابط بنجاح!\n\n"
                "⏳ خدمة تنزيل الفيديوهات "
                "سيتم ربطها في المرحلة القادمة."
            )
        else:
            reply = (
                "❌ الرابط غير صحيح.\n"
                "أرسل رابط فيديو كامل."
            )

    try:
        send_message(chat_id, reply)

    except Exception:
        logger.exception("Message sending failed")

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000"))
    )
