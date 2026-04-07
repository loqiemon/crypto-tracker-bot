import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from db.base import init_db
from handlers import common, subscription

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(subscription.router)

    await init_db()
    logger.info("Database initialized")

    from services.scheduler import init_scheduler, close_http_session

    async def on_startup():
        await init_scheduler(bot)
        logger.info("Scheduler initialized")

    async def on_shutdown():
        await close_http_session()
        logger.info("HTTP session closed")

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting bot in polling mode")
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())