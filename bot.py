import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import keyboards
import database


# ========== FSM ==========
class QueueStates(StatesGroup):
    waiting_for_name = State()


# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=config.config.BOT_TOKEN)
dp = Dispatcher()
db = database.db


# ========== /start ==========
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    is_admin = message.from_user.id == config.config.ADMIN_ID

    welcome_text = (
        "👋 *Добро пожаловать в систему очереди в кабинет Елисея!*\n\n"
        "*Основные функции:*\n"
        "• 👀 Посмотреть текущую очередь\n"
        "• 📝 Встать в очередь\n"
        "• 🔍 Узнать свой номер\n"
        "• 🚪 Выйти из очереди\n"
        "• ⏰ Проверить статус кабинета"
    )

    await message.answer(
        welcome_text,
        reply_markup=keyboards.get_user_keyboard(is_admin),
        parse_mode="Markdown"
    )


# ========== ПОСМОТРЕТЬ ОЧЕРЕДЬ ==========
@dp.message(
    StateFilter("*"),
    F.text == "👀 Посмотреть очередь"
)
async def view_queue(message: Message):
    queue = db.get_queue()
    status = db.get_office_status()

    if not queue:
        text = "📭 *Очередь пуста*\n\n"
    else:
        text = "📋 *Текущая очередь:*\n\n"
        for i, user in enumerate(queue, 1):
            text += f"{i}. {user['name']}\n"
        text += f"\n*Всего в очереди:* {len(queue)} человек(а)\n"

    status_map = {
        "open": "✅ Открыт",
        "closed": "❌ Закрыт",
        "paused": "⏸️ Приостановлен"
    }

    text += f"\n*Статус кабинета:* {status_map.get(status['status'], status['status'])}"

    if status.get("message"):
        text += f"\n*Комментарий:* {status['message']}"

    await message.answer(text, parse_mode="Markdown")


# ========== ВСТАТЬ В ОЧЕРЕДЬ ==========
@dp.message(F.text == "📝 Встать в очередь")
async def join_queue_start(message: Message, state: FSMContext):
    status = db.get_office_status()

    if message.from_user.id == config.config.ADMIN_ID:
        await message.answer(
            "👑 Босс ВТиПО не может вставать в очередь.",
            parse_mode="Markdown"
        )
        return

    if status["status"] == "closed":
        await message.answer(
            f"❌ *Кабинет закрыт!*\n{status.get('message', '')}",
            parse_mode="Markdown"
        )
        return

    if status["status"] == "paused":
        await message.answer(
            f"⏸️ *Прием приостановлен!*\n{status.get('message', '')}",
            parse_mode="Markdown"
        )
        return

    position = db.get_user_position(message.from_user.id)
    if position:
        await message.answer(
            f"⚠️ Вы уже в очереди! Ваш номер: *{position}*",
            parse_mode="Markdown"
        )
        return

    await message.answer(
        "📝 *Введите ваше имя для очереди:*",
        parse_mode="Markdown"
    )
    await state.set_state(QueueStates.waiting_for_name)


@dp.message(QueueStates.waiting_for_name)
async def join_queue_finish(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            "❌ Имя должно быть не короче 2 символов. Попробуйте еще раз:"
        )
        return

    db.add_to_queue(message.from_user.id, name)

    queue = db.get_queue()
    position = next(
        i for i, u in enumerate(queue, 1)
        if u["user_id"] == message.from_user.id
    )

    if position == -1:
        await message.answer("⚠️ Вы уже в очереди!")
    else:
        await message.answer(
            f"✅ *Вы добавлены в очередь!*\n\n"
            f"• Ваш номер: *{position}*\n"
            f"• Имя в очереди: *{name}*\n"
            f"• Людей перед вами: *{position - 1}*",
            parse_mode="Markdown"
        )

    await state.clear()


# ========== МОЙ НОМЕР ==========
@dp.message(F.text == "🔍 Мой номер в очереди")
async def my_position(message: Message):
    position = db.get_user_position(message.from_user.id)

    if position:
        queue = db.get_queue()
        await message.answer(
            f"🔢 *Ваш номер:* {position}\n"
            f"👥 *Перед вами:* {position - 1}\n"
            f"📊 *Всего в очереди:* {len(queue)}",
            parse_mode="Markdown"
        )
    else:
        await message.answer("ℹ️ *Вы не в очереди*", parse_mode="Markdown")


# ========== ВЫЙТИ ИЗ ОЧЕРЕДИ ==========
@dp.message(
    StateFilter("*"),
    F.text == "🚪 Выйти из очереди"
)
async def leave_queue(message: Message, state: FSMContext):
    if db.remove_from_queue(message.from_user.id):
        await state.clear()
        await message.answer("✅ *Вы вышли из очереди*", parse_mode="Markdown")
    else:
        await message.answer("ℹ️ *Вы не были в очереди*", parse_mode="Markdown")


# ========== СТАТУС КАБИНЕТА ==========
@dp.message(
    StateFilter("*"),
    F.text == "⏰ Статус кабинета"
)
async def office_status(message: Message):
    status = db.get_office_status()

    status_texts = {
        "open": "✅ *ОТКРЫТ*",
        "closed": "❌ *ЗАКРЫТ*",
        "paused": "⏸️ *ПРИОСТАНОВЛЕН*"
    }

    text = f"🚪 *Статус кабинета:* {status_texts.get(status['status'], status['status'])}\n"

    if status.get("message"):
        text += f"\n*Комментарий:* {status['message']}"

    text += f"\n\n*Обновлено:* {status['updated_at'][:16].replace('T', ' ')}"

    await message.answer(text, parse_mode="Markdown")


# ========== АДМИН-ПАНЕЛЬ ==========
@dp.message(
    StateFilter("*"),
    F.text == "⚙️ Админ-панель"
)
async def admin_panel(message: Message):
    if message.from_user.id != config.config.ADMIN_ID:
        await message.answer("❌ Доступ запрещен!")
        return

    queue = db.get_queue()
    status = db.get_office_status()

    text = (
        "⚙️ *Админ-панель*\n\n"
        f"Статус кабинета: *{status['status']}*\n"
        f"Людей в очереди: *{len(queue)}*\n"
    )

    await message.answer(
        text,
        reply_markup=keyboards.get_admin_keyboard(),
        parse_mode="Markdown"
    )


# ========== CALLBACK АДМИНА ==========
@dp.callback_query(F.data.startswith("admin_"))
async def admin_actions(callback: CallbackQuery):
    if callback.from_user.id != config.config.ADMIN_ID:
        await callback.answer("Доступ запрещен!", show_alert=True)
        return

    action = callback.data

    if action == "admin_open":
        db.set_office_status("open", "Кабинет открыт")
        await notify_all("ℹ️ *Кабинет открыт!* Можно вставать в очередь.")

    elif action == "admin_close":
        db.set_office_status("closed", "Кабинет закрыт")
        await notify_all("⚠️ *Кабинет закрыт!*")

    elif action == "admin_pause":
        db.set_office_status("paused", "Прием приостановлен")
        await notify_all("⏸️ *Прием приостановлен!*")

    elif action == "admin_clear":
        db.clear_queue()
        await notify_all("🗑️ *Очередь очищена администратором*")

    await callback.answer("Готово")
    await callback.message.edit_reply_markup(
        reply_markup=keyboards.get_admin_keyboard()
    )


# ========== УВЕДОМЛЕНИЯ ==========
async def notify_all(text: str):
    for user in db.get_queue():
        try:
            await bot.send_message(user["user_id"], text, parse_mode="Markdown")
        except:
            pass


# ========== ЗАПУСК ==========
async def main():
    print("🤖 Бот 'Очередь в кабинет Елисея' запущен...")
    print(f"👑 Админ ID: {config.config.ADMIN_ID}")

    try:
        if not db.redis.exists("office:status"):
            db.set_office_status("open")
    except Exception as e:
        print("⚠️ Redis недоступен:", e)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
