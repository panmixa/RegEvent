import os
import logging
from datetime import datetime
import pytz
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
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
                async with session.get(self.webhook_url, params=params, timeout=10) as response:
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
        """Додати запис у таблицю через Apps Script"""
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
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Додано запис #{data.get('number')} для користувача {user_id}")
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"Помилка додавання запису: {response.status} - {error_text}")
                        raise Exception(f"Apps Script error: {response.status}")
        except Exception as e:
            logger.error(f"Помилка додавання запису: {e}")
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
    await update.message.reply_text(
        "Чудово! 🎯\n\n"
        "Тепер оберіть категорію:\n\n"
        "1️⃣ Категорія 1 — назва продукту + рекомендація\n"
        "3️⃣ Категорія 3 — назва продукту\n\n"
        "Введіть номер категорії (1 або 3):"
    )
    return CATEGORY


async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отримати категорію"""
    is_open, message = is_registration_open()
    if not is_open:
        await update.message.reply_text(message)
        return ConversationHandler.END
    
    category_text = update.message.text.strip()
    
    if category_text not in ['1', '3']:
        await update.message.reply_text(
            "❌ Будь ласка, введіть 1 або 3.\n\n"
            "1️⃣ — назва продукту + рекомендація\n"
            "3️⃣ — назва продукту"
        )
        return CATEGORY
    
    category = int(category_text)
    context.user_data['category'] = category
    
    user_id = update.effective_user.id
    is_duplicate = await apps_script_manager.check_duplicate(category, user_id)
    
    if is_duplicate:
        await update.message.reply_text(
            f"❌ Ви вже надіслали відповідь у категорії {category}.\n\n"
            "Кожен учасник може надіслати тільки одну відповідь в одній категорії.\n\n"
            "Якщо хочете взяти участь в іншій категорії, введіть /start"
        )
        return ConversationHandler.END
    
    category_desc = "назва продукту + рекомендація" if category == 1 else "назва продукту"
    await update.message.reply_text(
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


def main() -> None:
    """Запуск бота"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не знайдено в .env файлі")
    
    application = Application.builder().token(token).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FULLNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fullname)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
            ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Адмін-команди
    application.add_handler(CommandHandler('admin_stop', admin_stop))
    application.add_handler(CommandHandler('admin_start', admin_start))
    application.add_handler(CommandHandler('admin_status', admin_status))
    
    logger.info("Бот запущено!")
    if ADMIN_USER_IDS:
        logger.info(f"Адміністратори: {ADMIN_USER_IDS}")
    else:
        logger.warning("УВАГА: Не налаштовано жодного адміністратора (ADMIN_USER_IDS)")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
