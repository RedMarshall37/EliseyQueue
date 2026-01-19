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
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    is_admin = message.from_user.id == config.config.ADMIN_ID

    # Сохраняем пользователя в базу
    db.add_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    if is_admin:
        welcome_text = (
            "👋 <b>Приветствую, Елисей!</b>\n\n"
            "<b>Основные функции:</b>\n"
            "• 👀 Посмотреть текущую очередь\n"
            "• ⏰ Проверить статус кабинета\n"
            "<b>Функции главного любителя белого монстра:</b>\n"
            "• ✅ Открыть кабинет\n"
            "• ❌ Закрыть кабинет\n"
            "• ⏸️ Приостановить\n"
            "• 🗑️ Очистить очередь"
        )
        await message.answer(
            welcome_text,
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode="HTML"
        )
    else:
        welcome_text = (
            "👋 <b>Добро пожаловать в систему очереди в кабинет Елисея!</b>\n\n"
            "<b>Основные функции:</b>\n"
            "• 👀 Посмотреть текущую очередь\n"
            "• 📝 Встать в очередь\n"
            "• 🔍 Узнать свой номер\n"
            "• 🚪 Выйти из очереди\n"
            "• ⏰ Проверить статус кабинета"
        )
        await message.answer(
            welcome_text,
            reply_markup=keyboards.get_user_keyboard(),
            parse_mode="HTML"
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
        for i, user in enumerate(queue, start=1):
            text += f"{i}. {user['name']}\n"
        text += f"\n*Всего в очереди:* {len(queue)} человек(а)\n"

    status_map = {
        "open": "✅ Открыт",
        "closed": "❌ Закрыт",
        "paused": "⏸️ Приостановлен"
    }

    text += f"\n*Статус кабинета:* {status_map.get(status['status'], status['status'])}"

    if status.get("message"):
        text += f"\n{status['message']}"

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


# ========== АДМИН ПАНЕЛЬ ==========
@dp.message(F.text == "✅ Открыть кабинет")
async def admin_open(message: Message):
    if message.from_user.id != config.config.ADMIN_ID:
        return
    
    db.set_office_status("open", "Кабинет открыт")
    await notify_all("ℹ️ <b>Кабинет открыт!</b> Можно вставать в очередь.")
    await message.answer("✅ <b>Кабинет открыт</b>", parse_mode="HTML")


@dp.message(F.text == "❌ Закрыть кабинет")
async def admin_close(message: Message):
    if message.from_user.id != config.config.ADMIN_ID:
        return
    
    db.set_office_status("closed", "Кабинет закрыт")
    await notify_all("⚠️ <b>Кабинет закрыт!</b>")
    await message.answer("❌ <b>Кабинет закрыт</b>", parse_mode="HTML")


@dp.message(F.text == "⏸️ Приостановить")
async def admin_pause(message: Message):
    if message.from_user.id != config.config.ADMIN_ID:
        return
    
    db.set_office_status("paused", "Прием приостановлен")
    await notify_all("⏸️ <b>Прием приостановлен!</b>")
    await message.answer("⏸️ <b>Прием приостановлен</b>", parse_mode="HTML")


@dp.message(F.text == "🗑️ Очистить очередь")
async def admin_clear(message: Message):
    if message.from_user.id != config.config.ADMIN_ID:
        return
    
    db.clear_queue()
    await notify_all("🗑️ <b>Очередь очищена администратором</b>")
    await message.answer("🗑️ <b>Очередь очищена</b>", parse_mode="HTML")


# ========== УВЕДОМЛЕНИЯ ==========
# ========== УВЕДОМЛЕНИЯ ==========
async def notify_all(text: str):
    """Отправить уведомление всем пользователям бота"""
    user_ids = db.get_all_user_ids()
    success_count = 0
    fail_count = 0
    
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            success_count += 1
        except Exception as e:
            # Логируем ошибки, если нужно
            fail_count += 1
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
    
    # Для админа можно добавить статистику отправки
    if config.config.ADMIN_ID:
        try:
            await bot.send_message(
                config.config.ADMIN_ID,
                f"📊 Уведомление отправлено:\n"
                f"✅ Успешно: {success_count}\n"
                f"❌ Не удалось: {fail_count}",
                parse_mode="HTML"
            )
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
