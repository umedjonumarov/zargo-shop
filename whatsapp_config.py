"""
Zargo Shop - WhatsApp Business API Sozlamalar
Meta Business API uchun zarur o'zgaruvchilar
"""
import os

# === META BUSINESS API ===
WHATSAPP_PHONE_ID = os.environ.get('WHATSAPP_PHONE_ID', '')
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN', '')
WHATSAPP_BUSINESS_ACCT_ID = os.environ.get('WHATSAPP_BUSINESS_ACCT_ID', '')

# === ADMIN ALERTS ===
ADMIN_WHATSAPP_PHONE = os.environ.get('ADMIN_WHATSAPP_PHONE', '99291234567')

# === WEBHOOK ===
WEBHOOK_VERIFY_TOKEN = os.environ.get('WEBHOOK_VERIFY_TOKEN', 'zargo-webhook-token-2024')

# === META API ENDPOINTS ===
WHATSAPP_API_URL = 'https://graph.instagram.com/v18.0'
SEND_MESSAGE_URL = f'{WHATSAPP_API_URL}/{WHATSAPP_PHONE_ID}/messages'

# === CONSTANTS ===
MIN_ORDER_AMOUNT = 100  # сомонӣ
DELIVERY_TIME = '30-60'  # minutes
CURRENCY = 'с'  # сомонӣ (Tajik Somoni)
