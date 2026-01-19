import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import keyboards
import database

# Состояния для FSM
class QueueStates(StatesGroup):
    waiting_for_name = State()

# Инициализация
bot = Bot(token=config.config.BOT_TOKEN)
dp = Dispatcher()
db = database.db

# ========== ОБЩИЕ КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    is_admin = message.from_user.id == config.config.ADMIN_ID
    
    welcome_text = """
👋 *Добро пожаловать в систему очереди в кабинет Елисея!*

*Основные функции:*
• 👀 Посмотреть текущую очередь
• 📝 Встать в очередь
• 🔍 Узнать свой номер
• 🚪 Выйти из очереди
• ⏰ Проверить статус кабинета
    """
    
    await message.answer(
        welcome_text,
        reply_markup=keyboards.get_user_keyboard(is_admin),
        parse_mode="Markdown"
    )

# ========== ПОСМОТРЕТЬ ОЧЕРЕДЬ ==========
@dp.message(F.text == "👀 Посмотреть очередь", state="*")
async def view_queue(message: Message):
    queue = db.get_queue()
    status = db.get_office_status()
    
    if not queue:
        text = "📭 *Очередь пуста*\n\n"
    else:
        text = "📋 *Текущая очередь:*\n\n"
        for i, user in enumerate(queue, 1):
            text += f"{i}. {user['name']}\n"
        text += f"\n*Всего в очереди:* {len(queue)} человек(а)\n"
    
    text += f"\n*Статус кабинета:* {'✅ Открыт' if status['status'] == 'open' else '❌ Закрыт' if status['status'] == 'closed' else '⏸️ Приостановлен'}"
    if status['message']:
        text += f"\n*Комментарий:* {status['message']}"
    
    await message.answer(text, parse_mode="Markdown")

# ========== ВСТАТЬ В ОЧЕРЕДЬ ==========
@dp.message(F.text == "📝 Встать в очередь")
async def join_queue_start(message: Message, state: FSMContext):
    status = db.get_office_status()
    
    if status['status'] == 'closed':
        await message.answer(f"❌ *Кабинет закрыт!*\n{status.get('message', '')}", parse_mode="Markdown")
        return
    
    if status['status'] == 'paused':
        await message.answer(f"⏸️ *Прием приостановлен!*\n{status.get('message', '')}", parse_mode="Markdown")
        return
    
    # Проверяем, не в очереди ли уже
    position = db.get_user_position(message.from_user.id)
    if position:
        await message.answer(f"⚠️ Вы уже в очереди! Ваш номер: *{position}*", parse_mode="Markdown")
        return
    
    await message.answer("📝 *Введите ваше имя для очереди:*", parse_mode="Markdown")
    await state.set_state(QueueStates.waiting_for_name)

@dp.message(QueueStates.waiting_for_name)
async def join_queue_finish(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Имя должно быть не короче 2 символов. Попробуйте еще раз:")
        return
    
    # Добавляем в очередь
    position = db.add_to_queue(message.from_user.id, name)
    
    if position == -1:
        await message.answer("⚠️ Вы уже в очереди!")
    else:
        queue_length = len(db.get_queue())
        await message.answer(
            f"✅ *Вы добавлены в очередь!*\n\n"
            f"• Ваш номер: *{position}*\n"
            f"• Имя в очереди: *{name}*\n"
            f"• Людей перед вами: *{queue_length - 1}*",
            parse_mode="Markdown"
        )
    
    await state.clear()

# ========== МОЙ НОМЕР В ОЧЕРЕДИ ==========
@dp.message(F.text == "🔍 Мой номер в очереди")
async def my_position(message: Message):
    position = db.get_user_position(message.from_user.id)
    
    if position:
        queue = db.get_queue()
        await message.answer(
            f"🔢 *Ваш номер в очереди:* {position}\n"
            f"👥 *Людей перед вами:* {position - 1}\n"
            f"📊 *Всего в очереди:* {len(queue)}",
            parse_mode="Markdown"
        )
    else:
        await message.answer("ℹ️ *Вы не в очереди*", parse_mode="Markdown")

# ========== ВЫЙТИ ИЗ ОЧЕРЕДИ ==========
@dp.message(F.text == "🚪 Выйти из очереди", state="*")
async def leave_queue(message: Message):
    if db.remove_from_queue(message.from_user.id):
        await state.clear()
        await message.answer("✅ *Вы вышли из очереди*", parse_mode="Markdown")
    else:
        await message.answer("ℹ️ *Вы не были в очереди*", parse_mode="Markdown")

# ========== СТАТУС КАБИНЕТА ==========
@dp.message(F.text == "⏰ Статус кабинета", state="*")
async def office_status(message: Message):
    status = db.get_office_status()
    
    status_texts = {
        'open': '✅ *ОТКРЫТ*',
        'closed': '❌ *ЗАКРЫТ*',
        'paused': '⏸️ *ПРИОСТАНОВЛЕН*'
    }
    
    text = f"🚪 *Статус кабинета:* {status_texts.get(status['status'], status['status'])}\n"
    
    if status['message']:
        text += f"\n*Комментарий:* {status['message']}\n"
    
    text += f"\n*Обновлено:* {status['updated_at'][:16].replace('T', ' ')}"
    
    await message.answer(text, parse_mode="Markdown")

# ========== АДМИН-ПАНЕЛЬ ==========
@dp.message(F.text == "⚙️ Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id != config.config.ADMIN_ID:
        await message.answer("❌ Доступ запрещен!")
        return
    
    queue = db.get_queue()
    status = db.get_office_status()
    
    text = f"⚙️ *Админ-панель*\n\n"
    text += f"Статус кабинета: *{'✅ Открыт' if status['status'] == 'open' else '❌ Закрыт' if status['status'] == 'closed' else '⏸️ Приостановлен'}*\n"
    text += f"Людей в очереди: *{len(queue)}*\n\n"
    
    if queue:
        text += "Следующие 5 человек:\n"
        for i, user in enumerate(queue[:5], 1):
            text += f"{i}. {user['name']}\n"
    
    await message.answer(text, reply_markup=keyboards.get_admin_keyboard(), parse_mode="Markdown")

# ========== АДМИН-КОМАНДЫ (callback) ==========
@dp.callback_query(F.data.startswith("admin_"))
async def admin_actions(callback: CallbackQuery):
    if callback.from_user.id != config.config.ADMIN_ID:
        await callback.answer("Доступ запрещен!", show_alert=True)
        return
    
    action = callback.data
    
    if action == "admin_open":
        db.set_office_status("open", "Кабинет открыт")
        await callback.message.edit_text(
            "✅ *Кабинет открыт!*\n\nОчередь активирована.",
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode="Markdown"
        )
        await notify_all("ℹ️ *Кабинет открыт!* Можно вставать в очередь.")
    
    elif action == "admin_close":
        db.set_office_status("closed", "Кабинет закрыт")
        await callback.message.edit_text(
            "❌ *Кабинет закрыт!*\n\nОчередь отключена.",
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode="Markdown"
        )
        await notify_all("⚠️ *Кабинет закрыт!* Прием временно не ведется.")
    
    elif action == "admin_pause":
        db.set_office_status("paused", "Прием приостановлен")
        await callback.message.edit_text(
            "⏸️ *Прием приостановлен!*\n\nОчередь заморожена.",
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode="Markdown"
        )
        await notify_all("⏸️ *Прием приостановлен!* Ожидайте возобновления.")
    
    elif action == "admin_next":
        next_user = db.get_next_user()
        if next_user:
            await callback.message.edit_text(
                f"✅ *Пропущен:* {next_user['name']}\n\n"
                f"ID: {next_user['user_id']}\n"
                f"Встал в очередь: {next_user['joined_at'][:16].replace('T', ' ')}",
                reply_markup=keyboards.get_admin_keyboard(),
                parse_mode="Markdown"
            )
            # Уведомляем пользователя
            try:
                await bot.send_message(
                    next_user['user_id'],
                    "🎉 *Ваша очередь подошла!* Проходите в кабинет.",
                    parse_mode="Markdown"
                )
            except:
                pass
            
            # Уведомляем следующего в очереди
            queue = db.get_queue()
            if queue:
                try:
                    next_in_line = queue[0]
                    await bot.send_message(
                        next_in_line['user_id'],
                        "🔔 *Вы следующий в очереди!* Будьте готовы.",
                        parse_mode="Markdown"
                    )
                except:
                    pass
        else:
            await callback.answer("Очередь пуста!", show_alert=True)
    
    elif action == "admin_clear":
        db.clear_queue()
        await callback.message.edit_text(
            "🗑️ *Очередь очищена!*\n\nВсе пользователи удалены.",
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode="Markdown"
        )
        await notify_all("🗑️ *Очередь была очищена администратором.*")
    
    elif action == "admin_stats":
        queue = db.get_queue()
        status = db.get_office_status()
        
        text = "📊 *Статистика*\n\n"
        text += f"• Статус: *{status['status']}*\n"
        text += f"• В очереди: *{len(queue)} человек*\n"
        text += f"• Обновлено: *{status['updated_at'][:16].replace('T', ' ')}*\n\n"
        
        if queue:
            text += "Текущая очередь:\n"
            for i, user in enumerate(queue[:10], 1):
                text += f"{i}. {user['name']}\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode="Markdown"
        )
    
    elif action == "admin_view":
        queue = db.get_queue()
        
        if not queue:
            text = "📭 *Очередь пуста*"
        else:
            text = "👥 *Текущая очередь:*\n\n"
            for i, user in enumerate(queue, 1):
                text += f"{i}. {user['name']}\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode="Markdown"
        )
    
    elif action == "admin_back":
        await callback.message.delete()
        await callback.message.answer(
            "Возврат в главное меню:",
            reply_markup=keyboards.get_user_keyboard(True)
        )
    
    await callback.answer()

# ========== УВЕДОМЛЕНИЕ ВСЕХ ==========
async def notify_all(text: str):
    """Уведомить всех пользователей в очереди"""
    queue = db.get_queue()
    for user in queue:
        try:
            await bot.send_message(user['user_id'], text, parse_mode="Markdown")
        except:
            continue

# ========== ЗАПУСК БОТА ==========
async def main():
    print("🤖 Бот 'Очередь в кабинет Елисея' запущен...")
    print(f"👑 Админ ID: {config.config.ADMIN_ID}")
    
    # Инициализация статуса
    if not db.redis.exists("office:status"):
        db.set_office_status("open")
    
    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())

