/**
 * ZarGo Shop — Google Apps Script (Backend)
 *
 * SOZLASH:
 * 1. Google Sheets oching (3 varaq: customers, orders, products)
 * 2. Extensions > Apps Script > ushbu kodni joylashtiring
 * 3. Deploy > New deployment > Web app
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 4. Olingan URL ni SHEETS_URL env ga joylashtiring
 *
 * VARAQLAR TUZILISHI:
 *  customers : phone | name | gender | language | first_contact | last_contact | total_orders
 *  orders    : number | phone | name | address | items | total | payment | status | date | source
 *  products  : id | name | category | description | price | unit | image_url | available
 */

const SS = SpreadsheetApp.getActiveSpreadsheet();

// ─── GET Handler ──────────────────────────────────────────────────────────────
function doGet(e) {
  const action = e.parameter.action;
  try {
    switch (action) {
      case 'get_customer':   return ok(getCustomer(e.parameter.phone));
      case 'customers':      return ok({ customers: getAllCustomers() });
      case 'products':       return ok({ products: getProducts() });
      case 'orders':         return ok({ orders: getAllOrders() });
      case 'get_order':      return ok({ order: getOrder(e.parameter.number) });
      case 'orders_by_date': return ok({ orders: getOrdersByDate(e.parameter.date) });
      default:               return err('Unknown action: ' + action);
    }
  } catch (ex) {
    return err(ex.toString());
  }
}

// ─── POST Handler ─────────────────────────────────────────────────────────────
function doPost(e) {
  const body   = JSON.parse(e.postData.contents);
  const action = body.action;
  try {
    switch (action) {
      case 'save_customer':       return ok(saveCustomer(body.customer));
      case 'save_order':          return ok({ number: saveOrder(body.order) });
      case 'update_order_status': return ok(updateOrderStatus(body.number, body.status));
      case 'update_order':        return ok(updateOrder(body.number, body.data));
      case 'delete_order':        return ok(deleteOrder(body.number));
      default:                    return err('Unknown action: ' + action);
    }
  } catch (ex) {
    return err(ex.toString());
  }
}

// ─── Response helpers ─────────────────────────────────────────────────────────
function ok(data) {
  return ContentService
    .createTextOutput(JSON.stringify({ success: true, ...data }))
    .setMimeType(ContentService.MimeType.JSON);
}
function err(msg) {
  return ContentService
    .createTextOutput(JSON.stringify({ success: false, error: msg }))
    .setMimeType(ContentService.MimeType.JSON);
}

// ─── CUSTOMERS ────────────────────────────────────────────────────────────────
function getCustomer(phone) {
  const sheet = SS.getSheetByName('customers');
  const data  = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]) === String(phone)) {
      return {
        customer: {
          phone:         data[i][0],
          name:          data[i][1],
          gender:        data[i][2],
          language:      data[i][3],
          first_contact: data[i][4],
          last_contact:  data[i][5],
          total_orders:  data[i][6],
        }
      };
    }
  }
  return { customer: null };
}

function saveCustomer(c) {
  const sheet = SS.getSheetByName('customers');
  const data  = sheet.getDataRange().getValues();
  const now   = new Date().toISOString();

  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]) === String(c.phone)) {
      // Mavjud mijozni yangilash
      sheet.getRange(i + 1, 2).setValue(c.name          || data[i][1]);
      sheet.getRange(i + 1, 3).setValue(c.gender        || data[i][2]);
      sheet.getRange(i + 1, 4).setValue(c.language      || data[i][3]);
      sheet.getRange(i + 1, 6).setValue(now);
      return { updated: true };
    }
  }

  // Yangi mijoz
  sheet.appendRow([c.phone, c.name, c.gender || 'unknown', c.language || 'uz', now, now, 0]);
  return { created: true };
}

function getAllCustomers() {
  const sheet = SS.getSheetByName('customers');
  const data  = sheet.getDataRange().getValues();
  const result = [];
  for (let i = 1; i < data.length; i++) {
    if (!data[i][0]) continue;
    result.push({
      phone:        data[i][0],
      name:         data[i][1],
      gender:       data[i][2],
      language:     data[i][3],
      last_contact: data[i][5],
      total_orders: data[i][6],
    });
  }
  return result;
}

// ─── ORDERS ───────────────────────────────────────────────────────────────────
function getNextOrderNumber() {
  const sheet = SS.getSheetByName('orders');
  const last  = sheet.getLastRow();
  if (last <= 1) return 1;
  const nums = sheet.getRange(2, 1, last - 1, 1).getValues()
    .map(r => parseInt(r[0]) || 0);
  return Math.max(...nums) + 1;
}

function saveOrder(o) {
  const sheet  = SS.getSheetByName('orders');
  const number = getNextOrderNumber();
  const now    = new Date().toISOString();
  sheet.appendRow([
    number,
    o.phone,
    o.name,
    o.address,
    o.items,
    o.total,
    o.payment || 'naqd',
    o.status  || 'yangi',
    now,
    o.source  || 'web',
  ]);

  // Mijozning total_orders ni +1 qilish
  try {
    const cSheet = SS.getSheetByName('customers');
    const cData  = cSheet.getDataRange().getValues();
    for (let i = 1; i < cData.length; i++) {
      if (String(cData[i][0]) === String(o.phone)) {
        cSheet.getRange(i + 1, 7).setValue((parseInt(cData[i][6]) || 0) + 1);
        break;
      }
    }
  } catch (_) {}

  return String(number);
}

function getOrder(number) {
  const sheet = SS.getSheetByName('orders');
  const data  = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]) === String(number)) {
      return rowToOrder(data[i]);
    }
  }
  return null;
}

function getAllOrders() {
  const sheet  = SS.getSheetByName('orders');
  const data   = sheet.getDataRange().getValues();
  const result = [];
  for (let i = 1; i < data.length; i++) {
    if (!data[i][0]) continue;
    result.push(rowToOrder(data[i]));
  }
  return result;
}

function getOrdersByDate(dateStr) {
  return getAllOrders().filter(o => String(o.date || '').startsWith(dateStr));
}

function updateOrderStatus(number, status) {
  const sheet = SS.getSheetByName('orders');
  const data  = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]) === String(number)) {
      sheet.getRange(i + 1, 8).setValue(status);
      return { updated: true };
    }
  }
  return { updated: false };
}

function updateOrder(number, fields) {
  const sheet = SS.getSheetByName('orders');
  const data  = sheet.getDataRange().getValues();
  const map   = { name: 3, address: 4, items: 5, total: 6, status: 8 };
  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]) === String(number)) {
      for (const [key, col] of Object.entries(map)) {
        if (fields[key] !== undefined) sheet.getRange(i + 1, col).setValue(fields[key]);
      }
      return { updated: true };
    }
  }
  return { updated: false };
}

function deleteOrder(number) {
  const sheet = SS.getSheetByName('orders');
  const data  = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]) === String(number)) {
      sheet.deleteRow(i + 1);
      return { deleted: true };
    }
  }
  return { deleted: false };
}

function rowToOrder(row) {
  return {
    number:  row[0],
    phone:   row[1],
    name:    row[2],
    address: row[3],
    items:   row[4],
    total:   row[5],
    payment: row[6],
    status:  row[7],
    date:    row[8],
    source:  row[9],
  };
}

// ─── PRODUCTS ─────────────────────────────────────────────────────────────────
function getProducts() {
  const sheet  = SS.getSheetByName('products');
  const data   = sheet.getDataRange().getValues();
  const result = [];
  for (let i = 1; i < data.length; i++) {
    const avail = String(data[i][7]).toLowerCase();
    if (!data[i][0] || avail === 'false' || avail === 'нет' || avail === '') continue;
    result.push({
      id:          data[i][0],
      name:        data[i][1],
      category:    data[i][2],
      description: data[i][3],
      somoni:      data[i][4],
      unit:        data[i][5],
      image_url:   data[i][6],
      available:   data[i][7],
    });
  }
  return result;
}
