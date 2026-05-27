from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.database.db import AsyncSessionLocal
from backend.services.order_service import add_log, get_all_active_orders_raw, compute_status
from sqlalchemy import select
from backend.models.models import Order, Branch, Settings

scheduler = AsyncIOScheduler()


async def _get_settings():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Settings))
        s = result.scalar_one_or_none()
        return s


async def check_reminders():
    async with AsyncSessionLocal() as db:
        settings = await db.execute(select(Settings))
        s = settings.scalar_one_or_none()
        tg_on = s.telegram_on if s else True
        repeat_interval = s.repeat_interval if s else 10

        rows = await get_all_active_orders_raw(db)
        now = datetime.now()

        for order, branch in rows:
            diff_min = (order.delivery_dt - now).total_seconds() / 60

            # 1 hour reminder
            if 55 <= diff_min <= 65 and not order.reminded_60:
                order.reminded_60 = True
                await db.commit()
                await add_log(db, f"#{order.order_num} — 1 soatlik eslatma yuborildi", "reminder")
                if tg_on:
                    await send_tg_reminder(order, branch, diff_min, "warning")

            # 30 min / urgent reminder
            if 25 <= diff_min <= 35 and not order.reminded_30:
                order.reminded_30 = True
                await db.commit()
                await add_log(db, f"#{order.order_num} — Shoshilinch eslatma yuborildi", "urgent")
                if tg_on:
                    await send_tg_reminder(order, branch, diff_min, "urgent")

            # Repeat reminders every N minutes when overdue or urgent
            if diff_min <= 30:
                # Use created_at to calculate repeat slots
                elapsed = (now - order.created_at).total_seconds() / 60
                slot = int(elapsed / repeat_interval)
                repeat_key = f"repeat_{order.id}_{slot}"
                if not hasattr(check_reminders, "_sent"):
                    check_reminders._sent = set()
                if repeat_key not in check_reminders._sent:
                    check_reminders._sent.add(repeat_key)
                    if diff_min <= 0:
                        await add_log(db, f"#{order.order_num} — Qayta eslatma (kechikdi)", "repeat")
                    else:
                        await add_log(db, f"#{order.order_num} — Qayta eslatma yuborildi", "repeat")
                    if tg_on:
                        await send_tg_reminder(order, branch, diff_min, "repeat")


async def send_tg_reminder(order, branch, diff_min: float, kind: str):
    try:
        import os
        from aiogram import Bot
        from dotenv import load_dotenv
        load_dotenv()
        token    = os.getenv("BOT_TOKEN")
        group_id = os.getenv("GROUP_ID")
        if not token or not group_id:
            return
        bot = Bot(token=token)
        abs_min = int(abs(diff_min))
        h, m = divmod(abs_min, 60)
        if h > 0:
            remaining = f"{h} soat {m} daqiqa"
        else:
            remaining = f"{abs_min} daqiqa"

        late = diff_min < 0

        suffix = "o'tdi" if late else "qoldi"
        if kind == "warning":
            text = (
                f"⚠️ <b>OGOHLANTIRISH</b>\n\n"
                f"Zakaz: <b>#{order.order_num}</b>\n"
                f"Filial: {branch.name}\n"
                f"Yetkazish: {order.delivery_time}\n\n"
                f"⏱ <b>{remaining} qoldi</b>"
            )
        elif kind == "urgent":
            text = (
                f"🚨 <b>SHOSHILINCH</b>\n\n"
                f"Zakaz: <b>#{order.order_num}</b>\n"
                f"Filial: {branch.name}\n"
                f"Yetkazish: {order.delivery_time}\n\n"
                f"⏱ <b>{remaining} {suffix}</b>"
            )
        else:
            text = (
                f"🔁 <b>QAYTA ESLATMA</b>\n\n"
                f"Zakaz: <b>#{order.order_num}</b>\n"
                f"Filial: {branch.name}\n\n"
                f"⏱ <b>{remaining} {suffix}</b>"
            )

        if order.note:
            text += f"\n📝 {order.note}"

        await bot.send_message(chat_id=int(group_id), text=text, parse_mode="HTML")
        await bot.session.close()
    except Exception as e:
        print(f"[TG ERROR] {e}")


def start_scheduler():
    scheduler.add_job(check_reminders, "interval", seconds=60, id="reminders")
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown()
