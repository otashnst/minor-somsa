from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database.db import get_db
from backend.services.order_service import (
    get_active_orders, create_order, mark_ready, delete_order, add_log
)
from backend.models.models import Order, Branch

router = APIRouter(prefix="/api/orders", tags=["orders"])

WORK_START = 6
WORK_END   = 24


class OrderCreate(BaseModel):
    order_num:     str
    branch_id:     int
    delivery_time: str   # HH:MM
    date_offset:   int = 0
    note:          str = ""


@router.get("/")
async def list_orders(db: AsyncSession = Depends(get_db)):
    return await get_active_orders(db)


@router.post("/")
async def add_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    h, m = map(int, data.delivery_time.split(":"))
    if h < WORK_START or (data.date_offset == 0 and h == 0 and m == 0):
        raise HTTPException(400, "Ish vaqti: 06:00 — 00:00")
    base = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
    delivery_dt = base + timedelta(days=data.date_offset)
    try:
        order = await create_order(
            db, data.order_num, data.branch_id,
            data.delivery_time, delivery_dt, data.note
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "id": order.id}


@router.post("/{order_id}/ready")
async def ready_order(order_id: int, db: AsyncSession = Depends(get_db)):
    ok = await mark_ready(db, order_id)
    if not ok:
        raise HTTPException(404, "Buyurtma topilmadi")
    return {"ok": True}


@router.delete("/{order_id}")
async def remove_order(order_id: int, db: AsyncSession = Depends(get_db)):
    ok = await delete_order(db, order_id)
    if not ok:
        raise HTTPException(404, "Buyurtma topilmadi")
    return {"ok": True}


@router.get("/archive")
async def get_archive(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order, Branch)
        .join(Branch, Order.branch_id == Branch.id)
        .where(Order.completed_at != None)
        .order_by(Order.completed_at.desc())
        .limit(200)
    )
    rows = result.all()
    return [
        {
            "id": o.id,
            "order_num": o.order_num,
            "branch_name": b.name,
            "delivery_time": o.delivery_time,
            "completed_at": o.completed_at.strftime("%H:%M") if o.completed_at else "",
            "note": o.note or "",
        }
        for o, b in rows
    ]
