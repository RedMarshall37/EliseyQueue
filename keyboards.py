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

# Админ-клавиатура
def get_admin_keyboard():
    buttons = [
        [InlineKeyboardButton(text="✅ Открыть кабинет", callback_data="admin_open")],
        [InlineKeyboardButton(text="❌ Закрыть кабинет", callback_data="admin_close")],
        [InlineKeyboardButton(text="⏸️ Приостановить", callback_data="admin_pause")],
        [InlineKeyboardButton(text="➡️ Пропустить следующего", callback_data="admin_next")],
        [InlineKeyboardButton(text="🗑️ Очистить очередь", callback_data="admin_clear")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Текущая очередь", callback_data="admin_view")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=[buttons[i:i+2] for i in range(0, len(buttons), 2)])