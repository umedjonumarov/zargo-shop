"""
ZarGo Shop — Green API (WhatsApp)
Mijozlarga va adminga xabar yuborish.
"""
import logging
import requests
from config import GREEN_INSTANCE_ID, GREEN_API_TOKEN, ADMIN_PHONE, CURRENCY

logger = logging.getLogger(__name__)


def _url(method: str) -> str:
    return f"https://api.green-api.com/waInstance{GREEN_INSTANCE_ID}/{method}/{GREEN_API_TOKEN}"


def send_text(phone: str, text: str) -> bool:
    """Xabar yuborish. phone = '992901234567' (+ belgisisiz)"""
    if not GREEN_INSTANCE_ID or not GREEN_API_TOKEN:
        logger.warning("Green API credentials yo'q")
        return False
    try:
        r = requests.post(
            _url("sendMessage"),
            json={"chatId": f"{phone}@c.us", "message": text},
            timeout=10,
        )
        if r.status_code == 200:
            return True
        logger.error(f"Green API {r.status_code}: {r.text}")
        return False
    except Exception as e:
        logger.error(f"send_text xatosi: {e}")
        return False


def notify_admin(order_number, name, phone, address, items_text, total):
    """Adminga yangi buyurtma haqida xabar"""
    msg = (
        f"🛒 *YANGI BUYURTMA!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 #{order_number}\n"
        f"👤 {name}\n"
        f"📱 +{phone}\n"
        f"📍 {address}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{items_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Jami: *{total}{CURRENCY}*"
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
