# UI State Synchronization (Task 10)

Task 10 introduces a lightweight client-side state manager that keeps the HTML Service UI aligned with the sheet data while updates are in flight. This note summarizes the moving pieces implemented in `followup/index.html`.

## Sync State Model

- A new `state.sync` branch tracks:
  - `networkOnline`: current connectivity (`navigator.onLine` with graceful fallback).
  - `pendingByRecordId`: optimistic mutations keyed by Apps Script record id.
  - `lastSuccessfulFetch` / `lastSuccessfulUpdate`: timestamps (ms) used for toast-style banners.
  - `lastErrorMessage` / `lastErrorRecordId`: allows UI banners to surface actionable errors without blocking forms.
- `getStateSnapshot()` now includes sync metadata so embedded tools or future integrations can inspect pending counts externally.

## Optimistic Update Flow

1. `handleDetailFormSubmit` validates inputs, blocks duplicate submissions per record, and aborts early when offline.
2. `applyOptimisticUpdate(recordId, fields)`:
   - Stores a `snapshot` of the current newcomer data.
   - Mutates the in-memory record with projected values (`Pending sync…` label, comment preview, powerhouse display, etc.).
   - Flags the record with `pendingSync` so list/detail badges can react immediately.
3. UI feedback:
   - Global banner (`#syncStatusBanner`) flips to “Syncing n updates…”.
   - Selected detail view shows a dashed card (`#detailSyncNotice`) with the same status.
   - The list item receives a `chip--pending` pill beside the newcomer name.
4. `handleDetailFormSuccess` clears the pending entry, replaces the record with the server’s response, and restores the detail form to a clean slate.
5. `handleDetailFormFailure` rolls back to the stored snapshot without touching user inputs, leaving the typed comment in the form for quick edits.

## Refresh & Reconciliation

- `reapplyPendingUpdatesAfterRefresh()` runs whenever `applyNewcomerRecords()` loads fresh sheet data (initial load or manual refresh).
- The routine replays each pending entry on top of the new baseline, ensuring optimistic changes remain visible even if the volunteer triggers a full list refresh mid-sync.
- `refreshDetailPreviewIfSelected()` updates the detail summary without resetting the form, so volunteers never lose in-progress text unless the record itself disappears.

## Offline Handling

- `initializeNetworkMonitor()` wires the standard `online`/`offline` events and feeds `updateNetworkStatus()`.
- When offline:
  - The global banner swaps to a yellow/amber warning.
  - The detail sync notice shows “Offline. Reconnect to submit updates.”
  - Submissions are blocked with a descriptive error so volunteers understand why the action failed.
- Once reconnected, the banner hides automatically after a short delay (unless another pending/error state is active).

## Limitations & Mitigations

- No persistent queue: optimistic entries live only in memory. A full page reload during a sync will drop them. Mitigation: wait until the green confirmation banner or the form success message appears before closing the tab.
- Offline capture is advisory only; updates are not cached for later replay. Volunteers should keep the tab open and retry once connectivity returns.
- The optimistic overlay assumes volunteer submissions will clear the overdue flag. If the backend rejects the change (e.g., validation error), the rollback restores the stale state and surfaces the error message.
- Apps Script runtime failures still reset the detail view to the last good snapshot; volunteers should reattempt after reviewing the banner/form error text.

