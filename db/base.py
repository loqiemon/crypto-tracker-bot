from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from config import settings

# Проверяем, есть ли уже параметры в URL, если нет - можно добавить программно
db_url = settings.DATABASE_URL
if "prepared_statement_cache_size" not in db_url:
    separator = "&" if "?" in db_url else "?"
    db_url += f"{separator}prepared_statement_cache_size=0"

engine = create_async_engine(
    db_url, # Используем модифицированный URL
    echo=True,
    poolclass=NullPool,
    connect_args={
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
    # Используем соединение напрямую, чтобы избежать лишних проверок диалекта
    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()