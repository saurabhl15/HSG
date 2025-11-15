# Data API Layer (Task 3)

This document describes the data API exposed from `followup/code.gs` to support the Holy Spirit Generation follow-up web UI. The API runs on top of Google Apps Script’s web app runtime (`doGet`/`doPost`) and enforces volunteer authentication, sheet validation, and history preservation.

## Overview

- **Authentication:** Every request runs under the signed-in Google account. The script verifies that the email is listed in the `Volunteer Access` sheet with `Is Active (Y/N) = Y`. Unauthorized users receive an `ok: false` response with `error`.
- **Sheet validation:** All operations require the `Newcomers`, `Volunteer Access`, and `Newcomer Update History` sheets to pass header validation. The `status` action returns the current validation state.
- **History preservation:** Updates append JSON snapshots to the `Newcomer Update History` sheet with headers:
  1. `Record Id`
  2. `Updated At`
  3. `Updated By`
  4. `Updated By Name`
  5. `Changes JSON`

If the history sheet is missing the script creates it automatically; header mismatches raise a `HISTORY_SHEET_INVALID` error so coordinators can fix the schema.

## GET Actions (`doGet`)

| Action | Description |
| ------ | ----------- |
| `status` (default) | Returns authorization status plus sheet validation details. |
| `newcomers`, `list_newcomers`, `listnewcomers` | Returns newcomer records assigned to the authenticated volunteer. |

### `status` Response

```json
{
  "ok": true,
  "volunteer": {"email": "leader@example.com", "name": "Jane Doe"},
  "dataSheet": {"sheetName": "Newcomers", "headers": ["Record Id", "..."]},
  "historySheet": {"sheetName": "Newcomer Update History", "headers": ["Record Id", "..."]},
  "timestamp": "2025-11-12T12:34:56.789Z"
}
```

Failure cases set `ok: false` and include `error` plus optional `details.dataSheet`, `details.accessSheet`, and `details.historySheet` with the validation output.

### `newcomers` Response

```json
{
  "ok": true,
  "volunteer": {"email": "leader@example.com", "name": "Jane Doe"},
  "newcomers": [
    {
      "recordId": "123",
      "newcomerName": "Alex Example",
      "contactNumber": "123-456-7890",
      "assignedVolunteerName": "Jane Doe",
      "assignedVolunteerEmail": "leader@example.com",
      "lastAttendance": "Y",
      "regularity": "YYN",
      "powerhouseStatus": "Invited",
      "lastComment": "See you next week",
      "lastUpdatedAt": "2025-11-05T20:15:00+05:30",
      "lastUpdatedBy": "leader@example.com",
      "isOverdue": false,
      "daysSinceLastUpdate": 2,
      "overdueThresholdDays": 7,
      "regularityVisual": {
        "tokens": ["Y", "Y", "N"],
        "attendanceBooleans": [true, true, false],
        "totalWeeks": 3,
        "presentCount": 2,
        "absentCount": 1
      }
    }
  ],
  "timestamp": "2025-11-12T12:34:56.789Z"
}
```

Each newcomer object now includes:
- `isOverdue`, `daysSinceLastUpdate`, and `overdueThresholdDays` for stale follow-up highlighting (Task 5).
- `regularityVisual` for ready-to-render attendance streaks, exposing both the original `"Y"`/`"N"` tokens and precomputed boolean values (Task 6). Rows without a recent timestamp default to `isOverdue: true` so coordinators can quickly identify newcomers needing attention.

Records never include the internal `__rowNumber` metadata; the front-end should rely on `recordId`.

## POST Actions (`doPost`)

| Action | Description |
| ------ | ----------- |
| `update_newcomer`, `update-newcomer`, `updatenewcomer` | Updates mutable newcomer fields and appends a history entry. |

### Request Payload

```json
{
  "action": "update_newcomer",
  "recordId": "123",
  "fields": {
    "lastAttendance": "N",
    "regularity": "YYNY",
    "lastComment": "Called, no answer"
  }
}
```

- `recordId` must match the `Record Id` column in the `Newcomers` sheet.
- `fields` accepts either sheet headers (`"Last Attendance"`) or camelCase aliases shown above. Allowed keys are:
  - `Last Attendance` / `lastAttendance`
  - `Regularity` / `regularity`
  - `Powerhouse Status` / `powerhouseStatus`
  - `Last Comment` / `lastComment`
- Empty strings clear a field. Date objects are formatted as `yyyy-MM-dd`.

### Response Payload

```json
{
  "ok": true,
  "result": {
    "recordId": "123",
    "updatedFields": {
      "Last Attendance": "N",
      "Regularity": "YYNY",
      "Last Comment": "Called, no answer"
    },
    "lastUpdatedAt": "2025-11-12T12:34:56+05:30",
    "lastUpdatedBy": "leader@example.com",
    "newcomer": {
      "recordId": "123",
      "...": "...",
      "isOverdue": false,
      "daysSinceLastUpdate": 0,
      "overdueThresholdDays": 7,
      "regularityVisual": {
        "tokens": ["Y", "Y", "N"],
        "attendanceBooleans": [true, true, false],
        "totalWeeks": 3,
        "presentCount": 2,
        "absentCount": 1
      }
    }
  },
  "timestamp": "2025-11-12T12:34:56.789Z"
}
```

The `newcomer` object reflects the sheet snapshot after the update. If another column changes the API still returns only the whitelisted fields.

## Error Handling

All error responses follow:

```json
{
  "ok": false,
  "error": {
    "message": "Human-readable message",
    "code": "ERROR_CODE",
    "status": 400,
    "details": { "...": "..." }
  },
  "timestamp": "2025-11-12T12:34:56.789Z"
}
```

Notable error codes:

| Code | Status | Meaning | Suggested Fix |
| ---- | ------ | ------- | ------------- |
| `UNAUTHORIZED` | 403 | Volunteer email missing from ACL or inactive. | Add/activate the Gmail in `Volunteer Access`. |
| `SHEET_INVALID` | 500 | `Newcomers` headers mismatch. | Align headers with `tasks.md` and rerun `runSetupAudit`. |
| `HISTORY_SHEET_INVALID` | 500 | History sheet headers missing/unexpected. | Fix the `Newcomer Update History` header row (`Record Id`, `Updated At`, `Updated By`, `Updated By Name`, `Changes JSON`). |
| `FIELD_NOT_ALLOWED` | 400 | Request attempted to update a disallowed column. | Restrict updates to `Last Attendance`, `Regularity`, `Last Comment`. |
| `NOT_FOUND` | 404 | `recordId` not present or filtered out. | Confirm the sheet row exists and belongs to the volunteer. |
| `FORBIDDEN` | 403 | Record assigned to a different volunteer. | Escalate to a coordinator; volunteers can’t modify others’ rows. |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Non-JSON POST payload. | Send `Content-Type: application/json` bodies only. |

Errors are logged to `Logger` for audit, while history logging failures are non-blocking (updates still commit).

## Integration Checklist

1. Call `doGet?action=status` when bootstrapping the UI; guard the interface if `ok: false`.
2. Load assigned newcomers with `doGet?action=newcomers`.
3. Send updates via `doPost` using the payload above. Refresh the UI with the returned `newcomer` snapshot.
4. Highlight newcomers when `isOverdue` is `true`; the default window is controlled via `OVERDUE_FOLLOW_UP_CONFIG.staleThresholdDays`.
5. Handle `36x/37x` errors gracefully in the UI (show volunteer instructions) and surface `details` for coordinators when present.

