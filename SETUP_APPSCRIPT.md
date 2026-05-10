# 🚀 Швидке налаштування з Apps Script

**Цей варіант ПРОСТІШИЙ** — не потрібен Service Account, JSON credentials, або складні налаштування Google Cloud!

## ⏱️ Час налаштування: 10-15 хвилин

---

## Крок 1: Створіть Telegram бота (3 хв)

1. Відкрийте [@BotFather](https://t.me/BotFather) в Telegram
2. Відправте: `/newbot`
3. Назва: `L'Oréal Event Bot`
4. Username: `loreal_event_bot` (або інший на `bot`)
5. **Збережіть токен** (наприклад: `7960884843:AAGxOCe7NjF0nzWPjM_oL4mlbg3oe80xwmc`)

---

## Крок 2: Створіть Google таблицю (2 хв)

### 2.1. Створіть таблицю

1. Відкрийте https://sheets.google.com/
2. Створіть нову таблицю: **"L'Oréal Event"**

### 2.2. Налаштуйте дві вкладки

1. **Перейменуйте** перший лист (знизу) на **"Категорія-1"**
2. **Додайте** новий лист (натисніть + знизу)
3. **Перейменуйте** другий лист на **"Категорія-3"**

### 2.3. Додайте заголовки

У **КОЖНІЙ вкладці** (Категорія-1 та Категорія-3):

1. **Додайте заголовки** в перший рядок (A1-H1):

| A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|
| Номер | ПІБ | Телефон | Telegram Username | Telegram ID | Категорія | Відповідь | Дата і час |

---

## Крок 3: Налаштуйте Apps Script (3-5 хв)

#### 3.1. Відкрийте Apps Script

1. У вашій Google таблиці: **Розширення** (Extensions) → **Apps Script**
2. Відкриється редактор коду

#### 3.2. Вставте код

1. Видаліть весь код, який там є (function myFunction() {...})
2. Відкрийте файл **`apps_script_code.gs`** з проекту
3. Скопіюйте **весь код**
4. Вставте в Apps Script редактор

⚠️ **ВАЖЛИВО**: Перевірте, що назви листів у коді збігаються з вашими:
```javascript
const SHEET_NAME_CATEGORY_1 = 'Категорія-1';
const SHEET_NAME_CATEGORY_3 = 'Категорія-3';
```

#### 3.3. Збережіть проект

1. Натисніть **💾 (Save project)** або Ctrl+S
2. Назва проекту: `L'Oréal Event Bot`

#### 3.4. Задеплойте як Web App

1. Натисніть **Deploy** (Розгорнути) → **New deployment** (Нове розгортання)
2. Натисніть **⚙️ (шестерня)** → Select type → **Web app**
3. Налаштування:
   - **Description**: `L'Oréal Event Bot API`
   - **Execute as**: **Me** (ваш email)
   - **Who has access**: **Anyone** (Будь-хто)
4. Натисніть **Deploy**
5. **Дозвольте доступ**:
   - Review permissions → Оберіть ваш Google акаунт
   - Advanced → Go to "назва проекту" (unsafe)
   - Allow
6. **СКОПІЮЙТЕ URL** (виглядає як `https://script.google.com/macros/s/ABC.../exec`)
7. Натисніть **Done**

---

## Крок 4: Налаштуйте проект бота (3 хв)

### 4.1. Встановіть залежності

```powershell
cd c:\Users\Legion\Desktop\RegEvent
pip install -r requirements_appscript.txt
```

### 4.2. Створіть .env файл

```powershell
copy .env_appscript.example .env
```

### 4.3. Відредагуйте .env

Відкрийте `.env` і заповніть:

```env
TELEGRAM_BOT_TOKEN=7960884843:AAGxOCe7NjF0nzWPjM_oL4mlbg3oe80xwmc

APPS_SCRIPT_URL=https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec
```

**Замініть**:
- Токен бота (вже є: `7960884843:AAGxOCe7NjF0nzWPjM_oL4mlbg3oe80xwmc`)
- URL з Apps Script деплою (з кроку 3.4)

---

## Крок 5: Запустіть бота

```powershell
python bot_appscript.py
```

Має з'явитись:
```
INFO - Бот запущено!
```

---

## ✅ Тестування

1. Знайдіть бота в Telegram
2. Натисніть `/start`
3. Пройдіть реєстрацію
4. Перевірте Google таблицю — дані мають з'явитись!

---

## 📊 Переваги Apps Script підходу

✅ **Простіше налаштувати** — без Service Account, credentials.json  
✅ **Менше залежностей** — не потрібен gspread  
✅ **Працює з будь-якого місця** — через HTTPS  
✅ **Безкоштовно** — використовує Google квоти Apps Script  
✅ **Безпечно** — Apps Script виконується на серверах Google  

---

## 🔧 Можливі проблеми

### "Apps Script URLs не налаштовані"
- Перевірте, що файл `.env` існує
- Перевірте, що URL правильно скопійовані

### "Error 403" або "Authorization required"
- У налаштуваннях деплою перевірте **Who has access: Anyone**
- Передеплойте: Deploy → Manage deployments → Edit → Version: New version → Deploy

### Дані не додаються в таблицю
- Перевірте, що лист називається **"Відповіді"**
- Перевірте заголовки в таблиці
- Перегляньте логи: Apps Script → Executions (для діагностики)

### Бот не відповідає
- Перевірте, що `bot_appscript.py` запущений
- Перевірте інтернет-з'єднання
- Перегляньте логи у консолі

---

## 📁 Структура файлів

```
c:\Users\Legion\Desktop\RegEvent\
├── bot_appscript.py              # ← ЗАПУСКАТИ ЦЕЙ ФАЙЛ
├── apps_script_code.gs           # Код для Apps Script
├── requirements_appscript.txt    # Залежності (спрощені)
├── .env_appscript.example       # Приклад конфігурації
├── .env                         # Ваша конфігурація
└── SETUP_APPSCRIPT.md           # Ця інструкція
```

---

## 🎯 Чек-лист

- [ ] Telegram бот створений ✓ (токен є: `7960884843:...`)
- [ ] Одна Google таблиця створена: "L'Oréal Event"
- [ ] Дві вкладки створені: "Категорія-1" та "Категорія-3"
- [ ] Заголовки додані в обидві вкладки
- [ ] Apps Script код вставлений в таблицю
- [ ] Назви листів у коді збігаються: `Категорія-1` та `Категорія-3`
- [ ] Web App задеплоєний (Who has access: Anyone)
- [ ] URL скопійований
- [ ] `.env` файл створений та заповнений
- [ ] Залежності встановлені: `pip install -r requirements_appscript.txt`
- [ ] Бот запущений: `python bot_appscript.py`
- [ ] Тест пройдено — дані з'явились у відповідних вкладках

---

## 🆘 Підтримка

Якщо щось не працює:
1. Перевірте чек-лист
2. Перегляньте логи бота
3. Перегляньте Apps Script Executions
4. Перезапустіть бота

Готово! 🎉
