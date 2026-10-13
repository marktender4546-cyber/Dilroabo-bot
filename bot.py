import asyncio
import html
import json
import logging
import os
import sqlite3
from pathlib import Path

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InputMediaPhoto,
    KeyboardButton,
    Message,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

logging.basicConfig(level=logging.INFO)

# ───────────────────────── SOZLAMALAR (Render > Environment) ─────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()]
SHOP_NAME = os.getenv("SHOP_NAME", "LaptopShop")
SHOP_PHONE = os.getenv("SHOP_PHONE", "+998 90 123 45 67")
SHOP_USERNAME = os.getenv("SHOP_USERNAME", "@your_manager")
SHOP_ADDRESS = os.getenv("SHOP_ADDRESS", "Toshkent sh., Chilonzor tumani")
SHOP_HOURS = os.getenv("SHOP_HOURS", "09:00 – 20:00")
DB_PATH = os.getenv("DB_PATH", "bot.db")
PAGE_SIZE = 5

# ───────────────────────── MA'LUMOTLAR ─────────────────────────
PRODUCTS = json.loads((Path(__file__).parent / "products.json").read_text(encoding="utf-8"))
PRODUCT_BY_ID = {p["id"]: p for p in PRODUCTS}
BRANDS = sorted({p["brand"] for p in PRODUCTS})
CATS = ["gaming", "office", "ultra", "student"]
PRICE_RANGES = {
    "1": (0, 6_000_000),
    "2": (6_000_000, 10_000_000),
    "3": (10_000_000, 15_000_000),
    "4": (15_000_000, 10**12),
}

# ───────────────────────── TARJIMALAR ─────────────────────────
T = {
    "uz": {
        "choose_lang": "🌐 Tilni tanlang / Выберите язык",
        "welcome": "👋 Assalomu alaykum, <b>{name}</b>!\n\n💻 <b>{shop}</b> noutbuklar do'koniga xush kelibsiz.\nKerakli bo'limni tanlang 👇",
        "btn_catalog": "💻 Katalog",
        "btn_search": "🔍 Qidirish",
        "btn_fav": "❤️ Sevimlilar",
        "btn_about": "ℹ️ Biz haqimizda",
        "btn_contact": "📞 Aloqa",
        "btn_help": "🚚 Yetkazish va kafolat",
        "btn_lang": "🌐 Til",
        "catalog_text": "💻 <b>Katalog</b>\n\nKategoriya, brend yoki narx bo'yicha tanlang:",
        "cat_gaming": "🎮 O'yin",
        "cat_office": "💼 Ish uchun",
        "cat_ultra": "🪶 Ultrabook",
        "cat_student": "🎓 O'qish uchun",
        "price_1": "💰 6 mln gacha",
        "price_2": "💰 6–10 mln",
        "price_3": "💰 10–15 mln",
        "price_4": "💰 15 mln dan yuqori",
        "all": "📋 Barcha noutbuklar",
        "all_title": "📋 <b>Barcha noutbuklar</b>",
        "fav_title": "❤️ <b>Sevimlilar</b>",
        "search_title": "🔍 <b>Qidiruv natijalari</b>",
        "found": "Topildi: <b>{n}</b> ta",
        "empty": "😔 Hech narsa topilmadi.",
        "back": "⬅️ Orqaga",
        "to_catalog": "🏠 Katalog",
        "currency": "so'm",
        "cpu": "Protsessor",
        "ram": "Operativ xotira",
        "storage": "Xotira (SSD)",
        "gpu": "Videokarta",
        "display": "Ekran",
        "battery": "Batareya",
        "weight": "Og'irligi",
        "os": "Tizim",
        "warranty": "Kafolat",
        "months": "oy",
        "in_stock": "✅ Sotuvda bor",
        "out_stock": "❌ Sotuvda yo'q",
        "order_btn": "🛒 Buyurtma berish",
        "photos_btn": "🖼 Ko'proq rasm",
        "fav_add": "🤍 Sevimlilarga",
        "fav_del": "❤️ Sevimlilardan olib tashlash",
        "fav_added": "❤️ Sevimlilarga qo'shildi",
        "fav_removed": "💔 Sevimlilardan olib tashlandi",
        "order_phone": "📱 Buyurtma uchun telefon raqamingizni yuboring (pastdagi tugma orqali yoki +998... ko'rinishida yozing):",
        "send_phone": "📱 Raqamni yuborish",
        "cancel": "❌ Bekor qilish",
        "cancelled": "Bekor qilindi.",
        "order_ok": "✅ Rahmat! So'rovingiz qabul qilindi.\nMenejerimiz tez orada siz bilan bog'lanadi.",
        "bad_phone": "⚠️ Telefon raqami noto'g'ri. Qaytadan yuboring.",
        "search_prompt": "🔍 Qidiruv so'zini yozing (masalan: <i>Lenovo</i>, <i>i7</i>, <i>RTX 4060</i>):",
        "about": "ℹ️ <b>{shop}</b>\n\nBiz original noutbuklarni kafolat bilan sotamiz.\n\n✔️ Keng tanlov\n✔️ Hamyonbop narxlar\n✔️ Tez yetkazib berish\n✔️ Kafolat va servis xizmati",
        "contact": "📞 <b>Aloqa</b>\n\n☎️ Telefon: {phone}\n💬 Telegram: {username}\n📍 Manzil: {address}\n🕘 Ish vaqti: {hours}",
        "help": "🚚 <b>Yetkazib berish va kafolat</b>\n\n🚚 Toshkent bo'ylab — 1 kun ichida, viloyatlarga — 2–3 kun.\n🛡 Barcha noutbuklarga rasmiy kafolat beriladi.\n🔄 Muammo bo'lsa, 14 kun ichida almashtirish mumkin.\n💳 To'lov — mahsulotni qabul qilganda.\n\nSavollar bo'lsa, menejerimizga yozing: {username}",
        "lang_changed": "✅ Til o'zgartirildi.",
        "order_admin": "🛒 <b>Yangi buyurtma so'rovi</b>",
    },
    "ru": {
        "choose_lang": "🌐 Tilni tanlang / Выберите язык",
        "welcome": "👋 Здравствуйте, <b>{name}</b>!\n\n💻 Добро пожаловать в магазин ноутбуков <b>{shop}</b>.\nВыберите нужный раздел 👇",
        "btn_catalog": "💻 Каталог",
        "btn_search": "🔍 Поиск",
        "btn_fav": "❤️ Избранное",
        "btn_about": "ℹ️ О нас",
        "btn_contact": "📞 Контакты",
        "btn_help": "🚚 Доставка и гарантия",
        "btn_lang": "🌐 Язык",
        "catalog_text": "💻 <b>Каталог</b>\n\nВыберите по категории, бренду или цене:",
        "cat_gaming": "🎮 Игровые",
        "cat_office": "💼 Для работы",
        "cat_ultra": "🪶 Ультрабуки",
        "cat_student": "🎓 Для учёбы",
        "price_1": "💰 до 6 млн",
        "price_2": "💰 6–10 млн",
        "price_3": "💰 10–15 млн",
        "price_4": "💰 от 15 млн",
        "all": "📋 Все ноутбуки",
        "all_title": "📋 <b>Все ноутбуки</b>",
        "fav_title": "❤️ <b>Избранное</b>",
        "search_title": "🔍 <b>Результаты поиска</b>",
        "found": "Найдено: <b>{n}</b>",
        "empty": "😔 Ничего не найдено.",
        "back": "⬅️ Назад",
        "to_catalog": "🏠 Каталог",
        "currency": "сум",
        "cpu": "Процессор",
        "ram": "Оперативная память",
        "storage": "Накопитель (SSD)",
        "gpu": "Видеокарта",
        "display": "Экран",
        "battery": "Батарея",
        "weight": "Вес",
        "os": "Система",
        "warranty": "Гарантия",
        "months": "мес.",
        "in_stock": "✅ В наличии",
        "out_stock": "❌ Нет в наличии",
        "order_btn": "🛒 Заказать",
        "photos_btn": "🖼 Больше фото",
        "fav_add": "🤍 В избранное",
        "fav_del": "❤️ Убрать из избранного",
        "fav_added": "❤️ Добавлено в избранное",
        "fav_removed": "💔 Убрано из избранного",
        "order_phone": "📱 Отправьте номер телефона для заказа (кнопкой ниже или в формате +998...):",
        "send_phone": "📱 Отправить номер",
        "cancel": "❌ Отмена",
        "cancelled": "Отменено.",
        "order_ok": "✅ Спасибо! Ваша заявка принята.\nНаш менеджер скоро свяжется с вами.",
        "bad_phone": "⚠️ Неверный номер телефона. Отправьте ещё раз.",
        "search_prompt": "🔍 Введите запрос (например: <i>Lenovo</i>, <i>i7</i>, <i>RTX 4060</i>):",
        "about": "ℹ️ <b>{shop}</b>\n\nМы продаём оригинальные ноутбуки с гарантией.\n\n✔️ Большой выбор\n✔️ Доступные цены\n✔️ Быстрая доставка\n✔️ Гарантия и сервис",
        "contact": "📞 <b>Контакты</b>\n\n☎️ Телефон: {phone}\n💬 Telegram: {username}\n📍 Адрес: {address}\n🕘 Время работы: {hours}",
        "help": "🚚 <b>Доставка и гарантия</b>\n\n🚚 По Ташкенту — в течение 1 дня, в регионы — 2–3 дня.\n🛡 На все ноутбуки действует официальная гарантия.\n🔄 При проблемах — обмен в течение 14 дней.\n💳 Оплата — при получении товара.\n\nЕсли есть вопросы, напишите менеджеру: {username}",
        "lang_changed": "✅ Язык изменён.",
        "order_admin": "🛒 <b>Новая заявка на заказ</b>",
    },
}

# ───────────────────────── BAZA (SQLite) ─────────────────────────
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT, name TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS favs (user_id INTEGER, product_id INTEGER, PRIMARY KEY (user_id, product_id))")
db.commit()


def db_add_user(uid: int, name: str):
    db.execute("INSERT OR IGNORE INTO users (id, lang, name) VALUES (?, NULL, ?)", (uid, name))
    db.commit()


def db_get_lang(uid: int):
    row = db.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
    return row[0] if row and row[0] else None


def db_set_lang(uid: int, lang: str, name: str = ""):
    db_add_user(uid, name)
    db.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))
    db.commit()


def db_favs(uid: int):
    return [r[0] for r in db.execute("SELECT product_id FROM favs WHERE user_id=?", (uid,))]


def db_toggle_fav(uid: int, pid: int) -> bool:
    """True qaytarsa — qo'shildi, False — olib tashlandi."""
    if db.execute("SELECT 1 FROM favs WHERE user_id=? AND product_id=?", (uid, pid)).fetchone():
        db.execute("DELETE FROM favs WHERE user_id=? AND product_id=?", (uid, pid))
        db.commit()
        return False
    db.execute("INSERT INTO favs VALUES (?, ?)", (uid, pid))
    db.commit()
    return True


# ───────────────────────── YORDAMCHI FUNKSIYALAR ─────────────────────────
LAST_LIST: dict[int, tuple] = {}
LAST_QUERY: dict[int, str] = {}


def lang_of(uid: int) -> str:
    return db_get_lang(uid) or "uz"


def t(uid: int, key: str, **kw) -> str:
    base = dict(
        shop=SHOP_NAME, phone=SHOP_PHONE, username=SHOP_USERNAME,
        address=SHOP_ADDRESS, hours=SHOP_HOURS,
    )
    base.update(kw)
    return T[lang_of(uid)][key].format(**base)


def fmt_price(uid: int, value: int) -> str:
    return f"{value:,}".replace(",", " ") + " " + T[lang_of(uid)]["currency"]


def btn_texts(key: str) -> set[str]:
    return {T["uz"][key], T["ru"][key]}


def Btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def main_menu(uid: int):
    b = ReplyKeyboardBuilder()
    for key in ("btn_catalog", "btn_search", "btn_fav", "btn_about", "btn_contact", "btn_help", "btn_lang"):
        b.add(KeyboardButton(text=T[lang_of(uid)][key]))
    b.adjust(2, 2, 2, 1)
    return b.as_markup(resize_keyboard=True)


def lang_kb():
    b = InlineKeyboardBuilder()
    b.row(Btn("🇺🇿 O'zbekcha", "lang:uz"), Btn("🇷🇺 Русский", "lang:ru"))
    return b.as_markup()


def catalog_kb(uid: int):
    L = T[lang_of(uid)]
    b = InlineKeyboardBuilder()
    for c in CATS:
        b.add(Btn(L[f"cat_{c}"], f"lst:cat:{c}:0"))
    b.adjust(2)
    brand_btns = [Btn(f"🏷 {br}", f"lst:brand:{br}:0") for br in BRANDS]
    for i in range(0, len(brand_btns), 3):
        b.row(*brand_btns[i:i + 3])
    price_btns = [Btn(L[f"price_{k}"], f"lst:price:{k}:0") for k in PRICE_RANGES]
    for i in range(0, len(price_btns), 2):
        b.row(*price_btns[i:i + 2])
    b.row(Btn(L["all"], "lst:all:-:0"))
    return b.as_markup()


def get_items(uid: int, typ: str, val: str):
    if typ == "all":
        return PRODUCTS
    if typ == "cat":
        return [p for p in PRODUCTS if p["category"] == val]
    if typ == "brand":
        return [p for p in PRODUCTS if p["brand"] == val]
    if typ == "price":
        lo, hi = PRICE_RANGES[val]
        return [p for p in PRODUCTS if lo <= p["price"] < hi]
    if typ == "fav":
        ids = set(db_favs(uid))
        return [p for p in PRODUCTS if p["id"] in ids]
    if typ == "q":
        q = LAST_QUERY.get(uid, "").lower().strip()
        words = q.split()
        res = []
        for p in PRODUCTS:
            hay = " ".join(str(p.get(k, "")) for k in ("brand", "name", "cpu", "ram", "storage", "gpu", "display", "category")).lower()
            if all(w in hay for w in words):
                res.append(p)
        return res
    return []


def list_title(uid: int, typ: str, val: str) -> str:
    L = T[lang_of(uid)]
    if typ == "cat":
        return f"<b>{L['cat_' + val]}</b>"
    if typ == "brand":
        return f"🏷 <b>{html.escape(val)}</b>"
    if typ == "price":
        return f"<b>{L['price_' + val]}</b>"
    if typ == "fav":
        return L["fav_title"]
    if typ == "q":
        return L["search_title"]
    return L["all_title"]


def list_kb(uid: int, typ: str, val: str, page: int):
    L = T[lang_of(uid)]
    items = get_items(uid, typ, val)
    pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    b = InlineKeyboardBuilder()
    for p in items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        b.row(Btn(f"{p['name']} · {fmt_price(uid, p['price'])}", f"p:{p['id']}"))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(Btn("◀️", f"lst:{typ}:{val}:{page - 1}"))
        nav.append(Btn(f"{page + 1}/{pages}", "noop"))
        if page < pages - 1:
            nav.append(Btn("▶️", f"lst:{typ}:{val}:{page + 1}"))
        b.row(*nav)
    b.row(Btn(L["to_catalog"], "menu:catalog"))
    return b.as_markup(), page, len(items)


def product_card(uid: int, p: dict) -> str:
    L = T[lang_of(uid)]
    lg = lang_of(uid)
    stock = L["in_stock"] if p.get("stock", True) else L["out_stock"]
    return (
        f"💻 <b>{html.escape(p['name'])}</b>\n"
        f"💰 <b>{fmt_price(uid, p['price'])}</b>   {stock}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🧠 {L['cpu']}: <b>{html.escape(p['cpu'])}</b>\n"
        f"⚡ {L['ram']}: <b>{html.escape(p['ram'])}</b>\n"
        f"💾 {L['storage']}: <b>{html.escape(p['storage'])}</b>\n"
        f"🎮 {L['gpu']}: <b>{html.escape(p['gpu'])}</b>\n"
        f"🖥 {L['display']}: <b>{html.escape(p['display'])}</b>\n"
        f"🔋 {L['battery']}: <b>{html.escape(p['battery'])}</b>\n"
        f"⚖️ {L['weight']}: <b>{html.escape(p['weight'])}</b>\n"
        f"🪟 {L['os']}: <b>{html.escape(p['os'])}</b>\n"
        f"🛡 {L['warranty']}: <b>{p['warranty_months']} {L['months']}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"📝 {html.escape(p['desc'][lg])}"
    )


def product_kb(uid: int, p: dict):
    L = T[lang_of(uid)]
    is_fav = p["id"] in db_favs(uid)
    b = InlineKeyboardBuilder()
    if p.get("stock", True):
        b.row(Btn(L["order_btn"], f"ord:{p['id']}"))
    row = [Btn(L["fav_del"] if is_fav else L["fav_add"], f"fav:{p['id']}")]
    b.row(*row)
    if len(p.get("images", [])) > 1:
        b.row(Btn(L["photos_btn"], f"ph:{p['id']}"))
    b.row(Btn(L["back"], "back"))
    return b.as_markup()


async def show(target, text: str, kb=None, photo: str | None = None):
    """Ekranni almashtiradi: matn bo'lsa tahrirlaydi, rasm bo'lsa o'chirib qayta yuboradi."""
    msg = target.message if isinstance(target, CallbackQuery) else target
    bot = msg.bot
    chat_id = msg.chat.id
    if isinstance(target, CallbackQuery):
        if not photo and not msg.photo:
            try:
                await msg.edit_text(text, reply_markup=kb)
                return
            except Exception:
                pass
        try:
            await msg.delete()
        except Exception:
            pass
    if photo:
        try:
            await bot.send_photo(chat_id, photo, caption=text, reply_markup=kb)
            return
        except Exception as e:
            logging.warning("Rasm yuborilmadi (%s): %s", photo, e)
    await bot.send_message(chat_id, text, reply_markup=kb)


async def show_list(target, typ: str, val: str, page: int):
    uid = target.from_user.id
    kb, page, n = list_kb(uid, typ, val, page)
    LAST_LIST[uid] = (typ, val, page)
    L = T[lang_of(uid)]
    text = list_title(uid, typ, val) + "\n\n" + (L["found"].format(n=n) if n else L["empty"])
    await show(target, text, kb)


# ───────────────────────── HOLATLAR ─────────────────────────
class Search(StatesGroup):
    query = State()


class Order(StatesGroup):
    phone = State()


r = Router()


# ───────────────────────── START / TIL ─────────────────────────
@r.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    uid = m.from_user.id
    db_add_user(uid, m.from_user.full_name)
    if db_get_lang(uid):
        await m.answer(t(uid, "welcome", name=html.escape(m.from_user.first_name)), reply_markup=main_menu(uid))
    else:
        await m.answer(T["uz"]["choose_lang"], reply_markup=lang_kb())


@r.callback_query(F.data.startswith("lang:"))
async def cb_lang(c: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = c.from_user.id
    db_set_lang(uid, c.data.split(":")[1], c.from_user.full_name)
    try:
        await c.message.delete()
    except Exception:
        pass
    await c.message.answer(t(uid, "welcome", name=html.escape(c.from_user.first_name)), reply_markup=main_menu(uid))
    await c.answer(t(uid, "lang_changed"))


@r.message(F.text.in_(btn_texts("btn_lang")))
async def menu_lang(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(T["uz"]["choose_lang"], reply_markup=lang_kb())


# ───────────────────────── ASOSIY MENYU ─────────────────────────
@r.message(F.text.in_(btn_texts("btn_catalog")))
async def menu_catalog(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(t(m.from_user.id, "catalog_text"), reply_markup=catalog_kb(m.from_user.id))


@r.callback_query(F.data == "menu:catalog")
async def cb_catalog(c: CallbackQuery):
    await show(c, t(c.from_user.id, "catalog_text"), catalog_kb(c.from_user.id))
    await c.answer()


@r.message(F.text.in_(btn_texts("btn_fav")))
async def menu_fav(m: Message, state: FSMContext):
    await state.clear()
    await show_list(m, "fav", "-", 0)


@r.message(F.text.in_(btn_texts("btn_about")))
async def menu_about(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(t(m.from_user.id, "about"))


@r.message(F.text.in_(btn_texts("btn_contact")))
async def menu_contact(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(t(m.from_user.id, "contact"))


@r.message(F.text.in_(btn_texts("btn_help")))
async def menu_help(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(t(m.from_user.id, "help"))


@r.message(F.text.in_(btn_texts("btn_search")))
async def menu_search(m: Message, state: FSMContext):
    await state.set_state(Search.query)
    await m.answer(t(m.from_user.id, "search_prompt"))


@r.message(Search.query, F.text)
async def do_search(m: Message, state: FSMContext):
    await state.clear()
    LAST_QUERY[m.from_user.id] = m.text
    await show_list(m, "q", "-", 0)


# ───────────────────────── RO'YXAT / MAHSULOT ─────────────────────────
@r.callback_query(F.data.startswith("lst:"))
async def cb_list(c: CallbackQuery):
    _, typ, val, page = c.data.split(":", 3)
    await show_list(c, typ, val, int(page))
    await c.answer()


@r.callback_query(F.data == "back")
async def cb_back(c: CallbackQuery):
    typ, val, page = LAST_LIST.get(c.from_user.id, ("all", "-", 0))
    await show_list(c, typ, val, page)
    await c.answer()


@r.callback_query(F.data.startswith("p:"))
async def cb_product(c: CallbackQuery):
    uid = c.from_user.id
    p = PRODUCT_BY_ID.get(int(c.data.split(":")[1]))
    if not p:
        return await c.answer()
    photo = p["images"][0] if p.get("images") else None
    await show(c, product_card(uid, p), product_kb(uid, p), photo)
    await c.answer()


@r.callback_query(F.data.startswith("ph:"))
async def cb_photos(c: CallbackQuery):
    p = PRODUCT_BY_ID.get(int(c.data.split(":")[1]))
    if p and len(p.get("images", [])) > 1:
        media = [InputMediaPhoto(media=u) for u in p["images"][:10]]
        try:
            await c.message.answer_media_group(media)
        except Exception as e:
            logging.warning("Albom yuborilmadi: %s", e)
    await c.answer()


@r.callback_query(F.data.startswith("fav:"))
async def cb_fav(c: CallbackQuery):
    uid = c.from_user.id
    p = PRODUCT_BY_ID.get(int(c.data.split(":")[1]))
    if not p:
        return await c.answer()
    added = db_toggle_fav(uid, p["id"])
    try:
        await c.message.edit_reply_markup(reply_markup=product_kb(uid, p))
    except Exception:
        pass
    await c.answer(t(uid, "fav_added" if added else "fav_removed"))


@r.callback_query(F.data == "noop")
async def cb_noop(c: CallbackQuery):
    await c.answer()


# ───────────────────────── BUYURTMA SO'ROVI ─────────────────────────
@r.callback_query(F.data.startswith("ord:"))
async def cb_order(c: CallbackQuery, state: FSMContext):
    uid = c.from_user.id
    pid = int(c.data.split(":")[1])
    await state.set_state(Order.phone)
    await state.update_data(pid=pid)
    L = T[lang_of(uid)]
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=L["send_phone"], request_contact=True))
    b.row(KeyboardButton(text=L["cancel"]))
    await c.message.answer(L["order_phone"], reply_markup=b.as_markup(resize_keyboard=True))
    await c.answer()


@r.message(Order.phone)
async def order_phone(m: Message, state: FSMContext):
    uid = m.from_user.id
    L = T[lang_of(uid)]
    if m.text and m.text == L["cancel"]:
        await state.clear()
        return await m.answer(L["cancelled"], reply_markup=main_menu(uid))

    phone = m.contact.phone_number if m.contact else (m.text or "")
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 9:
        return await m.answer(L["bad_phone"])

    data = await state.get_data()
    p = PRODUCT_BY_ID.get(data.get("pid"))
    await state.clear()

    if p:
        user = m.from_user
        uname = f"@{user.username}" if user.username else "—"
        text = (
            f"{T['uz']['order_admin']}\n\n"
            f"💻 {html.escape(p['name'])} (ID {p['id']})\n"
            f"💰 {p['price']:,} so'm\n\n"
            f"👤 {html.escape(user.full_name)}\n"
            f"🔗 {uname}\n"
            f"📱 {html.escape(phone)}\n"
            f"🆔 <code>{user.id}</code>"
        ).replace(",", " ")
        for admin in ADMIN_IDS:
            try:
                await m.bot.send_message(admin, text)
            except Exception as e:
                logging.warning("Adminga yuborilmadi %s: %s", admin, e)
    await m.answer(L["order_ok"], reply_markup=main_menu(uid))


# ───────────────────────── ADMIN ─────────────────────────
@r.message(Command("stats"))
async def cmd_stats(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    favs = db.execute("SELECT COUNT(*) FROM favs").fetchone()[0]
    await m.answer(f"📊 Foydalanuvchilar: <b>{users}</b>\n❤️ Sevimlilar: <b>{favs}</b>\n💻 Mahsulotlar: <b>{len(PRODUCTS)}</b>")


@r.message(Command("broadcast"))
async def cmd_broadcast(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    text = (m.text or "").partition(" ")[2].strip()
    if not text:
        return await m.answer("Foydalanish: /broadcast Xabar matni")
    ok = fail = 0
    for (uid,) in db.execute("SELECT id FROM users").fetchall():
        try:
            await m.bot.send_message(uid, text)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await m.answer(f"✅ Yuborildi: {ok}\n⚠️ Xato: {fail}")


# ───────────────────────── ISHGA TUSHIRISH ─────────────────────────
async def keepalive():
    """Render bepul tarifida uxlab qolmasligi uchun o'zini har 10 daqiqada chaqiradi."""
    url = os.getenv("RENDER_EXTERNAL_URL")
    if not url:
        return
    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(600)
            try:
                await session.get(url)
            except Exception:
                pass


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi! Environment Variables ga qo'shing.")

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(r)

    # Render uchun kichik web-server (port ochiq bo'lishi shart)
    app = web.Application()
    app.router.add_get("/", lambda _: web.Response(text="Bot ishlayapti ✅"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "10000"))).start()
    asyncio.create_task(keepalive())

    await bot.set_my_commands([BotCommand(command="start", description="Botni ishga tushirish / Запуск")])
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot ishga tushdi")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
