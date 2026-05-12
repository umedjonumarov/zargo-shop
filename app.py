"""
ZarGo Shop — Flask asosiy fayl
"""
import os
import logging
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session, flash
)

from config import SECRET_KEY, ADMIN_PASSWORD, META_VERIFY_TOKEN, SHOP_URL, MIN_ORDER, CURRENCY, PORT
from database import db
from ai_agent import handle_message
from whatsapp_meta import notify_admin
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Scheduler ishga tushirish (Render'da faqat bir worker bo'lganda)
if os.environ.get('WERKZEUG_RUN_MAIN') != 'true' or not app.debug:
    _scheduler = start_scheduler()


# ─── Admin decorator ─────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper


# ─── Do'kon (Shop) ────────────────────────────────────────────────────────────

@app.route('/shop')
def shop_index():
    phone = request.args.get('phone', '').strip()
    if phone:
        digits = ''.join(c for c in phone if c.isdigit())
        if digits:
            session['wa_phone'] = digits
            session.modified = True

    products = db.get_products()
    categories = {}
    for p in products:
        cat = p.get('category', 'Бошқа')
        categories.setdefault(cat, []).append(p)

    return render_template('shop/index.html', categories=categories)


@app.route('/shop/checkout', methods=['GET', 'POST'])
def shop_checkout():
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        phone   = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        cart    = session.get('cart', [])

        if not cart:
            flash('Сават бўш!', 'error')
            return redirect(url_for('shop_index'))

        total = sum(item['price_total'] for item in cart)

        if total < MIN_ORDER:
            flash(f'Энг кам буюртма {MIN_ORDER}{CURRENCY}!', 'error')
            return redirect(url_for('shop_checkout'))

        phone_digits = ''.join(c for c in phone if c.isdigit())
        if not phone_digits.startswith('992') or len(phone_digits) != 12:
            flash('Тожикистон телефон рақамини киритинг (+992 XX XXX XX XX)', 'error')
            return redirect(url_for('shop_checkout'))

        items_text = '\n'.join(
            f"• {item['name']} × {int(item['qty'])} = {item['price_total']}{CURRENCY}"
            for item in cart
        )

        order_number = db.save_order({
            'phone':   phone_digits,
            'name':    name,
            'address': address,
            'items':   items_text,
            'total':   total,
            'payment': 'naqd',
            'status':  'yangi',
            'source':  'web',
        })

        db.save_customer(phone_digits, name)
        notify_admin(order_number, name, phone_digits, address, items_text, total)

        session.pop('cart', None)
        return redirect(url_for('shop_confirm', number=order_number))

    cart  = session.get('cart', [])
    total = sum(item['price_total'] for item in cart)
    if not cart:
        return redirect(url_for('shop_index'))

    wa_phone     = session.get('wa_phone', '')
    prefill_phone = f"+{wa_phone}" if wa_phone else ''
    return render_template('shop/checkout.html', cart=cart, total=total, prefill_phone=prefill_phone)


@app.route('/shop/confirm/<number>')
def shop_confirm(number):
    order = db.get_order(number)
    if not order:
        return redirect(url_for('shop_index'))
    return render_template('shop/confirm.html', order=order, number=number)


# ─── Cart API ─────────────────────────────────────────────────────────────────

@app.route('/api/cart/add', methods=['POST'])
def cart_add():
    data        = request.json
    product_name = data.get('name', '')
    qty          = float(data.get('qty', 1))
    unit         = data.get('unit', 'dona')
    price_total  = float(data.get('price_total', 0))

    cart = session.get('cart', [])
    for item in cart:
        if item['name'] == product_name:
            item['qty']         += qty
            item['price_total'] += price_total
            break
    else:
        cart.append({'name': product_name, 'qty': qty, 'unit': unit, 'price_total': price_total})

    session['cart'] = cart
    session.modified = True
    return jsonify({'success': True, 'count': len(cart), 'total': sum(i['price_total'] for i in cart)})


@app.route('/api/cart/remove', methods=['POST'])
def cart_remove():
    name = request.json.get('name', '')
    cart = [i for i in session.get('cart', []) if i['name'] != name]
    session['cart'] = cart
    session.modified = True
    return jsonify({'success': True, 'count': len(cart), 'total': sum(i['price_total'] for i in cart)})


@app.route('/api/cart/info')
def cart_info():
    cart = session.get('cart', [])
    return jsonify({'count': len(cart), 'total': sum(i['price_total'] for i in cart)})


@app.route('/api/cart/clear', methods=['POST'])
def cart_clear():
    session.pop('cart', None)
    return jsonify({'success': True})


# ─── Admin Panel ─────────────────────────────────────────────────────────────

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Нотўғри парол!', 'error')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    orders    = db.get_all_orders()
    today_str = datetime.now().strftime('%Y-%m-%d')
    today_orders = [o for o in orders if str(o.get('date', '')).startswith(today_str)]
    today_total  = sum(float(o.get('total', 0)) for o in today_orders)
    avg_check    = (today_total / len(today_orders)) if today_orders else 0

    stats = {
        'total_orders':  len(orders),
        'today_orders':  len(today_orders),
        'today_total':   today_total,
        'avg_check':     round(avg_check, 1),
    }
    recent = sorted(orders, key=lambda o: o.get('date', ''), reverse=True)[:15]
    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent,
                           now=datetime.now().strftime('%d.%m.%Y %H:%M'))


@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = db.get_all_orders()
    orders = sorted(orders, key=lambda o: o.get('date', ''), reverse=True)
    return render_template('admin/orders.html', orders=orders)


@app.route('/admin/orders/<number>/status', methods=['POST'])
@admin_required
def admin_update_status(number):
    status = request.form.get('status', '')
    db.update_order_status(number, status)
    flash(f'#{number} buyurtma statusi yangilandi!', 'success')
    return redirect(url_for('admin_orders'))


@app.route('/admin/orders/<number>/delete', methods=['POST'])
@admin_required
def admin_delete_order(number):
    db.delete_order(number)
    flash(f'#{number} buyurtma o\'chirildi.', 'info')
    return redirect(url_for('admin_orders'))


# ─── WhatsApp Webhook ─────────────────────────────────────────────────────────

@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token', '')
        challenge    = request.args.get('hub.challenge', '')
        if verify_token == META_VERIFY_TOKEN:
            return challenge, 200
        return 'Unauthorized', 403

    try:
        data = request.get_json(silent=True) or {}
        if data.get('object') != 'whatsapp_business_account':
            return jsonify({'status': 'ignored'}), 200

        entry   = (data.get('entry') or [{}])[0]
        changes = (entry.get('changes') or [{}])[0]
        value   = changes.get('value', {})
        messages = value.get('messages', [])

        if not messages:
            return jsonify({'status': 'no_message'}), 200

        message = messages[0]
        sender  = message.get('from', '')
        msg_type = message.get('type', '')

        if msg_type == 'text':
            text = message.get('text', {}).get('body', '').strip()
        elif msg_type == 'interactive':
            inter = message.get('interactive', {})
            text = (
                inter.get('button_reply', {}).get('title') or
                inter.get('list_reply', {}).get('title') or ''
            )
        else:
            text = ''

        if not text or not sender:
            return jsonify({'status': 'empty'}), 200

        logger.info(f"WhatsApp: {sender} → {text[:80]}")
        handle_message(sender, text)
        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        logger.error(f"Webhook xatosi: {e}")
        return jsonify({'status': 'error'}), 500


# ─── Bosh sahifa yo'naltirish ─────────────────────────────────────────────────

@app.route('/')
def root():
    return redirect(url_for('admin_login'))


# ─── Ishga tushirish ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
