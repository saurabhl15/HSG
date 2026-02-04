## Follow-up WhatsApp Parser

This script parses newcomer follow-up updates that are posted in the **Followup Team** WhatsApp group using a fixed template, and converts them into a structured CSV file for reporting/analysis.

It supports both the **old** and **new** WhatsApp text export formats and can extract **multiple newcomer updates from a single message**.

---

## Overall flow

1. **Export WhatsApp chat** from the Followup Team group as a `.txt` file.
2. **Check all template messages** in the export and fix any template mistakes.
3. **Run the parser script** against the exported file for the date range you care about.
4. **Validate the number of records** in the generated CSV.

Each parsed newcomer update becomes **one row** in the output CSV.

---

## 1. Get WhatsApp chat export from Followup Team group

- **Open the Followup Team group in WhatsApp** (mobile or desktop).
- Use the **Export chat** option:
  - On mobile: `More > More options (⋮) > More > Export chat` (wording can vary slightly).
  - Choose **Without media**.
- Save the exported **`.txt` file** to your computer, e.g. `followup_chat.txt`.

You will pass this `.txt` file to the script using the `--file` argument.

---

## 2. Check the template messages

Before running the script:

- **Scan the chat export** (the `.txt` file) for messages that contain the newcomer template.
- **Count how many template messages** are present.  
  - This helps you later verify that the script extracted roughly the right number of records.
- **Check for template mistakes** in each message:
  - Spelling of field names
  - Extra/missing words
  - Missing colons (`:`) after field names
  - Wrong or missing numbering

The script is **tolerant** about:

- Bold (`*Field*`) vs plain (`Field`) field names
- Numbering like `1.`, `2.` before field names

But it **depends on the exact field labels** (spelling & spacing) below:

- `Newcomer Name`
- `Area`
- `Outstation`
- `Planted in another church`
- `Service Attended`
- `Came for Healing`
- `New Believer`
- `Showing desire to grow in the Lord`
- `Showing interest in being part of HSG`
- `Action Required`
- `Comments`

If any of these are mistyped or missing the colon, that value may be empty in the CSV.

---

## 3. Run the script

### Requirements

- Python 3 installed (on macOS, usually `python3`).

From the repository root (or directly from the `followup_parser` folder), you can run:

```bash
cd path/to/HSG/followup_parser

python3 parse_followup_updates.py \
  --file /absolute/path/to/followup_chat.txt \
  --start-date 05/01/2026 \
  --end-date 05/01/2026 \
  --output followup_output.csv
```

### Arguments

- **`--file`** (required):  
  Absolute path to the exported WhatsApp `.txt` file.

- **`--start-date`** (required):  
  Start date in `DD/MM/YYYY` format (e.g. `05/01/2026`).

- **`--end-date`** (required):  
  End date in `DD/MM/YYYY` format.

- **`--output`** (optional, default: `followup_output.csv`):  
  Name (or path) of the CSV file to write.

### What the script does

For each message in the WhatsApp export:

1. **Parses the WhatsApp header** (date, time, sender name).
2. **Filters by date** so only messages within `start-date` to `end-date` are considered.
3. **Finds one or more newcomer update blocks** in the message body, each starting with `Newcomer Name`.
4. For each block, it:
   - Extracts values for each template field.
   - Cleans formatting (bold markers, underscores, edited markers).
5. **Writes all extracted updates to CSV**, with one row per newcomer.

At the end it prints:

- How many updates it parsed.
- Where the CSV was written.

---

## 4. Validate the CSV record count

After the script completes:

1. **Open the generated CSV** (e.g. `followup_output.csv`) in Excel, Google Sheets, or Numbers.
2. **Check the number of data rows**:
   - Row count **minus 1** (for the header row) should roughly match the **number of newcomer updates** you expect from the chat.
   - Remember: a single WhatsApp message can contain **multiple newcomer blocks**, so the number of rows may be **greater** than the number of template messages.

If counts are off, re-check:

- Whether all messages used the correct template labels and colons.
- Whether the date range (`--start-date`, `--end-date`) was set correctly.

---

## WhatsApp template format

Below is the **recommended template** to be used in the Followup Team group.  
The numbering and bolding help readability, but the parser only requires that the **field names and colons match exactly**.

```text
1. *Newcomer Name*: <name>
2. *Area*: <area>
3. *Outstation*: <outstation / N.A.>
4. *Planted in another church*: <Yes/No/Unknown>
5. *Service Attended*: <service details>
6. *Came for Healing*: <Yes/No/Details>
7. *New Believer*: <Yes/No/Unknown>
8. *Showing desire to grow in the Lord*: <Yes/No/Details>
9. *Showing interest in being part of HSG*: <Yes/No/Details>
10. *Action Required*: <what needs to be done>
11. *Comments*: <any other notes>
```

Key points:

- Keep the **field names exactly as shown** (including capitalization and spaces).
- Ensure each field line has a **colon `:`** right after the field name.
- If you don’t know a value, still include the field line and put something like `N.A.` or `Unknown`.

Using this template consistently will make the CSV clean and reliable.


---

## Midweek option normalization

The parser has been extended to support a **midweek WhatsApp template** with
Yes/No/No update style questions such as:

- `Interested in Powerhouse`
- `Powerhouse Available`
- `Connected to Powerhouse`

For these midweek fields, the script interprets option values as follows:

- **Yes**: values like `Yes`, `Y`, `yes.`, etc. are stored canonically as `Yes`.
- **No**: values like `No`, `N`, `no.`, etc. are stored canonically as `No`.
- **No update** (leave unchanged):
  - Values like `No update`, `no update`, `NO UPDATE`, with any spacing/punctuation.
  - Shorthand such as `N.A.`, `N/A`, `NA`.
  - Completely blank values.
  - All of these are normalized to the canonical value `No update`.
- **Anything else**: any other non-empty text is preserved as-is so that
  important free-text notes are not lost.

When applying midweek updates to the newcomers CSV, a canonical `No update`
value will be treated as **“leave the existing value unchanged”** for that
field rather than writing the words `No update` into the sheet.


## Midweek updates – template, behavior, and edge cases

The parser now supports a **midweek WhatsApp template** that lets volunteers
update newcomer follow-up status during the week using a short form that is
separate from the main newcomer template.

Midweek updates are detected **from the same WhatsApp export file** as regular
newcomer updates, so you still run the script **once** and it will:

- Parse regular newcomer templates into `followup_output.csv`.
- Parse midweek templates and apply changes into the newcomers sheet.

---

### Midweek WhatsApp template

Use the following template in the Followup Team group for midweek updates:

```text
1. *Newcomer ID*: HSGNC0001
2. *Name*: <newcomer name>
3. *Interested in Powerhouse*: <Yes / No / No update>
4. *Powerhouse Available*: <Yes / No / No update>
5. *Connected to Powerhouse*: <Yes / No / No update>
6. *Update*: <free-text update or "No update">
```

Key expectations:

- **Newcomer ID is required**
  - The parser uses `Newcomer ID` to find the correct row in the newcomers CSV.
  - If `Newcomer ID` is missing or empty, that midweek block is ignored.
- **Field labels**
  - The script recognizes `Newcomer ID`, `Name` (or `Newcomer Name`), `Interested in Powerhouse`,
    `Powerhouse Available`, `Connected to Powerhouse`, and `Update`.
  - Bolding (`*Field*`) and numbering (`1.`, `2.`) are optional; spacing and casing are handled
    generously, but spelling of the core words should match.
- **Multiple blocks per message**
  - Like the main template, a single WhatsApp message can contain **multiple midweek blocks**,
    each starting with a `Newcomer ID` line.

---

### Where midweek updates are stored

Midweek data is applied into the main newcomers sheet:

- **Main newcomers CSV**
  - File: `followup_parser/hsg_newcomers_2026.csv` (relative to the repository root).
  - Additional midweek columns in the sheet:
    - `Interested in Powerhouse`
    - `Powerhouse Available`
    - `Connected to Powerhouse`
    - `Midweek Update Notes`
  - When midweek updates are applied, these columns are updated for matching `Newcomer ID`s,
    and free-text notes are appended into `Midweek Update Notes` instead of overwriting history.

- **Midweek updates report**
  - File: `followup_parser/midweek_updates_applied.csv`.
  - Each row summarizes a single applied midweek update:
    - `Newcomer ID`, canonical `Newcomer Name`
    - Normalized values for `Interested in Powerhouse`, `Powerhouse Available`,
      and `Connected to Powerhouse`
    - The raw cleaned `Update` text

If no valid midweek updates are found, these files are left unchanged or not created.

---

### Running the script with midweek updates

The **CLI interface is unchanged**. You still run:

```bash
cd path/to/HSG/followup_parser

python3 parse_followup_updates.py \
  --file /absolute/path/to/followup_chat.txt \
  --start-date 05/01/2026 \
  --end-date 05/01/2026 \
  --output followup_output.csv
```

In a single run the script will:

1. Parse regular newcomer templates into the `--output` CSV (default `followup_output.csv`).
2. Assign `Newcomer ID`s for those newcomers and append them into `hsg_newcomers_2026.csv`.
3. Re-scan the same WhatsApp export for **midweek** templates within the same date range.
4. Match midweek updates to existing newcomers by `Newcomer ID`.
5. Apply midweek changes to the in-memory newcomers dataset.
6. Persist the updated newcomers sheet and write `midweek_updates_applied.csv` when applicable.

You do **not** need any extra flags to enable midweek behavior.

---

### How midweek option values are interpreted

For the Yes/No/No update style midweek fields:

- **Yes**
  - Values like `Yes`, `Y`, `yes.`, `"Yes"`, `Yes!` are all stored as `Yes`.
- **No**
  - Values like `No`, `N`, `no?`, `"No"`, `No,` are all stored as `No`.
- **No update** (leave unchanged)
  - Values like `No update`, `no update`, `NO UPDATE`, with any spacing or punctuation.
  - Shorthand such as `N.A.`, `N/A`, `NA`.
  - Completely blank values.
  - All of these normalize to the canonical value `No update`.
- **Anything else**
  - Any other non-empty text is preserved as-is so important notes are not lost.

When applying midweek updates to the newcomers CSV:

- A canonical `No update` **does not overwrite** the existing value in that column
  (it is treated as “leave unchanged”).
- The same `No update` detection is also applied to the free-text `Update` line so that
  things like `"No update"` or `N.A.` do **not** clutter `Midweek Update Notes`.

---

### Midweek edge cases and how they are handled

- **Missing `Newcomer ID`**
  - Midweek blocks without a `Newcomer ID` are treated as invalid and skipped.
  - These do not stop the script; they are simply ignored.
- **Unknown `Newcomer ID`**
  - If a midweek block has an ID that does not match any row in `hsg_newcomers_2026.csv`,
    that update is skipped and a warning is printed to the console.
- **Partial or malformed midweek messages**
  - If only some fields are present, only those fields are considered for updates;
    others are left unchanged.
  - Completely empty or unusable blocks are ignored.
- **No midweek updates in the file**
  - The script behaves exactly as before: only the regular newcomer CSV is produced,
    with no midweek changes written.

