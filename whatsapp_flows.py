"""
Zargo Shop - WhatsApp Bot Conversation Flows
Bot'ning barcha orada bo'lgan gaplarini boshqarish
"""
import logging
from typing import List, Dict, Optional

from conversation_state import ConversationState, conversation_manager
from whatsapp_handler import (
    send_whatsapp_message, GoogleSheetsAPI, parse_order_number,
    validate_phone, format_order_for_display, notify_admin_new_order
)
from whatsapp_config import MIN_ORDER_AMOUNT, CURRENCY, DELIVERY_TIME

logger = logging.getLogger(__name__)


class WhatsAppBot:
    """WhatsApp bot - Conversation flows"""

    def __init__(self):
        self.sheets = GoogleSheetsAPI()

    def handle_message(self, phone_number: str, message_text: str) -> None:
        """Xabarni qabul qilish va javob berish"""
        state = conversation_manager.get_or_create(phone_number)
        text = message_text.strip().lower()

        logger.info(f"📨 {phone_number}: {message_text} [State: {state.state}]")

        # Menu komandalar
        if text in ['start', 'начало', 'меню', 'home', 'bosh', 'menu', '/start']:
            self.show_menu(phone_number, state)
        elif text in ['каталог', 'catalog', 'kataloq', '📦']:
            self.show_categories(phone_number, state)
        elif text in ['буюртма', 'buyurtma', 'orders', 'status', 'статус', '📋']:
            self.show_order_status_ask(phone_number, state)
        elif text in ['ёрдам', 'help', 'yordam', '❓']:
            self.show_help(phone_number, state)

        # Stateful flows
        elif state.state == 'menu':
            self.show_menu(phone_number, state)

        elif state.state == 'catalog':
            self.handle_category_selection(phone_number, state, message_text)

        elif state.state == 'category':
            self.handle_product_selection(phone_number, state, message_text)

        elif state.state == 'product':
            self.handle_quantity_input(phone_number, state, message_text)

        elif state.state == 'cart':
            self.handle_cart_action(phone_number, state, message_text)

        elif state.state == 'checkout_name':
            self.handle_checkout_name(phone_number, state, message_text)

        elif state.state == 'checkout_address':
            self.handle_checkout_address(phone_number, state, message_text)

        elif state.state == 'checkout_confirm':
            self.handle_checkout_confirm(phone_number, state, message_text)

        elif state.state == 'order_status_ask':
            self.handle_order_lookup(phone_number, state, message_text)

        else:
            self.show_menu(phone_number, state)

    def show_menu(self, phone_number: str, state: ConversationState) -> None:
        """Asosiy menu"""
        msg = f"""👋 Xush kelibsiz Zargo Shop'ga!

Nima xohlaysiz?"""

        buttons = [
            {'title': '📦 Каталог'},
            {'title': '📋 Buyu status'},
            {'title': '❓ Yordam'}
        ]

        state.set_state('menu')
        send_whatsapp_message(phone_number, msg, buttons)

    def show_categories(self, phone_number: str, state: ConversationState) -> None:
        """Kategoriyalar ro'yxati"""
        products = self.sheets.get_products()

        # Kategoriyalarni o'zga qilish
        categories = {}
        for p in products:
            cat = p.get('category', 'Boshqa')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p)

        if not categories:
            send_whatsapp_message(phone_number, "❌ Mahsulotlar topilmadi")
            return

        # Button'lar
        buttons = [{'title': cat[:20]} for cat in list(categories.keys())[:3]]
        msg = "Kategoriya tanlang:"

        state.set_state('catalog')
        state.current_product = None
        send_whatsapp_message(phone_number, msg, buttons)

    def handle_category_selection(self, phone_number: str, state: ConversationState, category_text: str) -> None:
        """Kategoriya tanlandi"""
        products = self.sheets.get_products()

        # Kategoriyalarni o'zga qilish
        categories = {}
        for p in products:
            cat = p.get('category', 'Boshqa')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p)

        # Closest match
        category_text_lower = category_text.strip().lower()
        matching_cat = None
        for cat in categories.keys():
            if cat.lower().startswith(category_text_lower) or category_text_lower in cat.lower():
                matching_cat = cat
                break

        if not matching_cat:
            send_whatsapp_message(phone_number, "❌ Kategoriya topilmadi. Qayta tanlang:")
            self.show_categories(phone_number, state)
            return

        # Mahsulotlar ro'yxati
        cat_products = categories[matching_cat]
        state.current_category = matching_cat
        state.set_state('category')
        state.current_page = 0

        msg = f"📦 {matching_cat}:\n\n"
        buttons = []
        for i, p in enumerate(cat_products[:3]):
            msg += f"{i + 1}️⃣ {p['name']} - {p.get('somoni', 0)}{CURRENCY}\n"
            buttons.append({'title': f"{i + 1} - {p['name'][:15]}"})

        send_whatsapp_message(phone_number, msg, buttons)

    def handle_product_selection(self, phone_number: str, state: ConversationState, product_text: str) -> None:
        """Mahsulot tanlandi"""
        products = self.sheets.get_products()

        cat_products = [p for p in products if p.get('category') == state.current_category]

        # Raqam yoki nom bo'yicha qidirib topish
        product_text = product_text.strip()
        product = None

        # Birinchi raqam bol'sa (1️⃣ format)
        if product_text[0].isdigit():
            idx = int(product_text[0]) - 1
            if 0 <= idx < len(cat_products):
                product = cat_products[idx]

        if not product:
            send_whatsapp_message(phone_number, "❌ Mahsulot topilmadi")
            return

        state.current_product = product
        state.set_state('product')

        price = f"{product.get('somoni', 0)}{CURRENCY}"
        msg = f"""📦 *{product['name']}*

💰 Narx: {price}

Qancha olib olmoqchisiz?"""

        buttons = [
            {'title': '1'},
            {'title': '2'},
            {'title': '3+'}
        ]

        send_whatsapp_message(phone_number, msg, buttons)

    def handle_quantity_input(self, phone_number: str, state: ConversationState, qty_text: str) -> None:
        """Miqdor kiriting"""
        product = state.current_product
        if not product:
            send_whatsapp_message(phone_number, "❌ Xato. Menu'ga qaytish...")
            self.show_menu(phone_number, state)
            return

        # Miqdor parser
        try:
            qty_str = qty_text.strip().split()[0]
            if qty_str.endswith('+'):
                qty = 3
            else:
                qty = float(qty_str)
        except:
            qty = 1

        # Narx hisoblash
        unit_price = float(product.get('somoni', 0))
        total_price = qty * unit_price

        state.add_to_cart(
            name=product['name'],
            qty=qty,
            unit=product.get('unit', 'dona'),
            price_total=total_price
        )

        cart_total = state.get_cart_total()
        msg = f"""✅ *{product['name']} × {int(qty)}*

💰 Mahsulot: {total_price}{CURRENCY}
🛒 Suvat jami: {cart_total}{CURRENCY}

Nima qilish?"""

        buttons = [
            {'title': '🛒 Savatni ko\'r'},
            {'title': '🏠 Menu'},
            {'title': '📦 Yana qo\'shing'}
        ]

        state.set_state('category')
        send_whatsapp_message(phone_number, msg, buttons)

    def handle_cart_action(self, phone_number: str, state: ConversationState, action_text: str) -> None:
        """Savat operatsiyalari"""
        action = action_text.strip().lower()

        if action in ['buyurtma', 'order', 'checkout', '✅']:
            self.start_checkout(phone_number, state)
        elif action in ['bosh', 'menu', 'home']:
            self.show_menu(phone_number, state)
        else:
            self.show_cart(phone_number, state)

    def show_cart(self, phone_number: str, state: ConversationState) -> None:
        """Savatni ko'rsatish"""
        if not state.cart:
            send_whatsapp_message(phone_number, "🛒 Savat bo'sh!\n\nKatalogga qayt")
            self.show_categories(phone_number, state)
            return

        msg = "🛒 *SAVAT*\n\n"
        for i, item in enumerate(state.cart):
            msg += f"{i + 1}. {item['name']} × {int(item['qty'])} = {item['price_total']}{CURRENCY}\n"

        msg += f"\n💰 Jami: {state.get_cart_total()}{CURRENCY}"

        buttons = [
            {'title': '✅ Buyurtma qil'},
            {'title': '📦 Ko\'proq'},
            {'title': '🗑️ Tozalash'}
        ]

        state.set_state('cart')
        send_whatsapp_message(phone_number, msg, buttons)

    def start_checkout(self, phone_number: str, state: ConversationState) -> None:
        """Checkout boshlash"""
        total = state.get_cart_total()

        if total < MIN_ORDER_AMOUNT:
            msg = f"❌ Eng kam buyu {MIN_ORDER_AMOUNT}{CURRENCY}!\n\nXozir {total}{CURRENCY} bor"
            send_whatsapp_message(phone_number, msg)
            self.show_menu(phone_number, state)
            return

        state.set_state('checkout_name')
        send_whatsapp_message(phone_number, "👤 Ismingizni kiriting:")

    def handle_checkout_name(self, phone_number: str, state: ConversationState, name_text: str) -> None:
        """Ismni qabul qilish"""
        name = name_text.strip()
        if not name or len(name) < 2:
            send_whatsapp_message(phone_number, "❌ Ismni to'g'ri kiriting:")
            return

        state.set_checkout_data(name=name)
        state.set_state('checkout_address')
        send_whatsapp_message(phone_number, "🏠 Manzilingizni kiriting:")

    def handle_checkout_address(self, phone_number: str, state: ConversationState, address_text: str) -> None:
        """Manzilni qabul qilish"""
        address = address_text.strip()
        if not address or len(address) < 5:
            send_whatsapp_message(phone_number, "❌ Manzi to'g'ri kiriting:")
            return

        state.set_checkout_data(address=address, phone=phone_number)
        state.set_state('checkout_confirm')

        # Tasdiq
        order_dict = state.to_order_dict()
        msg = f"""✅ *BUYURTMA TASDIQI*

👤 Ism: {order_dict['name']}
🏠 Manzil: {order_dict['address']}
📱 Tel: +{phone_number}
💰 Jami: {order_dict['total']}{CURRENCY}

Tasdiqlaysizmi?"""

        buttons = [
            {'title': '✅ Tasdiqlash'},
            {'title': '❌ Bekor qilish'}
        ]

        send_whatsapp_message(phone_number, msg, buttons)

    def handle_checkout_confirm(self, phone_number: str, state: ConversationState, response_text: str) -> None:
        """Buyurtmani tasdiqlash"""
        response = response_text.strip().lower()

        if response not in ['confirm', 'tasdiqlash', 'ok', '✅', 'yes']:
            self.show_menu(phone_number, state)
            return

        # Google Sheets'ga saqlash
        order_dict = state.to_order_dict()
        order_number = self.sheets.save_order(order_dict)

        if not order_number:
            send_whatsapp_message(phone_number, "❌ Xato! Buyurtma saqlanmadi. Qayta urinib ko'ring.")
            self.show_menu(phone_number, state)
            return

        # Mijozni saqlash
        self.sheets.save_customer({
            'phone': phone_number,
            'name': order_dict['name'],
            'address': order_dict['address']
        })

        # Admin'ga bildir
        notify_admin_new_order(
            phone_number,
            order_dict['name'],
            order_dict['total'],
            order_number
        )

        # Tasdiqlash
        msg = f"""✅ *BUYU KABUL QILINDI*

🆔 Raqam: #{order_number}
💰 Jami: {order_dict['total']}{CURRENCY}
⏱️ Yetkazilish: {DELIVERY_TIME} minut

Iltimos kutib oling!
Masalalar bo'lsa: +99290998***"""

        send_whatsapp_message(phone_number, msg)

        # Savatni tozalash va menu
        state.clear_cart()
        state.set_state('menu')
        self.show_menu(phone_number, state)

    def show_order_status_ask(self, phone_number: str, state: ConversationState) -> None:
        """Buyu raqamini so'rash"""
        state.set_state('order_status_ask')
        send_whatsapp_message(phone_number, "Qaysi buyurtmaning statusi?\n\n(Raqamni kiriting, masalan: 123)")

    def handle_order_lookup(self, phone_number: str, state: ConversationState, order_text: str) -> None:
        """Buyurtma statusini qidirib topish"""
        order_number = parse_order_number(order_text)

        if not order_number:
            send_whatsapp_message(phone_number, "❌ Raqam to'g'ri emas. Qayta kiriting:")
            return

        order = self.sheets.get_order_by_number(order_number)

        if not order:
            send_whatsapp_message(phone_number, f"❌ Buyu #{order_number} topilmadi")
            self.show_menu(phone_number, state)
            return

        msg = format_order_for_display(order)
        send_whatsapp_message(phone_number, msg)

        buttons = [
            {'title': '🏠 Menu'},
            {'title': '📋 Yana qidirib'}
        ]
        send_whatsapp_message(phone_number, "Nima qilish?", buttons)

        state.set_state('menu')

    def show_help(self, phone_number: str, state: ConversationState) -> None:
        """Yordam"""
        msg = """❓ *YORDAM*

Zargo Shop bot - mahsulot buyu berish xizmatidir.

📦 *Katalog* - Barcha mahsulotlarni ko'ring
📋 *Status* - Buyu holati
💬 *Yordam* - Bu sahifa

Muammo bo'lsa:
📱 +99290998***
🕐 10:00 - 22:00"""

        send_whatsapp_message(phone_number, msg)
        state.set_state('menu')


# Global bot instance
whatsapp_bot = WhatsAppBot()
