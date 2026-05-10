// Google Apps Script код для обробки запитів від Telegram бота
// Цей код потрібно вставити в Apps Script редактор Google Sheets

// Налаштування - назви листів (вкладок)
const SHEET_NAME_CATEGORY_1 = 'Категорія-1';
const SHEET_NAME_CATEGORY_3 = 'Категорія-3';

// Функція для обробки GET запитів (перевірка дублікатів)
function doGet(e) {
  try {
    const action = e.parameter.action;
    
    if (action === 'check_duplicate') {
      const userId = e.parameter.user_id;
      const category = parseInt(e.parameter.category);
      const exists = checkDuplicate(userId, category);
      
      return ContentService.createTextOutput(
        JSON.stringify({ exists: exists })
      ).setMimeType(ContentService.MimeType.JSON);
    }
    
    return ContentService.createTextOutput(
      JSON.stringify({ error: 'Unknown action' })
    ).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    Logger.log('Error in doGet: ' + error.toString());
    return ContentService.createTextOutput(
      JSON.stringify({ error: error.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

// Функція для обробки POST запитів (додавання запису)
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const action = data.action;
    
    if (action === 'add_entry') {
      const number = addEntry(
        data.fullname,
        data.phone,
        data.username,
        data.user_id,
        data.category,
        data.answer,
        data.timestamp
      );
      
      return ContentService.createTextOutput(
        JSON.stringify({ 
          success: true,
          number: number,
          message: 'Entry added successfully'
        })
      ).setMimeType(ContentService.MimeType.JSON);
    }
    
    return ContentService.createTextOutput(
      JSON.stringify({ error: 'Unknown action' })
    ).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    Logger.log('Error in doPost: ' + error.toString());
    return ContentService.createTextOutput(
      JSON.stringify({ error: error.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

// Отримати назву листа залежно від категорії
function getSheetName(category) {
  return category === 1 ? SHEET_NAME_CATEGORY_1 : SHEET_NAME_CATEGORY_3;
}

// Перевірка чи користувач вже існує
function checkDuplicate(userId, category) {
  const sheetName = getSheetName(category);
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sheetName);
  
  if (!sheet) {
    throw new Error('Sheet "' + sheetName + '" not found');
  }
  
  const data = sheet.getDataRange().getValues();
  
  // Пропускаємо заголовок (рядок 0)
  for (let i = 1; i < data.length; i++) {
    const telegramId = data[i][4]; // Telegram ID в колонці E (індекс 4)
    if (telegramId && telegramId.toString() === userId.toString()) {
      return true;
    }
  }
  
  return false;
}

// Додати новий запис
function addEntry(fullname, phone, username, userId, category, answer, timestamp) {
  const sheetName = getSheetName(category);
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sheetName);
  
  if (!sheet) {
    throw new Error('Sheet "' + sheetName + '" not found');
  }
  
  // Отримати наступний номер
  const lastRow = sheet.getLastRow();
  const number = lastRow; // Заголовок в рядку 1, тому lastRow = номер нового запису
  
  // Додати рядок
  const newRow = [
    number,
    fullname,
    phone,
    username,
    userId,
    'Категорія ' + category,
    answer,
    timestamp
  ];
  
  sheet.appendRow(newRow);
  
  Logger.log('Added entry #' + number + ' for user ' + userId);
  
  return number;
}

// Функція для тестування (опціонально)
function testCheckDuplicate() {
  const exists = checkDuplicate('123456789');
  Logger.log('User exists: ' + exists);
}

function testAddEntry() {
  const number = addEntry(
    'Тестовий Користувач',
    '+380501234567',
    '@testuser',
    '123456789',
    1,
    'Тестова відповідь',
    new Date().toLocaleString('uk-UA')
  );
  Logger.log('Added test entry #' + number);
}
