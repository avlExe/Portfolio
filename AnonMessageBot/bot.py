import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest
from config import (
    BOT_TOKEN, ADMIN_IDS, WELCOME_MESSAGE,
    SEND_MESSAGE_BTN, PREMIUM_INFO_BTN, MODERATOR_INFO_BTN, RULES_BTN,
    SEND_BTN, CANCEL_BTN, messages
)
from states import MessageStates

# Настраиваем расширенное логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Словарь для хранения информации о пользователях
# Храним по всем возможным ключам для надежности
users_db = {}

# Добавим константы для кнопок
CANCEL_INPUT_BTN = "❌ Отменить ввод"

def register_user(user: types.User, chat_id: int):
    """Регистрация пользователя во всех необходимых форматах"""
    user_data = {
        'chat_id': chat_id,
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Сохраняем по ID (всегда уникален)
    users_db[str(user.id)] = user_data
    
    # Сохраняем по username в разных форматах, если он есть
    if user.username:
        users_db[user.username.lower()] = user_data
        users_db[user.username] = user_data
        users_db[f"@{user.username}"] = user_data
        users_db[f"@{user.username.lower()}"] = user_data

def find_user(identifier: str) -> dict | None:
    """Поиск пользователя по любому идентификатору"""
    # Очищаем идентификатор
    clean_id = identifier.lstrip('@').strip()
    
    # Пробуем найти напрямую
    if clean_id in users_db:
        return users_db[clean_id]
    
    # Пробуем найти в нижнем регистре
    if clean_id.lower() in users_db:
        return users_db[clean_id.lower()]
    
    # Пробуем найти с @
    if f"@{clean_id}" in users_db:
        return users_db[f"@{clean_id}"]
    
    # Пробуем найти с @ в нижнем регистре
    if f"@{clean_id.lower()}" in users_db:
        return users_db[f"@{clean_id.lower()}"]
    
    # Если это ID
    if clean_id.isdigit():
        return users_db.get(clean_id)
    
    return None

# Создаем основную клавиатуру
def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SEND_MESSAGE_BTN)],
            [KeyboardButton(text=PREMIUM_INFO_BTN)],
            [KeyboardButton(text=MODERATOR_INFO_BTN)],
            [KeyboardButton(text=RULES_BTN)]
        ],
        resize_keyboard=True
    )
    return keyboard

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    chat_id = message.chat.id
    
    # Регистрируем пользователя
    register_user(user, chat_id)
    
    logger.info(f"User started bot - ID: {user.id}, Username: {user.username}, ChatID: {chat_id}")
    logger.info(f"Current users in database: {list(users_db.keys())}")
    
    await message.answer(
        text=WELCOME_MESSAGE,
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопки "Отправить сообщение"
@dp.message(F.text == SEND_MESSAGE_BTN)
async def send_message_handler(message: types.Message, state: FSMContext):
    await state.set_state(MessageStates.waiting_for_username)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_INPUT_BTN)]],
        resize_keyboard=True
    )
    await message.answer(
        "Кому вы хотели отправить анонимное сообщение?\n"
        "Введите @username получателя\n\n"
        "❗ Важно: получатель должен предварительно запустить бота, "
        "иначе отправка сообщения будет невозможна",
        reply_markup=keyboard
    )

# Обработчик отмены ввода
@dp.message(F.text == CANCEL_INPUT_BTN)
async def cancel_input_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer(
            "Ввод отменен. Выберите действие:",
            reply_markup=get_main_keyboard()
        )

# Обработчик ввода username получателя
@dp.message(MessageStates.waiting_for_username)
async def process_username(message: types.Message, state: FSMContext):
    if message.text == CANCEL_INPUT_BTN:
        await state.clear()
        await message.answer(
            "Ввод отменен. Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return

    username = message.text.strip()
    logger.info(f"Processing username input: {username}")
    
    if not username.startswith("@"):
        await message.answer(
            "❌ Пожалуйста, введите корректное имя пользователя, начинающееся с @\n"
            "Например: @username",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=CANCEL_INPUT_BTN)]],
                resize_keyboard=True
            )
        )
        return
    
    # Ищем пользователя
    user_data = find_user(username)
    logger.info(f"Search results for {username}: {user_data}")
    
    if user_data:
        await state.update_data(recipient_username=username, recipient_chat_id=user_data['chat_id'])
        await state.set_state(MessageStates.waiting_for_title)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=CANCEL_INPUT_BTN)]],
            resize_keyboard=True
        )
        await message.answer("Введите заголовок сообщения", reply_markup=keyboard)
    else:
        bot_username = (await bot.me()).username
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=CANCEL_INPUT_BTN)]],
            resize_keyboard=True
        )
        await message.answer(
            f"❌ Пользователь {username} не найден!\n\n"
            f"Для отправки сообщения получатель должен:\n"
            f"1. Найти бота: @{bot_username}\n"
            f"2. Запустить бота командой /start\n"
            f"3. После этого повторите отправку\n\n"
            f"Можете переслать получателю это сообщение:",
            reply_markup=keyboard
        )
        # Отправляем инструкцию для пересылки
        await message.answer(
            f"👋 Привет! Чтобы получить анонимное сообщение, нужно:\n"
            f"1. Перейти к боту @{bot_username}\n"
            f"2. Нажать кнопку ЗАПУСТИТЬ или отправить команду /start"
        )

# Обработчик ввода заголовка
@dp.message(MessageStates.waiting_for_title)
async def process_title(message: types.Message, state: FSMContext):
    if message.text == CANCEL_INPUT_BTN:
        await state.clear()
        await message.answer(
            "Ввод отменен. Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return

    logger.info(f"Processing title input: {message.text}")
    await state.update_data(message_title=message.text)
    await state.set_state(MessageStates.waiting_for_message)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_INPUT_BTN)]],
        resize_keyboard=True
    )
    await message.answer("Введите текст сообщения", reply_markup=keyboard)

# Обработчик ввода текста сообщения
@dp.message(MessageStates.waiting_for_message)
async def process_message(message: types.Message, state: FSMContext):
    if message.text == CANCEL_INPUT_BTN:
        await state.clear()
        await message.answer(
            "Ввод отменен. Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return

    logger.info(f"Processing message input, length: {len(message.text)}")
    user_data = await state.get_data()
    await state.update_data(message_text=message.text)
    
    preview = f"""
📧 Кому: {user_data['recipient_username']}
📑 Заголовок: {user_data['message_title']}
💬 Сообщение: {message.text}
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SEND_BTN), KeyboardButton(text=CANCEL_BTN)]
        ],
        resize_keyboard=True
    )
    
    await state.set_state(MessageStates.waiting_for_confirmation)
    await message.answer(f"Проверьте сообщение:\n{preview}", reply_markup=keyboard)

# Обработчик подтверждения отправки
@dp.message(MessageStates.waiting_for_confirmation, F.text.in_([SEND_BTN, CANCEL_BTN]))
async def process_confirmation(message: types.Message, state: FSMContext):
    logger.info(f"Processing confirmation: {message.text}")
    
    if message.text == SEND_BTN:
        user_data = await state.get_data()
        logger.info(f"Sending message with data: {user_data}")
        
        try:
            # Формируем сообщение
            message_text = f"""
📨 Вам пришло анонимное сообщение!

📑 Заголовок: {user_data['message_title']}
💬 Сообщение: {user_data['message_text']}
📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Отправить анонимное сообщение: @{(await bot.me()).username}"""

            # Отправляем сообщение
            await bot.send_message(user_data['recipient_chat_id'], message_text)
            logger.info(f"Message sent successfully to chat_id: {user_data['recipient_chat_id']}")
            
            # Уведомляем отправителя
            await message.answer("✅ Сообщение успешно доставлено!", reply_markup=get_main_keyboard())
            
            # Уведомляем админов
            if ADMIN_IDS:
                admin_notification = f"""
📧 Новое анонимное сообщение
👤 Отправитель: {message.from_user.id}
📨 Получатель: {user_data['recipient_username']}
📑 Заголовок: {user_data['message_title']}
"""
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, admin_notification)
                    except Exception as e:
                        logger.error(f"Failed to notify admin {admin_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            error_msg = str(e).lower()
            
            if "blocked by user" in error_msg:
                await message.answer(
                    "❌ Пользователь заблокировал бота. Сообщение не может быть доставлено.",
                    reply_markup=get_main_keyboard()
                )
            else:
                await message.answer(
                    f"❌ Ошибка при отправке сообщения: {str(e)}",
                    reply_markup=get_main_keyboard()
                )
    else:
        await message.answer("Отправка сообщения отменена", reply_markup=get_main_keyboard())
    
    await state.clear()

# Обработчик кнопки "Подробнее о Premium"
@dp.message(F.text == PREMIUM_INFO_BTN)
async def premium_info_handler(message: types.Message):
    await message.answer(messages.premium_info)

# Обработчик кнопки "Подробнее о работе модератора"
@dp.message(F.text == MODERATOR_INFO_BTN)
async def moderator_info_handler(message: types.Message):
    await message.answer(messages.moderator_unavailable)

# Обработчик кнопки "Правила"
@dp.message(F.text == RULES_BTN)
async def rules_handler(message: types.Message):
    await message.answer(messages.rules)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 