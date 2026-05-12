"""
ZarGo Shop — OpenAI GPT AI Agent
Mijozlar bilan WhatsApp orqali muloqot qiladi.
"""
import json
import logging
from datetime import datetime, date

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL, SHOP_URL, MIN_ORDER, CURRENCY, DELIVERY_AREA
from database import db
from whatsapp_meta import send_text

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# ─── Xotira (in-memory) ─────────────────────────────────────────────────────
# { phone: { history: [...], greeted_today: date | None, customer: dict | None } }
_sessions: dict = {}

MAX_HISTORY = 20  # GPT ga yuboriladigan maksimal xabar soni


# ─── Yordamchi funksiyalar ───────────────────────────────────────────────────

def _session(phone: str) -> dict:
    if phone not in _sessions:
        _sessions[phone] = {'history': [], 'greeted_today': None, 'customer': None}
    return _sessions[phone]


def _hour() -> int:
    return datetime.now().hour


def _time_word() -> str:
    h = _hour()
    if 5 <= h < 12:
        return "тонг"
    elif 12 <= h < 18:
        return "кун"
    else:
        return "кеч"


def _title(gender: str) -> str:
    return "опа" if gender == "female" else "ака"


# ─── OpenAI Function Definitions ────────────────────────────────────────────

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "register_customer",
            "description": "Yangi mijozni bazaga ro'yxatga olish. Mijoz ismini aytgandan keyin chaqiriladi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name":     {"type": "string", "description": "Mijoz ismi"},
                    "gender":   {"type": "string", "enum": ["male", "female", "unknown"],
                                 "description": "Ismdan aniqlanadigan jins"},
                    "language": {"type": "string", "enum": ["uz", "tj"],
                                 "description": "Mijoz tilini ismi/yozuvidan aniqlash"},
                },
                "required": ["name", "gender", "language"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_products",
            "description": "Barcha mavjud mahsulotlar ro'yxatini olish. Mijoz katalog ko'rmoqchi bo'lganda yoki mahsulot haqida so'raganda chaqiriladi.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_shop_link",
            "description": "Mijoz mahsulot tanlash uchun do'kon saytiga havolani olish.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Buyurtma holatini tekshirish.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {"type": "string", "description": "Buyurtma raqami (masalan: 42)"},
                },
                "required": ["order_number"],
            },
        },
    },
]


# ─── Function call bajargich ─────────────────────────────────────────────────

def _run_tool(phone: str, name: str, args: dict) -> str:
    sess = _session(phone)

    if name == "register_customer":
        gender   = args.get("gender", "unknown")
        language = args.get("language", "uz")
        cname    = args.get("name", "")
        db.save_customer(phone, cname, gender, language)
        sess["customer"] = {"name": cname, "gender": gender, "language": language}
        return f"Mijoz ro'yxatga olindi: {cname} ({gender}, {language})"

    if name == "get_products":
        products = db.get_products()
        if not products:
            return "Hozircha mahsulotlar yo'q."
        lines = [f"- {p['name']}: {p.get('somoni', p.get('price', 0))}{CURRENCY}" for p in products]
        return "Mavjud mahsulotlar:\n" + "\n".join(lines)

    if name == "get_shop_link":
        link = f"{SHOP_URL}/shop?phone={phone}"
        return f"Do'kon havolasi: {link}"

    if name == "get_order_status":
        order = db.get_order(str(args.get("order_number", "")))
        if not order:
            return "Buyurtma topilmadi."
        return (
            f"Buyurtma #{order.get('number')} holati: {order.get('status', '?')}\n"
            f"Sana: {order.get('date', '?')}\n"
            f"Jami: {order.get('total', '?')}{CURRENCY}"
        )

    return "Noma'lum funksiya."


# ─── System prompt ───────────────────────────────────────────────────────────

def _build_system(phone: str, sess: dict) -> str:
    customer        = sess.get("customer")
    greeted_today   = sess.get("greeted_today")
    today           = date.today()
    is_new          = customer is None
    first_msg_today = (greeted_today != today)

    if is_new:
        greeting_rule = (
            "Мижоз биринчи маротаба ёзмоқда. "
            "Илиқ саломлаш (Ассалому алайкум!), ва исмини сўра."
        )
    elif first_msg_today:
        name   = customer["name"]
        title  = _title(customer.get("gender", "unknown"))
        greeting_rule = (
            f"Қайтиб келган мижоз. Қуйидагини айт: "
            f"'Ассалому алайкум {name} {title}, ZarGo онлайн дўконида сизни қайта кўрганимиздан хурсандмиз! "
            f"Сизга қандай ёрдам бера оламан?'"
        )
    else:
        name   = customer["name"]
        title  = _title(customer.get("gender", "unknown"))
        tw     = _time_word()
        greeting_rule = (
            f"Мижоз ўша кун яна ёзди. Расмий салом ишлатма. "
            f"Шунчаки: 'Хайрли {tw} {name} {title}!' де ва давом эт."
        )

    return f"""Сен ZarGo онлайн дўконининг AI ёрдамчисисан.

ТИЛ: Мижоз ўзбек кирилида ёзса — ўзбек кирилида жавоб бер. Тожик кирилида ёзса — тожик кирилида жавоб бер. Ҳеч қачон лотин ёзуви ишлатма. Рус тилини ишлатма.

ВАЗИФА: Фақат маҳсулот танлашда ёрдам бер. Бошқа мавзуда: «Мен фақат сизга маҳсулот танлашда ёрдам бера оламан, холос» де.

МИЖОЗ МАЪЛУМОТИ:
- Телефон: {phone}
- Исм: {customer["name"] if customer else "номаълум"}
- Жинс: {customer.get("gender","unknown") if customer else "unknown"}
- Ҳолат: {"янги" if is_new else "доимий"}

САЛОМЛАШИШ ҚОИДАСИ: {greeting_rule}

ЖИНС: Исмдан жинсни аниқла. Аёл → опа. Эркак → ака. Номаълум → ака.

ҚОИДАЛАР:
• Минимал буюртма: {MIN_ORDER}{CURRENCY}. Камроқ бўлса рад эт.
• Ётказиб бериш: {DELIVERY_AREA} бўйича, {MIN_ORDER}{CURRENCY} дан юқори — бепул.
• Тўлов: фақат нақд (ётказилганда).

МАҲСУЛОТ/БУЮРТМА:
• Каталог кўрмоқчи бўлса — get_shop_link чақир ва ҳаволани бер.
• Маҳсулотлар ҳақида сўраса — get_products чақир.
• Буюртма рақами сўраса — get_order_status чақир.
• Янги мижоз исмини айтса — register_customer чақир.

Вақт: {_hour()}:00 ({_time_word()})"""


# ─── Asosiy xabarni qayta ishlash ────────────────────────────────────────────

def handle_message(phone: str, text: str) -> None:
    sess     = _session(phone)
    customer = sess.get("customer")

    # Agar sessiyada yo'q bo'lsa, DBdan qidir
    if customer is None:
        customer = db.get_customer(phone)
        sess["customer"] = customer

    # Tarix ga foydalanuvchi xabarini qo'sh
    sess["history"].append({"role": "user", "content": text})
    if len(sess["history"]) > MAX_HISTORY:
        sess["history"] = sess["history"][-MAX_HISTORY:]

    system_msg = _build_system(phone, sess)
    messages   = [{"role": "system", "content": system_msg}] + sess["history"]

    # GPT chaqiruvi (funksiyalar bilan)
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=_TOOLS,
            tool_choice="auto",
            max_tokens=600,
            temperature=0.7,
        )
    except Exception as e:
        logger.error(f"OpenAI xatosi: {e}")
        send_text(phone, "Хatolик юз берди. Илтимос, бироздан сўнг қайта уриниб кўринг.")
        return

    msg = response.choices[0].message

    # Funksiya chaqiruvlari
    if msg.tool_calls:
        tool_results = []
        for tc in msg.tool_calls:
            args   = json.loads(tc.function.arguments)
            result = _run_tool(phone, tc.function.name, args)
            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        # Tool natijalarini tarixa qo'sh va GPT dan yakuniy javob ol
        sess["history"].append(msg.model_dump(exclude_unset=True))
        sess["history"].extend(tool_results)

        messages2 = [{"role": "system", "content": system_msg}] + sess["history"]
        try:
            response2 = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages2,
                max_tokens=600,
                temperature=0.7,
            )
            final_text = response2.choices[0].message.content or ""
            sess["history"].append({"role": "assistant", "content": final_text})
        except Exception as e:
            logger.error(f"OpenAI 2-chaqiruv xatosi: {e}")
            final_text = "Хatolик юз берди."
    else:
        final_text = msg.content or ""
        sess["history"].append({"role": "assistant", "content": final_text})

    # Birinchi xabar belgilash
    if sess.get("greeted_today") != date.today():
        sess["greeted_today"] = date.today()

    # Mijozga javob yuborish
    if final_text.strip():
        send_text(phone, final_text.strip())
