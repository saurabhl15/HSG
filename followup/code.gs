/**
 * Holy Spirit Generation Follow-Up App – Sheet access flow (Task 1).
 *
 * This module verifies the Google Sheet structure and enforces Gmail-based
 * volunteer access before exposing any backend functionality.
 */

/**
 * Update these configuration values for the production spreadsheet.
 */
const SHEET_CONFIG = Object.freeze({
  /**
   * Primary follow-up spreadsheet ID.
   * Example: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
   */
  spreadsheetId: '150NFsI3LVM4FIdcOcQNuJKEET9btxjpkAM7R9A318uE',

  /**
   * Sheet tab containing newcomer follow-up records.
   */
  dataSheetName: 'Newcomers',

  /**
   * Sheet tab containing the volunteer access control list (ACL).
   */
  accessSheetName: 'Volunteer Access',

  /**
   * Sheet tab that stores newcomer update history snapshots.
   */
  historySheetName: 'Newcomer Update History',

  /**
   * Expected headers in the history sheet (row 1).
   */
  historyHeaders: [
    'Record Id',
    'Updated At',
    'Updated By',
    'Updated By Name',
    'Changes JSON'
  ],

  /**
   * Expected headers in the newcomer data sheet (row 1).
   */
  requiredDataHeaders: [
    'Record Id',
    'Newcomer Name',
    'Contact Number',
    'Location',
    'Outstation',
    'Assigned Volunteer Name',
    'Assigned Volunteer Email',
    'Last Attendance',
    'Regularity',
    'Powerhouse Status',
    'Powerhouse Name',
    'Last Comment',
    'Last Updated At',
    'Last Updated By'
  ],

  /**
   * Expected headers in the volunteer ACL sheet (row 1).
   */
  requiredAccessHeaders: [
    'Volunteer Email',
    'Volunteer Name',
    'Is Active (Y/N)'
  ]
});

/**
 * Domains permitted to access the follow-up app. Gmail is considered the
 * default volunteer domain, but coordinators can add additional domains here
 * when necessary (e.g., staff accounts).
 */
const ALLOWED_EMAIL_DOMAINS = Object.freeze([
  'gmail.com',
  'rwo.life'
]);

/**
 * Task 4 – Weekly update configuration.
 */
const WEEKLY_UPDATE_CONFIG = Object.freeze({
  /**
   * Maximum number of weeks to retain in the `Regularity` sequence.
   */
  maxRegularityLength: 8,

  /**
   * Attendance tokens recognized as "present".
   */
  positiveAttendanceTokens: Object.freeze(['Y', 'YES', 'P', 'PRESENT', '1', 'TRUE']),

  /**
   * Attendance tokens recognized as "absent".
   */
  negativeAttendanceTokens: Object.freeze(['N', 'NO', 'A', 'ABSENT', '0', 'FALSE'])
});

/**
 * Task 5 – Overdue follow-up highlighting configuration.
 */
const OVERDUE_FOLLOW_UP_CONFIG = Object.freeze({
  /**
   * Number of full days without an update before a newcomer is considered overdue.
   */
  staleThresholdDays: 7
});

/**
 * Millisecond constant used for date-difference calculations.
 */
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;

/**
 * Normalizes a raw attendance value into a single-character token (`Y` or `N`).
 * Empty/undefined values return an empty string to support clearing the field.
 * @param {*=} value
 * @returns {string}
 */
function normalizeAttendanceValue_(value) {
  if (value === null || typeof value === 'undefined') {
    return '';
  }

  if (typeof value === 'boolean') {
    return value ? 'Y' : 'N';
  }

  if (typeof value === 'number') {
    if (value === 1) {
      return 'Y';
    }
    if (value === 0) {
      return 'N';
    }
  }

  var stringValue = String(value).trim();
  if (stringValue === '') {
    return '';
  }

  var upperValue = stringValue.toUpperCase();
  if (WEEKLY_UPDATE_CONFIG.positiveAttendanceTokens.indexOf(upperValue) !== -1) {
    return 'Y';
  }
  if (WEEKLY_UPDATE_CONFIG.negativeAttendanceTokens.indexOf(upperValue) !== -1) {
    return 'N';
  }

  throw createAppError_(
    'INVALID_ATTENDANCE',
    'Attendance value must resolve to Y/N (accepted: Y/N, Yes/No, Present/Absent, true/false, 1/0).',
    400,
    { value: value }
  );
}

/**
 * Normalizes a historical regularity sequence to only `Y`/`N` characters and
 * enforces the configured maximum length (tail is preserved).
 * @param {*=} value
 * @returns {string}
 */
function normalizeRegularitySequence_(value) {
  if (value === null || typeof value === 'undefined') {
    return '';
  }

  var rawSequence;
  if (Array.isArray(value)) {
    rawSequence = value.join('');
  } else {
    rawSequence = String(value);
  }

  if (rawSequence === '') {
    return '';
  }

  var cleaned = rawSequence
    .toUpperCase()
    .replace(/[^YN]/g, '');

  if (cleaned === '') {
    return '';
  }

  var maxLength = WEEKLY_UPDATE_CONFIG.maxRegularityLength;
  if (typeof maxLength === 'number' && maxLength > 0 && cleaned.length > maxLength) {
    cleaned = cleaned.substring(cleaned.length - maxLength);
  }

  return cleaned;
}

/**
 * Appends an attendance token to an existing regularity sequence while keeping
 * only the most recent `maxRegularityLength` values.
 * @param {string} currentSequence
 * @param {string} attendanceToken
 * @returns {string}
 */
function appendAttendanceToRegularity_(currentSequence, attendanceToken) {
  var normalizedAttendance = typeof attendanceToken === 'string'
    ? attendanceToken.trim().toUpperCase()
    : '';

  if (normalizedAttendance !== 'Y' && normalizedAttendance !== 'N') {
    return normalizeRegularitySequence_(currentSequence);
  }

  var normalizedSequence = normalizeRegularitySequence_(currentSequence);
  var candidate = normalizedSequence ? normalizedSequence + normalizedAttendance : normalizedAttendance;
  var maxLength = WEEKLY_UPDATE_CONFIG.maxRegularityLength;

  if (typeof maxLength === 'number' && maxLength > 0 && candidate.length > maxLength) {
    candidate = candidate.substring(candidate.length - maxLength);
  }

  return candidate;
}

/**
 * Cached spreadsheet handle.
 * @returns {GoogleAppsScript.Spreadsheet.Spreadsheet}
 */
function getFollowUpSpreadsheet_() {
  if (!SHEET_CONFIG.spreadsheetId || SHEET_CONFIG.spreadsheetId === 'REPLACE_WITH_SPREADSHEET_ID') {
    throw new Error('SHEET_CONFIG.spreadsheetId must be set to the production Google Sheet ID.');
  }

  return SpreadsheetApp.openById(SHEET_CONFIG.spreadsheetId);
}

/**
 * Retrieves the headers from the first row of a sheet.
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet
 * @returns {string[]}
 */
function getSheetHeaders_(sheet) {
  var lastColumn = sheet.getLastColumn();
  if (lastColumn === 0) {
    return [];
  }

  var headerValues = sheet.getRange(1, 1, 1, lastColumn).getValues();
  return headerValues[0].map(function (header) {
    return header ? String(header).trim() : '';
  });
}

/**
 * Compares actual sheet headers against a required schema.
 * @param {string[]} actualHeaders
 * @param {string[]} requiredHeaders
 * @returns {{missing: string[], unexpected: string[]}}
 */
function analyzeHeaderDiscrepancies_(actualHeaders, requiredHeaders) {
  var normalizedActual = actualHeaders.filter(function (header) {
    return header !== '';
  });

  var missing = requiredHeaders.filter(function (requiredHeader) {
    return normalizedActual.indexOf(requiredHeader) === -1;
  });

  var unexpected = normalizedActual.filter(function (header) {
    return requiredHeaders.indexOf(header) === -1;
  });

  return {
    missing: missing,
    unexpected: unexpected
  };
}

/**
 * Validates the newcomer data sheet structure.
 * @returns {{
 *   sheetName: string,
 *   headers: string[],
 *   missingHeaders: string[],
 *   unexpectedHeaders: string[],
 *   isValid: boolean
 * }}
 */
function validateDataSheetStructure() {
  var spreadsheet = getFollowUpSpreadsheet_();
  var dataSheet = spreadsheet.getSheetByName(SHEET_CONFIG.dataSheetName);
  if (!dataSheet) {
    throw new Error('Data sheet "' + SHEET_CONFIG.dataSheetName + '" was not found.');
  }

  var headers = getSheetHeaders_(dataSheet);
  var discrepancies = analyzeHeaderDiscrepancies_(headers, SHEET_CONFIG.requiredDataHeaders);

  return {
    sheetName: SHEET_CONFIG.dataSheetName,
    headers: headers,
    missingHeaders: discrepancies.missing,
    unexpectedHeaders: discrepancies.unexpected,
    isValid: discrepancies.missing.length === 0
  };
}

/**
 * Validates the volunteer ACL sheet structure.
 * @returns {{
 *   sheetName: string,
 *   headers: string[],
 *   missingHeaders: string[],
 *   unexpectedHeaders: string[],
 *   isValid: boolean
 * }}
 */
function validateAccessSheetStructure() {
  var spreadsheet = getFollowUpSpreadsheet_();
  var accessSheet = spreadsheet.getSheetByName(SHEET_CONFIG.accessSheetName);
  if (!accessSheet) {
    throw new Error('Access control sheet "' + SHEET_CONFIG.accessSheetName + '" was not found.');
  }

  var headers = getSheetHeaders_(accessSheet);
  var discrepancies = analyzeHeaderDiscrepancies_(headers, SHEET_CONFIG.requiredAccessHeaders);

  return {
    sheetName: SHEET_CONFIG.accessSheetName,
    headers: headers,
    missingHeaders: discrepancies.missing,
    unexpectedHeaders: discrepancies.unexpected,
    isValid: discrepancies.missing.length === 0
  };
}

/**
 * Validates the update history sheet structure.
 * @returns {{
 *   sheetName: string,
 *   headers: string[],
 *   missingHeaders: string[],
 *   unexpectedHeaders: string[],
 *   isValid: boolean,
 *   isPresent: boolean
 * }}
 */
function validateHistorySheetStructure() {
  var spreadsheet = getFollowUpSpreadsheet_();
  var historySheet = spreadsheet.getSheetByName(SHEET_CONFIG.historySheetName);
  if (!historySheet) {
    return {
      sheetName: SHEET_CONFIG.historySheetName,
      headers: [],
      missingHeaders: SHEET_CONFIG.historyHeaders.slice(),
      unexpectedHeaders: [],
      isValid: false,
      isPresent: false
    };
  }

  var headers = getSheetHeaders_(historySheet);
  var discrepancies = analyzeHeaderDiscrepancies_(headers, SHEET_CONFIG.historyHeaders);

  return {
    sheetName: SHEET_CONFIG.historySheetName,
    headers: headers,
    missingHeaders: discrepancies.missing,
    unexpectedHeaders: discrepancies.unexpected,
    isValid: discrepancies.missing.length === 0 && discrepancies.unexpected.length === 0,
    isPresent: true
  };
}

/**
 * Returns the volunteer access control list.
 * Volunteers must have "Is Active (Y/N)" set to "Y".
 * @returns {{email: string, name: string, isActive: boolean, raw: *[]}[]}
 */
function getVolunteerAccessList_() {
  var accessValidation = validateAccessSheetStructure();
  if (!accessValidation.isValid) {
    throw new Error(
      'Volunteer access sheet is missing required headers: ' + accessValidation.missingHeaders.join(', ')
    );
  }

  var spreadsheet = getFollowUpSpreadsheet_();
  var accessSheet = spreadsheet.getSheetByName(SHEET_CONFIG.accessSheetName);
  var lastRow = accessSheet.getLastRow();
  if (lastRow < 2) {
    return [];
  }

  var headerPositions = {};
  accessValidation.headers.forEach(function (header, index) {
    headerPositions[header] = index;
  });

  var values = accessSheet.getRange(2, 1, lastRow - 1, accessSheet.getLastColumn()).getValues();

  return values
    .map(function (row) {
      var email = String(row[headerPositions['Volunteer Email']] || '').trim().toLowerCase();
      var name = String(row[headerPositions['Volunteer Name']] || '').trim();
      var isActive = String(row[headerPositions['Is Active (Y/N)']] || '').trim().toUpperCase() === 'Y';

      return {
        email: email,
        name: name,
        isActive: isActive,
        raw: row
      };
    })
    .filter(function (entry) {
      return entry.email !== '';
    });
}

/**
 * Ensures the current Apps Script session user is an authorized volunteer.
 * @returns {{
 *   email: string,
 *   authorized: boolean,
 *   reason?: string,
 *   matchedVolunteer?: {email: string, name: string}
 * }}
 */
function ensureAuthorizedVolunteer() {
  // Try getActiveUser first (works for google.script.run context)
  var activeEmail = null;
  try {
    var activeUser = Session.getActiveUser();
    if (activeUser) {
      activeEmail = activeUser.getEmail();
    }
  } catch (e) {
    Logger.log('getActiveUser failed: ' + e.message);
  }

  // Fallback to getEffectiveUser (works for web app deployments)
  if (!activeEmail) {
    try {
      var effectiveUser = Session.getEffectiveUser();
      if (effectiveUser) {
        activeEmail = effectiveUser.getEmail();
      }
    } catch (e) {
      Logger.log('getEffectiveUser failed: ' + e.message);
    }
  }

  if (!activeEmail) {
    return {
      email: '',
      authorized: false,
      reason: 'No active user email found. Ensure you are logged into your Google account and the app is deployed with "Execute as: User accessing the app".'
    };
  }

  var normalizedEmail = activeEmail.trim().toLowerCase();

  var domain = normalizedEmail.split('@')[1] || '';
  var domainAllowed = ALLOWED_EMAIL_DOMAINS.some(function (allowedDomain) {
    return domain === allowedDomain;
  });

  if (!domainAllowed) {
    return {
      email: normalizedEmail,
      authorized: false,
      reason: 'Only authorized volunteer domains are permitted. Please switch to an approved account (' +
        ALLOWED_EMAIL_DOMAINS.join(', ') + ').'
    };
  }

  var volunteerRecords = getVolunteerAccessList_();
  var match = volunteerRecords.find(function (record) {
    return record.email === normalizedEmail && record.isActive;
  });

  if (!match) {
    return {
      email: normalizedEmail,
      authorized: false,
      reason: 'Your Gmail is not listed as an active volunteer. Contact the coordinator to request access.'
    };
  }

  return {
    email: normalizedEmail,
    authorized: true,
    matchedVolunteer: {
      email: match.email,
      name: match.name
    }
  };
}

/**
 * Task 2 – Volunteer filtering logic helpers and entry points.
 */

/**
 * Normalizes volunteer email addresses for comparison.
 * @param {string|*} email
 * @returns {string}
 */
function normalizeVolunteerEmail_(email) {
  return String(email || '')
    .trim()
    .toLowerCase();
}

/**
 * Returns the local-part (before "@") of a normalized email.
 * @param {string} email
 * @returns {string}
 */
function getEmailLocalPart_(email) {
  var normalized = normalizeVolunteerEmail_(email);
  var parts = normalized.split('@');
  return parts.length > 1 ? parts[0] : normalized;
}

/**
 * Canonicalizes a volunteer name into a lowercase, punctuation-light format.
 * @param {string|*} name
 * @returns {string}
 */
function canonicalizeVolunteerName_(name) {
  return String(name || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Deduplicates string arrays while removing falsy entries.
 * @param {string[]} values
 * @returns {string[]}
 */
function uniqueStrings_(values) {
  var seen = Object.create(null);
  var result = [];

  values.forEach(function (value) {
    if (!value) {
      return;
    }
    var key = String(value);
    if (!seen[key]) {
      seen[key] = true;
      result.push(key);
    }
  });

  return result;
}

/**
 * Builds a lookup table (object map) for quick membership checks.
 * @param {string[]} values
 * @returns {Object.<string, boolean>}
 */
function createLookup_(values) {
  var lookup = Object.create(null);
  values.forEach(function (value) {
    lookup[value] = true;
  });
  return lookup;
}

/**
 * Task 3 – Data API configuration.
 */
const MUTABLE_DATA_HEADERS = Object.freeze([
  'Last Attendance',
  'Regularity',
  'Powerhouse Status',
  'Last Comment'
]);

const MUTABLE_DATA_HEADER_LOOKUP = Object.freeze(createLookup_(MUTABLE_DATA_HEADERS));

const API_FIELD_TO_HEADER_MAP = Object.freeze({
  lastattendance: 'Last Attendance',
  'last attendance': 'Last Attendance',
  lastAttendance: 'Last Attendance',
  regularity: 'Regularity',
  powerhousestatus: 'Powerhouse Status',
  'powerhouse status': 'Powerhouse Status',
  powerhouseStatus: 'Powerhouse Status',
  lastcomment: 'Last Comment',
  'last comment': 'Last Comment',
  lastComment: 'Last Comment'
});

/**
 * Generates normalized name metadata and aliases for matching.
 * @param {string|*} rawName
 * @returns {{
 *   canonical: string,
 *   compact: string,
 *   firstName: string,
 *   lastName: string,
 *   lastInitial: string,
 *   isSingleToken: boolean,
 *   aliases: string[]
 * }}
 */
function buildNameProfile_(rawName) {
  var canonical = canonicalizeVolunteerName_(rawName);
  if (!canonical) {
    return {
      canonical: '',
      compact: '',
      firstName: '',
      lastName: '',
      lastInitial: '',
      isSingleToken: true,
      aliases: []
    };
  }

  var parts = canonical.split(' ');
  var firstName = parts[0] || '';
  var lastName = parts.length > 1 ? parts[parts.length - 1] : '';
  var lastInitial = lastName ? lastName.charAt(0) : '';
  var compact = canonical.replace(/\s+/g, '');

  var aliasCandidates = [
    canonical,
    compact
  ];

  if (firstName) {
    aliasCandidates.push(firstName);
  }
  if (firstName && lastInitial) {
    aliasCandidates.push(firstName + lastInitial);
    aliasCandidates.push(firstName + ' ' + lastInitial);
  }

  return {
    canonical: canonical,
    compact: compact,
    firstName: firstName,
    lastName: lastName,
    lastInitial: lastInitial,
    isSingleToken: parts.length === 1,
    aliases: uniqueStrings_(aliasCandidates)
  };
}

/**
 * Builds a unified identity object for volunteers and sheet rows.
 * @param {{email: string, name: string}} payload
 * @returns {{
 *   email: string,
 *   emailLocal: string,
 *   nameProfile: ReturnType<typeof buildNameProfile_>,
 *   tokens: string[],
 *   tokenLookup: Object.<string, boolean>
 * }}
 */
function buildVolunteerIdentity_(payload) {
  var normalizedEmail = normalizeVolunteerEmail_(payload && payload.email);
  var emailLocal = normalizedEmail ? getEmailLocalPart_(normalizedEmail) : '';
  var nameProfile = buildNameProfile_(payload && payload.name);

  var tokens = uniqueStrings_(
    []
      .concat(normalizedEmail || [])
      .concat(emailLocal || [])
      .concat(nameProfile.aliases)
  );

  return {
    email: normalizedEmail,
    emailLocal: emailLocal,
    nameProfile: nameProfile,
    tokens: tokens,
    tokenLookup: createLookup_(tokens)
  };
}

/**
 * Builds an identity object for a newcomer row.
 * @param {Object<string, *>} newcomerRecord
 * @returns {ReturnType<typeof buildVolunteerIdentity_> & {
 *   rawEmail: string,
 *   rawName: string
 * }}
 */
function buildRowVolunteerIdentity_(newcomerRecord) {
  var rawEmail = newcomerRecord['Assigned Volunteer Email'];
  var rawName = newcomerRecord['Assigned Volunteer Name'];

  var identity = buildVolunteerIdentity_({
    email: rawEmail,
    name: rawName
  });

  return Object.assign({}, identity, {
    rawEmail: rawEmail,
    rawName: rawName
  });
}

/**
 * Determines whether a newcomer row is assigned to the volunteer identity.
 * @param {ReturnType<typeof buildRowVolunteerIdentity_>} rowIdentity
 * @param {ReturnType<typeof buildVolunteerIdentity_>} volunteerIdentity
 * @returns {boolean}
 */
function rowMatchesVolunteer_(rowIdentity, volunteerIdentity) {
  if (!volunteerIdentity) {
    return false;
  }

  // Prefer exact email matches when available.
  if (rowIdentity.email && volunteerIdentity.email &&
      rowIdentity.email === volunteerIdentity.email) {
    return true;
  }

  // Match based on email local-part when sheet omits domain.
  if (rowIdentity.emailLocal && volunteerIdentity.emailLocal &&
      rowIdentity.emailLocal === volunteerIdentity.emailLocal) {
    return true;
  }

  // Compare alias tokens derived from names/emails.
  var sharedToken = rowIdentity.tokens.some(function (token) {
    return volunteerIdentity.tokenLookup[token];
  });
  if (sharedToken) {
    return true;
  }

  // Fallback: if the sheet only contains a single first name, align on first name.
  if (rowIdentity.nameProfile.isSingleToken &&
      rowIdentity.nameProfile.firstName &&
      rowIdentity.nameProfile.firstName === volunteerIdentity.nameProfile.firstName) {
    return true;
  }

  // Final fallback: first name + last initial combinations.
  if (rowIdentity.nameProfile.firstName &&
      rowIdentity.nameProfile.lastInitial &&
      rowIdentity.nameProfile.firstName === volunteerIdentity.nameProfile.firstName &&
      rowIdentity.nameProfile.lastInitial === volunteerIdentity.nameProfile.lastInitial) {
    return true;
  }

  return false;
}

/**
 * Diagnostic function to debug volunteer matching issues.
 * Run this from the Apps Script editor to see detailed matching information.
 * @returns {Object}
 */
function debugVolunteerMatching() {
  var authorization = ensureAuthorizedVolunteer();
  if (!authorization.authorized) {
    return {
      error: 'Not authorized',
      reason: authorization.reason
    };
  }

  var volunteer = authorization.matchedVolunteer;
  var volunteerIdentity = buildVolunteerIdentity_(volunteer);
  var allRecords = getDataSheetRecords_();
  
  var sampleRecords = allRecords.slice(0, 5).map(function(record) {
    var rowIdentity = buildRowVolunteerIdentity_(record);
    var matches = rowMatchesVolunteer_(rowIdentity, volunteerIdentity);
    return {
      recordId: record['Record Id'],
      newcomerName: record['Newcomer Name'],
      assignedVolunteerEmail: record['Assigned Volunteer Email'],
      assignedVolunteerName: record['Assigned Volunteer Name'],
      rowIdentity: {
        email: rowIdentity.email,
        emailLocal: rowIdentity.emailLocal,
        tokens: rowIdentity.tokens.slice(0, 5),
        nameProfile: {
          canonical: rowIdentity.nameProfile.canonical,
          firstName: rowIdentity.nameProfile.firstName,
          lastInitial: rowIdentity.nameProfile.lastInitial,
          isSingleToken: rowIdentity.nameProfile.isSingleToken
        }
      },
      matches: matches
    };
  });

  var result = {
    volunteer: volunteer,
    volunteerIdentity: {
      email: volunteerIdentity.email,
      emailLocal: volunteerIdentity.emailLocal,
      tokens: volunteerIdentity.tokens.slice(0, 10),
      nameProfile: {
        canonical: volunteerIdentity.nameProfile.canonical,
        firstName: volunteerIdentity.nameProfile.firstName,
        lastInitial: volunteerIdentity.nameProfile.lastInitial
      }
    },
    totalRecords: allRecords.length,
    sampleRecords: sampleRecords,
    matchedCount: filterNewcomerRecordsForVolunteer_(allRecords, volunteerIdentity).length
  };

  Logger.log(JSON.stringify(result, null, 2));
  return result;
}

/**
 * Builds a map of header titles to column indexes (zero-based).
 * @param {string[]} headers
 * @returns {Object.<string, number>}
 */
function buildHeaderIndexMap_(headers) {
  var map = Object.create(null);
  headers.forEach(function (header, index) {
    if (header) {
      map[header] = index;
    }
  });
  return map;
}

/**
 * Loads newcomer records from the sheet as objects keyed by header.
 * @returns {Object<string, *>[]}
 */
function getDataSheetRecords_() {
  var validation = validateDataSheetStructure();
  if (!validation.isValid) {
    throw new Error('Cannot load newcomer records: sheet schema validation failed.');
  }

  var spreadsheet = getFollowUpSpreadsheet_();
  var dataSheet = spreadsheet.getSheetByName(SHEET_CONFIG.dataSheetName);
  var lastRow = dataSheet.getLastRow();
  if (lastRow < 2) {
    return [];
  }

  var headers = validation.headers;
  var headerIndexMap = buildHeaderIndexMap_(headers);
  var lastColumn = dataSheet.getLastColumn();
  var values = dataSheet.getRange(2, 1, lastRow - 1, lastColumn).getValues();

  return values.map(function (rowValues, offset) {
    var record = {};
    headers.forEach(function (header) {
      var index = headerIndexMap[header];
      record[header] = typeof index === 'number' ? rowValues[index] : '';
    });
    record.__rowNumber = offset + 2; // Preserve sheet row index for updates/debugging.
    return record;
  });
}

/**
 * Filters newcomer records to those assigned to the provided volunteer identity.
 * @param {Object<string, *>[]} newcomerRecords
 * @param {ReturnType<typeof buildVolunteerIdentity_>} volunteerIdentity
 * @returns {Object<string, *>[]}
 */
function filterNewcomerRecordsForVolunteer_(newcomerRecords, volunteerIdentity) {
  if (!volunteerIdentity) {
    return [];
  }

  return newcomerRecords.filter(function (record) {
    var rowIdentity = buildRowVolunteerIdentity_(record);
    return rowMatchesVolunteer_(rowIdentity, volunteerIdentity);
  });
}

/**
 * Returns newcomer records assigned to the specified volunteer.
 * @param {{email: string, name: string}} volunteer
 * @returns {Object<string, *>[]}
 */
function getAssignedNewcomersForVolunteer(volunteer) {
  if (!volunteer || (!volunteer.email && !volunteer.name)) {
    Logger.log('WARNING: getAssignedNewcomersForVolunteer called with invalid volunteer: ' + JSON.stringify(volunteer));
    return [];
  }

  var volunteerIdentity = buildVolunteerIdentity_(volunteer || {});
  var newcomerRecords = getDataSheetRecords_();
  Logger.log('Total newcomer records in sheet: ' + newcomerRecords.length);
  
  if (newcomerRecords.length > 0) {
    Logger.log('Sample record volunteer assignment: ' + JSON.stringify({
      email: newcomerRecords[0]['Assigned Volunteer Email'],
      name: newcomerRecords[0]['Assigned Volunteer Name']
    }));
  }

  var filtered = filterNewcomerRecordsForVolunteer_(newcomerRecords, volunteerIdentity);
  Logger.log('Filtered to ' + filtered.length + ' records for volunteer: ' + JSON.stringify({
    email: volunteer.email,
    name: volunteer.name,
    identityEmail: volunteerIdentity.email,
    identityEmailLocal: volunteerIdentity.emailLocal,
    identityTokens: volunteerIdentity.tokens.slice(0, 5) // First 5 tokens
  }));
  
  return filtered;
}

/**
 * Convenience wrapper for the currently signed-in volunteer.
 * Returns records in API format (same as GET endpoint).
 * This function is called via google.script.run from the HTML frontend.
 * @returns {Object<string, *>[]}
 */
function listNewcomersForCurrentVolunteer() {
  var result = [];
  try {
    var authorization = ensureAuthorizedVolunteer();
    if (!authorization.authorized) {
      Logger.log('listNewcomersForCurrentVolunteer: Unauthorized - ' + (authorization.reason || 'Unknown reason'));
      // Return empty array instead of throwing for better error handling in frontend
      return [];
    }

    if (!authorization.matchedVolunteer) {
      Logger.log('WARNING: authorization.matchedVolunteer is missing');
      return [];
    }

    Logger.log('Getting newcomers for volunteer: ' + JSON.stringify(authorization.matchedVolunteer));
    var rawRecords = getAssignedNewcomersForVolunteer(authorization.matchedVolunteer);
    Logger.log('Found ' + rawRecords.length + ' assigned newcomers (raw)');
    
    if (!Array.isArray(rawRecords)) {
      Logger.log('ERROR: getAssignedNewcomersForVolunteer returned non-array: ' + typeof rawRecords);
      return [];
    }
    
    // Transform to API format for consistency with GET endpoint
    var apiRecords = buildNewcomerApiPayload_(rawRecords);
    Logger.log('Transformed to ' + apiRecords.length + ' API records');
    
    if (!Array.isArray(apiRecords)) {
      Logger.log('ERROR: buildNewcomerApiPayload_ returned non-array: ' + typeof apiRecords);
      return [];
    }
    
    // Ensure we have a valid array and sanitize for serialization
    result = apiRecords.map(function(record) {
      // Create a clean object with only serializable properties
      return {
        recordId: String(record.recordId || ''),
        newcomerName: String(record.newcomerName || ''),
        contactNumber: String(record.contactNumber || ''),
        location: String(record.location || ''),
        outstation: String(record.outstation || ''),
        assignedVolunteerName: String(record.assignedVolunteerName || ''),
        assignedVolunteerEmail: String(record.assignedVolunteerEmail || ''),
        lastAttendance: String(record.lastAttendance || ''),
        regularity: String(record.regularity || ''),
        powerhouseStatus: String(record.powerhouseStatus || ''),
        powerhouseName: String(record.powerhouseName || ''),
        lastComment: String(record.lastComment || ''),
        lastUpdatedAt: String(record.lastUpdatedAt || ''),
        lastUpdatedBy: String(record.lastUpdatedBy || ''),
        isOverdue: Boolean(record.isOverdue === true),
        daysSinceLastUpdate: typeof record.daysSinceLastUpdate === 'number' ? record.daysSinceLastUpdate : null,
        overdueThresholdDays: typeof record.overdueThresholdDays === 'number' ? record.overdueThresholdDays : null,
        regularityVisual: record.regularityVisual && typeof record.regularityVisual === 'object' ? record.regularityVisual : null
      };
    });
    
    Logger.log('Final result array length: ' + result.length);
    return result;
  } catch (error) {
    Logger.log('ERROR in listNewcomersForCurrentVolunteer: ' + error.message);
    Logger.log('Stack: ' + (error.stack || 'No stack trace'));
    // Return empty array instead of throwing to prevent frontend issues
    return [];
  }
}

/**
 * Sample scenarios intended for manual verification and logging.
 * Executes mock data through the filtering pipeline and writes results to Logger.
 * This can be invoked from the Apps Script editor.
 */
function runVolunteerFilteringSample() {
  var volunteer = {
    email: 'leader@example.com',
    name: 'Jane Doe'
  };
  var volunteerIdentity = buildVolunteerIdentity_(volunteer);

  var mockRecords = [
    {
      'Record Id': 1,
      'Newcomer Name': 'Alex Example',
      'Assigned Volunteer Name': 'Jane Doe',
      'Assigned Volunteer Email': 'leader@example.com'
    },
    {
      'Record Id': 2,
      'Newcomer Name': 'Bela Sample',
      'Assigned Volunteer Name': 'Jane D.',
      'Assigned Volunteer Email': ''
    },
    {
      'Record Id': 3,
      'Newcomer Name': 'Chris Test',
      'Assigned Volunteer Name': 'JANE',
      'Assigned Volunteer Email': ''
    },
    {
      'Record Id': 4,
      'Newcomer Name': 'Dana Control',
      'Assigned Volunteer Name': 'John Smith',
      'Assigned Volunteer Email': 'jsmith@example.com'
    }
  ];

  var filtered = filterNewcomerRecordsForVolunteer_(mockRecords, volunteerIdentity);
  Logger.log(JSON.stringify({
    volunteer: volunteer,
    filteredRecordIds: filtered.map(function (record) {
      return record['Record Id'];
    }),
    totalCandidates: mockRecords.length,
    matchedCount: filtered.length
  }, null, 2));

  return filtered;
}

/**
 * Aggregates start-up checks for the frontend shell.
 * @returns {{
 *   authorization: ReturnType<typeof ensureAuthorizedVolunteer>,
 *   dataSheet: ReturnType<typeof validateDataSheetStructure>,
 *   accessSheet: ReturnType<typeof validateAccessSheetStructure>
 * }}
 */
function getStartupStatus() {
  var authorization = ensureAuthorizedVolunteer();

  var dataSheetStatus;
  try {
    dataSheetStatus = validateDataSheetStructure();
  } catch (dataError) {
    dataSheetStatus = {
      sheetName: SHEET_CONFIG.dataSheetName,
      headers: [],
      missingHeaders: SHEET_CONFIG.requiredDataHeaders.slice(),
      unexpectedHeaders: [],
      isValid: false,
      error: dataError.message
    };
  }

  var accessSheetStatus;
  try {
    accessSheetStatus = validateAccessSheetStructure();
  } catch (accessError) {
    accessSheetStatus = {
      sheetName: SHEET_CONFIG.accessSheetName,
      headers: [],
      missingHeaders: SHEET_CONFIG.requiredAccessHeaders.slice(),
      unexpectedHeaders: [],
      isValid: false,
      error: accessError.message
    };
  }

  var historySheetStatus;
  try {
    historySheetStatus = validateHistorySheetStructure();
  } catch (historyError) {
    historySheetStatus = {
      sheetName: SHEET_CONFIG.historySheetName,
      headers: [],
      missingHeaders: SHEET_CONFIG.historyHeaders.slice(),
      unexpectedHeaders: [],
      isValid: false,
      error: historyError.message
    };
  }

  return {
    authorization: authorization,
    dataSheet: dataSheetStatus,
    accessSheet: accessSheetStatus,
    historySheet: historySheetStatus
  };
}

/**
 * Task 3 – Data API layer helpers.
 */

/**
 * Creates a standardized application error.
 * @param {string} code
 * @param {string} message
 * @param {number} status
 * @param {Object=} details
 * @returns {Error}
 */
function createAppError_(code, message, status, details) {
  var error = new Error(message || code || 'Application error');
  error.name = 'FollowUpAppError';
  error.code = code || 'APP_ERROR';
  error.status = status || 400;
  if (details) {
    error.details = details;
  }
  return error;
}

/**
 * Parses JSON input, throwing a normalized error on failure.
 * @param {string} raw
 * @returns {*}
 */
function parseJson_(raw) {
  if (!raw) {
    throw createAppError_('INVALID_JSON', 'Request body is empty.', 400);
  }

  try {
    return JSON.parse(raw);
  } catch (parseError) {
    throw createAppError_('INVALID_JSON', 'Unable to parse request JSON payload.', 400, {
      snippet: raw.substring(0, 100)
    });
  }
}

/**
 * Normalizes a record identifier into a trimmed string.
 * @param {*=} value
 * @returns {string}
 */
function normalizeRecordId_(value) {
  if (value === null || typeof value === 'undefined') {
    return '';
  }
  var normalized = String(value).trim();
  return normalized;
}

/**
 * Produces a shallow clone of a newcomer record without metadata.
 * @param {Object<string, *>} record
 * @returns {Object<string, *>}
 */
function cloneRecordSansMetadata_(record) {
  var clone = {};
  if (!record) {
    return clone;
  }

  Object.keys(record).forEach(function (key) {
    if (key !== '__rowNumber') {
      clone[key] = record[key];
    }
  });

  return clone;
}

/**
 * Sanitizes update fields sent via the API, mapping aliases to sheet headers.
 * @param {Object<string, *>} fields
 * @returns {Object<string, string>}
 */
function sanitizeUpdateFields_(fields) {
  if (!fields || typeof fields !== 'object') {
    throw createAppError_('INVALID_FIELDS', '"fields" must be an object of key/value pairs.', 400);
  }

  var sanitized = {};

  Object.keys(fields).forEach(function (rawKey) {
    if (!Object.prototype.hasOwnProperty.call(fields, rawKey)) {
      return;
    }

    var normalizedKey = String(rawKey);
    var lookupKey = normalizedKey;
    if (!Object.prototype.hasOwnProperty.call(API_FIELD_TO_HEADER_MAP, lookupKey)) {
      lookupKey = normalizedKey.toLowerCase();
    }

    var sheetHeader = API_FIELD_TO_HEADER_MAP[lookupKey] || normalizedKey;
    if (!Object.prototype.hasOwnProperty.call(MUTABLE_DATA_HEADER_LOOKUP, sheetHeader)) {
      throw createAppError_(
        'FIELD_NOT_ALLOWED',
        'Field "' + normalizedKey + '" cannot be updated via the API.',
        400,
        {
          field: normalizedKey,
          allowed: MUTABLE_DATA_HEADERS
        }
      );
    }

    var value = fields[rawKey];
    var sanitizedValue;
    if (sheetHeader === 'Last Attendance') {
      sanitizedValue = normalizeAttendanceValue_(value);
    } else if (sheetHeader === 'Regularity') {
      sanitizedValue = normalizeRegularitySequence_(value);
    } else if (value === null || typeof value === 'undefined') {
      sanitizedValue = '';
    } else if (value instanceof Date) {
      sanitizedValue = Utilities.formatDate(
        value,
        Session.getScriptTimeZone(),
        'yyyy-MM-dd'
      );
    } else if (typeof value === 'string') {
      sanitizedValue = value.trim();
    } else {
      sanitizedValue = String(value);
    }

    sanitized[sheetHeader] = sanitizedValue;
  });

  return sanitized;
}

/**
 * Parses an Apps Script sheet value into a JavaScript Date if possible.
 * @param {*=} value
 * @returns {Date|null}
 */
function parseDateValue_(value) {
  if (value === null || typeof value === 'undefined') {
    return null;
  }

  if (value instanceof Date) {
    return isNaN(value.getTime()) ? null : new Date(value.getTime());
  }

  if (typeof value === 'number') {
    var numericDate = new Date(value);
    return isNaN(numericDate.getTime()) ? null : numericDate;
  }

  var stringValue = String(value).trim();
  if (stringValue === '') {
    return null;
  }

  var parsed = new Date(stringValue);
  if (!isNaN(parsed.getTime())) {
    return parsed;
  }

  var isoFallback = stringValue.replace(' ', 'T');
  parsed = new Date(isoFallback);
  if (!isNaN(parsed.getTime())) {
    return parsed;
  }

  try {
    parsed = Utilities.parseDate(
      stringValue,
      Session.getScriptTimeZone(),
      "yyyy-MM-dd HH:mm:ss"
    );
    if (parsed && !isNaN(parsed.getTime())) {
      return parsed;
    }
  } catch (parseError) {
    // Ignore parsing errors; fall through to null return.
  }

  return null;
}

/**
 * Translates a `Regularity` sequence into data suitable for UI visualization.
 * @param {*=} sequence
 * @returns {{
 *   tokens: string[],
 *   attendanceBooleans: boolean[],
 *   totalWeeks: number,
 *   presentCount: number,
 *   absentCount: number
 * }}
 */
function buildRegularityVisualizationData_(sequence) {
  var normalized = normalizeRegularitySequence_(sequence);
  if (!normalized) {
    return {
      tokens: [],
      attendanceBooleans: [],
      totalWeeks: 0,
      presentCount: 0,
      absentCount: 0
    };
  }

  var tokens = normalized.split('');
  var attendanceBooleans = [];
  var presentCount = 0;
  var absentCount = 0;

  tokens.forEach(function (token) {
    var isPresent = token === 'Y';
    attendanceBooleans.push(isPresent);
    if (isPresent) {
      presentCount++;
    } else {
      absentCount++;
    }
  });

  return {
    tokens: tokens,
    attendanceBooleans: attendanceBooleans,
    totalWeeks: tokens.length,
    presentCount: presentCount,
    absentCount: absentCount
  };
}

/**
 * Determines whether a newcomer record should be highlighted as overdue.
 * @param {Object<string, *>} record
 * @param {Date=} referenceDate
 * @returns {{isOverdue: boolean, daysSinceUpdate: (number|null), thresholdDays: number}}
 */
function determineOverdueMetadata_(record, referenceDate) {
  var configuredThreshold = OVERDUE_FOLLOW_UP_CONFIG && OVERDUE_FOLLOW_UP_CONFIG.staleThresholdDays;
  var thresholdDays = parseInt(configuredThreshold, 10);
  if (!isFinite(thresholdDays) || thresholdDays <= 0) {
    thresholdDays = 7;
  }

  var now = referenceDate instanceof Date && !isNaN(referenceDate.getTime())
    ? referenceDate
    : new Date();

  var lastUpdatedDate = record ? parseDateValue_(record['Last Updated At']) : null;
  var daysSinceUpdate = null;
  var isOverdue = true;

  if (lastUpdatedDate) {
    var diffMilliseconds = now.getTime() - lastUpdatedDate.getTime();
    if (diffMilliseconds < 0) {
      diffMilliseconds = 0;
    }

    daysSinceUpdate = diffMilliseconds / MILLISECONDS_PER_DAY;
    isOverdue = diffMilliseconds >= thresholdDays * MILLISECONDS_PER_DAY;
  }

  return {
    isOverdue: isOverdue,
    daysSinceUpdate: daysSinceUpdate !== null
      ? Math.floor(Math.max(daysSinceUpdate, 0))
      : null,
    thresholdDays: thresholdDays
  };
}

/**
 * Converts newcomer records into API-friendly payloads.
 * @param {Object<string, *>[]} records
 * @returns {Object<string, *[]>}
 */
function buildNewcomerApiPayload_(records) {
  return (records || []).map(function (record) {
    var safeRecord = cloneRecordSansMetadata_(record);
    var overdueMetadata = determineOverdueMetadata_(safeRecord);
    var regularityVisual = buildRegularityVisualizationData_(safeRecord['Regularity']);

      return {
        recordId: normalizeRecordId_(safeRecord['Record Id']),
        newcomerName: safeRecord['Newcomer Name'] || '',
        contactNumber: safeRecord['Contact Number'] || '',
        location: safeRecord['Location'] || '',
        outstation: safeRecord['Outstation'] || '',
        assignedVolunteerName: safeRecord['Assigned Volunteer Name'] || '',
        assignedVolunteerEmail: normalizeVolunteerEmail_(safeRecord['Assigned Volunteer Email']),
        lastAttendance: safeRecord['Last Attendance'] || '',
        regularity: safeRecord['Regularity'] || '',
        powerhouseStatus: safeRecord['Powerhouse Status'] || '',
        powerhouseName: safeRecord['Powerhouse Name'] || '',
        lastComment: safeRecord['Last Comment'] || '',
        lastUpdatedAt: safeRecord['Last Updated At'] || '',
        lastUpdatedBy: safeRecord['Last Updated By'] || '',
        isOverdue: overdueMetadata.isOverdue,
        daysSinceLastUpdate: overdueMetadata.daysSinceUpdate,
        overdueThresholdDays: overdueMetadata.thresholdDays,
        regularityVisual: regularityVisual
      };
  });
}

/**
 * Ensures a history sheet exists with the expected headers.
 * @returns {GoogleAppsScript.Spreadsheet.Sheet}
 */
function getOrCreateHistorySheet_() {
  var spreadsheet = getFollowUpSpreadsheet_();
  var historySheet = spreadsheet.getSheetByName(SHEET_CONFIG.historySheetName);

  if (!historySheet) {
    historySheet = spreadsheet.insertSheet(SHEET_CONFIG.historySheetName);
    historySheet.getRange(1, 1, 1, SHEET_CONFIG.historyHeaders.length).setValues([
      SHEET_CONFIG.historyHeaders
    ]);
    return historySheet;
  }

  var headers = getSheetHeaders_(historySheet);
  if (headers.length === 0) {
    historySheet.getRange(1, 1, 1, SHEET_CONFIG.historyHeaders.length).setValues([
      SHEET_CONFIG.historyHeaders
    ]);
    return historySheet;
  }

  var discrepancies = analyzeHeaderDiscrepancies_(headers, SHEET_CONFIG.historyHeaders);
  if (discrepancies.missing.length > 0 || discrepancies.unexpected.length > 0) {
    throw createAppError_(
      'HISTORY_SHEET_INVALID',
      'History sheet headers do not match the expected schema.',
      500,
      {
        missingHeaders: discrepancies.missing,
        unexpectedHeaders: discrepancies.unexpected
      }
    );
  }

  return historySheet;
}

/**
 * Appends an update snapshot to the history sheet (best-effort).
 * @param {string} recordId
 * @param {Object<string, *>} beforeSnapshot
 * @param {Object<string, *>} afterSnapshot
 * @param {ReturnType<typeof ensureAuthorizedVolunteer>} authorization
 * @param {Object<string, string>} updatedFields
 */
function logUpdateHistory_(recordId, beforeSnapshot, afterSnapshot, authorization, updatedFields) {
  try {
    var historySheet = getOrCreateHistorySheet_();
    var timestamp = Utilities.formatDate(
      new Date(),
      Session.getScriptTimeZone(),
      "yyyy-MM-dd'T'HH:mm:ssXXX"
    );

    var volunteerEmail = '';
    var volunteerName = '';
    if (authorization) {
      volunteerEmail = authorization.email || '';
      if (authorization.matchedVolunteer) {
        volunteerEmail = authorization.matchedVolunteer.email || volunteerEmail;
        volunteerName = authorization.matchedVolunteer.name || '';
      }
    }

    var historyPayload = {
      updatedFields: Object.keys(updatedFields || {}),
      before: beforeSnapshot || {},
      after: afterSnapshot || {}
    };

    historySheet.appendRow([
      recordId,
      timestamp,
      volunteerEmail,
      volunteerName,
      JSON.stringify(historyPayload)
    ]);
  } catch (historyError) {
    Logger.log('History logging failed for record ' + recordId + ': ' + historyError.message);
  }
}

/**
 * Returns history entries for a specific record ID, ordered from newest to oldest.
 * @param {string} recordId
 * @param {number=} limit
 * @returns {{
 *   recordId: string,
 *   updatedAt: string,
 *   updatedBy: string,
 *   updatedByName: string,
 *   changes: Object|null
 * }[]}
 */
function getHistoryEntriesForRecord_(recordId, limit) {
  var normalizedRecordId = normalizeRecordId_(recordId);
  if (!normalizedRecordId) {
    return [];
  }

  var historySheet = getOrCreateHistorySheet_();
  var lastRow = historySheet.getLastRow();
  if (lastRow < 2) {
    return [];
  }

  var headers = getSheetHeaders_(historySheet);
  var headerIndexMap = buildHeaderIndexMap_(headers);

  var recordIdIndex = headerIndexMap['Record Id'];
  var updatedAtIndex = headerIndexMap['Updated At'];
  var updatedByIndex = headerIndexMap['Updated By'];
  var updatedByNameIndex = headerIndexMap['Updated By Name'];
  var changesIndex = headerIndexMap['Changes JSON'];

  if (typeof recordIdIndex !== 'number' || typeof changesIndex !== 'number') {
    throw createAppError_(
      'HISTORY_SHEET_INVALID',
      'History sheet is missing required columns.',
      500,
      { headers: headers }
    );
  }

  var rowCount = lastRow - 1;
  var values = historySheet.getRange(2, 1, rowCount, historySheet.getLastColumn()).getValues();
  var entries = [];
  var maxEntries = typeof limit === 'number' && limit > 0 ? limit : 25;

  for (var index = values.length - 1; index >= 0; index--) {
    var row = values[index];
    var rowRecordId = normalizeRecordId_(row[recordIdIndex]);
    if (rowRecordId !== normalizedRecordId) {
      continue;
    }

    var rawChanges = row[changesIndex];
    var parsedChanges = null;
    if (rawChanges) {
      try {
        parsedChanges = typeof rawChanges === 'string' ? JSON.parse(rawChanges) : rawChanges;
      } catch (parseError) {
        Logger.log('Failed to parse history JSON for record ' + normalizedRecordId + ': ' + parseError.message);
      }
    }

    entries.push({
      recordId: rowRecordId,
      updatedAt: typeof updatedAtIndex === 'number' ? (row[updatedAtIndex] || '') : '',
      updatedBy: typeof updatedByIndex === 'number' ? (row[updatedByIndex] || '') : '',
      updatedByName: typeof updatedByNameIndex === 'number' ? (row[updatedByNameIndex] || '') : '',
      changes: parsedChanges
    });

    if (entries.length >= maxEntries) {
      break;
    }
  }

  return entries;
}

/**
 * Extracts the prior week's comment value from history entries.
 * @param {ReturnType<typeof getHistoryEntriesForRecord_>} entries
 * @returns {{
 *   comment: string,
 *   sourceUpdatedAt: string,
 *   sourceVolunteerEmail: string,
 *   sourceVolunteerName: string
 * }|null}
 */
function findPreviousWeekCommentFromHistory_(entries) {
  if (!entries || entries.length === 0) {
    return null;
  }

  var latestEntry = entries[0];
  var latestChanges = latestEntry && latestEntry.changes ? latestEntry.changes : null;
  if (latestChanges && latestChanges.before && Object.prototype.hasOwnProperty.call(latestChanges.before, 'Last Comment')) {
    var beforeComment = latestChanges.before['Last Comment'];
    var afterComment = latestChanges.after && Object.prototype.hasOwnProperty.call(latestChanges.after, 'Last Comment')
      ? latestChanges.after['Last Comment']
      : beforeComment;

    if (beforeComment !== afterComment) {
      return {
        comment: beforeComment || '',
        sourceUpdatedAt: latestEntry.updatedAt || '',
        sourceVolunteerEmail: latestEntry.updatedBy || '',
        sourceVolunteerName: latestEntry.updatedByName || ''
      };
    }
  }

  for (var position = 1; position < entries.length; position++) {
    var entry = entries[position];
    var changes = entry && entry.changes ? entry.changes : null;
    if (!changes || !changes.after || !Object.prototype.hasOwnProperty.call(changes.after, 'Last Comment')) {
      continue;
    }

    return {
      comment: changes.after['Last Comment'] || '',
      sourceUpdatedAt: entry.updatedAt || '',
      sourceVolunteerEmail: entry.updatedBy || '',
      sourceVolunteerName: entry.updatedByName || ''
    };
  }

  return null;
}

/**
 * Returns a snapshot containing the comment written prior to the most recent update.
 * @param {string} recordId
 * @returns {{
 *   recordId: string,
 *   comment: string,
 *   sourceUpdatedAt: string,
 *   sourceVolunteerEmail: string,
 *   sourceVolunteerName: string
 * }|null}
 */
function getPreviousWeekCommentSnapshot_(recordId) {
  var normalizedRecordId = normalizeRecordId_(recordId);
  if (!normalizedRecordId) {
    return null;
  }

  var entries = getHistoryEntriesForRecord_(normalizedRecordId, 15);
  var snapshot = findPreviousWeekCommentFromHistory_(entries);
  if (!snapshot) {
    return null;
  }

  snapshot.recordId = normalizedRecordId;
  return snapshot;
}

/**
 * Applies updates to a newcomer record after authorization checks.
 * @param {Object<string, *>} payload
 * @param {ReturnType<typeof ensureAuthorizedVolunteer>} authorization
 * @returns {{
 *   recordId: string,
 *   updatedFields: Object<string, string>,
 *   lastUpdatedAt: string,
 *   lastUpdatedBy: string,
 *   newcomer: Object<string, *>
 * }}
 */
function applyNewcomerUpdate_(payload, authorization) {
  var recordId = normalizeRecordId_(payload && payload.recordId);
  if (!recordId) {
    throw createAppError_('INVALID_REQUEST', '"recordId" is required.', 400);
  }

  var sanitizedFields = sanitizeUpdateFields_(payload && payload.fields);
  var fieldKeys = Object.keys(sanitizedFields);
  if (fieldKeys.length === 0) {
    throw createAppError_('INVALID_REQUEST', 'At least one mutable field must be provided.', 400);
  }

  var dataSheetStatus = validateDataSheetStructure();
  if (!dataSheetStatus.isValid) {
    throw createAppError_(
      'SHEET_INVALID',
      'Data sheet validation failed; cannot apply updates.',
      500,
      {
        missingHeaders: dataSheetStatus.missingHeaders,
        unexpectedHeaders: dataSheetStatus.unexpectedHeaders
      }
    );
  }

  var newcomerRecords = getDataSheetRecords_();
  var targetRecord = null;
  newcomerRecords.some(function (record) {
    if (normalizeRecordId_(record['Record Id']) === recordId) {
      targetRecord = record;
      return true;
    }
    return false;
  });

  if (!targetRecord) {
    throw createAppError_('NOT_FOUND', 'Newcomer record not found for id "' + recordId + '".', 404);
  }

  var volunteerIdentity = buildVolunteerIdentity_(authorization && authorization.matchedVolunteer);
  var rowIdentity = buildRowVolunteerIdentity_(targetRecord);
  if (!rowMatchesVolunteer_(rowIdentity, volunteerIdentity)) {
    throw createAppError_('FORBIDDEN', 'You are not assigned to this newcomer.', 403);
  }

  var attendanceHeader = 'Last Attendance';
  var regularityHeader = 'Regularity';
  var hasAttendanceUpdate = Object.prototype.hasOwnProperty.call(sanitizedFields, attendanceHeader);
  var hasRegularityUpdate = Object.prototype.hasOwnProperty.call(sanitizedFields, regularityHeader);

  if (hasAttendanceUpdate) {
    var attendanceToken = sanitizedFields[attendanceHeader];
    if (attendanceToken) {
      sanitizedFields[regularityHeader] = appendAttendanceToRegularity_(
        targetRecord[regularityHeader] || '',
        attendanceToken
      );
      hasRegularityUpdate = true;
    }
  }

  if (hasRegularityUpdate) {
    sanitizedFields[regularityHeader] = normalizeRegularitySequence_(sanitizedFields[regularityHeader]);
  }

  fieldKeys = Object.keys(sanitizedFields);

  var spreadsheet = getFollowUpSpreadsheet_();
  var dataSheet = spreadsheet.getSheetByName(SHEET_CONFIG.dataSheetName);
  var headerIndexMap = buildHeaderIndexMap_(dataSheetStatus.headers);
  var rowNumber = targetRecord.__rowNumber;
  var lastColumn = dataSheet.getLastColumn();
  var range = dataSheet.getRange(rowNumber, 1, 1, lastColumn);
  var rowValues = range.getValues()[0];

  var beforeSnapshot = cloneRecordSansMetadata_(targetRecord);

  fieldKeys.forEach(function (header) {
    var columnIndex = headerIndexMap[header];
    if (typeof columnIndex !== 'number') {
      throw createAppError_('CONFIG_ERROR', 'Column "' + header + '" is missing from the sheet.', 500);
    }
    var cleanValue = sanitizedFields[header];
    rowValues[columnIndex] = cleanValue;
    targetRecord[header] = cleanValue;
  });

  var timestamp = new Date();
  var formattedTimestamp = Utilities.formatDate(
    timestamp,
    Session.getScriptTimeZone(),
    "yyyy-MM-dd'T'HH:mm:ssXXX"
  );

  var updatedByEmail = authorization && authorization.matchedVolunteer
    ? authorization.matchedVolunteer.email
    : authorization && authorization.email
      ? authorization.email
      : '';

  if (typeof headerIndexMap['Last Updated At'] === 'number') {
    rowValues[headerIndexMap['Last Updated At']] = formattedTimestamp;
    targetRecord['Last Updated At'] = formattedTimestamp;
  }
  if (typeof headerIndexMap['Last Updated By'] === 'number') {
    rowValues[headerIndexMap['Last Updated By']] = updatedByEmail;
    targetRecord['Last Updated By'] = updatedByEmail;
  }

  range.setValues([rowValues]);

  var afterSnapshot = cloneRecordSansMetadata_(targetRecord);
  logUpdateHistory_(recordId, beforeSnapshot, afterSnapshot, authorization, sanitizedFields);

  var newcomerPayload = buildNewcomerApiPayload_([afterSnapshot])[0];
  var previousWeekComment = getPreviousWeekCommentSnapshot_(recordId);

  return {
    recordId: recordId,
    updatedFields: sanitizedFields,
    lastUpdatedAt: afterSnapshot['Last Updated At'] || formattedTimestamp,
    lastUpdatedBy: afterSnapshot['Last Updated By'] || updatedByEmail,
    newcomer: newcomerPayload,
    previousWeekComment: previousWeekComment
  };
}

/**
 * Returns the previous week's comment snapshot for the signed-in volunteer.
 * Intended for HTML Service clients using `google.script.run`.
 * @param {string} recordId
 * @returns {{
 *   ok: boolean,
 *   recordId: string,
 *   previousWeekComment: ReturnType<typeof getPreviousWeekCommentSnapshot_>
 * }}
 */
function getPreviousWeekComment(recordId) {
  var authorization = ensureAuthorizedVolunteer();
  if (!authorization.authorized) {
    throw createAppError_(
      'UNAUTHORIZED',
      authorization.reason || 'Unauthorized volunteer',
      403
    );
  }

  var normalizedRecordId = normalizeRecordId_(recordId);
  if (!normalizedRecordId) {
    throw createAppError_('INVALID_REQUEST', '"recordId" is required.', 400);
  }

  var newcomerRecords = getAssignedNewcomersForVolunteer(authorization.matchedVolunteer);
  var ownsRecord = newcomerRecords.some(function (record) {
    return normalizeRecordId_(record['Record Id']) === normalizedRecordId;
  });

  if (!ownsRecord) {
    throw createAppError_('FORBIDDEN', 'You are not assigned to this newcomer.', 403);
  }

  return {
    ok: true,
    recordId: normalizedRecordId,
    previousWeekComment: getPreviousWeekCommentSnapshot_(normalizedRecordId)
  };
}

/**
 * Handles newcomer update submissions from the HTML Service client.
 * @param {{
 *   recordId: string,
 *   fields?: Object<string, *>,
 *   lastAttendance?: *,
 *   attendance?: *,
 *   lastComment?: *,
 *   comment?: *,
 *   powerhouseStatus?: *
 * }} payload
 * @returns {ReturnType<typeof applyNewcomerUpdate_>}
 */
function submitNewcomerUpdate(payload) {
  var authorization = ensureAuthorizedVolunteer();
  if (!authorization.authorized) {
    throw createAppError_(
      'UNAUTHORIZED',
      authorization.reason || 'Unauthorized volunteer',
      403
    );
  }

  var normalizedRecordId = normalizeRecordId_(payload && (payload.recordId || payload.RecordId));
  if (!normalizedRecordId) {
    throw createAppError_('INVALID_REQUEST', '"recordId" is required.', 400);
  }

  var fields = payload && payload.fields && typeof payload.fields === 'object'
    ? payload.fields
    : {};

  if (!Object.keys(fields).length) {
    if (payload && Object.prototype.hasOwnProperty.call(payload, 'lastAttendance')) {
      fields.lastAttendance = payload.lastAttendance;
    } else if (payload && Object.prototype.hasOwnProperty.call(payload, 'attendance')) {
      fields.lastAttendance = payload.attendance;
    }

    if (payload && Object.prototype.hasOwnProperty.call(payload, 'lastComment')) {
      fields.lastComment = payload.lastComment;
    } else if (payload && Object.prototype.hasOwnProperty.call(payload, 'comment')) {
      fields.lastComment = payload.comment;
    }

    if (payload && Object.prototype.hasOwnProperty.call(payload, 'powerhouseStatus')) {
      fields.powerhouseStatus = payload.powerhouseStatus;
    }
  }

  return applyNewcomerUpdate_({
    recordId: normalizedRecordId,
    fields: fields
  }, authorization);
}

/**
 * Wraps handler execution with JSON serialization and error handling.
 * @param {function(): *} handler
 * @returns {GoogleAppsScript.Content.TextOutput}
 */
function respondWithJson_(handler) {
  var responseBody;
  try {
    var result = handler();
    if (typeof result === 'undefined') {
      responseBody = { ok: true };
    } else if (result && typeof result.ok === 'boolean') {
      responseBody = result;
    } else {
      responseBody = {
        ok: true,
        data: result
      };
    }
  } catch (error) {
    responseBody = {
      ok: false,
      error: {
        message: error && error.message ? String(error.message) : 'Unexpected error',
        code: error && error.code ? error.code : 'SERVER_ERROR',
        status: error && error.status ? error.status : 500
      }
    };

    if (error && error.details) {
      responseBody.error.details = error.details;
    }

    if (error && error.stack) {
      Logger.log('API handler error: ' + error.stack);
    } else if (error) {
      Logger.log('API handler error: ' + error);
    }
  }

  if (!responseBody.timestamp) {
    responseBody.timestamp = new Date().toISOString();
  }

  return ContentService
    .createTextOutput(JSON.stringify(responseBody))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Builds the GET status action response, including validation checks.
 * @returns {{ok: boolean, error?: string, details?: Object, volunteer?: Object, dataSheet?: Object, historySheet?: Object}}
 */
function buildStatusResponse_() {
  var status = getStartupStatus();

  if (!status.authorization.authorized) {
    return {
      ok: false,
      error: status.authorization.reason || 'Unauthorized volunteer'
    };
  }

  if (!status.dataSheet.isValid || !status.accessSheet.isValid || !status.historySheet.isValid) {
    return {
      ok: false,
      error: 'Sheet validation failed',
      details: {
        dataSheet: status.dataSheet,
        accessSheet: status.accessSheet,
        historySheet: status.historySheet
      }
    };
  }

  return {
    ok: true,
    volunteer: status.authorization.matchedVolunteer,
    dataSheet: {
      sheetName: status.dataSheet.sheetName,
      headers: status.dataSheet.headers
    },
    historySheet: {
      sheetName: status.historySheet.sheetName,
      headers: status.historySheet.headers
    }
  };
}

/**
 * Handles GET requests for status checks and newcomer data retrieval.
 *
 * When no action parameter is provided, returns the HTML page.
 * Supported actions:
 * - `status`: returns authorization + sheet validation results.
 * - `newcomers` (aliases: `list_newcomers`, `listnewcomers`): returns newcomer records for the volunteer.
 *
 * @param {GoogleAppsScript.Events.DoGet} e
 * @returns {GoogleAppsScript.HTML.HtmlOutput|GoogleAppsScript.Content.TextOutput}
 */
function doGet(e) {
  var parameters = e && e.parameter ? e.parameter : {};
  var action = parameters && parameters.action
    ? String(parameters.action).trim().toLowerCase()
    : null;

  // If no action parameter, serve the HTML page
  if (!action) {
    return HtmlService.createHtmlOutputFromFile('index');
  }

  // Otherwise, return JSON response for API calls
  return respondWithJson_(function () {
    if (action === 'status') {
      return buildStatusResponse_();
    }

    var authorization = ensureAuthorizedVolunteer();
    if (!authorization.authorized) {
      throw createAppError_(
        'UNAUTHORIZED',
        authorization.reason || 'Unauthorized volunteer',
        403
      );
    }

    switch (action) {
      case 'list_newcomers':
      case 'listnewcomers':
      case 'newcomers': {
        var newcomers = getAssignedNewcomersForVolunteer(authorization.matchedVolunteer);
        return {
          ok: true,
          volunteer: authorization.matchedVolunteer,
          newcomers: buildNewcomerApiPayload_(newcomers)
        };
      }
      default:
        throw createAppError_(
          'UNKNOWN_ACTION',
          'Unsupported GET action "' + action + '".',
          400,
          { action: action }
        );
    }
  });
}

/**
 * Handles POST requests for newcomer data mutations.
 *
 * Supported actions:
 * - `update_newcomer` (aliases: `update-newcomer`, `updatenewcomer`)
 *
 * @param {GoogleAppsScript.Events.DoPost} e
 * @returns {GoogleAppsScript.Content.TextOutput}
 */
function doPost(e) {
  return respondWithJson_(function () {
    if (!e || !e.postData || !e.postData.contents) {
      throw createAppError_('INVALID_REQUEST', 'POST body is required.', 400);
    }

    var authorization = ensureAuthorizedVolunteer();
    if (!authorization.authorized) {
      throw createAppError_(
        'UNAUTHORIZED',
        authorization.reason || 'Unauthorized volunteer',
        403
      );
    }

    var contentType = (e.postData.type || '').toLowerCase();
    if (contentType && contentType.indexOf('application/json') === -1) {
      throw createAppError_(
        'UNSUPPORTED_MEDIA_TYPE',
        'POST payload must be JSON.',
        415,
        { contentType: e.postData.type }
      );
    }

    var payload = parseJson_(e.postData.contents);
    var actionValue = payload && payload.action
      ? String(payload.action).trim().toLowerCase()
      : '';
    if (!actionValue) {
      throw createAppError_('INVALID_REQUEST', 'POST payload must include an "action".', 400);
    }

    switch (actionValue) {
      case 'update_newcomer':
      case 'update-newcomer':
      case 'updatenewcomer': {
        var result = applyNewcomerUpdate_(payload, authorization);
        return {
          ok: true,
          result: result
        };
      }
      default:
        throw createAppError_(
          'UNKNOWN_ACTION',
          'Unsupported POST action "' + (payload && payload.action) + '".',
          400,
          { action: payload && payload.action }
        );
    }
  });
}

/**
 * Utility runner that can be executed from the Apps Script editor to audit the
 * deployment configuration. This writes the validation summary to the log.
 */
function runSetupAudit() {
  var status = getStartupStatus();
  Logger.log(JSON.stringify(status, null, 2));
  return status;
}

