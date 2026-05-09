"""
Zargo Shop - Sozlamalar
"""
import os

# === ASOSIY ===
SECRET_KEY = os.environ.get('SECRET_KEY', 'zargo-shop-secret-2024')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'zargo123')

# === GOOGLE SHEETS ===
SHEETS_URL = 'https://script.google.com/macros/s/AKfycbziUIX313Iw8gkdwnIXtjJROIBSN12vvIanzLVcxugQXb_eJFOXj0mrMqRzHLo3WAdXGQ/exec'

# === GREEN API (WhatsApp admin xabar) ===
GREEN_API_INSTANCE_ID = os.environ.get('GREEN_API_INSTANCE_ID', '7107601809')
GREEN_API_TOKEN = os.environ.get('GREEN_API_TOKEN', '')
ADMIN_PHONE = os.environ.get('ADMIN_PHONE', '992927909698')

# === RENDER ===
PORT = int(os.environ.get('PORT', 5000))