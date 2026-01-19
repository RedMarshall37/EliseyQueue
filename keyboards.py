from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                          InlineKeyboardMarkup, InlineKeyboardButton)

# Основная клавиатура для пользователей
def get_user_keyboard(is_admin: bool = False):
    buttons = [
        [KeyboardButton(text="👀 Посмотреть очередь")],
        [KeyboardButton(text="📝 Встать в очередь")],
        [KeyboardButton(text="🔍 Мой номер в очереди")],
        [KeyboardButton(text="🚪 Выйти из очереди")],
        [KeyboardButton(text="⏰ Статус кабинета")]
    ]
    
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Админ-панель")])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )

# Админ-клавиатура (обычная Reply-клавиатура)
def get_admin_keyboard():
    buttons = [
        [KeyboardButton(text="✅ Открыть кабинет"), KeyboardButton(text="❌ Закрыть кабинет")],
        [KeyboardButton(text="⏸️ Приостановить"), KeyboardButton(text="➡️ Пропустить следующего")],
        [KeyboardButton(text="🗑️ Очистить очередь"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="👥 Показать очередь"), KeyboardButton(text="◀️ Назад в меню")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Админ-команды"
    )
