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
        [KeyboardButton(text="✅ Открыть кабинет"), KeyboardButton(text="✅ Открыть кабинет")],
        [KeyboardButton(text="❌ Закрыть кабинет"), KeyboardButton(text="❌ Закрыть кабинет")],
        [KeyboardButton(text="⏸️ Приостановить"), KeyboardButton(text="⏸️ Приостановить")],
        [KeyboardButton(text="🗑️ Очистить очередь"), KeyboardButton(text="🗑️ Очистить очередь")],
        [KeyboardButton(text="◀️ Назад в меню"), KeyboardButton(text="◀️ Назад в меню")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Админ-команды"
    )

