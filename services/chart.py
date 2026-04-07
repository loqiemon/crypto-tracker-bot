import io
import logging
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from aiogram.types import BufferedInputFile

from db.queries import get_price_history_for_chart

logger = logging.getLogger(__name__)

COIN_COLORS: dict[str, str] = {
    "btc": "#F7931A",
    "eth": "#627EEA",
    "sol": "#00D4AA",
    "doge": "#C3A634",
    "ton": "#0098EA",
}

COIN_LABELS: dict[str, str] = {
    "btc": "Bitcoin (BTC)",
    "eth": "Ethereum (ETH)",
    "sol": "Solana (SOL)",
    "doge": "Dogecoin (DOGE)",
    "ton": "Toncoin (TON)",
}

BG_COLOR = "#1a1a2e"
GRID_COLOR = "#2a2a4a"
TEXT_COLOR = "#cccccc"
TICK_COLOR = "#888888"


async def generate_chart(coin_symbols: list[str]) -> BufferedInputFile | None:
    fig = None
    try:
        records = await get_price_history_for_chart(coin_symbols, days=30)

        if not records:
            logger.warning("No price history records found for chart")
            return None

        data_by_coin: dict[str, list] = {s: [] for s in coin_symbols}
        for r in records:
            if r.coin_symbol in data_by_coin:
                data_by_coin[r.coin_symbol].append(
                    (r.recorded_at, float(r.price_usd))
                )

        valid_coins = {
            sym: pts
            for sym, pts in data_by_coin.items()
            if len(pts) >= 2
        }

        if not valid_coins:
            logger.warning("Not enough data points for any coin")
            return None

        use_normalized = len(valid_coins) > 1

        fig, ax = plt.subplots(figsize=(12, 5))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)

        for symbol, points in valid_coins.items():
            dates = [p[0] for p in points]
            prices = [p[1] for p in points]
            color = COIN_COLORS.get(symbol, "#FFFFFF")
            label = COIN_LABELS.get(symbol, symbol.upper())

            if use_normalized:
                first = prices[0]
                if first == 0:
                    continue
                y_values = [(p / first - 1) * 100 for p in prices]
                current = y_values[-1]
                sign = "+" if current >= 0 else ""
                plot_label = f"{label}  {sign}{current:.1f}%"
            else:
                y_values = prices
                current = prices[-1]
                plot_label = f"{label}  ${current:,.2f}"

            ax.plot(
                dates,
                y_values,
                color=color,
                linewidth=1.8,
                label=plot_label,
                alpha=0.95,
            )
            ax.scatter(
                [dates[-1]],
                [y_values[-1]],
                color=color,
                s=30,
                zorder=5,
            )

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
        fig.autofmt_xdate(rotation=0, ha="center")

        ax.tick_params(colors=TICK_COLOR, labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID_COLOR)

        ax.grid(
            color=GRID_COLOR,
            linestyle="--",
            linewidth=0.5,
            alpha=0.8,
        )

        if use_normalized:
            ax.axhline(y=0, color="#555577", linewidth=0.8, linestyle="-")
            ax.set_ylabel("Изменение, %", color=TICK_COLOR, fontsize=9)
        else:
            ax.set_ylabel("Цена, USD", color=TICK_COLOR, fontsize=9)

        legend = ax.legend(
            facecolor="#252540",
            edgecolor=GRID_COLOR,
            labelcolor=TEXT_COLOR,
            fontsize=9,
            loc="upper left",
            framealpha=0.85,
        )

        days_count = (
            records[-1].recorded_at - records[0].recorded_at
        ).days + 1
        period_label = f"последние {days_count} дн." if days_count > 1 else "сегодня"

        today_str = datetime.now(tz=timezone.utc).strftime("%d.%m.%Y")
        ax.set_title(
            f"Ценовая динамика — {period_label}  ·  {today_str}",
            color=TEXT_COLOR,
            fontsize=11,
            pad=12,
            fontweight="normal",
        )

        plt.tight_layout(pad=1.5)

        buf = io.BytesIO()
        plt.savefig(
            buf,
            format="PNG",
            dpi=150,
            facecolor=fig.get_facecolor(),
            bbox_inches="tight",
        )
        buf.seek(0)

        return BufferedInputFile(buf.read(), filename="chart.png")

    except Exception as e:
        logger.error("Chart generation error: %s", e, exc_info=True)
        return None
    finally:
        if fig is not None:
            plt.close(fig)