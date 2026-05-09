"""
Zargo Shop - Sozlamalar
"""
import os

# === ASOSIY ===
SECRET_KEY = os.environ.get('SECRET_KEY', 'zargo-shop-secret-2024')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'zargo123')

# === GOOGLE SHEETS ===
SHEETS_URL = 'https://script.google.com/macros/s/AKfycbziUIX313Iw8gkdwnIXtjJROIBSN12vvIanzLVcxugQXb_eJFOXj0mrMqRzHLo3WAdXGQ/exec'
# === RENDER ===
PORT = int(os.environ.get('PORT', 5000))