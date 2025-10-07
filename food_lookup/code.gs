/** ===================== CONFIG ===================== **/
const SPREADSHEET_ID = '1DqrzUf3oFzbwIzCdAnCA0jEVeYSWNzts_4xSKlHjWtY';
const SHEET_NAME = 'Schema';
const HEADER_ROW = 1;

// Branding
const CHURCH_NAME = 'Holy Spirit Generation';
const CONFERENCE_NAME = 'Voice of Apostles';

/** SCHEMA (must match header row in the sheet exactly) **/
const HEADERS = [
  'ID','Name','Gender','Age','Phone','Email','Church Name','Type of Member',
  'City','State','Country','Aggregate','QR Code','Food Included','Paid for Food','VIPs','VVIPs','Registration'
];

/** ===================== SHEET HELPERS ===================== **/
function getSheet_() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID.trim());
  return ss.getSheetByName(SHEET_NAME) || ss.getSheets()[0];
}

function getHeaders_() {
  const sh = getSheet_();
  return sh.getRange(HEADER_ROW, 1, 1, sh.getLastColumn()).getValues()[0];
}

function colIndex_(name) {
  const idx = getHeaders_().indexOf(name);
  if (idx === -1) throw new Error(`Column "${name}" not found.`);
  return idx + 1;
}

/** ===================== DATA LOADING ===================== **/
function getAllData() {
  console.log('Loading all data from sheet...');
  const sh = getSheet_();
  const headers = getHeaders_();
  const dataRange = sh.getRange(HEADER_ROW + 1, 1, Math.max(0, sh.getLastRow() - HEADER_ROW), headers.length);
  const rawData = dataRange.getValues();
  
  const allRecords = [];
  
  // Process each row
  rawData.forEach((row, index) => {
    const record = {};
    headers.forEach((header, colIndex) => {
      record[header] = row[colIndex];
    });
    
    // Pre-calculate food status
    const city = String(record['City'] || '').trim().toLowerCase();
    const isNotBangalore = city !== 'bangalore' && city !== 'bengaluru' && city !== '';
    const paidForFood = String(record['Paid for Food'] || '').toLowerCase() === 'yes';
    const foodIncluded = String(record['Food Included'] || '').toLowerCase() === 'yes';
    
    const hasFood = isNotBangalore || paidForFood || foodIncluded;
    
    allRecords.push({
      name: record['Name'] || '',
      phone: record['Phone'] || '',
      email: record['Email'] || '',
      city: record['City'] || '',
      typeOfMember: record['Type of Member'] || '',
      aggregate: String(record['Aggregate'] || '').trim().toLowerCase(),
      hasFood: hasFood
    });
  });
  
  console.log(`Loaded ${allRecords.length} records`);
  return allRecords;
}

/** ===================== CORE LOOKUP FUNCTIONS ===================== **/
function lookupByAggregate(aggText) {
  if (!aggText || !String(aggText).trim()) {
    return { status: 'ERROR', message: 'Empty scan.' };
  }
  
  const data = getAllData();
  const needle = String(aggText).trim().toLowerCase();
  const found = data.find(record => record.aggregate === needle);
  
  if (!found) {
    return { status: 'NOT_FOUND', aggregate: aggText };
  }
  
  return {
    status: 'FOUND',
    attendee: {
      name: found.name,
      phone: found.phone,
      email: found.email,
      city: found.city,
      typeOfMember: found.typeOfMember
    },
    hasFood: found.hasFood
  };
}

function searchAttendees(query) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) {
    return { items: [] };
  }
  
  const data = getAllData();
  
  // Simple substring search for speed
  const results = data.filter(record => {
    const searchText = [
      record.name || '',
      record.phone || '',
      record.email || ''
    ].join(' ').toLowerCase();
    
    return searchText.includes(q);
  }).slice(0, 20);
  
  return { items: results };
}

/** ===================== UI ===================== **/
function doGet(e) {
  const tmpl = HtmlService.createTemplateFromFile('index');
  tmpl.churchName = CHURCH_NAME;
  tmpl.conferenceName = CONFERENCE_NAME;
  return tmpl.evaluate()
    .setTitle(`Food Lookup • ${CONFERENCE_NAME} • ${CHURCH_NAME}`)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function include(name) {
  return HtmlService.createHtmlOutputFromFile(name).getContent();
}

/** ===================== INITIALIZATION ===================== **/
function initializeApp() {
  try {
    const data = getAllData();
    return { 
      status: 'OK', 
      message: `Loaded ${data.length} records for fast lookup`,
      recordCount: data.length,
      data: data
    };
  } catch (error) {
    return { 
      status: 'ERROR', 
      message: `Failed to load data: ${error.toString()}` 
    };
  }
}
