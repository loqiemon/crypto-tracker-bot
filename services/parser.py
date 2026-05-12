import logging
import asyncio
from datetime import datetime, timedelta, timezone
import aiohttp

from services.coins import COIN_IDS

logger = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=5)

# --- Глобальные переменные для кеширования ---
_price_cache: dict | None = None
_last_fetch_time: datetime | None = None
CACHE_TTL_SECONDS = 600  # 10 минут (минимум между реальными запросами к API)
# ---------------------------------------------

async def fetch_prices(coin_symbols: list[str] | None = None) -> dict | None:
    global _price_cache, _last_fetch_time
    
    now = datetime.now(timezone.utc)

    # 1. Проверяем, есть ли данные в кеше и не рано ли делать новый запрос
    if _price_cache is not None and _last_fetch_time is not None:
        time_passed = (now - _last_fetch_time).total_seconds()
        if time_passed < CACHE_TTL_SECONDS:
            logger.info("Используем кешированные цены (прошло %d сек)", time_passed)
            return _price_cache

    # Подготовка параметров для запроса
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
                
                # Если поймали 429, возвращаем старый кеш
                if response.status == 429:
                    logger.warning("CoinGecko limit hit (429). Возвращаем старые данные.")
                    return _price_cache

                if response.status != 200:
                    logger.warning("Ошибка CoinGecko: %s. Возвращаем старые данные.", response.status)
                    return _price_cache

                data = await response.json()
                
                if data:
                    # 2. Обновляем кеш при успешном запросе
                    _price_cache = data
                    _last_fetch_time = now
                    logger.info("Цены успешно обновлены через API")
                    return data
                
    except Exception as e:
        logger.error("Ошибка при запросе к CoinGecko: %s. Используем кеш.", e)
        # Если API лежит или нет интернета — отдаем то, что было
        return _price_cache

    return _price_cache