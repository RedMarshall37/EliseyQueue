from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                          InlineKeyboardMarkup, InlineKeyboardButton)

# Основная клавиатура для пользователей
def get_user_keyboard():
    buttons = [
        [KeyboardButton(text="👀 Посмотреть очередь")],
        [KeyboardButton(text="📝 Встать в очередь")],
        [KeyboardButton(text="🔍 Мой номер в очереди")],
        [KeyboardButton(text="🚪 Выйти из очереди")],
        [KeyboardButton(text="⏰ Статус кабинета")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )

# Админ-клавиатура (обычная Reply-клавиатура)
def get_admin_keyboard():
    buttons = [
        [KeyboardButton(text="👀 Посмотреть очередь"), KeyboardButton(text="✅ Открыть кабинет")],
        [KeyboardButton(text="👤 Управление очередью"), KeyboardButton(text="❌ Закрыть кабинет")],
        [KeyboardButton(text="✏️ Изменить имя"), KeyboardButton(text="⏰ Статус кабинета")],
        [KeyboardButton(text="🗑️ Очистить очередь")],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Админ-команды"
    )

# Клавиатура управления очередью
def get_queue_management_keyboard():
    buttons = [
        [KeyboardButton(text="🎯 Показать следующего"), KeyboardButton(text="✅ Завершить прием текущего")],
        [KeyboardButton(text="✅ Завершить прием текущего"), KeyboardButton(text="❌ Отклонить следующего")],
        [KeyboardButton(text="◀️ Назад в меню"), KeyboardButton(text="📊 Статистика очереди")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Управление очередью"
    )

# Клавиатура для принятия/отклонения пользователя
def get_accept_reject_keyboard(user_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
            ]
        ]
    )

# Клавиатура для завершения приема
def get_finish_reception_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Завершить прием", callback_data="finish_reception")]
        ]
    )


# Клавиатура для отмены действия
def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
