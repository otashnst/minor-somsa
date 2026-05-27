from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database.db import get_db
from backend.models.models import Branch, Settings, Log

# ── Branches ──────────────────────────────────────────────────────────────────
branches_router = APIRouter(prefix="/api/branches", tags=["branches"])

class BranchCreate(BaseModel):
    name:  str
    color: str = "#ef4444"

class BranchUpdate(BaseModel):
    active: bool

@branches_router.get("/")
async def list_branches(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Branch))
    return [{"id": b.id, "name": b.name, "color": b.color, "active": b.active}
            for b in result.scalars().all()]

@branches_router.post("/")
async def add_branch(data: BranchCreate, db: AsyncSession = Depends(get_db)):
    branch = Branch(name=data.name, color=data.color)
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return {"ok": True, "id": branch.id}

@branches_router.patch("/{branch_id}")
async def update_branch(branch_id: int, data: BranchUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if not branch:
        raise HTTPException(404, "Topilmadi")
    branch.active = data.active
    await db.commit()
    return {"ok": True}


# ── Settings ──────────────────────────────────────────────────────────────────
settings_router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    sound:            bool = True
    popups:           bool = True
    telegram_on:      bool = True
    repeat_interval:  int  = 10
    refresh_interval: int  = 5
    work_start:       str  = "06:00"
    work_end:         str  = "00:00"

@settings_router.get("/")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings))
    s = result.scalar_one_or_none()
    if not s:
        return SettingsUpdate().model_dump()
    return {"sound": s.sound, "popups": s.popups, "telegram_on": s.telegram_on,
            "repeat_interval": s.repeat_interval, "refresh_interval": s.refresh_interval,
            "work_start": s.work_start, "work_end": s.work_end}

@settings_router.put("/")
async def save_settings(data: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings))
    s = result.scalar_one_or_none()
    if not s:
        s = Settings()
        db.add(s)
    s.sound = data.sound
    s.popups = data.popups
    s.telegram_on = data.telegram_on
    s.repeat_interval = data.repeat_interval
    s.refresh_interval = data.refresh_interval
    s.work_start = data.work_start
    s.work_end = data.work_end
    await db.commit()
    return {"ok": True}


# ── Logs ──────────────────────────────────────────────────────────────────────
logs_router = APIRouter(prefix="/api/logs", tags=["logs"])

@logs_router.get("/")
async def get_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Log).order_by(Log.created_at.desc()).limit(100))
    return [{"id": l.id, "text": l.text, "type": l.log_type,
             "time": l.created_at.strftime("%H:%M")} for l in result.scalars().all()]
