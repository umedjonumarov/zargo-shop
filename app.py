"""
Zargo Shop - Flask Web Application
Mahsulot katalogi, savat, buyurtma
"""
import os
import json
import requests
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash

# === CONFIG IMPORT ===
from config import SHEETS_URL, SECRET_KEY, ADMIN_PASSWORD, GREEN_API_INSTANCE_ID, GREEN_API_TOKEN, ADMIN_PHONE
from whatsapp_config import WEBHOOK_VERIFY_TOKEN
from whatsapp_flows import whatsapp_bot

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def notify_admin_whatsapp(order_number, name, phone, address, items_text, total):
    """Adminga WhatsApp orqali yangi zakaz haqida xabar yuborish"""
    if not GREEN_API_TOKEN:
        logger.warning("GREEN_API_TOKEN yo'q — WhatsApp xabar yuborilmadi")
        return
    try:
        msg = (
            f"🛒 *YANGI WEB ZAKAZ!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 #{order_number}\n"
            f"👤 {name}\n"
            f"📱 +{phone}\n"
            f"📍 {address}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{items_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Jami: *{total} so'm*\n"
            f"🌐 Manba: Sayt (zargo-shop.onrender.com)"
        )
        url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
        requests.post(url, json={
            "chatId": f"{ADMIN_PHONE}@c.us",
            "message": msg
        }, timeout=10)
        logger.info(f"Admin WhatsApp xabari yuborildi: #{order_number}")
    except Exception as e:
        logger.error(f"WhatsApp xabar xatosi: {e}")

app = Flask(__name__)
app.secret_key = SECRET_KEY

def sheets_get(action, **params):
    """Google Sheets'dan ma'lumot olish"""
    try:
        params['action'] = action
        resp = requests.get(SHEETS_URL, params=params, timeout=15)
        return resp.json()
    except Exception as e:
        print(f"Sheets GET xato: {e}")
        return {}

def sheets_post(action, payload):
    """Google Sheets'ga ma'lumot yozish"""
    try:
        payload['action'] = action
        resp = requests.post(SHEETS_URL, json=payload, timeout=15)
        return resp.json()
    except Exception as e:
        print(f"Sheets POST xato: {e}")
        return {}

# =========================================================================
# ASOSIY SAHIFALAR
# =========================================================================

@app.route('/')
def index():
    """Bosh sahifa - kategoriyalar va mahsulotlar"""
    # WhatsApp botdan kelgan telefon raqamini sessiyaga saqlash
    phone_param = request.args.get('phone', '').strip()
    if phone_param:
        digits = ''.join(c for c in phone_param if c.isdigit())
        if digits:
            session['wa_phone'] = digits
            session.modified = True

    products = sheets_get('products').get('products', [])

    # Kategoriyalar bo'yicha guruhlash
    categories = {}
    for p in products:
        cat = p.get('category', 'Boshqa')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(p)

    return render_template('index.html', categories=categories)

@app.route('/product/<product_name>')
def product_detail(product_name):
    """Mahsulot batafsil sahifasi"""
    products = sheets_get('products').get('products', [])
    product = None
    for p in products:
        if p['name'] == product_name:
            product = p
            break
    if not product:
        return "Mahsulot topilmadi", 404
    price = f"{product['somoni']}c"
    if product['diram']:
        price += f"{product['diram']}diram"
    return render_template('product.html', product=product, price=price)

@app.route('/cart')
def cart():
    """Savat sahifasi"""
    cart_items = session.get('cart', [])
    total = sum(item['price_total'] for item in cart_items)
    return render_template('cart.html', cart=cart_items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Buyurtma sahifasi"""
    if request.method == 'POST':
        name = request.form.get('name', '')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        cart_items = session.get('cart', [])

        if not cart_items:
            flash('Savat bosh!', 'error')
            return redirect(url_for('cart'))

        total = sum(item['price_total'] for item in cart_items)

        if total < 100:
            flash('Eng kam buyurtma 100 somoni!', 'error')
            return redirect(url_for('cart'))

        phone_digits = ''.join(c for c in phone if c.isdigit())
        if not phone_digits.startswith('992') or len(phone_digits) != 12:
            flash('Tojikiston telefon raqamini kiriting (+992 XX XXX XX XX)', 'error')
            return redirect(url_for('checkout'))

        items_text = '\n'.join([
            f"* {item['name']} x {item['qty']} = {item['price_total']}c"
            for item in cart_items
        ])

        result = sheets_post('save_order', {
            'order': {
                'phone': phone_digits,
                'name': name,
                'address': address,
                'items': items_text,
                'total': total,
                'payment': 'naqd',
                'status': 'qabul qilindi',
                'source': 'web'
            }
        })

        order_number = result.get('number', '?')

        sheets_post('save_customer', {
            'customer': {
                'phone': phone_digits,
                'name': name,
                'address': address
            }
        })

        # Adminga WhatsApp xabar yuborish
        notify_admin_whatsapp(order_number, name, phone_digits, address, items_text, total)

        session.pop('cart', None)

        return render_template('confirm.html',
                             order_number=order_number,
                             total=total,
                             name=name,
                             phone=phone,
                             address=address)

    # GET
    cart_items = session.get('cart', [])
    total = sum(item['price_total'] for item in cart_items)

    if not cart_items:
        return redirect(url_for('cart'))

    wa_phone = session.get('wa_phone', '')
    prefill_phone = f"+{wa_phone}" if wa_phone else ''

    return render_template('checkout.html', cart=cart_items, total=total, prefill_phone=prefill_phone)

# =========================================================================
# API ENDPOINT'LAR
# =========================================================================

@app.route('/api/cart/info')
def api_cart_info():
    cart = session.get('cart', [])
    return jsonify({
        'count': len(cart),
        'total': sum(item['price_total'] for item in cart)
    })

@app.route('/api/cart/add', methods=['POST'])
def api_cart_add():
    data = request.json
    product_name = data.get('name', '')
    qty = float(data.get('qty', 1))
    unit = data.get('unit', '')
    price_total = float(data.get('price_total', 0))

    cart = session.get('cart', [])

    for item in cart:
        if item['name'] == product_name:
            item['qty'] += qty
            item['price_total'] += price_total
            break
    else:
        cart.append({
            'name': product_name,
            'qty': qty,
            'unit': unit,
            'price_total': price_total
        })

    session['cart'] = cart
    session.modified = True

    return jsonify({
        'success': True,
        'cart_count': len(cart),
        'cart_total': sum(item['price_total'] for item in cart)
    })

@app.route('/api/cart/remove', methods=['POST'])
def api_cart_remove():
    data = request.json
    product_name = data.get('name', '')
    cart = session.get('cart', [])
    cart = [item for item in cart if item['name'] != product_name]
    session['cart'] = cart
    session.modified = True
    return jsonify({
        'success': True,
        'cart_count': len(cart),
        'cart_total': sum(item['price_total'] for item in cart)
    })

@app.route('/api/cart/clear', methods=['POST'])
def api_cart_clear():
    session.pop('cart', None)
    return jsonify({'success': True})

# =========================================================================
# ADMIN PANEL
# =========================================================================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Notogri parol!', 'error')
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    orders = sheets_get('orders').get('orders', [])
    customers = sheets_get('customers').get('customers', [])

    today = datetime.now().strftime('%Y-%m-%d')
    today_orders = [o for o in orders if o.get('date', '').startswith(today)]

    stats = {
        'total_orders': len(orders),
        'today_orders': len(today_orders),
        'total_customers': len(customers),
        'total_revenue': sum(o.get('total', 0) for o in orders)
    }

    recent_orders = sorted(orders, key=lambda o: o.get('date', ''), reverse=True)[:10]

    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent_orders)

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = sheets_get('orders').get('orders', [])
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/order/<number>/status', methods=['POST'])
@admin_required
def admin_update_status(number):
    new_status = request.form.get('status', '')
    sheets_post('update_order_status', {
        'number': number,
        'status': new_status
    })
    return redirect(url_for('admin_orders'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

# =========================================================================
# WHATSAPP WEBHOOK
# =========================================================================

@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token', '')
        challenge = request.args.get('hub.challenge', '')
        if verify_token == WEBHOOK_VERIFY_TOKEN:
            return challenge
        return 'Unauthorized', 403

    try:
        data = request.get_json()
        if data.get('object') != 'whatsapp_business_account':
            return jsonify({'success': False})

        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])

        if not messages:
            return jsonify({'success': True})

        message = messages[0]
        sender_phone = message.get('from', '')
        message_text = None

        if message.get('type') == 'text':
            message_text = message.get('text', {}).get('body', '')
        elif message.get('type') == 'interactive':
            interactive = message.get('interactive', {})
            button_reply = interactive.get('button_reply', {})
            message_text = button_reply.get('title', '')

        if not message_text:
            return jsonify({'success': True})

        logger.info(f"Yangi xabar: {sender_phone} - {message_text}")
        whatsapp_bot.handle_message(sender_phone, message_text)

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Webhook xatosi: {e}")
        return jsonify({'success': False}), 500

# =========================================================================
# ISHGA TUSHIRISH
# =========================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
