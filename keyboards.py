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
        [KeyboardButton(text="📝 Встать в очередь"), KeyboardButton(text="❌ Закрыть кабинет")],
        [KeyboardButton(text="✏️ Изменить имя"), KeyboardButton(text="⏰ Статус кабинета")],
        [KeyboardButton(text="🚪 Выйти из очереди"), KeyboardButton(text="🗑️ Очистить очередь")],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Админ-команды"
    )

# Клавиатура для отмены действия
def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
