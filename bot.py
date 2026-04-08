import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import settings
from db.base import init_db
from handlers import common, subscription

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/webhook"


def create_bot_and_dp() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(common.router)
    dp.include_router(subscription.router)
    return bot, dp


async def on_startup(bot: Bot) -> None:
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Database init failed: %s", e)
        raise

    try:
        from services.scheduler import init_scheduler
        await init_scheduler(bot)
        logger.info("Scheduler initialized")
    except Exception as e:
        logger.error("Scheduler init failed: %s", e)
        raise

    if settings.USE_WEBHOOK:
        try:
            webhook_url = f"{settings.WEBHOOK_BASE_URL}{WEBHOOK_PATH}"
            await bot.set_webhook(url=webhook_url, drop_pending_updates=True)
            logger.info("Webhook set: %s", webhook_url)
        except Exception as e:
            logger.error("Webhook set failed: %s", e)
            raise


async def on_shutdown(bot: Bot) -> None:
    try:
        from services.scheduler import close_http_session, scheduler
        scheduler.shutdown(wait=False)
        await close_http_session()
    except Exception as e:
        logger.warning("Shutdown error: %s", e)

    if settings.USE_WEBHOOK:
        try:
            await bot.delete_webhook()
        except Exception:
            pass

    logger.info("Bot stopped")


async def run_webhook(bot: Bot, dp: Dispatcher) -> None:
    app = web.Application()

    async def health(request):
        return web.Response(text="OK", status=200)

    app.router.add_get("/health", health)

    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.HOST, port=settings.PORT)
    await site.start()

    # сервер запущен — теперь инициализируем бота
    logger.info("Webhook server started on %s:%s", settings.HOST, settings.PORT)
    await on_startup(bot)

    try:
        await asyncio.Event().wait()
    finally:
        await on_shutdown(bot)
        await runner.cleanup()


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    await on_startup(bot)
    logger.info("Starting in polling mode")
    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        await on_shutdown(bot)


async def main() -> None:
    bot, dp = create_bot_and_dp()

    if settings.USE_WEBHOOK:
        await run_webhook(bot, dp)
    else:
        await run_polling(bot, dp)


if __name__ == "__main__":
    asyncio.run(main())