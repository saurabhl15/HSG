# Weekly Update Utilities (Task 4)

This note documents the helper utilities implemented in `followup/code.gs` to support weekly newcomer updates. They extend the Task&nbsp;3 data layer by handling attendance normalization, `Regularity` maintenance, and comment history lookups.

## Attendance Normalization

- Use `normalizeAttendanceValue_(value)` to coerce raw inputs into a single-character token:
  - `Y`, `Yes`, `Present`, `true`, `1` → `Y`
  - `N`, `No`, `Absent`, `false`, `0` → `N`
  - Empty/undefined values return an empty string (treated as “no update”).
- Invalid tokens raise `INVALID_ATTENDANCE` (HTTP 400) so the front-end can prompt volunteers immediately.

## Regularity Sequence

- `WEEKLY_UPDATE_CONFIG.maxRegularityLength` (default **8**) caps the history retained in the `Regularity` string.
- `appendAttendanceToRegularity_(existing, token)` handles rolling updates:
  - Cleans the existing sequence (`normalizeRegularitySequence_`).
  - Appends the latest attendance token.
  - Truncates the sequence to the configured length, preserving the most recent weeks on the **right**.
- `applyNewcomerUpdate_` now recalculates `Regularity` automatically whenever `Last Attendance` is supplied, so client code only needs to pass the attendance toggle and optional comment.

### Visual Encoding (Task 6)

- `buildRegularityVisualizationData_(sequence)` converts a normalized `Regularity` string into structured data for UI components.
- The helper returns:
  - `tokens`: array of `"Y"`/`"N"` characters (oldest → newest).
  - `attendanceBooleans`: parallel boolean array (`true` = present, `false` = absent).
  - `totalWeeks`, `presentCount`, `absentCount` for quick summaries.
- The data API includes this structure under `regularityVisual` for each newcomer payload so the front-end can render attendance streaks as green/red boxes without re-parsing strings.

## Comment History

- Every mutation still writes a row to `Newcomer Update History`.
- `getHistoryEntriesForRecord_(recordId, limit)` loads recent history (newest first) with parsed change payloads.
- `findPreviousWeekCommentFromHistory_(entries)` inspects those changes and returns:
  - the comment prior to the latest update (if the comment changed), or
  - the last persisted comment from earlier weeks.
- `getPreviousWeekCommentSnapshot_(recordId)` wraps the logic and returns `{recordId, comment, sourceUpdatedAt, sourceVolunteerEmail, sourceVolunteerName}` or `null`.
- Front-end code can call the exported Apps Script function `getPreviousWeekComment(recordId)` via `google.script.run` to fetch the previous-week snapshot with volunteer authorization enforced.

## Update Response Payload

The `update_newcomer` POST action now returns the `previousWeekComment` snapshot alongside the refreshed newcomer record:

```
{
  "ok": true,
  "result": {
    "recordId": "123",
    "updatedFields": {"Last Attendance": "Y", "Regularity": "YYNY"},
    "lastUpdatedAt": "...",
    "lastUpdatedBy": "leader@example.com",
    "newcomer": {...},
    "previousWeekComment": {
      "recordId": "123",
      "comment": "Called, no answer",
      "sourceUpdatedAt": "2025-11-05T20:15:00+05:30",
      "sourceVolunteerEmail": "leader@example.com",
      "sourceVolunteerName": "Jane Doe"
    }
  }
}
```

This allows the UI detail view to show last week’s notes immediately after a successful submission.


