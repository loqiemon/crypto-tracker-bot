from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.coins import COIN_EMOJI, COIN_NAMES, COIN_ORDER

INTERVALS = [1, 5, 10, 15, 30, 60]


def get_coins_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    buttons = []
    for symbol in COIN_ORDER:
        is_selected = symbol in selected
        label = f"✓ {COIN_EMOJI[symbol]} {COIN_NAMES[symbol]}" if is_selected else f"{COIN_EMOJI[symbol]} {COIN_NAMES[symbol]}"
        buttons.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"coin_{symbol}",
            )
        )

    rows = [[btn] for btn in buttons]

    done_text = f"Готово → ({len(selected)} выбрано)" if selected else "Выберите монеты"
    rows.append([
        InlineKeyboardButton(
            text=done_text,
            callback_data="coins_done",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_interval_keyboard() -> InlineKeyboardMarkup:
    row1 = [
        InlineKeyboardButton(text=f"{i} мин", callback_data=f"interval_{i}")
        for i in INTERVALS[:3]
    ]
    row2 = [
        InlineKeyboardButton(text=f"{i} мин", callback_data=f"interval_{i}")
        for i in INTERVALS[3:]
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_yes"),
        InlineKeyboardButton(text="✏️ Изменить", callback_data="confirm_edit"),
    ]])