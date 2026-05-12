"""
ZarGo Shop — Meta WhatsApp Business API
Mijozlarga va adminga xabar yuborish.
"""
import logging
import requests
from config import (
    META_PHONE_NUMBER_ID, META_ACCESS_TOKEN,
    META_API_VERSION, ADMIN_PHONE, CURRENCY
)

logger = logging.getLogger(__name__)

_BASE = f"https://graph.facebook.com/{META_API_VERSION}/{META_PHONE_NUMBER_ID}/messages"
_HEADERS = lambda: {
    "Authorization": f"Bearer {META_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def send_text(phone: str, text: str) -> bool:
    """Oddiy matn xabar yuborish"""
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        logger.warning("Meta API credentials yo'q")
        return False
    try:
        r = requests.post(
            _BASE,
            headers=_HEADERS(),
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": text, "preview_url": False},
            },
            timeout=10,
        )
        if r.status_code == 200:
            return True
        logger.error(f"Meta API {r.status_code}: {r.text}")
        return False
    except Exception as e:
        logger.error(f"send_text xatosi: {e}")
        return False


def notify_admin(order_number, name, phone, address, items_text, total):
    """Adminga yangi buyurtma haqida xabar"""
    msg = (
        f"🛒 *ЯНГИ БУЮРТМА!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 #{order_number}\n"
        f"👤 {name}\n"
        f"📱 +{phone}\n"
        f"📍 {address}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{items_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Жами: *{total}{CURRENCY}*"
    )
    return send_text(ADMIN_PHONE, msg)


def send_3day_reminder(phone: str, name: str, title: str) -> bool:
    """3 kunlik eslatma xabari"""
    msg = (
        f"Ассалому алайкум {name} {title}!\n\n"
        f"Сиз 3 кун олдин бизнинг дўкондан харид қилгандингиз. "
        f"Агар бирор нарса тугаб қолган бўлса, бизга мурожаат қилинг — "
        f"бепул etказиб берамиз! 🚚\n\n"
        f"ZarGo онлайн дўкони"
    )
    return send_text(phone, msg)
