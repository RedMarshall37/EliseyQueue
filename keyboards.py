from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                          InlineKeyboardMarkup, InlineKeyboardButton)

# Основная клавиатура для пользователей
def get_user_keyboard():
    buttons = [
        [KeyboardButton(text="👀 Посмотреть очередь"), KeyboardButton(text="🔍 Мой номер в очереди")],
        [KeyboardButton(text="🚪 Выйти из очереди"), KeyboardButton(text="📝 Встать в очередь")],
        [KeyboardButton(text="⏰ Статус кабинета")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )

# Админ-клавиатура
def get_admin_keyboard():
    buttons = [
        [KeyboardButton(text="❌ Закрыть кабинет"), KeyboardButton(text="✅ Открыть кабинет")],
        [KeyboardButton(text="👤 Управление очередью"), KeyboardButton(text="👀 Посмотреть очередь")],
        [KeyboardButton(text="✏️ Изменить имя"), KeyboardButton(text="⏰ Статус кабинета")],
        [KeyboardButton(text="🗑️ Очистить очередь")],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Админ-команды"
    )

# Клавиатура управления очередью (динамическая)
def get_queue_management_keyboard(first_user_name: str = None):
    buttons = []
    
    if first_user_name:
        # Если есть пользователь в очереди
        buttons = [
            [KeyboardButton(text=f"❌ Отклонить {first_user_name}"), KeyboardButton(text=f"✅ Принять {first_user_name}")],
            KeyboardButton(text="◀️ Назад в меню"), [KeyboardButton(text="📊 Статистика очереди")],
        ]
    else:
        # Если очередь пуста
        buttons = [
            [KeyboardButton(text="📊 Статистика очереди")],
            [KeyboardButton(text="◀️ Назад в меню")]
        ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Управление очередью"
    )

# Клавиатура для отмены действия
def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
