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


