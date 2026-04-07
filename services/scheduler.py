import logging
from datetime import datetime, timezone

import aiohttp
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from db.queries import (
    get_all_active_subscriptions,
    get_price_history_for_chart,
    get_subscription,
    save_price_history,
)
from services.parser import fetch_prices, format_price_message

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)

_http_session: aiohttp.ClientSession | None = None


def get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
    return _http_session


async def close_http_session() -> None:
    global _http_session
    if _http_session and not _http_session.closed:
        await _http_session.close()
        _http_session = None


async def send_price_update(bot: Bot, user_id: int) -> None:
    sub = await get_subscription(user_id)
    if not sub or not sub.is_active:
        logger.warning("Job fired for user %s but no active subscription found", user_id)
        return

    coin_symbols = sub.coins_list
    prices = await fetch_prices(coin_symbols)

    if prices is None:
        logger.warning("Skipping update for user %s: could not fetch prices", user_id)
        return

    await save_price_history(prices, coin_symbols)

    message_text = format_price_message(coin_symbols, prices)

    try:
        await bot.send_message(
            chat_id=sub.channel_id,
            text=message_text,
            parse_mode="HTML",
        )
        logger.info("Sent price update to channel %s for user %s", sub.channel_id, user_id)
    except Exception as e:
        logger.warning(
            "Failed to send message to channel %s for user %s: %s",
            sub.channel_id, user_id, e,
        )


async def send_night_report(bot: Bot, user_id: int) -> None:
    sub = await get_subscription(user_id)
    if not sub or not sub.is_active:
        return

    coin_symbols = sub.coins_list

    try:
        from services.chart import generate_chart
        chart_file = await generate_chart(coin_symbols)
    except Exception as e:
        logger.error("Chart generation failed for user %s: %s", user_id, e)
        return

    if chart_file is None:
        logger.warning("No chart data for user %s", user_id)
        return

    today = datetime.now(tz=timezone.utc).strftime("%d.%m.%Y")

    try:
        await bot.send_photo(
            chat_id=sub.channel_id,
            photo=chart_file,
            caption=f"<b>📈 График цен за 30 дней</b>\n<i>{today}</i>",
            parse_mode="HTML",
        )
        logger.info("Sent night report to channel %s for user %s", sub.channel_id, user_id)
    except Exception as e:
        logger.warning(
            "Failed to send chart to channel %s for user %s: %s",
            sub.channel_id, user_id, e,
        )


async def register_user_job(bot: Bot, sub) -> None:
    price_job_id = f"price_{sub.user_id}"
    chart_job_id = f"chart_{sub.user_id}"

    if scheduler.get_job(price_job_id):
        scheduler.remove_job(price_job_id)
    if scheduler.get_job(chart_job_id):
        scheduler.remove_job(chart_job_id)

    scheduler.add_job(
        send_price_update,
        trigger=IntervalTrigger(minutes=sub.interval_minutes),
        id=price_job_id,
        kwargs={"bot": bot, "user_id": sub.user_id},
        replace_existing=True,
        misfire_grace_time=30,
    )

    scheduler.add_job(
        send_night_report,
        trigger=CronTrigger(hour=0, minute=0, timezone=settings.TIMEZONE),
        id=chart_job_id,
        kwargs={"bot": bot, "user_id": sub.user_id},
        replace_existing=True,
        misfire_grace_time=300,
    )

    logger.info(
        "Registered jobs for user %s: interval=%s min",
        sub.user_id, sub.interval_minutes,
    )


async def remove_user_job(user_id: int) -> None:
    for prefix in ("price_", "chart_"):
        job_id = f"{prefix}{user_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info("Removed job %s", job_id)


async def init_scheduler(bot: Bot) -> None:
    subscriptions = await get_all_active_subscriptions()

    for sub in subscriptions:
        await register_user_job(bot, sub)

    scheduler.start()
    logger.info(
        "Scheduler started with %s active jobs total",
        len(scheduler.get_jobs()),
    )