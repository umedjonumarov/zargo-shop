"""
Zargo Shop - WhatsApp Conversation State Manager
Har bir foydalanuvchining DialogState holatini boshqarish
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class ConversationState:
    """Bitta WhatsApp foydalanuvchining holati"""

    def __init__(self, phone_number: str):
        self.phone = phone_number
        self.state = 'menu'  # menu, catalog, category, product, cart, checkout_name, checkout_address, checkout_confirm
        self.cart: List[Dict] = []  # [{name, qty, unit, price_total}, ...]
        self.checkout_data: Dict = {}  # {name, address, phone}
        self.current_category = None
        self.current_product = None
        self.current_page = 0  # For pagination in product list
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

    def set_state(self, new_state: str) -> None:
        """Holatni o'zgartirish"""
        self.state = new_state
        self.last_activity = datetime.now()

    def add_to_cart(self, name: str, qty: float, unit: str, price_total: float) -> bool:
        """Savatga mahsulot qo'shish"""
        # Agar allaqachon mavjud bo'lsa, miqdorini oshirish
        for item in self.cart:
            if item['name'] == name:
                item['qty'] += qty
                item['price_total'] += price_total
                self.last_activity = datetime.now()
                return True

        # Yangi mahsulot
        self.cart.append({
            'name': name,
            'qty': qty,
            'unit': unit,
            'price_total': price_total
        })
        self.last_activity = datetime.now()
        return True

    def remove_from_cart(self, name: str) -> bool:
        """Savatdan mahsulot o'chirish"""
        initial_len = len(self.cart)
        self.cart = [item for item in self.cart if item['name'] != name]
        self.last_activity = datetime.now()
        return len(self.cart) < initial_len

    def get_cart_total(self) -> float:
        """Savat jami narxi"""
        return sum(item['price_total'] for item in self.cart)

    def clear_cart(self) -> None:
        """Savatni tozalash"""
        self.cart = []
        self.last_activity = datetime.now()

    def set_checkout_data(self, name: str = None, address: str = None, phone: str = None) -> None:
        """Checkout ma'lumotlari"""
        if name:
            self.checkout_data['name'] = name
        if address:
            self.checkout_data['address'] = address
        if phone:
            self.checkout_data['phone'] = phone
        self.last_activity = datetime.now()

    def is_expired(self, hours: int = 24) -> bool:
        """Conversation holatining qadimiy bo'lishini tekshirish"""
        return (datetime.now() - self.last_activity) > timedelta(hours=hours)

    def to_order_dict(self) -> Dict:
        """Order sifatida Google Sheets'ga saqlash uchun"""
        items_text = '\n'.join([
            f"• {item['name']} × {item['qty']} = {item['price_total']}с"
            for item in self.cart
        ])
        return {
            'phone': self.checkout_data.get('phone', self.phone),
            'name': self.checkout_data.get('name', ''),
            'address': self.checkout_data.get('address', ''),
            'items': items_text,
            'total': self.get_cart_total(),
            'payment': 'нақд',
            'status': 'қабул қилинди',
            'source': 'whatsapp'
        }


class ConversationManager:
    """Barcha foydalanuvchi holatlarini boshqarish"""

    def __init__(self):
        self.states: Dict[str, ConversationState] = {}

    def get_or_create(self, phone_number: str) -> ConversationState:
        """Foydalanuvchi holatini olish yoki yaratish"""
        if phone_number not in self.states:
            self.states[phone_number] = ConversationState(phone_number)
        return self.states[phone_number]

    def cleanup_expired(self, hours: int = 24) -> int:
        """Qadimiy holatlarni o'chirish"""
        expired = [phone for phone, state in self.states.items() if state.is_expired(hours)]
        for phone in expired:
            del self.states[phone]
        return len(expired)


# Global manager instance
conversation_manager = ConversationManager()
