# Швидкий старт

## Покрокова інструкція для запуску бота

### Крок 1: Створіть Telegram бота (5 хв)

1. Відкрийте [@BotFather](https://t.me/BotFather) в Telegram
2. Відправте: `/newbot`
3. Введіть назву: `L'Oréal Event Bot`
4. Введіть username: `loreal_event_bot` (або інший, що закінчується на `bot`)
5. **Збережіть токен** (виглядає як `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Крок 2: Налаштуйте Google Sheets (10-15 хв)

#### 2.1. Створіть Google Cloud проект

1. Відкрийте https://console.cloud.google.com/
2. Натисніть "Select a project" → "New Project"
3. Назва: `loreal-event-bot` → "Create"

#### 2.2. Увімкніть API

1. У меню зліва: "APIs & Services" → "Library"
2. Знайдіть та увімкніть:
   - **Google Sheets API** → Enable
   - **Google Drive API** → Enable

#### 2.3. Створіть Service Account

1. "APIs & Services" → "Credentials"
2. "Create Credentials" → "Service Account"
3. Назва: `loreal-bot` → "Create and Continue"
4. Role: **Editor** → "Continue" → "Done"

#### 2.4. Завантажте ключ

1. Натисніть на створений Service Account
2. Вкладка "Keys" → "Add Key" → "Create new key"
3. Тип: **JSON** → "Create"
4. Файл `credentials.json` завантажиться
5. **Перемістіть його в папку `c:\Users\Legion\Desktop\RegEvent\`**

#### 2.5. Створіть таблиці

1. Відкрийте https://sheets.google.com/
2. Створіть дві таблиці:
   - Назва 1: `L'Oréal Event - Категорія 1`
   - Назва 2: `L'Oréal Event - Категорія 3`

3. У **кожній таблиці**:
   - Перейменуйте лист (знизу) на **"Відповіді"**
   - У перший рядок додайте заголовки:
     ```
     A1: Номер
     B1: ПІБ
     C1: Телефон
     D1: Telegram Username
     E1: Telegram ID
     F1: Категорія
     G1: Відповідь
     H1: Дата і час
     ```

4. **Скопіюйте ID таблиць:**
   - Відкрийте таблицю
   - URL: `https://docs.google.com/spreadsheets/d/`**`ID_ТУТ`**`/edit`
   - Збережіть обидва ID

5. **Надайте доступ боту:**
   - Відкрийте `credentials.json` (текстовим редактором)
   - Знайдіть `"client_email": "...@....gserviceaccount.com"`
   - Скопіюйте цей email
   - У **кожній таблиці** натисніть "Share" (Поділитися)
   - Вставте email
   - Role: **Editor**
   - Зніміть галочку "Notify people"
   - "Share"

### Крок 3: Налаштуйте проект (2 хв)

1. Відкрийте PowerShell у папці проекту:
```powershell
cd c:\Users\Legion\Desktop\RegEvent
```

2. Встановіть залежності:
```powershell
pip install -r requirements.txt
```

3. Створіть файл `.env`:
```powershell
copy .env.example .env
```

4. Відредагуйте `.env` (блокнотом або VSCode):
```env
TELEGRAM_BOT_TOKEN=ваш_токен_від_BotFather
GOOGLE_SHEET_ID_CATEGORY_1=ID_таблиці_1
GOOGLE_SHEET_ID_CATEGORY_3=ID_таблиці_3
SHEET_NAME=Відповіді
GOOGLE_CREDENTIALS_FILE=credentials.json
```

### Крок 4: Запустіть бота (1 хв)

```powershell
python bot.py
```

Якщо все налаштовано правильно, побачите:
```
INFO - Успішно підключено до Google Sheets
INFO - Бот запущено!
```

### Крок 5: Протестуйте

1. Знайдіть вашого бота в Telegram
2. Натисніть `/start`
3. Пройдіть реєстрацію
4. Перевірте, чи дані з'явились у Google таблиці

## Чек-лист перед запуском

- [ ] Telegram бот створений, токен є
- [ ] Google Cloud проект створений
- [ ] Google Sheets API та Drive API увімкнені
- [ ] Service Account створений
- [ ] Файл `credentials.json` в папці проекту
- [ ] Дві Google таблиці створені з листом "Відповіді"
- [ ] Заголовки додані в обидві таблиці
- [ ] Service Account має доступ до обох таблиць (Editor)
- [ ] Файл `.env` створений та заповнений
- [ ] Залежності встановлені (`pip install -r requirements.txt`)
- [ ] Бот запущений без помилок

## Корисна інформація

### Зупинити бота
Натисніть `Ctrl+C` у консолі

### Запустити бота у фоновому режимі (Windows)
Використовуйте Task Scheduler або запустіть у окремому вікні PowerShell

### Переглянути логи
Всі логи виводяться у консоль. Для збереження у файл:
```powershell
python bot.py > bot.log 2>&1
```

### Час роботи бота
- **Працює:** понеділок-п'ятниця до 16:00
- **Не працює:** п'ятниця після 16:00, субота, неділя

### Експорт даних з Google Sheets
File → Download → CSV або Excel

## Потрібна допомога?

Перевірте `README.md` для детальної інформації та вирішення проблем.
