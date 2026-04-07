import logging
from datetime import datetime, timezone

import aiohttp

from services.coins import COIN_IDS, COIN_NAMES, COIN_EMOJI, COIN_ORDER, REVERSE_IDS

logger = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=5)


async def fetch_prices(coin_symbols: list[str] | None = None) -> dict | None:
    if coin_symbols is None:
        coin_symbols = list(COIN_IDS.keys())

    ids = ",".join(
        COIN_IDS[c] for c in coin_symbols if c in COIN_IDS
    )

    params = {
        "ids": ids,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(COINGECKO_URL, params=params) as response:
                if response.status == 429:
                    logger.warning("CoinGecko rate limit hit (429)")
                    return None
                if response.status != 200:
                    logger.warning(
                        "CoinGecko returned unexpected status: %s", response.status
                    )
                    return None

                data = await response.json()

                if not data:
                    logger.warning("CoinGecko returned empty response")
                    return None

                return data

    except aiohttp.ClientConnectorError:
        logger.warning("CoinGecko: connection error - no network?")
        return None
    except TimeoutError:
        logger.warning("CoinGecko: request timed out after 5s")
        return None
    except aiohttp.ClientError as e:
        logger.warning("CoinGecko: client error: %s", e)
        return None
    except Exception as e:
        logger.error("CoinGecko: unexpected error: %s", e)
        return None


def format_price_message(
    coin_symbols: list[str],
    prices: dict,
) -> str:
    now_msk = datetime.now(tz=timezone.utc)
    time_str = now_msk.strftime("%H:%M UTC")

    lines = ["<b>📊 Курсы криптовалют</b>\n"]

    ordered = [c for c in COIN_ORDER if c in coin_symbols]
    for symbol in ordered:
        gecko_id = COIN_IDS.get(symbol)
        if not gecko_id:
            continue

        data = prices.get(gecko_id)
        if not data:
            continue

        price = float(data.get("usd", 0))
        raw_change = data.get("usd_24h_change")
        change = float(raw_change) if raw_change is not None else 0.0

        emoji = COIN_EMOJI.get(symbol, "")
        name = COIN_NAMES.get(symbol, symbol.upper())

        price_str = f"${price:,.2f}"

        if abs(change) < 0.001:
            change_str = "0.00%"
            change_icon = "➖"
        elif change > 0:
            change_str = f"+{change:.2f}%"
            change_icon = "🟢"
        else:
            change_str = f"{change:.2f}%"
            change_icon = "🔴"

        line = (
            f"{emoji} <b>{name}</b>: "
            f"<code>{price_str}</code>  "
            f"{change_icon} {change_str}"
        )
        lines.append(line)

    lines.append(f"\n<i>🕐 Обновлено: {time_str}</i>")

    return "\n".join(lines)