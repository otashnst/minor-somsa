from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.models.models import Order, Branch, Log


def compute_status(delivery_dt: datetime) -> str:
    now = datetime.now()
    diff = (delivery_dt - now).total_seconds() / 60
    if diff < 0 and abs(diff) > 240:
        return "LATE"
    if diff <= 30:
        return "URGENT"
    if diff <= 60:
        return "WARNING"
    return "SAFE"


async def get_active_orders(db: AsyncSession):
    result = await db.execute(
        select(Order, Branch)
        .join(Branch, Order.branch_id == Branch.id)
        .where(and_(Order.hidden == False, Order.completed_at == None))
        .order_by(Order.delivery_dt)
    )
    rows = result.all()
    orders = []
    for order, branch in rows:
        order.status = compute_status(order.delivery_dt)
        orders.append(serialize_order(order, branch))
    orders.sort(key=lambda o: ["LATE","URGENT","WARNING","SAFE"].index(o["status"]))
    return orders


async def get_all_active_orders_raw(db: AsyncSession):
    result = await db.execute(
        select(Order, Branch)
        .join(Branch, Order.branch_id == Branch.id)
        .where(and_(Order.hidden == False, Order.completed_at == None))
    )
    return result.all()


def serialize_order(order: Order, branch: Branch) -> dict:
    now = datetime.now()
    diff_min = int((order.delivery_dt - now).total_seconds() / 60)
    abs_min = abs(diff_min)
    h, m = divmod(abs_min, 60)
    if h > 0:
        countdown = f"{h} soat {m} min"
    else:
        countdown = f"{m} min"
    late = diff_min < 0
    return {
        "id": order.id,
        "order_num": order.order_num,
        "branch_id": order.branch_id,
        "branch_name": branch.name,
        "branch_color": branch.color,
        "delivery_time": order.delivery_time,
        "delivery_dt": order.delivery_dt.isoformat(),
        "note": order.note or "",
        "status": compute_status(order.delivery_dt),
        "countdown": countdown,
        "late": late,
        "created_at": order.created_at.isoformat(),
    }


async def create_order(db: AsyncSession, order_num: str, branch_id: int,
                       delivery_time: str, delivery_dt: datetime, note: str = "") -> Order:
    # check duplicate
    existing = await db.execute(
        select(Order).where(
            and_(Order.order_num == order_num,
                 Order.branch_id == branch_id,
                 Order.hidden == False,
                 Order.completed_at == None)
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Bu filialda bu raqamli buyurtma allaqachon mavjud!")
    order = Order(
        order_num=order_num,
        branch_id=branch_id,
        delivery_time=delivery_time,
        delivery_dt=delivery_dt,
        note=note,
        status=compute_status(delivery_dt),
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    await add_log(db, f"#{order_num} — Buyurtma yaratildi", "create")
    return order


async def mark_ready(db: AsyncSession, order_id: int) -> bool:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        return False
    order.completed_at = datetime.now()
    await db.commit()
    await add_log(db, f"#{order.order_num} — Bajarildi", "complete")
    return True


async def delete_order(db: AsyncSession, order_id: int) -> bool:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        return False
    order.hidden = True
    await db.commit()
    await add_log(db, f"#{order.order_num} — O'chirildi", "delete")
    return True


async def add_log(db: AsyncSession, text: str, log_type: str):
    from backend.models.models import Log
    db.add(Log(text=text, log_type=log_type))
    await db.commit()
