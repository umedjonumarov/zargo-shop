# 🤖 Zargo Shop WhatsApp Bot - Setup Guide

## O'zgartirilgan Fayllar

### Yangi Fayllar (MVP uchun):
1. **whatsapp_config.py** - Meta API sozlamalar
2. **conversation_state.py** - Foydalanuvchi holatini boshqarish
3. **whatsapp_handler.py** - Message handling va API calls
4. **whatsapp_flows.py** - Bot conversation logic
5. **.env.example** - Uzgaruvchilar namunasi

### O'zgartirilgan Fayllar:
1. **app.py** - `/webhook/whatsapp` endpoint qo'shildi
2. **requirements.txt** - `python-dotenv` qo'shildi

---

## 📋 Setup Bosqichlari

### 1️⃣ Meta Developer Account O'rnatish

```bash
1. https://developers.facebook.com ga o'ting
2. "My Apps" → "Create App"
3. App Type: "Business"
4. App Name: "Zargo WhatsApp Bot"
5. "Create App" tugmasini bosing
```

### 2️⃣ WhatsApp Business API Qo'shish

```
1. App dashboard'da "Products" → "+" bosing
2. "WhatsApp" qidirib topib, "Set Up" bosing
3. WhatsApp Business Account yaratish yoki mavjudini ulash
4. Telefon raqamini tasdiqlash (admin's number)
5. Business Phone Number ID va Access Token nusxalash
```

### 3️⃣ Environment Variables O'rnatish

```bash
# .env faylini yarating (Linux/Mac):
cp .env.example .env

# Keyin:
export $(cat .env | xargs)

# Windows PowerShell da:
Get-Content .env | ForEach-Object {
    $key, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($key, $value)
}
```

### 4️⃣ Webhook'ni Facebook'da Ro'yxatdan O'tkazish

```
1. App Settings → Webhooks → "Edit Subscription"
2. Callback URL: https://your-domain.com/webhook/whatsapp
   (MVP uchun ngrok: https://xxxx-xx-xxx-xxx-xx.ngrok.io/webhook/whatsapp)
3. Verify Token: WEBHOOK_VERIFY_TOKEN (env'dan)
4. Subscribe to these fields: messages, message_status
5. "Verify and Save" bosing
```

### 5️⃣ Dependency o'rnatish va Ishga Tushirish

```bash
# Dependency o'rnatish
pip install -r requirements.txt

# Flask'ni ishga tushirish
python app.py

# Or gunicorn bilan:
gunicorn --bind 0.0.0.0:5000 app:app
```

### 6️⃣ Local Testing (ngrok bilan)

```bash
# ngrok o'rnatish (https://ngrok.com)
brew install ngrok  # Mac
choco install ngrok # Windows

# Terminal 1 - Flask ishga tushirish
python app.py

# Terminal 2 - ngrok tunnel yaratish
ngrok http 5000

# Chiqarish: https://xxxx-xx-xxx-xxx-xx.ngrok.io
# Buni Facebook callback URL'da o'rnating
```

---

## 🧪 Testing Qismlari

### Webhook Verification

```bash
# Webhook verify token'ni tekshirish
curl "https://your-domain.com/webhook/whatsapp?hub.verify_token=zargo-webhook-token-2024&hub.challenge=test_challenge"

# Kutilgan javob: test_challenge
```

### Message Yuborish (cURL)

```bash
# Matn xabari yuborish
curl -X POST "https://graph.instagram.com/v18.0/YOUR_PHONE_ID/messages" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "99290998838",
    "type": "text",
    "text": {"body": "Test"}
  }'
```

### Bot'ni Sozlash

1. Meta dashboard'da "Phone Numbers" → Your number → "Manage"
2. "Message Templates" → "Create" (Admin xabarlari uchun)
3. "Display Name" → "Zargo Shop"

---

## 🔄 Conversation Flows

Bot quyidagi state'larda ishlaydi:

```
menu                  - Asosiy menu (Katalog / Status / Yordam)
catalog               - Kategoriya tanlash
category              - Mahsulot ro'yxati
product               - Mahsulot batafsili va qty
cart                  - Savat ko'rish
checkout_name         - Ismni kiritish
checkout_address      - Manzilni kiritish
checkout_confirm      - Tasdiqlash
order_status_ask      - Buyu raqami so'rash
```

### Customer Flow (Misol):

```
Customer: "Assalom"
Bot:      "Menu..." [📦 Katalog] [📋 Status]

Customer: [📦 Katalog]
Bot:      "Kategoriya:" [🥐 Noshushta] [🥫 Kunlik]

Customer: [🥐 Noshushta]
Bot:      "1️⃣ Lepinja - 25с\n2️⃣ Samsa - 15с"

Customer: "1️⃣"
Bot:      "Qancha?" [1] [2] [3+]

Customer: "2"
Bot:      "✅ 2x Lepinja = 50с (50/100с)"

Customer: [🛒 Savat]
Bot:      "Buyu qilasizmi?" [✅ Tasdiqlash]

Customer: [✅]
Bot:      "Ismingiz?"
Customer: "Ahror"
Bot:      "Manzili?"
Customer: "Somoniyon 45"
Bot:      "Tasdiqlash?" [✅]

Customer: [✅]
Bot:      "✅ Buyu #123!\nAdmin: 📨 NEW ORDER #123 | Ahror | 50с"
```

---

## 🚀 Production Deployment

### Environment Variables Ro'yxatdan O'tkazish

```bash
# Heroku
heroku config:set WHATSAPP_PHONE_ID=...
heroku config:set WHATSAPP_TOKEN=...
heroku config:set WEBHOOK_VERIFY_TOKEN=...

# Render
# .env file'ni settings'da o'rnating

# AWS / DigitalOcean
# Environment variables'ni o'rnating
```

### Webhook URL Update

```
Facebook App Settings → Webhooks → Edit Subscription
Callback URL: https://zargo-shop.herokuapp.com/webhook/whatsapp
```

### Error Handling & Logging

```python
# Barcha xatolar app.py'da log'lanadi
# Fayl: stdout/stderr
# Sms'da ko'rish:
tail -f app.log

# Production: Sentry/CloudWatch/ELK
```

---

## 📊 Admin Notifications

Admin +99290998838'ga quyidagi xabar oladi:

```
✅ YANGI BUYU

📦 Raqam: #456
👤 Mijoz: Ahror
📱 Tel: +99291234567
💰 Jami: 50с
⏱️ Vaqti: 14:35:22

/admin/orders'da ko'ring
```

---

## 🐛 Debugging

### Webhook'ni tekshirish:

```python
# app.py'da:
logger.info(f"Webhook: {request.get_json()}")

# Keyin:
python -u app.py 2>&1 | tee app.log
```

### Bot holatini tekshirish:

```python
from conversation_state import conversation_manager
state = conversation_manager.states['99290998838']
print(state.cart)
print(state.state)
```

### Google Sheets API tekshirish:

```python
from whatsapp_handler import GoogleSheetsAPI
sheets = GoogleSheetsAPI()
products = sheets.get_products()
print(products)
```

---

## ✅ Checklist

- [ ] Meta Developer Account yaratildi
- [ ] WhatsApp Business API qo'shildi
- [ ] Phone ID va Token nusxalandi
- [ ] .env fayli to'ldirildi
- [ ] Webhook verify token'i o'rnatildi
- [ ] ngrok bilan local testing qilindi
- [ ] Facebook'da webhook ro'yxatdan o'tkazildi
- [ ] Test message yuborildi va qabul qilindi
- [ ] Bot barcha menyularni ko'rsatadi
- [ ] Savat ishlaydi
- [ ] Buyurtma Google Sheets'ga saqlanadi
- [ ] Admin xabari oldi
- [ ] Production'da o'rnatildi

---

## 📞 Qo'llab-Quvvatlash

### Common Errors

1. **"Unauthorized" (403)**
   - `WEBHOOK_VERIFY_TOKEN` to'g'ri ekanligini tekshiring

2. **"Message not sent"**
   - `WHATSAPP_TOKEN` amal qilayotganligini tekshiring
   - Rate limit'ni tekshiring (100 msg/sec)

3. **"No messages received"**
   - Webhook subscribe fields'ni tekshiring
   - Firebase logs'ni tekshiring

---

**MVP uchun tayyor! 🎉**

Savollar bo'lsa, Facebook Developer docs'ni o'qing:
https://developers.facebook.com/docs/whatsapp/cloud-api
