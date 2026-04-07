from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Integer, Numeric, String, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    coins: Mapped[str] = mapped_column(String(64), nullable=False)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )

    @property
    def coins_list(self) -> list[str]:
        return [c.strip() for c in self.coins.split(",") if c.strip()]

    def __repr__(self) -> str:
        return f"<Subscription user={self.user_id} coins={self.coins} interval={self.interval_minutes}>"


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    price_usd: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    change_24h: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<PriceHistory coin={self.coin_symbol} price={self.price_usd}>"
    