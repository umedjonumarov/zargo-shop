/**
 * ZarGo — Ikki tilli (UZ/TJ) tarjima moduli
 * Barcha matnlar Rus Kiril yozuvida
 */

const TRANSLATIONS = {
  uz: {
    // Header / Nav
    cart:            "Сават",
    back_to_bot:     "WhatsApp ботга қайтиш",

    // Shop index
    welcome:         "Хуш келибсиз!",
    subtitle:        "Фреш маҳсулотлар — Зарзаминдан",
    free_delivery:   "100с дан бепул этказиб бериш",
    no_products:     "Ҳозирча маҳсулотлар йўқ",
    add_cart:        "Саватга",

    // Checkout
    step_cart:       "Сават",
    step_info:       "Маълумотлар",
    cart_empty:      "Сават бўш",
    total:           "Жами:",
    min_order_note:  "Минимал буюртма 100с. Этказиб бериш 100с дан бепул (Зарзамин қишлоғи).",
    next:            "Давом этиш",
    go_shop:         "Дўконга қайтиш",
    cash_note:       "Тўлов: фақат нақд (маҳсулот этказилганда)",
    your_name:       "Исмингиз *",
    name_hint:       "Тўлиқ ism ёки фақат исм киритинг",
    your_phone:      "Телефон рақам *",
    phone_hint:      "Масалан: +992 92 790 96 98",
    your_address:    "Манзил *",
    address_hint:    "Масалан: Зарзамин, Мустақиллик кўчаси, 12-уй",
    confirm_order:   "Буюртмани тасдиқлаш",
    back:            "Орқага",

    // Confirm
    order_accepted:      "Буюртма қабул қилинди!",
    order_accepted_sub:  "Тез орада этказиб берамиз",
    order_number:        "Буюртма рақами",
    customer_name:       "Исми",
    address:             "Манзил",
    payment:             "Тўлов",
    cash:                "Нақд (этказилганда)",
    delivery_time:       "Этказиб бериш 30–60 дақиқа ичида",
    continue_shopping:   "Харид давом эттириш",
  },

  tj: {
    // Header / Nav
    cart:            "Сабад",
    back_to_bot:     "Бозгашт ба бот WhatsApp",

    // Shop index
    welcome:         "Хуш омадед!",
    subtitle:        "Маҳсулоти тоза — аз Зарзамин",
    free_delivery:   "Аз 100с расонидан ройгон",
    no_products:     "Ҳоло маҳсулот нест",
    add_cart:        "Ба сабад",

    // Checkout
    step_cart:       "Сабад",
    step_info:       "Маълумот",
    cart_empty:      "Сабад холӣ аст",
    total:           "Ҳамагӣ:",
    min_order_note:  "Ҳадди ақали фармоиш 100с. Расонидан аз 100с ройгон (деҳаи Зарзамин).",
    next:            "Идома додан",
    go_shop:         "Бозгашт ба мағоза",
    cash_note:       "Пардохт: танҳо нақд (ҳангоми расонидан)",
    your_name:       "Номи шумо *",
    name_hint:       "Ному насаб ё танҳо ном ворид кунед",
    your_phone:      "Рақами телефон *",
    phone_hint:      "Масалан: +992 92 790 96 98",
    your_address:    "Суроға *",
    address_hint:    "Масалан: Зарзамин, хиёбони Истиқлол, хонаи 12",
    confirm_order:   "Тасдиқи фармоиш",
    back:            "Бозгашт",

    // Confirm
    order_accepted:      "Фармоиш қабул шуд!",
    order_accepted_sub:  "Зуд мерасонем",
    order_number:        "Рақами фармоиш",
    customer_name:       "Ном",
    address:             "Суроға",
    payment:             "Пардохт",
    cash:                "Нақд (ҳангоми расонидан)",
    delivery_time:       "Расонидан дар давоми 30–60 дақиқа",
    continue_shopping:   "Харидро идома додан",
  }
};

/**
 * Saytdagi barcha data-i18n elementlarini tanlangan tilga ko'ra tarjima qiladi.
 * @param {string} lang - 'uz' yoki 'tj'
 */
function applyLang(lang) {
  const t = TRANSLATIONS[lang] || TRANSLATIONS.uz;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (t[key] !== undefined) el.textContent = t[key];
  });

  // placeholder atributlarini ham o'zgartirish
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (t[key] !== undefined) el.placeholder = t[key];
  });

  // html lang atributini yangilash
  document.documentElement.lang = lang === 'tj' ? 'tg' : 'uz';
}
