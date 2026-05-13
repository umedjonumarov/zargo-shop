"""
ZarGo Shop — Google Sheets API wrapper
Barcha ma'lumotlar Google Sheets orqali saqlanadi (Apps Script orqali).
"""
import logging
import requests
from datetime import datetime, date, timedelta
from config import SHEETS_URL

logger = logging.getLogger(__name__)


class SheetsDB:

    def _get(self, action, **params):
        try:
            params['action'] = action
            r = requests.get(self.url, params=params, timeout=20, allow_redirects=True)
            if not r.text.strip():
                logger.error(f"Sheets GET [{action}]: empty response (status {r.status_code})")
                return {}
            try:
                return r.json()
            except Exception:
                logger.error(f"Sheets GET [{action}]: status={r.status_code} body={r.text[:300]}")
                return {}
        except Exception as e:
            logger.error(f"Sheets GET [{action}]: {e}")
            return {}

    def _post(self, action, payload):
        try:
            payload['action'] = action
            r = requests.post(self.url, json=payload, timeout=15)
            return r.json()
        except Exception as e:
            logger.error(f"Sheets POST [{action}]: {e}")
            return {}

    def __init__(self):
        self.url = SHEETS_URL

    # ── MIJOZLAR ─────────────────────────────────────────────────────────────

    def get_customer(self, phone: str) -> dict | None:
        """Telefon raqami bo'yicha mijozni qaytaradi yoki None"""
        result = self._get('get_customer', phone=phone)
        return result.get('customer')

    def save_customer(self, phone: str, name: str,
                      gender: str = 'unknown', language: str = 'uz') -> bool:
        """Yangi mijoz yaratish yoki mavjudini yangilash"""
        result = self._post('save_customer', {
            'customer': {
                'phone':        phone,
                'name':         name,
                'gender':       gender,
                'language':     language,
                'last_contact': datetime.now().isoformat(),
            }
        })
        return result.get('success', False)

    def get_all_customers(self) -> list:
        return self._get('customers').get('customers', [])

    def get_orders_3days_ago(self) -> list:
        """3 kun oldin buyurtma bergan mijozlar ro'yxati"""
        target = (date.today() - timedelta(days=3)).strftime('%Y-%m-%d')
        return self._get('orders_by_date', date=target).get('orders', [])

    # ── MAHSULOTLAR ──────────────────────────────────────────────────────────

    def get_products(self) -> list:
        return self._get('products').get('products', [])

    def get_all_products(self) -> list:
        """Admin uchun — mavjud bo'lmaganlarni ham qaytaradi"""
        return self._get('all_products').get('products', [])

    def update_product(self, product_id, data: dict) -> bool:
        result = self._post('update_product', {'id': product_id, 'data': data})
        return result.get('success', False)

    # ── BUYURTMALAR ──────────────────────────────────────────────────────────

    def save_order(self, order_data: dict) -> str | None:
        """Buyurtmani saqlaydi va tartib raqamini qaytaradi"""
        result = self._post('save_order', {'order': order_data})
        return result.get('number')

    def get_order(self, number: str) -> dict | None:
        result = self._get('get_order', number=number)
        return result.get('order')

    def get_all_orders(self) -> list:
        return self._get('orders').get('orders', [])

    def update_order_status(self, number: str, status: str) -> bool:
        result = self._post('update_order_status', {
            'number': number,
            'status': status,
        })
        return result.get('success', False)

    def update_order(self, number: str, data: dict) -> bool:
        result = self._post('update_order', {'number': number, 'data': data})
        return result.get('success', False)

    def delete_order(self, number: str) -> bool:
        result = self._post('delete_order', {'number': number})
        return result.get('success', False)


db = SheetsDB()
