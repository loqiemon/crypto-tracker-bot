import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import settings
from db.queries import (
    deactivate_subscription,
    get_or_create_user,
    get_subscription,
)
from keyboards.inline import get_coins_keyboard
from services.coins import COIN_EMOJI, COIN_NAMES

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
    )
    await state.clear()

    await message.answer(
        f"Привет, <b>{message.from_user.first_name}</b>! 👋\n\n"
        "Я буду публиковать актуальные курсы криптовалют в твой Telegram-канал "
        "по расписанию — без лишних действий с твоей стороны.\n\n"
        "<b>Шаг 1 из 3:</b> Выбери монеты для отслеживания (до 3-х):",
        reply_markup=get_coins_keyboard([]),
        parse_mode="HTML",
    )

    from handlers.subscription import SubscriptionStates
    await state.set_state(SubscriptionStates.select_coins)
    await state.update_data(selected_coins=[])
    logger.info("User %s started setup", message.from_user.id)


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext) -> None:
    sub = await get_subscription(message.from_user.id)
    await state.clear()

    if sub:
        await message.answer(
            "Настроим подписку заново.\n\n"
            "<b>Шаг 1 из 3:</b> Выбери монеты для отслеживания (до 3-х):",
            reply_markup=get_coins_keyboard(sub.coins_list),
            parse_mode="HTML",
        )
        from handlers.subscription import SubscriptionStates
        await state.set_state(SubscriptionStates.select_coins)
        await state.update_data(selected_coins=sub.coins_list)
    else:
        await message.answer(
            "У тебя пока нет активной подписки.\n"
            "Используй /start чтобы настроить."
        )


@router.message(Command("stop"))
async def cmd_stop(message: Message, state: FSMContext) -> None:
    await state.clear()
    sub = await get_subscription(message.from_user.id)

    if not sub:
        await message.answer("У тебя нет активной подписки.")
        return

    await deactivate_subscription(message.from_user.id)

    try:
        from services.scheduler import remove_user_job
        await remove_user_job(message.from_user.id)
    except Exception as e:
        logger.warning("Could not remove job for user %s: %s", message.from_user.id, e)

    await message.answer(
        "⏸ Подписка приостановлена.\n"
        "Публикации в канал остановлены.\n\n"
        "Используй /start чтобы настроить заново."
    )
    logger.info("User %s stopped subscription", message.from_user.id)


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    sub = await get_subscription(message.from_user.id)

    if not sub:
        await message.answer(
            "У тебя нет активной подписки.\n"
            "Используй /start чтобы настроить."
        )
        return

    coins_display = ", ".join(
        f"{COIN_EMOJI[c]} {COIN_NAMES[c]}"
        for c in sub.coins_list
        if c in COIN_NAMES
    )

    await message.answer(
        "<b>📋 Твоя подписка</b>\n\n"
        f"Монеты: {coins_display}\n"
        f"Интервал: каждые <b>{sub.interval_minutes} мин.</b>\n"
        f"Канал ID: <code>{sub.channel_id}</code>\n\n"
        "Используй /settings чтобы изменить настройки.",
        parse_mode="HTML",
    )


@router.message(Command("chart"))
async def cmd_chart_test(message: Message) -> None:
    from aiogram import Bot as AiogramBot
    sub = await get_subscription(message.from_user.id)
    if not sub:
        await message.answer("Нет активной подписки.")
        return

    await message.answer("Генерирую график, подожди...")

    from services.chart import generate_chart
    chart = await generate_chart(sub.coins_list)

    if chart is None:
        await message.answer(
            "Данных пока недостаточно для графика.\n"
            "Подожди несколько минут — бот накопит историю цен."
        )
        return

    bot = AiogramBot(token=settings.BOT_TOKEN)
    await bot.send_photo(
        chat_id=sub.channel_id,
        photo=chart,
        caption="<b>📈 Тестовый график</b>",
        parse_mode="HTML",
    )
    await bot.session.close()
    await message.answer("График отправлен в канал!")