"""
Zargo Shop - WhatsApp Message Handler
Meta Webhook'dan kelgan xabarlarni qabul qilish va javob berish
"""
import requests
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime

from whatsapp_config import (
    WHATSAPP_TOKEN, SEND_MESSAGE_URL, ADMIN_WHATSAPP_PHONE,
    MIN_ORDER_AMOUNT, DELIVERY_TIME, CURRENCY, WEBHOOK_VERIFY_TOKEN
)
from config import SHEETS_URL

logger = logging.getLogger(__name__)


class WhatsAppAPI:
    """Meta WhatsApp Business API bilan ishlash"""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def send_text_message(self, phone_number: str, text: str) -> bool:
        """Oddiy matn xabar yubor"""
        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': phone_number,
            'type': 'text',
            'text': {'body': text}
        }

        try:
            resp = requests.post(SEND_MESSAGE_URL, json=payload, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                logger.info(f"✅ Xabar yuborildi: {phone_number}")
                return True
            else:
                logger.error(f"❌ Xabar yuborish xatosi: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            logger.error(f"❌ API xatosi: {e}")
            return False

    def send_button_message(self, phone_number: str, body_text: str, buttons: List[Dict]) -> bool:
        """Button'li xabar yubor (Interactive Message)"""
        button_list = []
        for i, btn in enumerate(buttons[:3]):  # Max 3 button
            button_list.append({
                'type': 'reply',
                'reply': {
                    'id': f'btn_{i}',
                    'title': btn['title'][:20]  # 20 char limit
                }
            })

        payload = {
            'messaging_product': 'whatsapp',
            'to': phone_number,
            'type': 'interactive',
            'interactive': {
                'type': 'button',
                'body': {'text': body_text},
                'action': {'buttons': button_list}
            }
        }

        try:
            resp = requests.post(SEND_MESSAGE_URL, json=payload, headers=self.headers, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"❌ Button xabari yuborish xatosi: {e}")
            return False


class GoogleSheetsAPI:
    """Google Sheets'dan ma'lumot olish va saqlash"""

    @staticmethod
    def get_products() -> List[Dict]:
        """Barcha mahsulotlarni olish"""
        try:
            resp = requests.get(SHEETS_URL, params={'action': 'products'}, timeout=15)
            data = resp.json()
            return data.get('products', [])
        except Exception as e:
            logger.error(f"❌ Mahsulot olish xatosi: {e}")
            return []

    @staticmethod
    def save_order(order_dict: Dict) -> Optional[str]:
        """Buyurtmani saqlash va raqam qaytarish"""
        try:
            payload = {'action': 'save_order', 'order': order_dict}
            resp = requests.post(SHEETS_URL, json=payload, timeout=15)
            data = resp.json()
            return data.get('number')
        except Exception as e:
            logger.error(f"❌ Buyurtma saqlash xatosi: {e}")
            return None

    @staticmethod
    def get_order_by_number(order_number: str) -> Optional[Dict]:
        """Raqam bo'yicha buyurtma qidirib topish"""
        try:
            resp = requests.get(
                SHEETS_URL,
                params={'action': 'get_order', 'number': order_number},
                timeout=15
            )
            data = resp.json()
            return data.get('order')
        except Exception as e:
            logger.error(f"❌ Buyurtma qidirib topish xatosi: {e}")
            return None

    @staticmethod
    def save_customer(customer_dict: Dict) -> bool:
        """Mijozni saqlash"""
        try:
            payload = {'action': 'save_customer', 'customer': customer_dict}
            requests.post(SHEETS_URL, json=payload, timeout=15)
            return True
        except Exception as e:
            logger.error(f"❌ Mijoz saqlash xatosi: {e}")
            return False


def send_whatsapp_message(phone_number: str, text: str, buttons: Optional[List[Dict]] = None) -> bool:
    """WhatsApp'ga xabar yubor"""
    if not WHATSAPP_TOKEN:
        logger.warning("⚠️ WHATSAPP_TOKEN sozlanmagan!")
        return False

    api = WhatsAppAPI(WHATSAPP_TOKEN)

    if buttons:
        return api.send_button_message(phone_number, text, buttons)
    else:
        return api.send_text_message(phone_number, text)


def notify_admin_new_order(phone_number: str, name: str, total: float, order_number: str) -> bool:
    """Admin'ga yangi buyurtma haqida bildir"""
    admin_msg = f"""✅ *YANGI BUYU*

📦 Raqam: #{order_number}
👤 Mijoz: {name}
📱 Tel: +{phone_number}
💰 Jami: {total}{CURRENCY}
⏱️ Vaqti: {datetime.now().strftime('%H:%M:%S')}

/admin/orders'da ko'ring"""

    return send_whatsapp_message(ADMIN_WHATSAPP_PHONE, admin_msg)


def parse_order_number(text: str) -> Optional[str]:
    """Matndan buyurtma raqamini chiqarib olish"""
    # "#456" yoki "456" yoki "buyu 456" formatlarni qabul qilish
    text = text.strip().replace('#', '').strip()
    if text.isdigit():
        return text
    return None


def validate_phone(phone_str: str) -> Optional[str]:
    """Telefon raqamini tekshirish va normalizatsiya qilish"""
    # +992901234567, 992901234567, 901234567 formatlarini qabul qilish
    phone_digits = ''.join(c for c in phone_str if c.isdigit())

    # Agar 9 raqamdan boshlansa, 992 qo'shish
    if len(phone_digits) == 9 and phone_digits[0] == '9':
        phone_digits = '992' + phone_digits
    elif len(phone_digits) == 10 and phone_digits[0] == '0':
        phone_digits = '992' + phone_digits[1:]

    # Tekshirish: 992 bilan boshlash va umumiy 12 raqam
    if phone_digits.startswith('992') and len(phone_digits) == 12:
        return phone_digits

    return None


def format_order_for_display(order: Dict) -> str:
    """Buyurtmani foydalanuvchiga ko'rsatish uchun formatlash"""
    status_emoji = {
        'қабул қилинди': '✅',
        'тайёрланмоқда': '👨‍🍳',
        'йўлда': '🚗',
        'етказилди': '📦',
        'бекор': '❌'
    }

    status_text = order.get('status', 'нома\'лум')
    emoji = status_emoji.get(status_text, '⏱️')

    return f"""🆔 Buyu: #{order.get('number', '?')}
{emoji} Status: {status_text}
💰 Jami: {order.get('total', 0)}{CURRENCY}
⏱️ Yetkazilish: {DELIVERY_TIME} minut"""
