import logging
from datetime import datetime, timezone
import aiohttp

# Импортируем необходимые константы
from services.coins import COIN_IDS, COIN_NAMES, COIN_EMOJI, COIN_ORDER

logger = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=5)

# --- Кеширование ---
_price_cache: dict | None = None
_last_fetch_time: datetime | None = None
CACHE_TTL_SECONDS = 600  # 10 минут

async def fetch_prices(coin_symbols: list[str] | None = None) -> dict | None:
    global _price_cache, _last_fetch_time
    
    now = datetime.now(timezone.utc)

    # Проверка кеша
    if _price_cache is not None and _last_fetch_time is not None:
        if (now - _last_fetch_time).total_seconds() < CACHE_TTL_SECONDS:
            logger.info("Используем кешированные цены")
            return _price_cache

    if coin_symbols is None:
        coin_symbols = list(COIN_IDS.keys())

    ids = ",".join(COIN_IDS[c] for c in coin_symbols if c in COIN_IDS)
    params = {
        "ids": ids,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(COINGECKO_URL, params=params) as response:
                if response.status == 429:
                    logger.warning("CoinGecko 429: лимит исчерпан. Используем кеш.")
                    return _price_cache
                
                if response.status != 200:
                    return _price_cache

                data = await response.json()
                if data:
                    _price_cache = data
                    _last_fetch_time = now
                    return data
    except Exception as e:
        logger.error("Ошибка при запросе к API: %s", e)
        return _price_cache

    return _price_cache

def format_price_message(coin_symbols: list[str], prices: dict) -> str:
    now_msk = datetime.now(timezone.utc)
    time_str = now_msk.strftime("%H:%M UTC")

    lines = ["<b>📊 Курсы криптовалют</b>\n"]

    ordered = [c for c in COIN_ORDER if c in coin_symbols]
    for symbol in ordered:
        gecko_id = COIN_IDS.get(symbol)
        if not gecko_id or gecko_id not in prices:
            continue

        data = prices[gecko_id]
        price = float(data.get("usd", 0))
        change = float(data.get("usd_24h_change") or 0)

        emoji = COIN_EMOJI.get(symbol, "")
        name = COIN_NAMES.get(symbol, symbol.upper())
        price_str = f"${price:,.2f}"

        if abs(change) < 0.01:
            change_str = "0.00%"; icon = "➖"
        elif change > 0:
            change_str = f"+{change:.2f}%"; icon = "🟢"
        else:
            change_str = f"{change:.2f}%"; icon = "🔴"

        lines.append(f"{emoji} <b>{name}</b>: <code>{price_str}</code> {icon} {change_str}")

    lines.append(f"\n<i>🕐 Обновлено: {time_str}</i>")
    return "\n".join(lines)