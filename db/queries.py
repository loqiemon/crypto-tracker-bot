import logging
from datetime import datetime, timedelta

from sqlalchemy import select, update

from db.base import async_session_maker
from db.models import PriceHistory, Subscription, User

logger = logging.getLogger(__name__)


async def get_or_create_user(user_id: int, username: str | None = None) -> User:
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            user = User(id=user_id, username=username)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info("Created new user %s", user_id)
        return user


async def get_subscription(user_id: int) -> Subscription | None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()


async def save_subscription(
    user_id: int,
    channel_id: int,
    coins: str,
    interval_minutes: int,
) -> Subscription:
    async with async_session_maker() as session:
        existing = await session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        sub = existing.scalar_one_or_none()

        if sub:
            sub.channel_id = channel_id
            sub.coins = coins
            sub.interval_minutes = interval_minutes
            sub.is_active = True
            sub.updated_at = datetime.utcnow()
        else:
            sub = Subscription(
                user_id=user_id,
                channel_id=channel_id,
                coins=coins,
                interval_minutes=interval_minutes,
            )
            session.add(sub)

        await session.commit()
        await session.refresh(sub)
        logger.info("Saved subscription for user %s", user_id)
        return sub


async def deactivate_subscription(user_id: int) -> None:
    async with async_session_maker() as session:
        await session.execute(
            update(Subscription)
            .where(Subscription.user_id == user_id)
            .values(is_active=False)
        )
        await session.commit()
        logger.info("Deactivated subscription for user %s", user_id)



async def get_all_active_subscriptions() -> list[Subscription]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Subscription).where(Subscription.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())


async def save_price_history(prices: dict, coin_symbols: list[str]) -> None:
    from services.parser import COIN_IDS
    reverse_map = {v: k for k, v in COIN_IDS.items()}

    async with async_session_maker() as session:
        for gecko_id, data in prices.items():
            symbol = reverse_map.get(gecko_id)
            if not symbol:
                continue
            record = PriceHistory(
                coin_symbol=symbol,
                price_usd=float(data.get("usd", 0)),
                change_24h=float(data.get("usd_24h_change") or 0),
            )
            session.add(record)
        await session.commit()


async def get_price_history_for_chart(
    coin_symbols: list[str],
    days: int = 30,
) -> list[PriceHistory]:
    since = datetime.utcnow() - timedelta(days=days)
    async with async_session_maker() as session:
        result = await session.execute(
            select(PriceHistory)
            .where(
                PriceHistory.coin_symbol.in_(coin_symbols),
                PriceHistory.recorded_at >= since,
            )
            .order_by(PriceHistory.recorded_at.asc())
        )
        return list(result.scalars().all())