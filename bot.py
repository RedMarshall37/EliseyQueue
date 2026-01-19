import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import keyboards
import database

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=config.config.BOT_TOKEN)
dp = Dispatcher()
db = database.db


# ========== /start ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    
    # Сохраняем пользователя в базу
    db.add_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    is_admin = message.from_user.id == config.config.ADMIN_ID

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
@dp.message(F.text == "👀 Посмотреть очередь")
async def view_queue(message: Message):
    # Сохраняем пользователя
    db.add_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    queue = db.get_queue()
    status = db.get_office_status()

    if not queue:
        text = "📭 <b>Очередь пуста</b>\n\n"
    else:
        text = "📋 <b>Текущая очередь:</b>\n\n"
        for i, user in enumerate(queue, start=1):
            text += f"{i}. {user['name']}\n"
        text += f"\n<b>Всего в очереди:</b> {len(queue)} человек(а)\n"

    status_map = {
        "open": "✅ Открыт",
        "closed": "❌ Закрыт"
    }

    text += f"\n*Статус кабинета:* {status_map.get(status['status'], status['status'])}"

    if status.get("message"):
        text += f"\n{status['message']}"

    await message.answer(text, parse_mode="HTML")


# ========== ВСТАТЬ В ОЧЕРЕДЬ ==========
@dp.message(F.text == "📝 Встать в очередь")
async def join_queue_start(message: Message, state: FSMContext):
    # Сохраняем пользователя
    db.add_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    status = db.get_office_status()

    if message.from_user.id == config.config.ADMIN_ID:
        await message.answer(
            "👑 <b>Босс ВТиПО не может вставать в очередь.</b>",
            parse_mode="HTML"
        )
        return

    if status["status"] == "closed":
        await message.answer(
            f"❌ <b>Кабинет закрыт!</b>\n{status.get('message', '')}",
            parse_mode="HTML"
        )
        return

    position = db.get_user_position(message.from_user.id)
    if position:
        await message.answer(
            f"⚠️ <b>Вы уже в очереди!</b> Ваш номер: <b>{position}</b>",
            parse_mode="HTML"
        )
        return
    
    # Получаем имя пользователя из аккаунта Telegram
    user_name = message.from_user.first_name
    if message.from_user.last_name:
        user_name += f" {message.from_user.last_name}"

     # Если нет имени, используем username
    if not user_name or user_name.strip() == "":
        if message.from_user.username:
            user_name = f"@{message.from_user.username}"
        else:
            user_name = f"User_{message.from_user.id}"

    # Добавляем в очередь
    result = db.add_to_queue(message.from_user.id, user_name)

    if result == -1:
        await message.answer("⚠️ <b>Вы уже в очереди!</b>", parse_mode="HTML")
        return

    queue = db.get_queue()
    position = db.get_user_position(message.from_user.id)

    if position:
        await message.answer(
            f"✅ <b>Вы добавлены в очередь!</b>\n\n"
            f"• Ваш номер: <b>{position}</b>\n"
            f"• Имя в очереди: <b>{user_name}</b>\n"
            f"• Людей перед вами: <b>{position - 1}</b>",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ <b>Произошла ошибка при добавлении в очередь</b>", parse_mode="HTML")

# ========== МОЙ НОМЕР ==========
@dp.message(F.text == "🔍 Мой номер в очереди")
async def my_position(message: Message):
    # Сохраняем пользователя
    db.add_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    position = db.get_user_position(message.from_user.id)

    if position:
        queue = db.get_queue()
        await message.answer(
            f"🔢 <b>Ваш номер:</b> {position}\n"
            f"👥 <b>Перед вами:</b> {position - 1}\n"
            f"📊 <b>Всего в очереди:</b> {len(queue)}",
            parse_mode="HTML"
        )
    else:
        await message.answer("ℹ️ <b>Вы не в очереди</b>", parse_mode="HTML")


# ========== ВЫЙТИ ИЗ ОЧЕРЕДИ ==========
@dp.message(F.text == "🚪 Выйти из очереди")
async def leave_queue(message: Message):
    # Сохраняем пользователя
    db.add_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    if db.remove_from_queue(message.from_user.id):
        await message.answer("✅ <b>Вы вышли из очереди</b>", parse_mode="HTML")
    else:
        await message.answer("ℹ️ <b>Вы не были в очереди</b>", parse_mode="HTML")

# ========== СТАТУС КАБИНЕТА ==========
@dp.message(F.text == "⏰ Статус кабинета")
async def office_status(message: Message):
    # Сохраняем пользователя
    db.add_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    status = db.get_office_status()

    status_texts = {
        "open": "✅ <b>ОТКРЫТ</b>",
        "closed": "❌ <b>ЗАКРЫТ</b>"
    }

    text = f"🚪 <b>Статус кабинета:</b> {status_texts.get(status['status'], status['status'])}\n"

    if status.get("message"):
        text += f"\n<b>Комментарий:</b> {status['message']}"

    # Форматируем дату
    updated_at = status['updated_at']
    if 'T' in updated_at:
        updated_at = updated_at.replace('T', ' ')[:16]
    
    text += f"\n\n<b>Обновлено:</b> {updated_at}"

    await message.answer(text, parse_mode="HTML")


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


@dp.message(F.text == "🗑️ Очистить очередь")
async def admin_clear(message: Message):
    if message.from_user.id != config.config.ADMIN_ID:
        return
    
    db.clear_queue()
    await notify_all("🗑️ <b>Очередь очищена администратором</b>")
    await message.answer("🗑️ <b>Очередь очищена</b>", parse_mode="HTML")


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

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
