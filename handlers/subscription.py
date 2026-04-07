import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from db.queries import save_subscription
from keyboards.inline import get_coins_keyboard, get_confirm_keyboard, get_interval_keyboard
from services.coins import COIN_EMOJI, COIN_NAMES

router = Router()
logger = logging.getLogger(__name__)

MAX_COINS = 3


class SubscriptionStates(StatesGroup):
    select_coins = State()
    input_channel = State()
    select_interval = State()
    confirm = State()


@router.callback_query(SubscriptionStates.select_coins, F.data.startswith("coin_"))
async def process_coin_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    symbol = callback.data.replace("coin_", "")
    data = await state.get_data()
    selected: list[str] = data.get("selected_coins", [])

    if symbol in selected:
        selected.remove(symbol)
    elif len(selected) >= MAX_COINS:
        await callback.answer(
            f"Максимум {MAX_COINS} монеты. Сначала отмени одну.",
            show_alert=True,
        )
        return
    else:
        selected.append(symbol)

    await state.update_data(selected_coins=selected)

    new_keyboard = get_coins_keyboard(selected)
    try:
        await callback.message.edit_reply_markup(reply_markup=new_keyboard)
    except Exception:
        pass

    await callback.answer()


@router.callback_query(SubscriptionStates.select_coins, F.data == "coins_done")
async def process_coins_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected: list[str] = data.get("selected_coins", [])

    if not selected:
        await callback.answer("Выбери хотя бы одну монету!", show_alert=True)
        return

    await state.set_state(SubscriptionStates.input_channel)
    await callback.message.answer(
        "<b>Шаг 2 из 3:</b> Введи username или ID канала.\n\n"
        "Сначала убедись что бот добавлен в администраторы канала "
        "с правом публикации сообщений.\n\n"
        "Примеры:\n"
        "<code>@my_crypto_channel</code>\n"
        "<code>-1001234567890</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SubscriptionStates.input_channel)
async def process_channel_input(message: Message, state: FSMContext, bot: Bot) -> None:
    raw = message.text.strip()

    try:
        chat = await bot.get_chat(raw)
    except Exception:
        await message.answer(
            "Канал не найден. Проверь username или ID и попробуй снова.\n\n"
            "Убедись что бот добавлен в канал.",
        )
        return

    try:
        bot_info = await bot.me()
        member = await bot.get_chat_member(chat.id, bot_info.id)
        if member.status not in ("administrator", "creator"):
            await message.answer(
                f"Бот не является администратором канала <b>{chat.title}</b>.\n\n"
                "Добавь бота в администраторы канала с правом "
                "публикации сообщений и попробуй снова.",
                parse_mode="HTML",
            )
            return
    except Exception:
        await message.answer(
            "Не удалось проверить права бота в этом канале.\n"
            "Убедись что бот добавлен в администраторы.",
        )
        return

    await state.update_data(channel_id=chat.id, channel_title=chat.title)
    await state.set_state(SubscriptionStates.select_interval)

    await message.answer(
        f"Канал <b>{chat.title}</b> подключён! ✅\n\n"
        "<b>Шаг 3 из 3:</b> Как часто публиковать курсы?",
        reply_markup=get_interval_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(SubscriptionStates.select_interval, F.data.startswith("interval_"))
async def process_interval(callback: CallbackQuery, state: FSMContext) -> None:
    interval = int(callback.data.replace("interval_", ""))
    data = await state.get_data()
    await state.update_data(interval_minutes=interval)
    await state.set_state(SubscriptionStates.confirm)

    selected: list[str] = data.get("selected_coins", [])
    channel_title: str = data.get("channel_title", "канал")

    coins_display = "\n".join(
        f"  {COIN_EMOJI[c]} {COIN_NAMES[c]}"
        for c in selected if c in COIN_NAMES
    )

    await callback.message.answer(
        "<b>Проверь настройки:</b>\n\n"
        f"📊 Монеты:\n{coins_display}\n\n"
        f"📢 Канал: <b>{channel_title}</b>\n"
        f"⏱ Интервал: каждые <b>{interval} мин.</b>\n\n"
        "Всё верно?",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(SubscriptionStates.confirm, F.data == "confirm_edit")
async def process_confirm_edit(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected: list[str] = data.get("selected_coins", [])

    await state.set_state(SubscriptionStates.select_coins)
    await callback.message.answer(
        "Выбери монеты заново:",
        reply_markup=get_coins_keyboard(selected),
    )
    await callback.answer()


@router.callback_query(SubscriptionStates.confirm, F.data == "confirm_yes")
async def process_confirm_yes(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()

    user_id = callback.from_user.id
    channel_id: int = data["channel_id"]
    coins_str: str = ",".join(data["selected_coins"])
    interval: int = data["interval_minutes"]

    try:
        from services.scheduler import register_user_job, remove_user_job
        await remove_user_job(user_id)
    except Exception as e:
        logger.warning("Could not remove old job for user %s: %s", user_id, e)

    sub = await save_subscription(
        user_id=user_id,
        channel_id=channel_id,
        coins=coins_str,
        interval_minutes=interval,
    )

    try:
        from services.scheduler import register_user_job
        await register_user_job(bot, sub)
    except Exception as e:
        logger.warning("Could not register job for user %s: %s", user_id, e)

    await state.clear()

    await callback.message.answer(
        "🚀 <b>Подписка активирована!</b>\n\n"
        f"Курсы будут публиковаться в канал каждые <b>{interval} мин.</b>\n"
        "Ночью в 00:00 пришлю график за 30 дней.\n\n"
        "Используй /stop чтобы остановить.\n"
        "Используй /settings чтобы изменить настройки.",
        parse_mode="HTML",
    )
    await callback.answer("Готово!")
    logger.info(
        "User %s activated subscription: coins=%s interval=%s",
        user_id, coins_str, interval,
    )