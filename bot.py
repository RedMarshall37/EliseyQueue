import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

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
            "• 🗑️ Очистить очередь\n"
            "• ✏️ Изменить имя пользователя\n"
            "• 👤 Управление очередью"
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

# Перезагрузка сообщения очереди
async def refresh_queue_management(chat_id: int, message_id: int = None):
    """Обновить сообщение с управлением очередью"""
    queue = db.get_queue()
    
    if queue:
        # Получаем первого пользователя в очереди
        first_user = queue[0]
        first_user_name = first_user['name']
        
        text = f"👤 <b>Управление очередью</b>\n\n"
        text += f"<b>Первый в очереди:</b>\n"
        text += f"✅ <b>{first_user_name}</b>\n"
        text += f"🆔 ID: {first_user['user_id']}\n"
        text += f"⏰ В очереди с: {first_user['joined_at'][11:16]}\n\n"
        
        if len(queue) > 1:
            text += f"<b>Ожидают:</b> {len(queue) - 1} человек(а)\n"
            text += f"<b>Следующий:</b> {queue[1]['name']}\n"
        
        keyboard = keyboards.get_queue_management_keyboard(first_user_name)
    else:
        text = "👤 <b>Управление очередью</b>\n\n📭 <i>Очередь пуста</i>"
        keyboard = keyboards.get_queue_management_keyboard()
    
    # Если есть message_id, редактируем сообщение
    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except:
            # Если не удалось редактировать (сообщение слишком старое), отправляем новое
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    else:
        # Иначе отправляем новое сообщение
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

# ========== КНОПКА УПРАВЛЕНИЯ ОЧЕРЕДЬЮ ==========
@dp.message(F.text == "👤 Управление очередью")
async def manage_queue(message: Message):
    if message.from_user.id != config.config.ADMIN_ID:
        await message.answer("❌ <b>Доступ запрещен!</b>", parse_mode="HTML")
        return
    
    queue = db.get_queue()
    
    if queue:
        # Получаем первого пользователя в очереди
        first_user = queue[0]
        first_user_name = first_user['name']
        
        text = f"👤 <b>Управление очередью</b>\n\n"
        text += f"<b>Первый в очереди:</b>\n"
        text += f"✅ <b>{first_user_name}</b>\n"
        text += f"⏰ В очереди с: {first_user['joined_at'][11:16]}\n\n"
        
        if len(queue) > 1:
            text += f"<b>Ожидают:</b> {len(queue) - 1} человек(а)\n"
            text += f"<b>Следующий:</b> {queue[1]['name']}\n"
        
        await message.answer(
            text,
            reply_markup=keyboards.get_queue_management_keyboard(first_user_name),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "👤 <b>Управление очередью</b>\n\n"
            "📭 <i>Очередь пуста</i>",
            reply_markup=keyboards.get_queue_management_keyboard(),
            parse_mode="HTML"
        )


# ========== КНОПКА ПРИНЯТИЯ ПОЛЬЗОВАТЕЛЯ ==========
@dp.message(F.text.startswith("✅ Принять "))
async def accept_user(message: Message):
    if message.from_user.id != config.config.ADMIN_ID:
        return
    
    # Извлекаем имя пользователя из текста кнопки
    user_name = message.text.replace("✅ Принять ", "").strip()
    
    # Находим пользователя в очереди
    queue = db.get_queue()
    if not queue:
        await message.answer("📭 <b>Очередь пуста!</b>", parse_mode="HTML")
        return
    
    first_user = queue[0]
    
    # Проверяем, что это действительно первый пользователь
    if first_user['name'] != user_name:
        # Ищем пользователя по имени
        found_user = None
        for user in queue:
            if user['name'] == user_name:
                found_user = user
                break
        
        if not found_user:
            await message.answer(
                f"❌ <b>Пользователь {user_name} не найден в очереди!</b>",
                parse_mode="HTML"
            )
            return
        
        # Если это не первый пользователь, просто удаляем его
        db.remove_from_queue(found_user['user_id'])
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                found_user['user_id'],
                f"❌ <b>Вы были удалены из очереди администратором</b>\n\n"
                f"Причина: пропущен в очереди.\n"
                f"Попробуйте встать в очередь позже.",
                parse_mode="HTML"
            )
        except:
            pass
        
        # Отправляем сообщение об удалении
        response = await message.answer(
            f"❌ <b>Пользователь удален из очереди:</b>\n\n"
            f"👤 {user_name}",
            parse_mode="HTML"
        )
        
        # Обновляем управление очередью после паузы
        await asyncio.sleep(1)
        await refresh_queue_management(message.chat.id, response.message_id)
        return
    
    # Если это первый пользователь - принимаем его
    user_id = first_user['user_id']
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            user_id,
            f"✅ <b>Елисей готов вас принять!</b>\n\n"
            f"Подойдите к кабинету.\n"
            f"Ваше имя в очереди: <b>{user_name}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить пользователя {user_id}: {e}")
    
    # Удаляем пользователя из очереди
    db.remove_from_queue(user_id)
    
    # Отправляем сообщение о принятии
    response = await message.answer(
        f"✅ <b>Пользователь принят и удален из очереди!</b>\n\n"
        f"👤 {user_name}\n"
        f"<i>Пользователь получил уведомление о приеме.</i>",
        parse_mode="HTML"
    )
    
    # Обновляем управление очередью после паузы
    await asyncio.sleep(1)
    await refresh_queue_management(message.chat.id, response.message_id)



# ========== КНОПКА ОТКЛОНЕНИЯ ПОЛЬЗОВАТЕЛЯ ==========
@dp.message(F.text.startswith("❌ Отклонить "))
async def reject_user(message: Message):
    if message.from_user.id != config.config.ADMIN_ID:
        return
    
    # Извлекаем имя пользователя из текста кнопки
    user_name = message.text.replace("❌ Отклонить ", "").strip()
    
    # Находим пользователя в очереди
    queue = db.get_queue()
    if not queue:
        await message.answer("📭 <b>Очередь пуста!</b>", parse_mode="HTML")
        return
    
    # Ищем пользователя по имени
    found_user = None
    user_position = 0
    
    for i, user in enumerate(queue):
        if user['name'] == user_name:
            found_user = user
            user_position = i + 1
            break
    
    if not found_user:
        await message.answer(
            f"❌ <b>Пользователь {user_name} не найден в очереди!</b>",
            parse_mode="HTML"
        )
        return
    
    user_id = found_user['user_id']
    
    # Удаляем пользователя из очереди
    db.remove_from_queue(user_id)
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            user_id,
            f"❌ <b>Елисей пока не готов вас принять</b>\n\n"
            f"Попробуйте встать в очередь позже.\n"
            f"Ваше имя в очереди: <b>{user_name}</b>\n"
            f"Ваша позиция была: {user_position}",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить пользователя {user_id}: {e}")
    
    await message.answer(
        f"❌ <b>Пользователь отклонен и удален из очереди:</b>\n\n"
        f"👤 {user_name}\n"
        f"📊 Позиция была: {user_position}\n\n"
        f"<i>Пользователь получил уведомление.</i>",
        parse_mode="HTML"
    )
    
    # Показываем следующего пользователя, если есть
    queue = db.get_queue()
    if queue:
        next_user = queue[0]
        await asyncio.sleep(1)
        await message.answer(
            f"🎯 <b>Следующий в очереди:</b>\n\n"
            f"👤 <b>{next_user['name']}</b>\n"
            f"⏰ В очереди с: {next_user['joined_at'][11:16]}\n\n"
            f"<i>Для управления нажмите '👤 Управление очередью'</i>",
            parse_mode="HTML"
        )


# ========== КНОПКА СТАТИСТИКА ОЧЕРЕДИ ==========
@dp.message(F.text == "📊 Статистика очереди")
async def queue_statistics(message: Message):
    if message.from_user.id != config.config.ADMIN_ID:
        return
    
    queue = db.get_queue()
    
    text = "<b>📊 Статистика очереди</b>\n\n"
    
    text += f"<b>Всего в очереди:</b> {len(queue)} человек(а)\n"
    
    if queue:
        now = datetime.now()
        
        # Среднее время ожидания
        total_waiting = 0
        
        for user in queue:
            joined_at = datetime.fromisoformat(user['joined_at'])
            waiting_time = (now - joined_at).seconds // 60  # в минутах
            total_waiting += waiting_time
        
        if len(queue) > 0:
            avg_waiting = total_waiting // len(queue)
            text += f"<b>Среднее время ожидания:</b> {avg_waiting} мин.\n"
        
        # Самый долго ждущий (первый в очереди)
        first_user = queue[0]
        first_joined = datetime.fromisoformat(first_user['joined_at'])
        longest_wait = (now - first_joined).seconds // 60
        text += f"<b>Дольше всех ждет:</b> {first_user['name']} ({longest_wait} мин.)\n"
        
        # Если есть второй в очереди
        if len(queue) > 1:
            second_user = queue[1]
            second_joined = datetime.fromisoformat(second_user['joined_at'])
            second_wait = (now - second_joined).seconds // 60
            text += f"<b>Следующий:</b> {second_user['name']} ({second_wait} мин.)\n"
        
        # Общее время ожидания всех
        text += f"<b>Общее время ожидания:</b> {total_waiting} мин.\n"
    
    # Отправляем статистику в отдельном сообщении
    await message.answer(text, parse_mode="HTML")



# ========== УВЕДОМЛЕНИЕ АДМИНУ О НОВОМ ПОЛЬЗОВАТЕЛЕ ==========
@dp.message(F.text == "📝 Встать в очередь")
async def join_queue_start(message: Message):
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

    position = db.get_user_position(message.from_user.id)

    if position:
        await message.answer(
            f"✅ <b>Вы добавлены в очередь!</b>\n\n"
            f"• Ваш номер: <b>{position}</b>\n"
            f"• Имя в очереди: <b>{user_name}</b>\n"
            f"• Людей перед вами: <b>{position - 1}</b>",
            parse_mode="HTML"
        )
        
        # УВЕДОМЛЕНИЕ АДМИНУ О НОВОМ ПОЛЬЗОВАТЕЛЕ
        if config.config.ADMIN_ID:
            try:
                queue = db.get_queue()
                total_in_queue = len(queue)
                
                # Получаем список первых 3 в очереди для информации
                first_three = queue[:3]
                queue_info = ""
                for i, user in enumerate(first_three, 1):
                    queue_info += f"{i}. {user['name']}\n"
                
                if total_in_queue > 3:
                    queue_info += f"... и еще {total_in_queue - 3}\n"
                
                await bot.send_message(
                    config.config.ADMIN_ID,
                    f"👤 <b>Новый пользователь в очереди!</b>\n\n"
                    f"• Имя: <b>{user_name}</b>\n"
                    f"• Позиция в очереди: <b>{position}</b>\n"
                    f"• Всего в очереди: <b>{total_in_queue}</b>\n\n"
                    f"<b>Текущая очередь:</b>\n{queue_info}\n",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление админу: {e}")
    else:
        await message.answer("❌ <b>Произошла ошибка при добавлении в очередь</b>", parse_mode="HTML")


# ========== КНОПКА НАЗАД В МЕНЮ ==========
async def back_to_menu(message: Message):
    if message.from_user.id == config.config.ADMIN_ID:
        await message.answer(
            "🏠 <b>Главное меню админа</b>",
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "🏠 <b>Главное меню</b>",
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
    
    # Меняем имя в базе данных
    success = db.update_user_display_name(user_id, new_name)
    
    if success:
        # Получаем обновленную позицию
        position = db.get_user_position(user_id)
        
        response = await message.answer(
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
                pass
        
        # Если пользователь был первым в очереди, обновляем управление очередью
        queue = db.get_queue()
        if queue and queue[0]['user_id'] == user_id:
            await asyncio.sleep(1)
            await refresh_queue_management(message.chat.id, response.message_id)
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
