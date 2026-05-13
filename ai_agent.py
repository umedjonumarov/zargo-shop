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
_processed_ids: set = set()   # ikki marta kelgan webhook xabarlarini bloklash

MAX_HISTORY = 20


# ─── Yordamchi funksiyalar ───────────────────────────────────────────────────

def _session(phone: str) -> dict:
    if phone not in _sessions:
        _sessions[phone] = {'history': [], 'greeted_today': None, 'customer': None, 'db_checked': False}
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
        sess["customer"]   = {"name": cname, "gender": gender, "language": language}
        sess["db_checked"] = True
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
            "Мижоз биринчи маротаба ёзмоқда — базада топилмади. "
            "Илиқ саломла (Ассалому алайкум!) ва ФАҚАТ БИРА МАРТА исмини сўра. "
            "Мижоз исмини айтгандан кейин — register_customer чақир, "
            "сўнг дарҳол хуш келибсиз деб ёрдам таклиф қил. "
            "ИСМИНИ ҚАЙТА СўРАМА."
        )
    elif first_msg_today:
        name  = customer["name"]
        title = _title(customer.get("gender", "unknown"))
        greeting_rule = (
            f"Мижоз исми маълум: {name} ({title}). "
            f"Айт: 'Ассалому алайкум {name} {title}, "
            f"ZarGo онлайн дўконида сизни қайта кўрганимиздан хурсандмиз! "
            f"Сизга қандай ёрдам бера оламан?' "
            f"ҲЕЧ ҚАЧОН исмини қайта сўрама."
        )
    else:
        name  = customer["name"]
        title = _title(customer.get("gender", "unknown"))
        tw    = _time_word()
        greeting_rule = (
            f"Мижоз исми маълум: {name} ({title}). ўша кун яна ёзди. "
            f"Расмий салом ишлатма — шунчаки 'Хайрли {tw} {name} {title}!' де ва давом эт. "
            f"ҲЕЧ ҚАЧОН исмини қайта сўрама."
        )

    return f"""Сен ZarGo онлайн дўконининг AI ёрдамчисан.

ТИЛ ҚОИДАСИ (МУҲИМ):
- Мижоз рус тилида ёзса — ўзбек кирилида жавоб бер.
- Мижоз ўзбек кирилида ёзса — ўзбек кирилида жавоб бер.
- Мижоз тожик тилида ёзса — тожик кирилида жавоб бер.
- Ҳеч қачон лотин ёзуви ишлатма.
- Ҳеч қачон рус тилида жавоб берма.

ВАЗИФА: Фақат маҳсулот танлашда ёрдам бер. Бошқа мавзуда: «Мен фақат сизга маҳсулот танлашда ёрдам бера оламан, холос» де.

МИЖОЗ МАЪЛУМОТИ:
- Телефон: {phone}
- Исм: {customer["name"] if customer else "номаълум"}
- Жинс: {customer.get("gender","unknown") if customer else "unknown"}
- Ҳолат: {"янги" if is_new else "доимий"}

САЛОМЛАШИШ ҚОИДАСИ: {greeting_rule}

ЖИНС АНИҚЛАШ (МУҲИМ):
ўзбек/Тожик исмлари бўйича:
- Аёл исмлари (опа): Малика, Нилуфар, Зебо, Гулнора, Мадина, Замира, Шаҳло, Дилноза, Феруза, Барно, Мунира, Хурмо, Ойдин, Насиба, Лола, Шоира, Матлуба, Мухаббат, Нозима, Умида, Дилрабо, Хилола, Сабина, Камола, Ирода, Азиза, Латофат, Мафтуна, Ситора, Зулфия ва «а», «о», «е», «и» билан тугайдиган исмлар.
- Эркак исмлари (ака): Умеджон, Баҳром, Санжар, Жавлон, Музаффар, Суҳроб, Фирдавс, Бобур, Алишер, Жасур, ўткир, Шерзод, Нодир, Зафар, Равшан, Дониёр, Комил, Рустам, Тимур, Акбар, Шухрат, Ойбек, Улугбек, Хуршид, «жон», «бек», «али», «хон», «зод» билан тугайдиган исмлар.
- Номаълум бўлса — ака де.

МУҲИМ ҚОИДАЛАР:
• Мижозни рўйхатга олиш ёки базага сақлаш ҳақида ҲЕЧ ҚАЧОН айтма — бу ички жараён.
• Мижоз исмини айтса — register_customer чақир, сўнг дарҳол саломлашиб, ёрдам таклиф қил.
• Минимал буюртма: {MIN_ORDER}{CURRENCY}. Камроқ бўлса рад эт.
• Йўтказиб бериш: {DELIVERY_AREA} бўйича, {MIN_ORDER}{CURRENCY} дан юқори — бепул.
• Тўлов: фақат нақд (ётказилганда).

МАҲСУЛОТ/БУЮРТМА:
• Мижоз маҳсулот сўраса, каталог сўраса, буюртма бермоқчи бўлса — ҲАМИША get_shop_link чақир ва ҳаволани бер. Маҳсулот рўйхатини матн кўринишида ҲЕCH ҚАЧОН юборма.
• get_products ни фақат нарх ёки мавжудлигини аниқлаш учун ичкида ишлат, мижозга матн рўйхат кўрсатма.
• Буюртма рақами сўраса — get_order_status чақир.

Вақт: {_hour()}:00 ({_time_word()})"""


# ─── Asosiy xabarni qayta ishlash ────────────────────────────────────────────

def handle_message(phone: str, text: str, msg_id: str = "") -> None:
    # Ikki marta kelgan xabarni bloklash
    if msg_id:
        if msg_id in _processed_ids:
            return
        _processed_ids.add(msg_id)
        if len(_processed_ids) > 500:
            _processed_ids.clear()

    sess     = _session(phone)
    customer = sess.get("customer")

    # DBdan bir marta yuklash (session yangi bo'lsa)
    if customer is None and not sess.get("db_checked"):
        sess["db_checked"] = True
        customer = db.get_customer(phone)
        if customer:
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
        send_text(phone, "Хатолик юз берди. Илтимос, бироздан сўнг қайта уриниб кўринг.")
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
            final_text = "Хатолик юз берди."
    else:
        final_text = msg.content or ""
        sess["history"].append({"role": "assistant", "content": final_text})

    # Birinchi xabar belgilash
    if sess.get("greeted_today") != date.today():
        sess["greeted_today"] = date.today()

    # Mijozga javob yuborish
    if final_text.strip():
        send_text(phone, final_text.strip())
