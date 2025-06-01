import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token='7977800577:AAEMUa3rXThdYJv1VpLrsr-5HPaQQhgX49A')
dp = Dispatcher(storage=MemoryStorage())

# Available currency pairs
AVAILABLE_CURRENCIES = ['USD', 'EUR', 'RUB', 'KZT']

# Cache for exchange rates
exchange_rates_cache = {}
last_update_time = None

# States
class ConversionStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_target_currency = State()

# User data structure to store selected currencies
user_data = {}

def get_currency_keyboard(exclude_currency=None):
    buttons = []
    row = []
    for currency in AVAILABLE_CURRENCIES:
        if currency != exclude_currency:
            row.append(InlineKeyboardButton(
                text=currency,
                callback_data=f"currency_{currency}"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row:  # Add any remaining buttons
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command('start'))
async def cmd_start(message: Message):
    keyboard = get_currency_keyboard()
    await message.answer(
        "👋 Привет! Я бот для конвертации валют.\n\n"
        "Выберите базовую валюту (ИЗ какой валюты конвертировать):",
        reply_markup=keyboard
    )

@dp.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer(
        "🔍 Как пользоваться ботом:\n\n"
        "1. Нажмите /start чтобы начать конвертацию\n"
        "2. Выберите базовую валюту (ИЗ какой конвертировать)\n"
        "3. Введите сумму\n"
        "4. Выберите целевую валюту (В какую конвертировать)\n"
        "5. Получите результат\n\n"
        f"Поддерживаемые валюты: {', '.join(AVAILABLE_CURRENCIES)}"
    )

@dp.callback_query(lambda c: c.data.startswith('currency_'))
async def process_currency_selection(callback: CallbackQuery, state: FSMContext):
    selected_currency = callback.data.split('_')[1]
    user_id = callback.from_user.id
    
    if user_id not in user_data:
        # First currency selection (base currency)
        user_data[user_id] = {'base_currency': selected_currency}
        await callback.message.edit_text(
            f"Выбрана базовая валюта: {selected_currency}\n"
            f"Теперь введите сумму для конвертации:"
        )
        await state.set_state(ConversionStates.waiting_for_amount)
    else:
        # Target currency selection
        user_data[user_id]['target_currency'] = selected_currency
        amount = user_data[user_id]['amount']
        base_currency = user_data[user_id]['base_currency']
        
        # Get exchange rate and calculate
        try:
            rate = await get_exchange_rate(base_currency, selected_currency)
            result = amount * rate

            await callback.message.edit_text(
                f"💰 Результат конвертации:\n\n"
                f"{amount:,.2f} {base_currency} = {result:,.2f} {selected_currency}\n\n"
                f"Курс: 1 {base_currency} = {rate:,.4f} {selected_currency}\n\n"
                "Нажмите /start для новой конвертации"
            )
            
            # Clear user data
            user_data.pop(user_id)
            await state.clear()
            
        except Exception as e:
            logging.error(f"Error in conversion: {e}")
            await callback.message.edit_text(
                "❌ Произошла ошибка при конвертации. Нажмите /start чтобы попробовать снова."
            )
            user_data.pop(user_id)
            await state.clear()

@dp.message(ConversionStates.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        user_id = message.from_user.id
        user_data[user_id]['amount'] = amount
        base_currency = user_data[user_id]['base_currency']
        
        keyboard = get_currency_keyboard(exclude_currency=base_currency)
        await message.answer(
            f"Сумма: {amount:,.2f} {base_currency}\n"
            "Выберите целевую валюту (В какую валюту конвертировать):",
            reply_markup=keyboard
        )
        await state.set_state(ConversionStates.waiting_for_target_currency)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число.\n"
            "Используйте точку или запятую для разделения десятичных знаков."
        )

async def update_exchange_rates():
    """Обновляет кэш курсов валют из API ЦБ РФ"""
    global exchange_rates_cache, last_update_time
    
    try:
        url = "https://www.cbr.ru/scripts/XML_daily.asp"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content = await response.text()
                
        root = ET.fromstring(content)
        
        # Обновляем кэш
        exchange_rates_cache = {'RUB': 1.0}  # Базовая валюта - рубль
        
        for valute in root.findall('Valute'):
            char_code = valute.find('CharCode').text
            if char_code in AVAILABLE_CURRENCIES:
                nominal = float(valute.find('Nominal').text.replace(',', '.'))
                value = float(valute.find('Value').text.replace(',', '.'))
                rate = value / nominal
                exchange_rates_cache[char_code] = rate
        
        last_update_time = datetime.now()
        logging.info("Exchange rates updated successfully")
        
    except Exception as e:
        logging.error(f"Error updating exchange rates: {e}")
        if not exchange_rates_cache:  # If cache is empty, raise the error
            raise

async def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Получает курс конвертации между двумя валютами"""
    # Проверяем, нужно ли обновить кэш
    if last_update_time is None or (datetime.now() - last_update_time).seconds > 3600:
        await update_exchange_rates()
    
    if from_currency == to_currency:
        return 1.0
    
    if from_currency == 'RUB':
        return 1 / exchange_rates_cache[to_currency]
    elif to_currency == 'RUB':
        return exchange_rates_cache[from_currency]
    else:
        # Кросс-курс через рубль
        rub_to_from = exchange_rates_cache[from_currency]
        rub_to_to = exchange_rates_cache[to_currency]
        return rub_to_from / rub_to_to

@dp.message()
async def handle_other_messages(message: Message):
    await message.answer(
        "Нажмите /start чтобы начать конвертацию или /help для получения справки."
    )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main()) 