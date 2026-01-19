import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import keyboards
import database


# ========== FSM ДЛЯ ИЗМЕНЕНИЯ ИМЕНИ ==========
class ChangeNameStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_new_name = State()
    searching_user = State()


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
            "• 🗑️ Очистить очередь\n"
            "• ✏️ Изменить имя пользователя"
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

# ========== КОМАНДА ДЛЯ ИЗМЕНЕНИЯ ИМЕНИ ==========
@dp.message(Command("change_name"))
async def cmd_change_name(message: Message, state: FSMContext):
    """Команда для изменения имени пользователя (только для админа)"""
    if message.from_user.id != config.config.ADMIN_ID:
        await message.answer("❌ <b>Доступ запрещен!</b>", parse_mode="HTML")
        return
    
    await message.answer(
        "👤 <b>Введите ID пользователя, чье имя нужно изменить:</b>\n\n"
        "Можно также ввести часть имени для поиска.\n"
        "Или нажмите ❌ Отмена",
        reply_markup=keyboards.get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ChangeNameStates.waiting_for_user_id)

# ========== КНОПКА ИЗМЕНЕНИЯ ИМЕНИ ==========
@dp.message(F.text == "✏️ Изменить имя")
async def change_name_button(message: Message, state: FSMContext):
    """Кнопка для изменения имени пользователя (только для админа)"""
    if message.from_user.id != config.config.ADMIN_ID:
        await message.answer("❌ <b>Доступ запрещен!</b>", parse_mode="HTML")
        return
    
    await message.answer(
        "👤 <b>Введите ID пользователя, чье имя нужно изменить:</b>\n\n"
        "Можно также ввести часть имени для поиска.\n"
        "Или нажмите ❌ Отмена",
        reply_markup=keyboards.get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ChangeNameStates.waiting_for_user_id)    

# ========== ОТМЕНА ДЕЙСТВИЯ ==========
@dp.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Отмена любого действия"""
    await state.clear()
    if message.from_user.id == config.config.ADMIN_ID:
        await message.answer(
            "❌ <b>Действие отменено</b>",
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Действие отменено</b>",
            reply_markup=keyboards.get_user_keyboard(),
            parse_mode="HTML"
        )

# ========== ПОЛУЧЕНИЕ ID ПОЛЬЗОВАТЕЛЯ ==========
@dp.message(ChangeNameStates.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    user_input = message.text.strip()
    
    # Если ввели числовой ID
    if user_input.isdigit():
        user_id = int(user_input)
        user_info = db.get_user_info(user_id)
        
        if not user_info:
            await message.answer(
                f"❌ <b>Пользователь с ID {user_id} не найден в очереди.</b>\n\n"
                f"Попробуйте еще раз или введите часть имени для поиска:",
                parse_mode="HTML"
            )
            return
        
        # Сохраняем ID пользователя в состоянии
        await state.update_data(user_id=user_id, current_name=user_info['name'])
        
        await message.answer(
            f"👤 <b>Найден пользователь:</b>\n"
            f"ID: {user_id}\n"
            f"Текущее имя: <b>{user_info['name']}</b>\n\n"
            f"✏️ <b>Введите новое имя:</b>",
            parse_mode="HTML"
        )
        await state.set_state(ChangeNameStates.waiting_for_new_name)
    
    # Если ввели текст (поиск по имени)
    else:
        users = db.search_user_by_name(user_input)
        
        if not users:
            await message.answer(
                f"❌ <b>Пользователи с именем '{user_input}' не найдены.</b>\n\n"
                f"Попробуйте еще раз или введите ID пользователя:",
                parse_mode="HTML"
            )
            return
        
        if len(users) == 1:
            user = users[0]
            await state.update_data(user_id=user['user_id'], current_name=user['name'])
            
            await message.answer(
                f"👤 <b>Найден пользователь:</b>\n"
                f"ID: {user['user_id']}\n"
                f"Текущее имя: <b>{user['name']}</b>\n\n"
                f"✏️ <b>Введите новое имя:</b>",
                parse_mode="HTML"
            )
            await state.set_state(ChangeNameStates.waiting_for_new_name)
        else:
            # Показываем список найденных пользователей
            text = f"🔍 <b>Найдено пользователей ({len(users)}):</b>\n\n"
            for i, user in enumerate(users, 1):
                position = db.get_user_position(user['user_id'])
                text += f"{i}. <b>{user['name']}</b> (ID: {user['user_id']}, позиция: {position})\n"
            
            text += "\n<b>Введите ID нужного пользователя:</b>"
            
            await state.update_data(search_results=users)
            await message.answer(text, parse_mode="HTML")


# ========== ПОЛУЧЕНИЕ НОВОГО ИМЕНИ ==========
@dp.message(ChangeNameStates.waiting_for_new_name)
async def process_new_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    
    if len(new_name) < 2:
        await message.answer(
            "❌ <b>Имя должно быть не короче 2 символов.</b>\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    user_id = data.get('user_id')
    current_name = data.get('current_name')
    
    # Меняем имя в базе данных (теперь только в таблице users)
    success = db.update_user_display_name(user_id, new_name)
    
    if success:
        # Получаем обновленную позицию
        position = db.get_user_position(user_id)
        
        await message.answer(
            f"✅ <b>Имя успешно изменено!</b>\n\n"
            f"👤 Пользователь ID: {user_id}\n"
            f"📝 Было: <b>{current_name}</b>\n"
            f"📝 Стало: <b>{new_name}</b>\n"
            f"🔢 Позиция в очереди: <b>{position}</b>",
            parse_mode="HTML"
        )
        
        # Уведомляем пользователя, если это не админ
        if user_id != config.config.ADMIN_ID:
            try:
                await bot.send_message(
                    user_id,
                    f"✏️ <b>Администратор изменил ваше имя в очереди:</b>\n\n"
                    f"📝 Было: <b>{current_name}</b>\n"
                    f"📝 Стало: <b>{new_name}</b>\n"
                    f"🔢 Ваша позиция: <b>{position}</b>",
                    parse_mode="HTML"
                )
            except:
                pass  # Пользователь заблокировал бота или удалил чат
    else:
        await message.answer(
            "❌ <b>Не удалось изменить имя.</b>\n"
            "Возможно, пользователь вышел из очереди.",
            parse_mode="HTML"
        )
    
    # Возвращаем админа в меню
    await state.clear()
    await message.answer(
        "🏠 <b>Возврат в главное меню</b>",
        reply_markup=keyboards.get_admin_keyboard(),
        parse_mode="HTML"
    )

# ========== ПОСМОТРЕТЬ ОЧЕРЕДЬ ==========
@dp.message(F.text == "👀 Посмотреть очередь")
async def view_queue(message: Message):
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

    text += f"\n<b>Статус кабинета:</b> {status_map.get(status['status'], status['status'])}"

    if status.get("message"):
        text += f"\n{status['message']}"

    await message.answer(text, parse_mode="HTML")


# ========== ВСТАТЬ В ОЧЕРЕДЬ ==========
@dp.message(F.text == "📝 Встать в очередь")
async def join_queue_start(message: Message, state: FSMContext):
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
    if db.remove_from_queue(message.from_user.id):
        await message.answer("✅ <b>Вы вышли из очереди</b>", parse_mode="HTML")
    else:
        await message.answer("ℹ️ <b>Вы не были в очереди</b>", parse_mode="HTML")

# ========== СТАТУС КАБИНЕТА ==========
@dp.message(F.text == "⏰ Статус кабинета")
async def office_status(message: Message):
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
