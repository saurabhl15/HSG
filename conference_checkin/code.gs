/** ===================== CONFIG ===================== **/
const SPREADSHEET_ID = '1AsQHbIftBxuZyziVyiGaezKmsSVkG5xrAD9IOmbTScs';
const SHEET_NAME = 'Schema';
const HEADER_ROW = 1;

// Branding
const CHURCH_NAME = 'Holy Spirit Generation';
const CONFERENCE_NAME = 'Voice of Apostles';

/** SCHEMA (must match header row in the sheet exactly) **/
const HEADERS = [
  'ID','Name','Gender','Age','Phone','Email','Church Name','Type of Member',
  'City','State','Country','Aggregate','QR Code','Food Included','Paid for Food'
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
function getRecordByRow_(row) {
  const sh = getSheet_();
  const headers = getHeaders_();
  const data = sh.getRange(row, 1, 1, headers.length).getValues()[0];
  const rec = {};
  headers.forEach((h, i) => rec[h] = data[i]);
  rec._row = row;
  return rec;
}

/** ===================== MATCH BY AGGREGATE ===================== **/
function findRowByAggregate_(aggText) {
  if (!aggText || !String(aggText).trim()) return -1;
  const needle = String(aggText).trim();

  const sh = getSheet_();
  const aggCol = colIndex_('Aggregate');
  const rng = sh.getRange(HEADER_ROW + 1, aggCol, Math.max(0, sh.getLastRow() - HEADER_ROW), 1);
  const vals = rng.getValues();
  for (let i = 0; i < vals.length; i++) {
    if (String(vals[i][0]).trim() === needle) {
      const row = HEADER_ROW + 1 + i;
      return row;
    }
  }
  return -1;
}

/** ===================== SESSIONS ===================== **/
function ensureSessionColumn(sessionName) {
  if (!sessionName || !String(sessionName).trim()) throw new Error('Session name required');
  const lock = LockService.getScriptLock();
  lock.tryLock(30000);
  try {
    const sh = getSheet_();
    const headers = getHeaders_();
    const foundIdx = headers.indexOf(sessionName);
    if (foundIdx !== -1) return { ok: true, existed: true, col: foundIdx + 1 };
    const lastCol = sh.getLastColumn();
    sh.insertColumnAfter(lastCol); // never overwrite
    const newCol = lastCol + 1;
    sh.getRange(HEADER_ROW, newCol).setValue(sessionName);
    SpreadsheetApp.flush();
    return { ok: true, existed: false, col: newCol };
  } finally {
    lock.releaseLock();
  }
}
function startSession(sessionName) {
  if (!sessionName || !String(sessionName).trim())
    return { status: 'ERROR', message: 'Please provide a session name.' };
  const headers = getHeaders_();
  const idx = headers.indexOf(sessionName);
  if (idx !== -1) return { status: 'EXISTS', sessionName, col: idx + 1 };

  const sh = getSheet_();
  const lock = LockService.getScriptLock();
  lock.tryLock(30000);
  try {
    const lastCol = sh.getLastColumn();
    sh.insertColumnAfter(lastCol);
    const newCol = lastCol + 1;
    sh.getRange(HEADER_ROW, newCol).setValue(sessionName);
    SpreadsheetApp.flush();
    return { status: 'CREATED', sessionName, col: newCol };
  } finally {
    lock.releaseLock();
  }
}

/** ========= FORMULA EXTENSION HELPERS (ID & Aggregate copy-down) ========= **/
/**
 * Copy the nearest prior formula in column "col" to "targetRow".
 * If no formula above, do nothing (leaves cell empty).
 */
function copyDownFormulaFromAbove_(col, targetRow){
  const sh = getSheet_();
  // walk upwards to find the nearest formula
  for (let r = targetRow - 1; r >= HEADER_ROW + 1; r--){
    const f = sh.getRange(r, col).getFormula();
    if (f && f.trim() !== ''){ // found a formula: copy exactly (keeps relative references correct)
      sh.getRange(r, col).copyTo(sh.getRange(targetRow, col), {contentsOnly:false});
      return true;
    }
  }
  return false;
}

/** ===================== CORE OPS ===================== **/
function lookupByAggregate(aggText) {
  if (!aggText || !String(aggText).trim())
    return { status: 'ERROR', message: 'Empty scan.' };
  const row = findRowByAggregate_(aggText);
  if (row === -1) return { status: 'NOT_FOUND', aggregate: aggText };
  const rec = getRecordByRow_(row);
  return {
    status: 'FOUND',
    row,
    attendee: rec,
    view: {
      id: rec['ID'],
      name: rec['Name'],
      gender: rec['Gender'],
      typeOfMember: rec['Type of Member'],
      foodIncluded: rec['Food Included'] || '',
      paidForFood: rec['Paid for Food'] || ''
    }
  };
}

function togglePaidForFood(row, explicitValue) {
  const sh = getSheet_();
  const col = colIndex_('Paid for Food');
  const curr = String(sh.getRange(row, col).getValue() || '').trim().toLowerCase();
  let next;
  if (typeof explicitValue === 'boolean') next = explicitValue ? 'Yes' : 'No';
  else next = (curr === 'yes') ? 'No' : 'Yes';
  sh.getRange(row, col).setValue(next);
  return getRecordByRow_(row);
}

function checkInByAggregate(aggText, sessionName) {
  if (!aggText || !String(aggText).trim())
    return { status: 'ERROR', message: 'Empty scan.' };
  if (!sessionName || !String(sessionName).trim())
    return { status: 'ERROR', message: 'No session set.' };

  const row = findRowByAggregate_(aggText);
  if (row === -1) return { status: 'NOT_FOUND', aggregate: aggText };

  const sessionCol = ensureSessionColumn(sessionName).col;
  const sh = getSheet_();
  sh.getRange(row, sessionCol).setValue('Yes');
  const ts = new Date();
  const cell = sh.getRange(row, sessionCol);
  const prev = cell.getNote() || '';
  cell.setNote(`${prev}\nChecked in: ${ts.toLocaleString()}`);
  return { status: 'CHECKED_IN', row, attendee: getRecordByRow_(row) };
}

/**
 * Spot Registration
 * - No Aggregate asked
 * - No random ID; formulas fill ID & Aggregate
 * - Optionally check in immediately (if sessionName provided)
 */
function spotRegister(att, sessionName) {
  console.log('spotRegister called with:', att, sessionName);
  const sh = getSheet_();

  // Build row: leave ID/Aggregate blank – formulas will populate
  const rowVals = HEADERS.map(h => {
    if (h in att) return att[h] || '';
    if (h === 'Church Name') return CHURCH_NAME;
    return '';
  });

  const newRow = sh.getLastRow() + 1;
  console.log('Adding new row at:', newRow);
  
  // Add the row with data
  sh.getRange(newRow, 1, 1, HEADERS.length).setValues([rowVals]);
  
  // Handle ID and Aggregate columns
  const idCol = colIndex_('ID');
  const aggCol = colIndex_('Aggregate');
  
  // Manually increment ID value
  if (newRow > HEADER_ROW + 1) {
    try {
      // Get the last ID value
      const lastIdValue = sh.getRange(newRow - 1, idCol).getValue();
      console.log('Last ID value:', lastIdValue);
      
      if (lastIdValue && String(lastIdValue).startsWith('VOA')) {
        // Extract the number part and increment it
        const idStr = String(lastIdValue);
        const numberPart = idStr.substring(3); // Remove "VOA" prefix
        const nextNumber = parseInt(numberPart) + 1;
        const newId = 'VOA' + nextNumber.toString();
        
        // Set the new ID value
        sh.getRange(newRow, idCol).setValue(newId);
        console.log('New ID set:', newId);
      } else {
        // If no previous ID or format doesn't match, start with VOA1
        sh.getRange(newRow, idCol).setValue('VOA1');
        console.log('Starting with VOA1');
      }
    } catch(e) {
      console.log('Error setting ID value:', e);
      // Fallback to VOA1
      sh.getRange(newRow, idCol).setValue('VOA1');
    }
  } else {
    // First data row, start with VOA1
    sh.getRange(newRow, idCol).setValue('VOA1');
    console.log('First row, starting with VOA1');
  }
  
  // Copy Aggregate formula from the row above
  if (newRow > HEADER_ROW + 1) {
    try {
      sh.getRange(newRow - 1, aggCol).copyTo(sh.getRange(newRow, aggCol), {contentsOnly: false});
      console.log('Aggregate formula copied');
    } catch(e) {
      console.log('Error copying Aggregate formula:', e);
    }
  }

  // Optional immediate check-in
  if (sessionName && String(sessionName).trim()) {
    const sessionCol = ensureSessionColumn(sessionName).col;
    sh.getRange(newRow, sessionCol).setValue('Yes');
    const ts = new Date();
    const cell = sh.getRange(newRow, sessionCol);
    const prev = cell.getNote() || '';
    cell.setNote(`${prev}\nChecked in via Spot Reg: ${ts.toLocaleString()}`);
    console.log('Checked in to session:', sessionName);
  }

  // Get the final attendee record
  const attendee = getRecordByRow_(newRow);
  console.log('Final attendee record:', attendee);
  
  const result = { 
    status: 'ADDED', 
    row: newRow, 
    attendee: attendee
  };
  
  console.log('Returning result:', result);
  return result;
}

/** ===================== SEARCH / LOOKUP ===================== **/
/**
 * Simple search over Name / Phone / Email (case-insensitive, substring).
 * Returns up to 20 rows. Session name is accepted only for future extensions.
 */
function searchAttendees(query, _sessionName){
  const q = String(query || '').trim().toLowerCase();
  if (!q) return {items:[]};
  const sh = getSheet_();
  const headers = getHeaders_();
  const nameI = headers.indexOf('Name');
  const phoneI = headers.indexOf('Phone');
  const emailI = headers.indexOf('Email');

  const rng = sh.getRange(HEADER_ROW + 1, 1, Math.max(0, sh.getLastRow() - HEADER_ROW), headers.length);
  const data = rng.getValues();
  const results = [];
  for (let r=0; r<data.length; r++){
    const row = data[r];
    const hay = [
      String(row[nameI]||'').toLowerCase(),
      String(row[phoneI]||'').toLowerCase(),
      String(row[emailI]||'').toLowerCase()
    ].join(' ');
    if (hay.includes(q)){
      const rec = {};
      headers.forEach((h,i)=>rec[h]=row[i]);
      rec._row = HEADER_ROW + 1 + r;
      results.push(rec);
      if (results.length >= 20) break;
    }
  }
  return {items:results};
}
function getByRow(row){
  return {attendee:getRecordByRow_(row)};
}

/** ===================== STATS ===================== **/
function getSessionStats(sessionName) {
  if (!sessionName || !String(sessionName).trim())
    return { status: 'ERROR', message: 'Please set a session name.' };

  const headers = getHeaders_();
  const idx = headers.indexOf(sessionName);
  if (idx === -1) return { status: 'OK', session: sessionName, totalCheckedIn: 0, withFoodAmongCheckedIn: 0, bangalore: 0, outstation: 0 };

  const sh = getSheet_();
  const data = sh.getRange(HEADER_ROW + 1, 1, Math.max(0, sh.getLastRow() - HEADER_ROW), sh.getLastColumn()).getValues();
  const colSession = idx, colFoodInc = headers.indexOf('Food Included'), colPaid = headers.indexOf('Paid for Food'), colCity = headers.indexOf('City');
  let total = 0, withFood = 0, bangalore = 0, outstation = 0;
  data.forEach(r => {
    if (String(r[colSession] || '').trim().toLowerCase() === 'yes') {
      total++;
      if (String(r[colFoodInc] || '').toLowerCase() === 'yes' || String(r[colPaid] || '').toLowerCase() === 'yes') withFood++;
      
      // Check if Bangalore or Outstation
      const city = String(r[colCity] || '').trim().toLowerCase();
      if (city === 'bangalore' || city === 'bengaluru') {
        bangalore++;
      } else if (city && city !== '') {
        outstation++;
      }
    }
  });
  return { status: 'OK', session: sessionName, totalCheckedIn: total, withFoodAmongCheckedIn: withFood, bangalore: bangalore, outstation: outstation };
}

/** ===================== UI ===================== **/
function doGet(e) {
  const tmpl = HtmlService.createTemplateFromFile('index');
  tmpl.session = (e && e.parameter && e.parameter.session) || '';
  tmpl.churchName = CHURCH_NAME;
  tmpl.conferenceName = CONFERENCE_NAME;
  return tmpl.evaluate()
    .setTitle(`${CONFERENCE_NAME} • ${CHURCH_NAME}`)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
function include(name) {
  return HtmlService.createHtmlOutputFromFile(name).getContent();
}
