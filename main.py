import asyncio
import json
from html import escape
from os import getenv

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from dotenv import load_dotenv

from database import (
    create_application,
    get_application,
    get_application_stats,
    get_applications_by_status,
    init_db,
    update_application_status,
)


# --------------------
# НАСТРОЙКИ
# --------------------

load_dotenv()

TOKEN = getenv("BOT_TOKEN")
ADMIN_CHAT_ID = getenv("ADMIN_CHAT_ID")
WEBAPP_URL = getenv("WEBAPP_URL")

router = Router()
dp = Dispatcher()
dp.include_router(router)


# --------------------
# КЛАВИАТУРЫ
# --------------------

def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🚀 Хочу во «В курсе»",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ],
            [
                KeyboardButton(text="👀 Узнать о нас"),
                KeyboardButton(text="❓ FAQ"),
            ],
        ],
        resize_keyboard=True,
    )


def get_admin_application_keyboard(application_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 На собеседование",
                    callback_data=f"interview:{application_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"accept:{application_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отказать",
                    callback_data=f"reject:{application_id}",
                ),
            ],
        ]
    )


def get_interview_keyboard(application_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"accept:{application_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отказать",
                    callback_data=f"reject:{application_id}",
                ),
            ]
        ]
    )


# --------------------
# /START
# --------------------

@router.message(CommandStart())
async def start_handler(message: Message):
    # Web App-кнопка такого типа работает только в личном чате.
    if message.chat.type != "private":
        await message.answer(
            "👀 Чтобы подать заявку во «В курсе», "
            "открой личный чат со мной и напиши /start."
        )
        return

    await message.answer(
        "Привет! Я Вкурсик 👋\n\n"
        "Нажми кнопку ниже, чтобы подать заявку во «В курсе».",
        reply_markup=get_main_keyboard(),
    )


# --------------------
# MINI APP -> ЗАЯВКА
# --------------------

@router.message(F.web_app_data)
async def get_webapp_application(message: Message, bot: Bot):
    if message.chat.type != "private":
        return

    try:
        data = json.loads(message.web_app_data.data)
    except (json.JSONDecodeError, TypeError):
        await message.answer(
            "Не удалось прочитать заявку 😢\n"
            "Попробуй отправить её ещё раз."
        )
        return

    required_fields = (
        "name",
        "faculty",
        "course",
        "direction",
        "experience",
        "portfolio",
        "motivation",
    )

    if not all(field in data for field in required_fields):
        await message.answer(
            "В заявке не хватает некоторых данных 😢\n"
            "Попробуй заполнить её ещё раз."
        )
        return

    # Небольшая защита от пустых обязательных значений.
    required_non_empty = (
        "name",
        "faculty",
        "course",
        "direction",
        "experience",
        "motivation",
    )

    if any(not str(data[field]).strip() for field in required_non_empty):
        await message.answer(
            "Некоторые обязательные поля пустые 😢\n"
            "Вернись в приложение и заполни их."
        )
        return

    user = message.from_user

    application_id = create_application(
        telegram_id=user.id,
        username=user.username,
        name=str(data["name"]).strip(),
        faculty=str(data["faculty"]).strip(),
        course=str(data["course"]).strip(),
        direction=str(data["direction"]).strip(),
        experience=str(data["experience"]).strip(),
        portfolio=str(data["portfolio"]).strip() or "Нет портфолио",
        motivation=str(data["motivation"]).strip(),
    )

    username = f"@{user.username}" if user.username else "не указан"

    admin_text = (
        f"🆕 <b>Новая заявка #{application_id}</b>\n\n"
        f"👤 <b>Имя:</b> {escape(str(data['name']).strip())}\n"
        f"🏫 <b>Факультет:</b> {escape(str(data['faculty']).strip())}\n"
        f"🎓 <b>Курс:</b> {escape(str(data['course']).strip())}\n"
        f"🧩 <b>Направление:</b> {escape(str(data['direction']).strip())}\n\n"
        f"🧠 <b>Опыт:</b>\n"
        f"{escape(str(data['experience']).strip())}\n\n"
        f"🔗 <b>Портфолио:</b>\n"
        f"{escape(str(data['portfolio']).strip() or 'Нет портфолио')}\n\n"
        f"❤️ <b>Почему хочет во «В курсе»:</b>\n"
        f"{escape(str(data['motivation']).strip())}\n\n"
        f"📱 <b>Telegram:</b> {escape(username)}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n\n"
        "⚪️ <b>Статус:</b> Новая"
    )

    await bot.send_message(
        chat_id=int(ADMIN_CHAT_ID),
        text=admin_text,
        reply_markup=get_admin_application_keyboard(application_id),
        parse_mode="HTML",
    )

    await message.answer(
        "✅ <b>Заявка отправлена!</b>\n\n"
        f"Номер твоей заявки: <b>#{application_id}</b>\n\n"
        "Теперь она у команды «В курсе» 👀\n"
        "Когда по заявке будет решение, оно придёт прямо сюда.",
        parse_mode="HTML",
    )


# --------------------
# АДМИН-ПАНЕЛЬ
# --------------------

@router.message(Command("applications"))
async def applications_panel(message: Message):
    if message.chat.id != int(ADMIN_CHAT_ID):
        await message.answer("Эта команда доступна только администрации.")
        return

    stats = get_application_stats()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⚪️ Новые — {stats['new']}",
                    callback_data="apps:new",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💬 Собеседование — {stats['interview']}",
                    callback_data="apps:interview",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"✅ Приняты — {stats['accepted']}",
                    callback_data="apps:accepted",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"❌ Отказ — {stats['rejected']}",
                    callback_data="apps:rejected",
                )
            ],
        ]
    )

    await message.answer(
        "📋 <b>Заявки во «В курсе»</b>\n\n"
        f"Всего заявок: <b>{sum(stats.values())}</b>\n\n"
        "Выбери категорию:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("apps:"))
async def applications_list(callback: CallbackQuery):
    status = callback.data.split(":", 1)[1]

    status_names = {
        "new": "⚪️ Новые заявки",
        "interview": "💬 Собеседование",
        "accepted": "✅ Принятые",
        "rejected": "❌ Отказ",
    }

    if status not in status_names:
        await callback.answer("Неизвестный статус", show_alert=True)
        return

    applications = get_applications_by_status(status)

    if not applications:
        await callback.answer(
            "Заявок в этой категории пока нет",
            show_alert=True,
        )
        return

    buttons = []

    for application in applications[:20]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"#{application['id']} "
                        f"{application['name']} — "
                        f"{application['direction']}"
                    ),
                    callback_data=f"view_app:{application['id']}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="apps_home",
            )
        ]
    )

    await callback.message.edit_text(
        f"<b>{status_names[status]}</b>\n\n"
        f"Заявок: <b>{len(applications)}</b>\n\n"
        "Выбери кандидата:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "apps_home")
async def applications_home(callback: CallbackQuery):
    stats = get_application_stats()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⚪️ Новые — {stats['new']}",
                    callback_data="apps:new",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💬 Собеседование — {stats['interview']}",
                    callback_data="apps:interview",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"✅ Приняты — {stats['accepted']}",
                    callback_data="apps:accepted",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"❌ Отказ — {stats['rejected']}",
                    callback_data="apps:rejected",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        "📋 <b>Заявки во «В курсе»</b>\n\n"
        f"Всего заявок: <b>{sum(stats.values())}</b>\n\n"
        "Выбери категорию:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data.startswith("view_app:"))
async def view_application(callback: CallbackQuery):
    application_id = int(callback.data.split(":", 1)[1])
    application = get_application(application_id)

    if not application:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    status_names = {
        "new": "⚪️ Новая",
        "interview": "💬 Собеседование",
        "accepted": "✅ Принята",
        "rejected": "❌ Отказ",
    }

    buttons = []

    if application["status"] == "new":
        buttons = [
            [
                InlineKeyboardButton(
                    text="💬 На собеседование",
                    callback_data=f"interview:{application_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"accept:{application_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отказать",
                    callback_data=f"reject:{application_id}",
                ),
            ],
        ]

    elif application["status"] == "interview":
        buttons = [
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"accept:{application_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отказать",
                    callback_data=f"reject:{application_id}",
                ),
            ]
        ]

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к списку",
                callback_data=f"apps:{application['status']}",
            )
        ]
    )

    username = (
        f"@{application['username']}"
        if application["username"]
        else "не указан"
    )

    reviewed_by = application["reviewed_by_name"] or "—"

    text = (
        f"📄 <b>Заявка #{application['id']}</b>\n\n"
        f"👤 <b>Имя:</b> {escape(application['name'])}\n"
        f"🏫 <b>Факультет:</b> {escape(application['faculty'])}\n"
        f"🎓 <b>Курс:</b> {escape(application['course'])}\n"
        f"🧩 <b>Направление:</b> {escape(application['direction'])}\n\n"
        f"🧠 <b>Опыт:</b>\n{escape(application['experience'])}\n\n"
        f"🔗 <b>Портфолио:</b>\n{escape(application['portfolio'])}\n\n"
        f"❤️ <b>Мотивация:</b>\n{escape(application['motivation'])}\n\n"
        f"📱 <b>Telegram:</b> {escape(username)}\n\n"
        f"<b>Статус:</b> {status_names.get(application['status'], application['status'])}\n"
        f"<b>Рассмотрел:</b> {escape(reviewed_by)}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )

    await callback.answer()


# --------------------
# СТАТУСЫ ЗАЯВОК
# --------------------

@router.callback_query(F.data.startswith("interview:"))
async def admin_interview(callback: CallbackQuery, bot: Bot):
    application_id = int(callback.data.split(":", 1)[1])
    application = get_application(application_id)

    if not application:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if application["status"] != "new":
        await callback.answer(
            "Эта заявка уже обработана",
            show_alert=True,
        )
        return

    update_application_status(
        application_id=application_id,
        status="interview",
        reviewed_by_id=callback.from_user.id,
        reviewed_by_name=callback.from_user.full_name,
    )

    await bot.send_message(
        chat_id=application["telegram_id"],
        text=(
            "👀 <b>Твоя заявка нас заинтересовала!</b>\n\n"
            "Мы хотим познакомиться с тобой поближе "
            "и пригласить на собеседование 💬\n\n"
            "Скоро с тобой свяжется кто-то из команды «В курсе»."
        ),
        parse_mode="HTML",
    )

    await callback.message.edit_reply_markup(
        reply_markup=get_interview_keyboard(application_id)
    )

    await callback.message.answer(
        f"💬 <b>Заявка #{application_id} → собеседование</b>\n\n"
        f"Кандидат: {escape(application['name'])}\n"
        f"Решение: {escape(callback.from_user.full_name)}",
        parse_mode="HTML",
    )

    await callback.answer("Кандидат приглашён на собеседование")


@router.callback_query(F.data.startswith("accept:"))
async def admin_accept(callback: CallbackQuery, bot: Bot):
    application_id = int(callback.data.split(":", 1)[1])
    application = get_application(application_id)

    if not application:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if application["status"] in ("accepted", "rejected"):
        await callback.answer(
            "Эта заявка уже закрыта",
            show_alert=True,
        )
        return

    update_application_status(
        application_id=application_id,
        status="accepted",
        reviewed_by_id=callback.from_user.id,
        reviewed_by_name=callback.from_user.full_name,
    )

    await bot.send_message(
        chat_id=application["telegram_id"],
        text=(
            "🎉 <b>Ты во «В курсе»!</b>\n\n"
            "Мы приняли твою заявку ❤️\n\n"
            "Скоро с тобой свяжется команда "
            "и расскажет о следующих шагах."
        ),
        parse_mode="HTML",
    )

    await callback.message.edit_reply_markup()

    await callback.message.answer(
        f"✅ <b>Заявка #{application_id} принята</b>\n\n"
        f"Кандидат: {escape(application['name'])}\n"
        f"Направление: {escape(application['direction'])}\n"
        f"Решение: {escape(callback.from_user.full_name)}",
        parse_mode="HTML",
    )

    await callback.answer("Кандидат принят")


@router.callback_query(F.data.startswith("reject:"))
async def admin_reject(callback: CallbackQuery, bot: Bot):
    application_id = int(callback.data.split(":", 1)[1])
    application = get_application(application_id)

    if not application:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if application["status"] in ("accepted", "rejected"):
        await callback.answer(
            "Эта заявка уже закрыта",
            show_alert=True,
        )
        return

    update_application_status(
        application_id=application_id,
        status="rejected",
        reviewed_by_id=callback.from_user.id,
        reviewed_by_name=callback.from_user.full_name,
    )

    await bot.send_message(
        chat_id=application["telegram_id"],
        text=(
            "Спасибо за интерес к «В курсе» ❤️\n\n"
            "К сожалению, сейчас мы не готовы пригласить тебя в команду.\n\n"
            "Это не значит, что двери закрыты навсегда. "
            "Будем рады увидеть твою заявку снова!"
        ),
    )

    await callback.message.edit_reply_markup()

    await callback.message.answer(
        f"❌ <b>Заявка #{application_id} отклонена</b>\n\n"
        f"Кандидат: {escape(application['name'])}\n"
        f"Направление: {escape(application['direction'])}\n"
        f"Решение: {escape(callback.from_user.full_name)}",
        parse_mode="HTML",
    )

    await callback.answer("Отказ отправлен")


# --------------------
# О НАС / FAQ
# --------------------

@router.message(F.text == "👀 Узнать о нас")
async def about_handler(message: Message):
    await message.answer(
        "«В курсе» — студенческое интернет-издание РУДН.\n\n"
        "Мы рассказываем о студенческой жизни, "
        "университете и людях вокруг нас."
    )


@router.message(F.text == "❓ FAQ")
async def faq_handler(message: Message):
    await message.answer(
        "Здесь позже появятся ответы на частые вопросы 🙂"
    )


# --------------------
# ЗАПУСК
# --------------------

async def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN не найден в .env")

    if not ADMIN_CHAT_ID:
        raise ValueError("ADMIN_CHAT_ID не найден в .env")

    if not WEBAPP_URL:
        raise ValueError("WEBAPP_URL не найден в .env")

    init_db()

    bot = Bot(token=TOKEN)

    print("Вкурсик запущен 👀")
    print("База данных подключена ✅")
    print("Mini App:", WEBAPP_URL)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
