from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.db import Base


class Branch(Base):
    __tablename__ = "branches"
    id:         Mapped[int]  = mapped_column(Integer, primary_key=True)
    name:       Mapped[str]  = mapped_column(String(100), unique=True)
    color:      Mapped[str]  = mapped_column(String(20), default="#ef4444")
    active:     Mapped[bool] = mapped_column(Boolean, default=True)
    orders:     Mapped[list["Order"]] = relationship("Order", back_populates="branch_rel")


class Order(Base):
    __tablename__ = "orders"
    id:           Mapped[int]           = mapped_column(Integer, primary_key=True)
    order_num:    Mapped[str]           = mapped_column(String(20))
    branch_id:    Mapped[int]           = mapped_column(ForeignKey("branches.id"))
    delivery_time: Mapped[str]          = mapped_column(String(5))   # HH:MM
    delivery_dt:  Mapped[datetime]      = mapped_column(DateTime)
    note:         Mapped[str | None]    = mapped_column(Text, nullable=True)
    status:       Mapped[str]           = mapped_column(String(20), default="SAFE")
    hidden:       Mapped[bool]          = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)
    created_at:   Mapped[datetime]      = mapped_column(DateTime, default=datetime.now)
    # reminder flags
    reminded_60:  Mapped[bool] = mapped_column(Boolean, default=False)
    reminded_30:  Mapped[bool] = mapped_column(Boolean, default=False)
    branch_rel:   Mapped["Branch"] = relationship("Branch", back_populates="orders")


class Log(Base):
    __tablename__ = "logs"
    id:         Mapped[int]      = mapped_column(Integer, primary_key=True)
    text:       Mapped[str]      = mapped_column(Text)
    log_type:   Mapped[str]      = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Settings(Base):
    __tablename__ = "settings"
    id:              Mapped[int]  = mapped_column(Integer, primary_key=True)
    sound:           Mapped[bool] = mapped_column(Boolean, default=True)
    popups:          Mapped[bool] = mapped_column(Boolean, default=True)
    telegram_on:     Mapped[bool] = mapped_column(Boolean, default=True)
    repeat_interval: Mapped[int]  = mapped_column(Integer, default=10)
    refresh_interval:Mapped[int]  = mapped_column(Integer, default=5)
    work_start:      Mapped[str]  = mapped_column(String(5), default="06:00")
    work_end:        Mapped[str]  = mapped_column(String(5), default="00:00")
