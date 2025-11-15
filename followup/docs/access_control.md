# Follow-Up App Sheet Access Setup

This guide documents the configuration required for Task&nbsp;1 (Design Sheet Access Flow). Complete these steps before deploying or testing the rest of the follow-up app modules.

## 1. Spreadsheet Structure

Create a Google Sheets workbook for the follow-up workflow with two tabs:

| Tab | Purpose |
| --- | --- |
| `Newcomers` | Primary dataset containing one row per newcomer with the latest follow-up snapshot. |
| `Volunteer Access` | Access control list (ACL) defining which volunteer Gmail accounts can open the app. |

### 1.1 `Newcomers` Headers

Row&nbsp;1 must include the following headers exactly (capitalization and spacing matter):

1. `Record Id`
2. `Newcomer Name`
3. `Contact Number`
5. `Assigned Volunteer Name`
6. `Assigned Volunteer Email`
8. `Last Attendance`
9. `Regularity`
10. `Powerhouse Status`
11. `Last Comment`
12. `Last Updated At`
13. `Last Updated By`

Additional columns may be appended, but do not rename or delete the required headers. The backend validation will refuse to start if any header is missing.

### 1.2 `Volunteer Access` Headers

Row&nbsp;1 must contain:

1. `Volunteer Email`
2. `Volunteer Name`
4. `Is Active (Y/N)`

The app permits access only to rows with `Is Active (Y/N)` set to `Y`. Enter volunteer Gmail addresses in the `Volunteer Email` column (lowercase preferred). Storing deactivated volunteers with `N` keeps historical context without permitting sign-in.

## 2. Apps Script Configuration

1. Open **Extensions → Apps Script** inside the workbook.
2. Replace the default `Code.gs` with the source from `followup/code.gs`.
3. Update the `SHEET_CONFIG` object:
   - `spreadsheetId`: copy from the sheet URL (`https://docs.google.com/.../d/<ID>/edit`).
   - `dataSheetName` / `accessSheetName`: rename only if the tab names are different.
4. Save the script and run the `runSetupAudit` function once. Approve the requested OAuth scopes. The execution log should return a JSON summary with `ok: true` if headers and access entries are correctly configured.

## 3. Maintaining the Access List

- **Adding a volunteer:** Append their Gmail address (or approved staff domain such as `@rwo.life`) to the `Volunteer Access` tab and set `Is Active (Y/N)` to `Y`. Changes propagate immediately after the next app load.
- **Suspending access:** Switch `Is Active (Y/N)` to `N`. This keeps historical context without deleting the record.
- **Removing stale entries:** Archive or delete rows for volunteers who have left long-term. Export the sheet beforehand if record-keeping is required.
- **Audit cadence:** Review the ACL weekly to remove expired access and verify that only expected volunteers are marked active.

## 4. Deployment Checklist

1. Confirm both sheets pass validation (`runSetupAudit` shows no missing headers).
2. Ensure every volunteer uses a Gmail account (the script blocks non-Gmail domains).
3. Deploy the web app **as you**, with **access: only users in the Volunteer Access list**:
   - Select **Deploy → Test deployments → New** until later tasks wire up the UI.
   - For production, use **Deploy → Manage deployments** and choose **Execute as Me** and **Who has access: Only myself**; the script-level checks will still enforce the ACL.
4. Share the spreadsheet with volunteer email addresses as **Viewer** if they need sheet access outside the app. App access does not require sheet sharing once deployed.

## 5. Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `ok: false` with `Unauthorized volunteer` | The signed-in email is missing from the ACL, marked inactive, or uses a domain that isn’t listed in the allowed domains (`gmail.com`, `rwo.life`). |
| `Sheet validation failed` | One or both sheet tabs are missing required headers; fix them and rerun `runSetupAudit`. |
| `Exception: SHEET_CONFIG.spreadsheetId must be set...` | Update the configuration constant with the actual Sheet ID. |
| Session email is empty in audit logs | The script is running under a service or shared drive account; redeploy using a regular Gmail login. |

Maintain this document with any schema changes so downstream tasks (filtering, updates, UI) remain aligned with the data contract.

