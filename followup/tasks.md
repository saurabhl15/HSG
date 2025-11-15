# Holy Spirit Generation Follow-Up App – Agent Task Plan

## 1. Design Sheet Access Flow
- **Description:** Verify the Google Sheet column headers and enforce Gmail-based access control so only registered volunteers can reach the application. Ensure compatibility with the sheet schema provided by Holy Spirit Generation.
- **Agent Responsibilities:**
  - Confirm the sheet structure and document any discrepancies.
  - Implement and test Google Apps Script authentication checks tied to volunteer Gmail accounts.
  - Produce setup notes for maintaining the access control list.

## 2. Create Volunteer Filtering Logic
- **Description:** Build logic that retrieves sheet rows and returns only the newcomers assigned to the signed-in volunteer, accounting for variations in volunteer identifiers.
- **Agent Responsibilities:**
  - Design and implement the filtering function in Google Apps Script.
  - Normalize volunteer names/emails and document the chosen mapping strategy.
  - Provide unit tests or sample scenarios validating the filtering behaviour.

## 3. Construct Data API Layer
- **Description:** Expose newcomer data and update actions through `doGet`/`doPost` handlers so the web UI can read and write updates securely.
- **Agent Responsibilities:**
  - Define API contracts (request/response payloads) and handle validation.
  - Implement secure read/write operations to the sheet, preserving historical entries.
  - Document error cases and recovery strategies for agents integrating the UI.

## 4. Develop Weekly Update Tracking
- **Description:** Create utilities to append timestamped attendance updates, maintain the `Regularity` string, and retrieve the previous week’s comment history.
- **Agent Responsibilities:**
  - Update sheet records with weekly attendance (Y/N) and comments.
  - Manage history storage so prior comments remain accessible.
  - Provide helper functions or documentation for other agents to reuse.

## 5. Highlight Overdue Follow-Ups
- **Description:** Detect newcomers lacking updates in the past seven days and flag them for highlighting in the UI.
- **Agent Responsibilities:**
  - Implement date-difference calculations for each newcomer.
  - Include the overdue flag in the API response payload.
  - Outline configuration options for adjusting the “stale” window.

## 6. Implement Regularity Visual Encoding
- **Description:** Translate the `Regularity` Y/N sequence into a structured format suitable for rendering as green/red boxes in the UI.
- **Agent Responsibilities:**
  - Parse and validate the `Regularity` sequence coming from the sheet.
  - Deliver normalized data (e.g., boolean array) for the front-end to consume.
  - Document the mapping from Y/N to visual states for UI agents.

## 7. Build Responsive Web UI Shell
- **Description:** Create a mobile-first HTML/CSS/JS interface branded for Holy Spirit Generation, ensuring smooth navigation between list and detail views.
- **Agent Responsibilities:**
  - Design the overall layout using HTML Service with responsive styling.
  - Integrate loading and error states for data fetches.
  - Provide design tokens/notes so future agents can maintain branding consistency.

## 8. Create Newcomer List View
- **Description:** Render an accessible list or card layout showing each newcomer, key details, and overdue highlights.
- **Agent Responsibilities:**
  - Consume the filtered newcomer data and visualize highlight flags.
  - Implement tap-friendly interactions for mobile devices.
  - Ensure the list updates after submissions without full reloads.

## 9. Develop Detail & Update Form
- **Description:** Present newcomer-specific details, last week’s comments, and a form for submitting the next update (attendance Yes/No, comments, powerhouse status).
- **Agent Responsibilities:**
  - Populate the form with historical data via `google.script.run` calls.
  - Implement validation and submission handling to the API layer.
  - Provide UI feedback confirming successful updates or surfacing errors.

## 10. Handle UI-State Synchronization
- **Description:** Keep client state consistent with sheet data, managing optimistic updates, refreshes, and offline considerations.
- **Agent Responsibilities:**
  - Implement state management patterns suited for Apps Script HTML Service.
  - Handle refresh flows after submissions and reconcile server responses.
  - Document known limitations and suggested mitigations for future agents.

## 11. Add Security & Deployment Steps
- **Description:** Lock down the web app deployment to the approved Gmail accounts/domain and capture the deployment workflow.
- **Agent Responsibilities:**
  - Configure deployment settings (access level, versioning) in Apps Script.
  - Outline the process for adding/removing volunteer accounts.
  - Draft a maintenance checklist for weekly or monthly reviews.

## 12. Write Testing & QA Checklist
- **Description:** Define manual and automated scenarios covering filtering, updates, highlighting, and responsiveness.
- **Agent Responsibilities:**
  - Compile step-by-step QA scripts and data requirements.
  - Identify edge cases (e.g., missing fields, concurrent edits).
  - Provide regression guidance for future enhancements.

## 13. Prepare Documentation
- **Description:** Produce user-facing and developer-facing documentation describing setup, deployment, and daily usage for Holy Spirit Generation staff.
- **Agent Responsibilities:**
  - Draft a README with installation, configuration, and usage steps.
  - Include troubleshooting tips for authentication or sheet-sync issues.
  - Gather feedback from stakeholders and incorporate refinements.
