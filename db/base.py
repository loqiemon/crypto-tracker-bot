from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    # 1. ОБЯЗАТЕЛЬНО для PgBouncer: отключаем встроенный пул SQLAlchemy
    poolclass=NullPool, 
    connect_args={
        # 2. Явно отключаем кэширование подготовленных выражений
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
        # 3. Добавляем параметры для стабильности соединения
        "command_timeout": 60,
    },
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def init_db() -> None:
    from db.models import Base
    # Используем этот метод для инициализации таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)