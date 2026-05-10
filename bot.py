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
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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


class GoogleSheetsManager:
    def __init__(self):
        self.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        self.sheet_id_cat1 = os.getenv('GOOGLE_SHEET_ID_CATEGORY_1')
        self.sheet_id_cat3 = os.getenv('GOOGLE_SHEET_ID_CATEGORY_3')
        self.sheet_name = os.getenv('SHEET_NAME', 'Відповіді')
        self.client = None
        self._connect()

    def _connect(self):
        """Підключення до Google Sheets"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=scopes
            )
            self.client = gspread.authorize(creds)
            logger.info("Успішно підключено до Google Sheets")
        except Exception as e:
            logger.error(f"Помилка підключення до Google Sheets: {e}")
            raise

    def get_sheet(self, category: int):
        """Отримати таблицю залежно від категорії"""
        sheet_id = self.sheet_id_cat1 if category == 1 else self.sheet_id_cat3
        try:
            spreadsheet = self.client.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet(self.sheet_name)
            return worksheet
        except Exception as e:
            logger.error(f"Помилка відкриття таблиці: {e}")
            raise

    def check_duplicate(self, category: int, user_id: int) -> bool:
        """Перевірити, чи користувач вже надсилав відповідь у цій категорії"""
        try:
            worksheet = self.get_sheet(category)
            all_records = worksheet.get_all_records()
            
            for record in all_records:
                if str(record.get('Telegram ID', '')) == str(user_id):
                    return True
            return False
        except Exception as e:
            logger.error(f"Помилка перевірки дублікатів: {e}")
            return False

    def get_next_number(self, category: int) -> int:
        """Отримати наступний номер для категорії"""
        try:
            worksheet = self.get_sheet(category)
            all_records = worksheet.get_all_records()
            return len(all_records) + 1
        except Exception as e:
            logger.error(f"Помилка отримання номера: {e}")
            return 1

    def add_entry(self, category: int, user_id: int, username: str, fullname: str, 
                  phone: str, answer: str) -> int:
        """Додати запис у таблицю"""
        try:
            worksheet = self.get_sheet(category)
            number = self.get_next_number(category)
            timestamp = datetime.now(pytz.timezone('Europe/Kiev')).strftime('%Y-%m-%d %H:%M:%S')
            
            row = [
                number,
                fullname,
                phone,
                f"@{username}" if username else "Немає username",
                user_id,
                f"Категорія {category}",
                answer,
                timestamp
            ]
            
            worksheet.append_row(row)
            logger.info(f"Додано запис #{number} для користувача {user_id} в категорію {category}")
            return number
        except Exception as e:
            logger.error(f"Помилка додавання запису: {e}")
            raise


def is_registration_open() -> tuple[bool, str]:
    """Перевірити, чи відкрита реєстрація (з понеділка по п'ятницю до 16:00)"""
    kiev_tz = pytz.timezone('Europe/Kiev')
    now = datetime.now(kiev_tz)
    
    weekday = now.weekday()
    hour = now.hour
    
    if weekday > 4:
        return False, "❌ Реєстрація закрита на вихідних. Реєстрація працює з понеділка по п'ятницю."
    
    if weekday == 4 and hour >= 16:
        return False, "❌ Реєстрація закрита. У п'ятницю прийом відповідей зупиняється о 16:00."
    
    return True, ""


sheets_manager = GoogleSheetsManager()


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
    if sheets_manager.check_duplicate(category, user_id):
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
    """Отримати відповідь та зберегти все в Google Sheets"""
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
        number = sheets_manager.add_entry(
            category=category,
            user_id=user_id,
            username=username,
            fullname=fullname,
            phone=phone,
            answer=answer
        )
        
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
    
    logger.info("Бот запущено!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
