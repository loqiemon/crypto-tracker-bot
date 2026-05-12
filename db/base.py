from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    # Отключаем встроенный пул SQLAlchemy, так как Render использует PgBouncer
    poolclass=NullPool, 
    connect_args={
        # Эти две строки — критическое решение для ошибки DuplicatePreparedStatementError
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
    },
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def init_db() -> None:
    from db.models import Base
    # Важно: engine.begin() тоже будет использовать настройки выше
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)