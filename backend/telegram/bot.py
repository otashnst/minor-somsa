import os
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID  = int(os.getenv("GROUP_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())


# ── FSM States ────────────────────────────────────────────────────────────────
class NewOrder(StatesGroup):
    order_num     = State()
    branch        = State()
    delivery_time = State()
    confirm       = State()


BRANCHES = ["Minor", "Sergeli", "Yunusabad", "Chilonzor"]

main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="➕ Yangi zakaz"),   KeyboardButton(text="📋 Bugungi zakazlar")],
    [KeyboardButton(text="🚨 Shoshilinch"),   KeyboardButton(text="❓ Yordam")],
], resize_keyboard=True)

branch_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=b)] for b in BRANCHES] + [[KeyboardButton(text="❌ Bekor")]],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor")]], resize_keyboard=True)


# ── Helper ────────────────────────────────────────────────────────────────────
async def get_db_session():
    from backend.database.db import AsyncSessionLocal
    return AsyncSessionLocal()


# ── /start ────────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "👋 <b>Minor Somsa Dispatch Botiga xush kelibsiz!</b>\n\n"
        "Quyidagi buyruqlar mavjud:\n"
        "/new — Yangi zakaz\n"
        "/today — Bugungi zakazlar\n"
        "/urgent — Shoshilinch zakazlar\n"
        "/help — Yordam",
        parse_mode="HTML", reply_markup=main_kb
    )


# ── /help ─────────────────────────────────────────────────────────────────────
@dp.message(Command("help"))
@dp.message(F.text == "❓ Yordam")
async def cmd_help(msg: Message):
    await msg.answer(
        "📖 <b>Yordam</b>\n\n"
        "/new — Yangi zakaz qo'shish\n"
        "/today — Bugungi barcha zakazlar\n"
        "/urgent — 30 daqiqadan kam qolganlar\n"
        "/help — Ushbu xabar\n"
        "/start — Botni qayta ishga tushirish",
        parse_mode="HTML", reply_markup=main_kb
    )


# ── /today ────────────────────────────────────────────────────────────────────
@dp.message(Command("today"))
@dp.message(F.text == "📋 Bugungi zakazlar")
async def cmd_today(msg: Message):
    from sqlalchemy import select, and_
    from backend.models.models import Order, Branch
    from backend.services.order_service import compute_status
    async with await get_db_session() as db:
        result = await db.execute(
            select(Order, Branch)
            .join(Branch, Order.branch_id == Branch.id)
            .where(and_(Order.hidden == False, Order.completed_at == None))
            .order_by(Order.delivery_dt)
        )
        rows = result.all()
    if not rows:
        await msg.answer("📋 Hozircha faol zakazlar yo'q.", reply_markup=main_kb)
        return
    now = datetime.now()
    lines = ["📋 <b>Bugungi zakazlar:</b>\n"]
    icons = {"LATE": "🔴", "URGENT": "🚨", "WARNING": "⚠️", "SAFE": "✅"}
    for order, branch in rows:
        status = compute_status(order.delivery_dt)
        diff = int((order.delivery_dt - now).total_seconds() / 60)
        abs_m = abs(diff)
        h, m = divmod(abs_m, 60)
        t = f"{h}s {m}d" if h else f"{abs_m}d"
        suffix = "o'tdi" if diff < 0 else "qoldi"
        lines.append(f"{icons[status]} <b>#{order.order_num}</b> — {branch.name} | {order.delivery_time} | {t} {suffix}")
    await msg.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_kb)


# ── /urgent ───────────────────────────────────────────────────────────────────
@dp.message(Command("urgent"))
@dp.message(F.text == "🚨 Shoshilinch")
async def cmd_urgent(msg: Message):
    from sqlalchemy import select, and_
    from backend.models.models import Order, Branch
    from backend.services.order_service import compute_status
    async with await get_db_session() as db:
        result = await db.execute(
            select(Order, Branch)
            .join(Branch, Order.branch_id == Branch.id)
            .where(and_(Order.hidden == False, Order.completed_at == None))
            .order_by(Order.delivery_dt)
        )
        rows = result.all()
    urgent = [(o, b) for o, b in rows if compute_status(o.delivery_dt) in ("URGENT", "LATE")]
    if not urgent:
        await msg.answer("✅ Hozircha shoshilinch zakazlar yo'q!", reply_markup=main_kb)
        return
    now = datetime.now()
    text = "🚨 <b>SHOSHILINCH ZAKAZLAR:</b>\n\n"
    for order, branch in urgent:
        diff = int((order.delivery_dt - now).total_seconds() / 60)
        abs_m = abs(diff)
        h, m = divmod(abs_m, 60)
        t = f"{h}s {m}d" if h else f"{abs_m}d"
        suffix = "o'tdi" if diff < 0 else "qoldi"
        text += f"🔴 <b>#{order.order_num}</b> — {branch.name}\n"
        text += f"   ⏱ {order.delivery_time} | <b>{t} {suffix}</b>\n\n"
    await msg.answer(text, parse_mode="HTML", reply_markup=main_kb)


# ── /new — FSM ────────────────────────────────────────────────────────────────
@dp.message(Command("new"))
@dp.message(F.text == "➕ Yangi zakaz")
async def cmd_new(msg: Message, state: FSMContext):
    await state.set_state(NewOrder.order_num)
    await msg.answer("➕ <b>Yangi zakaz</b>\n\n🔢 Zakaz raqamini kiriting (masalan: 4839):",
                     parse_mode="HTML", reply_markup=cancel_kb)


@dp.message(NewOrder.order_num)
async def process_num(msg: Message, state: FSMContext):
    if msg.text == "❌ Bekor":
        await state.clear()
        await msg.answer("❌ Bekor qilindi.", reply_markup=main_kb)
        return
    if not msg.text.isdigit():
        await msg.answer("❌ Faqat raqam kiriting:")
        return
    await state.update_data(order_num=msg.text.strip())
    await state.set_state(NewOrder.branch)
    await msg.answer(f"✅ Raqam: <b>#{msg.text}</b>\n\n🏪 Filialni tanlang:",
                     parse_mode="HTML", reply_markup=branch_kb)


@dp.message(NewOrder.branch)
async def process_branch(msg: Message, state: FSMContext):
    if msg.text == "❌ Bekor":
        await state.clear()
        await msg.answer("❌ Bekor qilindi.", reply_markup=main_kb)
        return
    if msg.text not in BRANCHES:
        await msg.answer("❌ Tugmachadan tanlang:")
        return
    await state.update_data(branch=msg.text)
    await state.set_state(NewOrder.delivery_time)
    await msg.answer(f"✅ Filial: <b>{msg.text}</b>\n\n⏱ Yetkazib berish vaqtini kiriting (HH:MM):",
                     parse_mode="HTML", reply_markup=cancel_kb)


@dp.message(NewOrder.delivery_time)
async def process_time(msg: Message, state: FSMContext):
    if msg.text == "❌ Bekor":
        await state.clear()
        await msg.answer("❌ Bekor qilindi.", reply_markup=main_kb)
        return
    import re
    if not re.match(r"^\d{1,2}:\d{2}$", msg.text.strip()):
        await msg.answer("❌ Format noto'g'ri. HH:MM kiriting (masalan: 16:30):")
        return
    data = await state.get_data()
    await state.update_data(delivery_time=msg.text.strip())
    await state.set_state(NewOrder.confirm)
    confirm_kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="✅ Tasdiqlash"), KeyboardButton(text="❌ Bekor")]
    ], resize_keyboard=True)
    await msg.answer(
        f"📋 <b>Tekshirib ko'ring:</b>\n\n"
        f"🔢 Raqam: <b>#{data['order_num']}</b>\n"
        f"🏪 Filial: <b>{data['branch']}</b>\n"
        f"⏱ Vaqt: <b>{msg.text.strip()}</b>",
        parse_mode="HTML", reply_markup=confirm_kb
    )


@dp.message(NewOrder.confirm)
async def process_confirm(msg: Message, state: FSMContext):
    if msg.text == "❌ Bekor":
        await state.clear()
        await msg.answer("❌ Bekor qilindi.", reply_markup=main_kb)
        return
    if msg.text != "✅ Tasdiqlash":
        await msg.answer("Tasdiqlang yoki bekor qiling:")
        return
    data = await state.get_data()
    await state.clear()

    from sqlalchemy import select
    from backend.models.models import Branch as BranchModel
    from backend.services.order_service import create_order
    from datetime import datetime

    async with await get_db_session() as db:
        result = await db.execute(
            select(BranchModel).where(BranchModel.name == data["branch"])
        )
        branch = result.scalar_one_or_none()
        if not branch:
            await msg.answer("❌ Filial topilmadi.", reply_markup=main_kb)
            return
        h, m = map(int, data["delivery_time"].split(":"))
        delivery_dt = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        if delivery_dt < datetime.now():
            delivery_dt += timedelta(days=1)
        try:
            order = await create_order(db, data["order_num"], branch.id,
                                       data["delivery_time"], delivery_dt)
            await msg.answer(
                f"✅ <b>Zakaz #{data['order_num']} qo'shildi!</b>\n\n"
                f"🏪 {data['branch']} | ⏱ {data['delivery_time']}",
                parse_mode="HTML", reply_markup=main_kb
            )
        except ValueError as e:
            await msg.answer(f"❌ {e}", reply_markup=main_kb)


async def run_bot():
    await dp.start_polling(bot)
