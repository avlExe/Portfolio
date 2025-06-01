from typing import List
from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

@dataclass
class BotConfig:
    token: str
    admin_ids: List[int]

@dataclass
class Messages:
    welcome: str = "Привет! 👋 Этот анонимный бот поможет тебе конфиденциально отправить сообщение пользователю🤔"
    rules: str = """📜 Правила использования бота:
1. Запрещено отправлять спам
2. Запрещено отправлять оскорбления
3. Запрещено отправлять рекламу
4. Запрещено отправлять 18+ контент
5. Нарушение правил приведет к блокировке"""
    premium_info: str = """💎 Premium функции:
- Возможность отправлять медиафайлы
- Отложенная отправка сообщений
- Расширенная статистика
- Приоритетная поддержка"""
    moderator_unavailable: str = "Сейчас нам не требуются модераторы❌"

@dataclass
class Buttons:
    send_message: str = "📧Отправить сообщение"
    premium_info: str = "💎Подробние о Premium-функции (Акция)"
    moderator_info: str = "😊Подробнее о работе модератора"
    rules: str = "🟥Правила"
    send: str = "✅ Отправить"
    cancel: str = "❌ Отменить"

# Создаем конфигурацию бота
def load_config() -> BotConfig:
    token = getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN не установлен в .env файле")
    
    # Получаем список админов из .env
    admin_ids_str = getenv("ADMIN_IDS", "")
    admin_ids = [int(admin_id.strip()) for admin_id in admin_ids_str.split(",") if admin_id.strip()]
    
    return BotConfig(
        token=token,
        admin_ids=admin_ids
    )

# Инициализируем конфигурацию
config = load_config()
messages = Messages()
buttons = Buttons()

# Экспортируем все необходимые переменные
BOT_TOKEN = config.token
ADMIN_IDS = config.admin_ids
WELCOME_MESSAGE = messages.welcome
SEND_MESSAGE_BTN = buttons.send_message
PREMIUM_INFO_BTN = buttons.premium_info
MODERATOR_INFO_BTN = buttons.moderator_info
RULES_BTN = buttons.rules
SEND_BTN = buttons.send
CANCEL_BTN = buttons.cancel 