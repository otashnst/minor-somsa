from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./minor_somsa.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    from backend.models.models import Branch, Order, Log, Settings  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # seed default branches
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(Branch))
        if not result.scalars().first():
            session.add_all([
                Branch(name="Minor",      color="#ef4444", active=True),
                Branch(name="Sergeli",    color="#f97316", active=True),
                Branch(name="Yunusabad",  color="#a855f7", active=True),
                Branch(name="Chilonzor", color="#3b82f6", active=True),
            ])
            await session.commit()
        # seed default settings
        from backend.models.models import Settings
        res2 = await session.execute(select(Settings))
        if not res2.scalars().first():
            session.add(Settings())
            await session.commit()
