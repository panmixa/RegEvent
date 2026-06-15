import os
import logging
from datetime import datetime
import pytz
from dotenv import load_dotenv
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import NetworkError
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.request import HTTPXRequest
import aiohttp
import json
from pathlib import Path

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Адміністратор бота (отримайте свій Telegram ID через @userinfobot)
ADMIN_USER_IDS = [int(id.strip()) for id in os.getenv('ADMIN_USER_IDS', '').split(',') if id.strip()]

# Файл для збереження стану бота
BOT_STATE_FILE = Path(__file__).parent / 'bot_state.json'

FULLNAME, PHONE, CATEGORY, ANSWER = range(4)

WELCOME_MESSAGE = """Друзі, вітаю! 👋

Цей бот створений для зручної та швидкої фіксації ваших відповідей у розіграші «Вгадай товар з L'Oréal».

Бот працює з понеділка по п'ятницю.  
⏰ У п'ятницю о 16:00 прийом відповідей зупиняється.

Для участі напишіть, будь ласка:
• ПІБ  
• номер телефону  
• категорію, у якій хочете дати відповідь та саму відповідь 

Категорії:

1 категорія — назва продукту + рекомендація  
3 категорія — назва продукту

Ви можете брати участь у всіх категоріях — так ваші шанси на перемогу збільшуються.

Навіть якщо у вашій аптеці немає продукції La Roche-Posay, CeraVe та Vichy, ви все одно можете брати участь.

Вперед до перемоги! 🏆"""


class AppsScriptManager:
    """Менеджер для роботи з Google Apps Script"""
    
    def __init__(self):
        self.webhook_url = os.getenv('APPS_SCRIPT_URL')
        
        if not self.webhook_url:
            raise ValueError("APPS_SCRIPT_URL не налаштований в .env файлі")
    
    async def check_duplicate(self, category: int, user_id: int) -> bool:
        """Перевірити, чи користувач вже надсилав відповідь у цій категорії"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'action': 'check_duplicate',
                    'user_id': user_id,
                    'category': category
                }
                async with session.get(self.webhook_url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('exists', False)
                    else:
                        logger.error(f"Помилка перевірки дублікатів: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Помилка перевірки дублікатів: {e}")
            return False
    
    async def add_entry(self, category: int, user_id: int, username: str, 
                       fullname: str, phone: str, answer: str) -> dict:
        """Додати запис у таблицю через Apps Script з retry логікою"""
        max_retries = 3
        retry_delay = 2  # секунди
        
        for attempt in range(max_retries):
            try:
                timestamp = datetime.now(pytz.timezone('Europe/Kiev')).strftime('%Y-%m-%d %H:%M:%S')
                
                payload = {
                    'action': 'add_entry',
                    'fullname': fullname,
                    'phone': phone,
                    'username': f"@{username}" if username else "Немає username",
                    'user_id': user_id,
                    'category': category,
                    'answer': answer,
                    'timestamp': timestamp
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.webhook_url, 
                        json=payload,
                        headers={'Content-Type': 'application/json'},
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"Додано запис #{data.get('number')} для користувача {user_id}")
                            return data
                        else:
                            error_text = await response.text()
                            logger.error(f"Помилка додавання запису (спроба {attempt + 1}/{max_retries}): {response.status} - {error_text}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                continue
                            raise Exception(f"Apps Script error: {response.status}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout при додаванні запису (спроба {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                raise Exception("Apps Script timeout після всіх спроб")
            except Exception as e:
                logger.error(f"Помилка додавання запису (спроба {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                raise


def is_registration_open() -> tuple[bool, str]:
    """Перевірити, чи відкрита реєстрація"""
    # Перевірка ручного вимкнення адміністратором
    if not bot_state.is_active():
        return False, "❌ Прийом заявок закритий, до наступного тижня."
    
    # Автоматична перевірка часу
    kiev_tz = pytz.timezone('Europe/Kiev')
    now = datetime.now(kiev_tz)
    
    weekday = now.weekday()
    hour = now.hour
    
    if weekday > 4:
        return False, "❌ Реєстрація закрита на вихідних. Реєстрація працює з понеділка по п'ятницю."
    
    if weekday == 4 and hour >= 16:
        return False, "❌ Реєстрація закрита. У п'ятницю прийом відповідей зупиняється о 16:00."
    
    return True, ""


apps_script_manager = AppsScriptManager()


class BotStateManager:
    """Менеджер стану бота (активний/неактивний)"""
    
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self._ensure_state_file()
    
    def _ensure_state_file(self):
        """Створити файл стану, якщо він не існує"""
        if not self.state_file.exists():
            self._save_state({'active': True})
    
    def _load_state(self) -> dict:
        """Завантажити стан з файлу"""
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Помилка завантаження стану: {e}")
            return {'active': True}
    
    def _save_state(self, state: dict):
        """Зберегти стан у файл"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Помилка збереження стану: {e}")
    
    def is_active(self) -> bool:
        """Перевірити, чи бот активний"""
        state = self._load_state()
        return state.get('active', True)
    
    def activate(self):
        """Активувати бота"""
        self._save_state({'active': True})
        logger.info("Бот активовано")
    
    def deactivate(self):
        """Деактивувати бота"""
        self._save_state({'active': False})
        logger.info("Бот деактивовано")


bot_state = BotStateManager(BOT_STATE_FILE)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробник команди /start"""
    is_open, message = is_registration_open()
    
    if not is_open:
        await update.message.reply_text(message)
        return ConversationHandler.END
    
    await update.message.reply_text(WELCOME_MESSAGE)
    await update.message.reply_text(
        "Почнемо реєстрацію! 📝\n\n"
        "Будь ласка, введіть ваше ПІБ (Прізвище Ім'я По батькові):"
    )
    return FULLNAME


async def get_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отримати ПІБ"""
    is_open, message = is_registration_open()
    if not is_open:
        await update.message.reply_text(message)
        return ConversationHandler.END
    
    context.user_data['fullname'] = update.message.text.strip()
    await update.message.reply_text(
        "Дякую! 📱\n\n"
        "Тепер введіть ваш номер телефону (наприклад: +380501234567):"
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отримати номер телефону"""
    is_open, message = is_registration_open()
    if not is_open:
        await update.message.reply_text(message)
        return ConversationHandler.END
    
    context.user_data['phone'] = update.message.text.strip()
    
    # Створити inline-кнопки для вибору категорії
    keyboard = [
        [InlineKeyboardButton("Категорія 1", callback_data="category_1")],
        [InlineKeyboardButton("Категорія 3", callback_data="category_3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Чудово! 🎯\n\n"
        "Тепер оберіть категорію:\n\n"
        "1️⃣ Категорія 1 — назва продукту + рекомендація\n"
        "3️⃣ Категорія 3 — назва продукту",
        reply_markup=reply_markup
    )
    return CATEGORY


async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отримати категорію через inline-кнопки"""
    query = update.callback_query
    await query.answer()
    
    is_open, message = is_registration_open()
    if not is_open:
        await query.edit_message_text(message)
        return ConversationHandler.END
    
    # Отримати категорію з callback_data
    callback_data = query.data
    if callback_data == "category_1":
        category = 1
    elif callback_data == "category_3":
        category = 3
    else:
        await query.edit_message_text("❌ Помилка вибору категорії. Спробуйте ще раз або введіть /start")
        return ConversationHandler.END
    
    context.user_data['category'] = category
    
    # Показати індикатор "набирає текст..." під час перевірки
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    user_id = update.effective_user.id
    is_duplicate = await apps_script_manager.check_duplicate(category, user_id)
    
    if is_duplicate:
        await query.edit_message_text(
            f"❌ Ви вже надіслали відповідь у категорії {category}.\n\n"
            "Кожен учасник може надіслати тільки одну відповідь в одній категорії.\n\n"
            "Якщо хочете взяти участь в іншій категорії, введіть /start"
        )
        return ConversationHandler.END
    
    category_desc = "назва продукту + рекомендація" if category == 1 else "назва продукту"
    await query.edit_message_text(
        f"Відмінно! Ви обрали категорію {category} ({category_desc}) ✅\n\n"
        "Тепер введіть вашу відповідь:"
    )
    return ANSWER


async def get_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отримати відповідь та зберегти все через Apps Script"""
    is_open, message = is_registration_open()
    if not is_open:
        await update.message.reply_text(message)
        return ConversationHandler.END
    
    context.user_data['answer'] = update.message.text.strip()
    
    # Показати індикатор "набирає текст..." під час збереження
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    fullname = context.user_data['fullname']
    phone = context.user_data['phone']
    category = context.user_data['category']
    answer = context.user_data['answer']
    
    try:
        result = await apps_script_manager.add_entry(
            category=category,
            user_id=user_id,
            username=username,
            fullname=fullname,
            phone=phone,
            answer=answer
        )
        
        number = result.get('number', '?')
        
        await update.message.reply_text(
            f"✅ Дякуємо за вашу відповідь!\n\n"
            f"📋 Ваші дані зареєстровано:\n"
            f"• ПІБ: {fullname}\n"
            f"• Телефон: {phone}\n"
            f"• Категорія: {category}\n"
            f"• Ваш номерок: Категорія {category}, номер {number}\n\n"
            f"🎉 Бажаємо удачі у розіграші!\n\n"
            f"Якщо хочете взяти участь в іншій категорії, введіть /start"
        )
    except Exception as e:
        logger.error(f"Помилка збереження даних: {e}")
        await update.message.reply_text(
            "❌ Виникла помилка при збереженні ваших даних. "
            "Будь ласка, спробуйте ще раз або зверніться до адміністратора."
        )
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Скасувати реєстрацію"""
    await update.message.reply_text(
        "Реєстрацію скасовано. Якщо хочете почати знову, введіть /start"
    )
    return ConversationHandler.END


def is_admin(user_id: int) -> bool:
    """Перевірити, чи користувач є адміністратором"""
    return user_id in ADMIN_USER_IDS


async def admin_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Адмін-команда: зупинити прийом заявок"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас немає прав для виконання цієї команди.")
        return
    
    bot_state.deactivate()
    await update.message.reply_text(
        "🛑 Прийом заявок ЗУПИНЕНО\n\n"
        "Користувачі отримуватимуть повідомлення:\n"
        "'Прийом заявок закритий, до наступного тижня.'"
    )
    logger.info(f"Адміністратор {user_id} зупинив прийом заявок")


async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Адмін-команда: відновити прийом заявок"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас немає прав для виконання цієї команди.")
        return
    
    bot_state.activate()
    await update.message.reply_text(
        "✅ Прийом заявок ВІДНОВЛЕНО\n\n"
        "Користувачі знову можуть реєструватися."
    )
    logger.info(f"Адміністратор {user_id} відновив прийом заявок")


async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Адмін-команда: перевірити статус бота"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас немає прав для виконання цієї команди.")
        return
    
    is_active = bot_state.is_active()
    status_icon = "✅" if is_active else "🛑"
    status_text = "АКТИВНИЙ" if is_active else "ЗУПИНЕНИЙ"
    
    await update.message.reply_text(
        f"{status_icon} Статус бота: {status_text}\n\n"
        f"Адмін-команди:\n"
        f"/admin_stop - зупинити прийом заявок\n"
        f"/admin_start - відновити прийом заявок\n"
        f"/admin_status - перевірити статус"
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальний обробник помилок — щоб мережеві збої не зупиняли бота."""
    err = context.error
    # Мережеві помилки (ReadError/TimeoutError тощо) — очікувані, лише логуємо.
    if isinstance(err, NetworkError):
        logger.warning(f"Мережева помилка (бот продовжує роботу): {err}")
        return
    logger.error("Необроблена помилка під час обробки оновлення:", exc_info=err)


def main() -> None:
    """Запуск бота"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не знайдено в .env файлі")
    
    # Збільшені таймаути та пул з'єднань — стійкість до мережевих блипів.
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=10.0,
        read_timeout=10.0,
        write_timeout=10.0,
        pool_timeout=10.0,
    )
    # Окремий request для довгого getUpdates (read_timeout > polling timeout).
    get_updates_request = HTTPXRequest(
        connection_pool_size=2,
        connect_timeout=10.0,
        read_timeout=40.0,
        pool_timeout=10.0,
    )

    application = (
        Application.builder()
        .token(token)
        .request(request)
        .get_updates_request(get_updates_request)
        .build()
    )
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FULLNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fullname)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CATEGORY: [CallbackQueryHandler(get_category)],
            ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)

    # Адмін-команди
    application.add_handler(CommandHandler('admin_stop', admin_stop))
    application.add_handler(CommandHandler('admin_start', admin_start))
    application.add_handler(CommandHandler('admin_status', admin_status))

    # Глобальний обробник помилок
    application.add_error_handler(error_handler)

    logger.info("Бот запущено!")
    if ADMIN_USER_IDS:
        logger.info(f"Адміністратори: {ADMIN_USER_IDS}")
    else:
        logger.warning("УВАГА: Не налаштовано жодного адміністратора (ADMIN_USER_IDS)")

    # На Render працюємо через webhook (стабільніше за polling, не засинає).
    # Локально (без RENDER_EXTERNAL_URL) — fallback на polling.
    external_url = os.getenv('RENDER_EXTERNAL_URL') or os.getenv('WEBHOOK_URL')
    port = int(os.getenv('PORT', '10000'))

    if external_url:
        external_url = external_url.rstrip('/')
        # Секретний шлях = токен, щоб сторонні не слали підроблені апдейти.
        logger.info(f"Запуск у режимі webhook на порту {port}")
        application.run_webhook(
            listen='0.0.0.0',
            port=port,
            url_path=token,
            webhook_url=f"{external_url}/{token}",
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
    else:
        logger.info("RENDER_EXTERNAL_URL не задано — запуск у режимі polling (локально)")
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == '__main__':
    main()
