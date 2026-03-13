1. Analyze and extend the data model to support midweek updates:
   - Decide whether midweek updates will be written to a separate CSV or integrated into the existing `followup_output.csv` / `hsg_newcomers_2026.csv`.
   - Confirm that midweek updates must locate an existing newcomer row using `Newcomer ID` and then update specific columns in that row.
   - Identify which columns from the midweek template map to existing columns (e.g., `Interested in Powerhouse`, `Powerhouse Available`, `Connected to Powerhouse`, `Update`) and whether any new columns need to be added to the newcomers CSV.

### Outcome for Task 1
- What you did
- Files changed
- Important notes
- Edge cases handled

### Review Fixes for Task 1
- **What was fixed**
  - Relaxed the `parse_updates` block validation so it no longer depends on an exact `"Newcomer Name"` casing match, while still filtering out empty blocks.
  - Added a schema migration helper for `hsg_newcomers_2026.csv` so any existing newcomer sheet is automatically upgraded to include the new midweek columns in `ALL_COLUMNS` before appending new rows.
- **Why**
  - The previous block check could silently drop valid templates if the label casing varied, despite the regexes being case-insensitive.
  - Without automatic schema migration, older newcomer sheets could end up with headers that don’t match the extended data model, causing subtle downstream inconsistencies.
- **Remaining considerations**
  - Midweek parsing, normalization, and record update logic (Tasks 2–9) still need to be implemented on top of this extended schema.
  - Once midweek parsing is in place, `README.md` should be updated to document the new midweek columns and how “No update” / blank options are interpreted.

2. Design robust parsing rules for the midweek WhatsApp template:
   - Support the exact field labels from the template: `Newcomer ID`, `Name`, `Interested in Powerhouse`, `Powerhouse Available`, `Connected to Powerhouse`, and `Update`.
   - Make patterns tolerant of bold markers (`*Field*`), optional numbering (e.g., `1. *Newcomer ID*:`), extra whitespace, and minor variations in casing, similar to the existing `FIELD_PATTERNS`.
   - Normalize option values like `Yes / No / No update` by trimming spaces, making comparison case-insensitive, and mapping variants such as `No update`, `No Update`, or blank values to a consistent internal representation.

### Outcome for Task 2
- What you did
- Files changed
- Important notes
- Edge cases handled

### Review Fixes for Task 2
- **What was fixed**
  - Extended `normalize_midweek_option` so that common "no update" variants such as `N.A.`, `N/A`, and `NA` are all normalized to the canonical `No update` value in addition to the existing `No update` spellings and blanks.
- **Why**
  - Midweek option values in real WhatsApp exports are likely to include shorthand like `N.A.` alongside `No update`, and treating these inconsistently would either fragment the data model or require every downstream consumer to special-case them.
- **Remaining considerations**
  - The semantic treatment of `No update` (e.g., whether it should always be interpreted as "leave existing value unchanged" when applying midweek updates) still needs to be implemented as part of the midweek record update logic in later tasks.

3. Implement midweek message block detection in the parser:
   - Define a new block-start regular expression that detects the start of each midweek update block (e.g., lines beginning with `Newcomer ID:` with optional bold/numbering).
   - Assume midweek updates may appear in the same WhatsApp export as regular newcomer updates and ensure the parser can safely attempt to parse both kinds of blocks from any message body.
   - Ensure the parser can handle multiple midweek update blocks in a single WhatsApp message body, aggregating them similarly to how `parse_updates` works for regular updates.

### Outcome for Task 3
- What you did
- Files changed
- Important notes
- Edge cases handled

### Review Fixes for Task 3
- **What was fixed**
  - Refactored newcomer and midweek block detection to share a single `_split_blocks_by_start_regex` helper so both paths use identical logic for walking lines, handling trailing text, and skipping empty blocks.
- **Why**
  - Keeping two nearly identical block scanners separate would make it easy for their behavior to drift over time (e.g., one handling blank lines or partial blocks differently), leading to subtle inconsistencies between regular and midweek parsing.
- **Remaining considerations**
  - Midweek blocks are still only detected and returned as raw block texts; later tasks will be responsible for extracting fields, interpreting `No update`, and wiring midweek updates into the newcomer CSV and CLI workflow.

4. Implement a dedicated extractor for midweek update fields:
   - Create a function (analogous to `extract_fields_from_block`) that extracts `Newcomer ID`, `Name`, `Interested in Powerhouse`, `Powerhouse Available`, `Connected to Powerhouse`, and `Update` from a single midweek block using the new patterns.
   - Reuse existing normalization utilities (`normalize_unicode_spaces`, edit-marker stripping, underscore removal) so midweek parsing is equally robust.
   - Add basic validation so that blocks missing `Newcomer ID` are skipped or reported, since ID is required for matching.

### Outcome for Task 4
- What you did
- Files changed
- Important notes
- Edge cases handled

### Review Fixes for Task 4
- **What was fixed**
  - Verified that `extract_midweek_fields_from_block` mirrors `extract_fields_from_block` by reusing `normalize_unicode_spaces`, edit-marker stripping, and underscore removal so midweek parsing does not diverge from the existing newcomer path.
  - Confirmed that blocks missing a `Newcomer ID` cleanly return an empty dict, giving downstream code a simple way to skip invalid midweek blocks without side effects.
- **Why**
  - Keeping the midweek extractor behavior aligned with the regular newcomer extractor avoids subtle inconsistencies in how WhatsApp text is cleaned and parsed across different templates.
  - Treating `Newcomer ID` as a required field at the extractor boundary enforces the invariant needed for later record-matching logic while keeping this function focused on pure extraction.
- **Remaining considerations**
  - Midweek option values (`Interested in Powerhouse`, `Powerhouse Available`, `Connected to Powerhouse`) are still returned as raw cleaned strings; Task 5 will be responsible for applying `normalize_midweek_option` and defining the canonical Yes/No/No update semantics.
  - Callers that iterate over midweek blocks will need to explicitly filter out empty dicts (invalid blocks) and may later add logging or reporting so volunteers can see which malformed updates were ignored.

5. Add logic to interpret and sanitize midweek option values:
   - Map user-entered values (e.g., `Yes`, `No`, `No update`, `N.A.`, blanks) into consistent canonical values for storage (e.g., `Yes`, `No`, `No update`, or empty).
   - Decide whether to store `No update` as a distinct value or treat it as “leave existing value unchanged” when updating newcomer records.
   - Document these normalization rules in `README.md` so volunteers understand how their inputs affect the data.

### Outcome for Task 5
- What you did
- Files changed
- Important notes
- Edge cases handled

### Review Fixes for Task 5
- **What was fixed**
  - Extended `normalize_midweek_option` to handle trailing punctuation and simple surrounding quotes so common inputs like `Yes,`, `No?`, or `"No"` still normalize to the canonical `Yes` / `No` / `No update` values instead of being treated as arbitrary free-text.
- **Why**
  - In real WhatsApp messages volunteers often type short answers with punctuation or quotes, and previously those variants would not have been recognized as valid options, slightly fragmenting the data model and complicating downstream logic.
- **Remaining considerations**
  - Midweek option normalization is still not wired into newcomer record update logic; Tasks 6–7 must treat canonical `No update` as a no-op when applying changes to newcomer rows and define how to handle any non-standard free-text values that still appear in midweek option fields.

6. Implement newcomer record lookup and update by `Newcomer ID`:
   - Load the existing newcomers data (e.g., from `hsg_newcomers_2026.csv`) into memory keyed by `Newcomer ID` for fast lookup.
   - For each parsed midweek update, find the matching newcomer row by `Newcomer ID` and ignore the `Name` field when an ID match is present.
   - When `Newcomer ID` is not found, do not fail the run; instead log a clear warning (and optionally write to an “unmatched midweek updates” report) and skip updating that record.

### Outcome for Task 6
- What you did
- Files changed
- Important notes
- Edge cases handled

### Review Fixes for Task 6
- **What was fixed**
  - Normalized `Newcomer ID` values in both `load_newcomers_by_id` and `match_midweek_updates_to_newcomers` using `normalize_unicode_spaces` so lookups are robust to non-breaking spaces and other whitespace quirks.
- **Why**
  - Without consistent normalization, a newcomer ID copied through WhatsApp or edited in a spreadsheet could contain invisible unicode spaces, causing midweek updates to silently fail to match existing records.
- **Remaining considerations**
  - These helpers still only perform lookup and matching; Tasks 7–9 must wire them into the midweek parsing pipeline, define the exact column update rules, and decide how unmatched updates are ultimately reported (e.g., a dedicated CSV).

7. Define column update rules for midweek data:
   - Decide which newcomer columns should be updated from midweek fields (e.g., create or use columns such as `Interested in Powerhouse`, `Powerhouse Available`, `Connected to Powerhouse`, `Midweek Update Notes`).
   - Implement “no-op” behavior for `No update` selections so existing values are preserved when volunteers explicitly choose not to update a field.
   - Ensure free-text `Update` content is appended or stored in a dedicated comments/notes column without overwriting earlier follow-up history unintentionally.

### Outcome for Task 7
- What you did
- Files changed
- Important notes
- Edge cases handled

### Review Fixes for Task 7
- **What was fixed**
  - Updated `apply_midweek_update_to_newcomer_row` so that `Update` field values which normalize to the canonical “No update” (including variants like `N.A.`, `N/A`, `NA`, or blanks) are treated as a no-op and do not get appended into `Midweek Update Notes`.
- **Why**
  - Volunteers may explicitly type “No update” or similar tokens in the free-text `Update` line to indicate there is nothing new to add, and previously these would have been stored verbatim in the notes column, cluttering follow-up history with non-informative entries.
- **Remaining considerations**
  - The midweek column update helpers are still not wired into an end-to-end midweek pipeline; Tasks 8–9 must invoke midweek parsing, matching, and `apply_midweek_updates_to_newcomers`, then persist the mutated newcomer dataset back to CSV (and optionally emit an “applied updates” report).
  - We continue to allow non-standard free-text values in the Yes/No/No update option fields; if later data review shows many such cases, we may want to either expand normalization rules or add light validation/logging to highlight unusual inputs.

8. Extend CSV writing logic to persist midweek updates:
   - Update or add functions that write the modified newcomer dataset back to the appropriate CSV file(s) after applying all midweek updates.
   - Ensure headers are updated if new columns are introduced, and that the column order remains stable or is clearly documented.
   - Consider writing an auxiliary CSV (e.g., `midweek_updates_applied.csv`) summarizing each applied update for verification.

### Outcome for Task 8
- What you did
  - Added `write_newcomers_sheet_with_midweek_updates` to persist the in-memory newcomers dataset (mutated by midweek updates) back to the main newcomers CSV while keeping the header aligned with `ALL_COLUMNS` and preserving row order.
  - Added `write_midweek_updates_applied_report` to emit an auxiliary `midweek_updates_applied.csv` (or caller-specified path) that summarizes each matched midweek update with normalized option values and raw free-text `Update` content for verification.
- Files changed
  - `followup_parser/parse_followup_updates.py`
- Important notes
  - `write_newcomers_sheet_with_midweek_updates` always upgrades the existing newcomers sheet schema via `ensure_newcomers_sheet_schema` before reading, so midweek columns are guaranteed to be present and in the canonical order defined by `ALL_COLUMNS`.
  - When persisting, the function walks the existing CSV rows in order and replaces only those whose `Newcomer ID` appears in `newcomers_by_id`, leaving all other rows untouched while still normalizing them into the extended schema.
  - `write_midweek_updates_applied_report` reports the canonical newcomer name from the CSV when available, falling back to the midweek `Name` field, and normalizes Yes/No/No update style options using `interpret_midweek_options` for consistent downstream analysis.
- Edge cases handled
  - If there are no newcomers in memory (`newcomers_by_id` is empty) or the newcomers sheet does not exist, `write_newcomers_sheet_with_midweek_updates` returns early and logs a clear warning in the latter case instead of failing.
  - Rows without a `Newcomer ID` in the existing CSV are preserved as-is (normalized into `ALL_COLUMNS`) and never matched to midweek updates, avoiding accidental updates to anonymous or malformed rows.
  - The persistence logic now also appends any newcomers present in `newcomers_by_id` that were not found in the existing sheet so they are not silently dropped, keeping the on-disk dataset in sync with the in-memory representation.

### Review Fixes for Task 8
- **What was fixed**
  - Updated `write_newcomers_sheet_with_midweek_updates` so that any newcomer rows present in the in-memory `newcomers_by_id` mapping but missing from the existing CSV are appended to the rewritten sheet instead of being silently discarded.
- **Why**
  - Previously, the function only merged changes for rows already present in the CSV, which could lead to data loss if callers injected new newcomers into the in-memory dataset (for example, as part of a future pipeline that creates newcomers and applies midweek updates in the same run).
- **Remaining considerations**
  - The midweek persistence helpers are defined but not yet wired into the CLI flow (Task 9); once integrated, we should add end-to-end tests that cover mixed scenarios (existing rows updated, new rows added, and no-op updates) and confirm that `midweek_updates_applied.csv` accurately reflects what changed.
  - Depending on how volunteers and leaders want to review changes, we may later choose to filter the applied-updates report to omit pure no-op midweek updates (where all options normalize to `No update` and the `Update` field is effectively empty).

9. Integrate midweek parsing into the command-line workflow:
   - Keep the existing CLI interface the same and have the script always attempt to parse both regular newcomer updates and midweek updates from the provided WhatsApp export.
   - Update the `main()` function control flow to run the midweek parsing and update logic after generating or loading the newcomer dataset, without introducing new midweek-specific arguments.
   - Ensure that existing behavior for regular follow-up parsing remains backward compatible and that runs still succeed even when no midweek updates are present.

### Outcome for Task 9
- What you did
- Files changed
- Important notes
- Edge cases handled

### Review Fixes for Task 9
- **What was fixed**
  - Relaxed the new midweek-type annotations in `parse_followup_updates.py` to use `typing.Dict` / `List` / `Tuple` / `Optional` instead of Python 3.10+ features like `list[...]` / `dict[...]` and `|` unions, so the CLI remains runnable on older Python 3 versions in line with the simple “Python 3” requirement in the README.
- **Why**
  - The original Task 9 implementation was logically correct but would raise a syntax error on environments still running Python 3.8 or 3.9, even though the underlying midweek parsing and update logic does not depend on newer language features.
- **Remaining considerations**
  - The midweek integration currently reads the WhatsApp export twice (once for regular newcomer updates and once for midweek updates); if performance becomes a concern, we could later refactor to share a single message-iteration pass while keeping the CLI surface unchanged.
  - Once Task 10 documentation is written, we should add at least one end-to-end test that exercises a mixed file containing both newcomer and midweek templates to guard against future regressions in the CLI wiring.

10. Add documentation and usage examples for midweek updates:
    - Update `README.md` with the midweek template, expectations for field labels, and example WhatsApp messages.
    - Document how to run the script (with the unchanged CLI) to process both regular and midweek updates, including notes on where midweek changes are written.
    - Include guidance on common edge cases (e.g., missing `Newcomer ID`, “No update” behavior, handling of malformed midweek messages).

### Outcome for Task 10
- What you did
- Files changed
- Important notes
- Edge cases handled

### Review Fixes for Task 10
- **What was fixed**
  - Updated the type annotations in `parse_followup_updates.py` to avoid using the Python 3.9+ `set[str]` syntax, switching to `Set[str]` from `typing` so the CLI remains compatible with older supported Python 3 versions.
  - Refreshed the midweek documentation in `README.md` to remove “preview” wording and clearly state that midweek parsing and option normalization are now fully implemented.
- **Why**
  - The lingering `set[str]` annotation would have caused a syntax error on Python 3.8 despite earlier efforts (Task 9) to keep the midweek pipeline compatible with older runtimes.
  - The outdated “preview” language could mislead volunteers into thinking midweek support is experimental or incomplete even though the underlying code is wired into the CLI.
- **Remaining considerations**
  - We still don’t have an automated test that exercises a mixed WhatsApp export containing both regular newcomer templates and midweek templates end-to-end; adding such a test would help catch future regressions in the docs or CLI wiring.
  - If future changes adjust where newcomers or midweek CSVs live on disk, we should re-verify that `README.md` paths and examples stay in sync with `parse_followup_updates.py`.
