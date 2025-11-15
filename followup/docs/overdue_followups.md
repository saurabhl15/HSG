# Highlighting Overdue Follow-Ups (Task 5)

Task 5 adds backend support for surfacing newcomers who have not received a recent update so the UI can highlight them for volunteer follow-up.

## Detection Rules

- The script inspects the `Last Updated At` column for each newcomer row.
- Timestamps are parsed from ISO-8601 strings, Apps Script `Date` objects, or Sheet-formatted values such as `yyyy-MM-dd HH:mm:ss`. Missing or unparseable timestamps are treated as stale.
- A newcomer is marked overdue when the time since their last update meets or exceeds the configured stale window (default **7 days**).
- Records updated in the future (clock skew) are capped at zero days overdue.

## Configuration

The detection window is controlled via `OVERDUE_FOLLOW_UP_CONFIG` in `followup/code.gs`:

```
const OVERDUE_FOLLOW_UP_CONFIG = Object.freeze({
  staleThresholdDays: 7
});
```

- Increase `staleThresholdDays` to relax highlighting (e.g., `14` for a bi-weekly cadence).
- Decrease it to surface newcomers more aggressively (e.g., `3` for mid-week reminders).
- Changes take effect immediately after redeploying the Apps Script project; no sheet edits are required.

## API Payload

Each newcomer returned from `doGet?action=newcomers` now includes:

```
{
  "recordId": "123",
  "lastUpdatedAt": "2025-11-05T20:15:00+05:30",
  "lastUpdatedBy": "leader@example.com",
  "isOverdue": false,
  "daysSinceLastUpdate": 2,
  "overdueThresholdDays": 7
}
```

- `isOverdue` signals whether the UI should emphasize the card/row.
- `daysSinceLastUpdate` is the floored number of full days since the update (or `null` when unknown).
- `overdueThresholdDays` echoes the backend threshold, allowing the UI to display contextual messaging if desired.

## Front-End Guidance

- Apply a highlight treatment when `isOverdue` is `true`. Consider badges, color accents, or grouping overdue newcomers at the top of the list.
- Show the `daysSinceLastUpdate` value to give volunteers quick context.
- Because outdated timestamps default to overdue, coordinators should resolve empty `Last Updated At` cells in the sheet to prevent indefinite highlights.

