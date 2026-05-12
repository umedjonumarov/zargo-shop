"""
ZarGo Shop — Sozlamalar
"""
import os

# === FLASK ===
SECRET_KEY  = os.environ.get('SECRET_KEY', 'zargo-secret-2024')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'zargo123')

# === OPENAI ===
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL   = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

# === GREEN API (WhatsApp) ===
GREEN_INSTANCE_ID = os.environ.get('GREEN_INSTANCE_ID', '')
GREEN_API_TOKEN   = os.environ.get('GREEN_API_TOKEN', '')
GREEN_VERIFY_TOKEN = os.environ.get('GREEN_VERIFY_TOKEN', 'zargo_verify_2024')

# === ADMIN ===
ADMIN_PHONE = os.environ.get('ADMIN_PHONE', '992927909698')

# === GOOGLE SHEETS ===
SHEETS_URL = os.environ.get(
    'SHEETS_URL',
    'https://script.google.com/macros/s/AKfycbzjYrGtarRC-t8B2VQZQblamP3aocIL1vBEMt-nypuHu9BAV2AyQpi-mIBQFOVJ_Hso/exec'
)

# === SAYT ===
SHOP_URL = os.environ.get('SHOP_URL', 'https://zargo-shop.onrender.com')

# === DO'KON QOIDALARI ===
MIN_ORDER     = 100          # minimal buyurtma summasi (somoni)
CURRENCY      = 'с'          # valyuta belgisi
DELIVERY_AREA = 'Зарзамин қишлоғи'

# === SERVER ===
PORT = int(os.environ.get('PORT', 5000))
