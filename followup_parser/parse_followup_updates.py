import re
import csv
import argparse
import os
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

# =====================================================================
# NORMALIZE UNICODE WHITESPACE
# =====================================================================

def normalize_unicode_spaces(text: str) -> str:
    # Replace various unicode spaces with normal space, collapse multiples
    if text is None:
        return ""
    text = text.replace("\u202F", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =====================================================================
# WHATSAPP HEADER FORMATS
# =====================================================================

# New WhatsApp export format, e.g.:
# [2025-12-08, 9:50:53 AM] ~ SR: message...
WHATSAPP_REGEX_V2 = re.compile(
    r"^\[(\d{4}-\d{2}-\d{2}),\s*([\d:]+\s*[APMapm]{2})\]\s*(?:~\s*)?(.*?)\s*:\s*(.*)$",
    re.IGNORECASE,
)

# Old WhatsApp export format, e.g.:
# 12/09/2025, 10:20 pm - John Doe: message...
WHATSAPP_REGEX_V1 = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}\s*[APMapm]{2})\s*-\s*(.*?):\s*(.*)$",
    re.IGNORECASE,
)


# =====================================================================
# FIELD PATTERNS – accept bold, plain, and numbered formats
# =====================================================================

# Each pattern:
#   - optional leading "1. " or "2. "
#   - optional * around the field name
#   - colon and value
FIELD_PATTERNS = {
    "Newcomer Name": r"(?:\d+\.\s*)?\*?Newcomer Name\*?\s*:\s*(.*)",
    "Area": r"(?:\d+\.\s*)?\*?Area\*?\s*:\s*(.*)",
    "Outstation": r"(?:\d+\.\s*)?\*?Outstation\*?\s*:\s*(.*)",
    "Planted in another church": r"(?:\d+\.\s*)?\*?Planted in another church\*?\s*:\s*(.*)",
    "Service Attended": r"(?:\d+\.\s*)?\*?Service Attended\*?\s*:\s*(.*)",
    "Came for Healing": r"(?:\d+\.\s*)?\*?Came for Healing\*?\s*:\s*(.*)",
    "New Believer": r"(?:\d+\.\s*)?\*?New Believer\*?\s*:\s*(.*)",
    "Showing desire to grow in the Lord": r"(?:\d+\.\s*)?\*?Showing desire to grow in the Lord\*?\s*:\s*(.*)",
    "Showing interest in being part of HSG": r"(?:\d+\.\s*)?\*?Showing interest in being part of HSG\*?\s*:\s*(.*)",
    "Action Required": r"(?:\d+\.\s*)?\*?Action Required\*?\s*:\s*(.*)",
    "Comments": r"(?:\d+\.\s*)?\*?Comments\*?\s*:\s*(.*)",
}


# Midweek WhatsApp template field patterns.
# These mirror FIELD_PATTERNS but target the dedicated midweek
# template fields described in Task 2, and are intentionally:
#   - tolerant of bold markers (*Field*)
#   - tolerant of optional numbering ("1. *Field*: ...")
#   - tolerant of casing and excess whitespace
MIDWEEK_FIELD_PATTERNS = {
    "Newcomer ID": r"(?:\d+\.\s*)?\*?Newcomer ID\*?\s*:\s*(.*)",
    # Some volunteers may still use "Newcomer Name"; accept both.
    "Name": r"(?:\d+\.\s*)?\*?(?:Name|Newcomer Name)\*?\s*:\s*(.*)",
    "Interested in Powerhouse": r"(?:\d+\.\s*)?\*?Interested in Powerhouse\*?\s*:\s*(.*)",
    "Powerhouse Available": r"(?:\d+\.\s*)?\*?Powerhouse Available\*?\s*:\s*(.*)",
    "Connected to Powerhouse": r"(?:\d+\.\s*)?\*?Connected to Powerhouse\*?\s*:\s*(.*)",
    "Update": r"(?:\d+\.\s*)?\*?Update\*?\s*:\s*(.*)",
}

# Columns that store midweek follow-up state for each newcomer.
# These live alongside the regular follow-up columns in the same
# newcomers CSV (`hsg_newcomers_2026.csv`) so that midweek updates
# enrich a single master dataset instead of a separate sheet.
MIDWEEK_COLUMNS = [
    "Interested in Powerhouse",
    "Powerhouse Available",
    "Connected to Powerhouse",
    "Midweek Update Notes",
]


def normalize_midweek_option(value: str) -> str:
    """
    Normalize midweek Yes / No / No update style options into
    a consistent internal representation.

    Rules:
      - Trim and normalize unicode/ASCII whitespace.
      - Compare case-insensitively.
      - Map "yes" variants -> "Yes".
      - Map "no" variants  -> "No".
      - Map "no update" variants, common "N.A."-style tokens,
        and blank values -> "No update".
      - Fall back to the cleaned original text for anything else
        (e.g., free-text notes) so we do not lose information.
    """
    if value is None:
        value = ""

    # Normalize spaces and trim; keep a copy for fallback.
    cleaned = normalize_unicode_spaces(str(value))
    if not cleaned:
        return "No update"

    lower = cleaned.lower().strip()
    # Strip simple surrounding quotes that some volunteers may use,
    # e.g. "Yes" or 'No'.
    if (lower.startswith('"') and lower.endswith('"')) or (
        lower.startswith("'") and lower.endswith("'")
    ):
        lower = lower[1:-1].strip()

    # Strip common trailing punctuation (".", "!", "?", ",", ";", ":")
    # without being overly aggressive about other characters.
    lower = lower.rstrip(".!?,;:")

    if lower in {"yes", "y"}:
        return "Yes"
    if lower in {"no", "n"}:
        return "No"

    compact = lower.replace(" ", "")
    # Treat any "no update" spelling or spacing the same, and
    # intentionally also consider explicit "no update" choices
    # and common "N.A." / "N/A" style tokens equivalent to an
    # omitted/blank option.
    if compact == "noupdate":
        return "No update"
    if compact in {"na", "n/a", "n.a"}:
        return "No update"

    return cleaned


# Midweek fields that use the Yes/No/No update option semantics.
MIDWEEK_OPTION_FIELDS = [
    "Interested in Powerhouse",
    "Powerhouse Available",
    "Connected to Powerhouse",
]


def interpret_midweek_options(midweek_update: Dict[str, str]) -> Dict[str, str]:
    """
    Return a copy of a midweek update dict with all Yes/No/No update-style
    option fields normalized via normalize_midweek_option.

    Canonical behavior:
      - "Yes"/"Y"/variants -> "Yes"
      - "No"/"N"/variants  -> "No"
      - "No update" spellings, N.A./N/A/NA, and blanks -> "No update"
      - Any other non-empty text is preserved as-is.

    Downstream record-update logic (Tasks 6–7) should treat a canonical
    "No update" value as a *no-op* for that field, i.e. keep the existing
    newcomer CSV value unchanged rather than writing "No update" into the
    sheet.
    """
    sanitized = dict(midweek_update)

    for field in MIDWEEK_OPTION_FIELDS:
        if field in sanitized:
            sanitized[field] = normalize_midweek_option(sanitized[field])

    return sanitized


def is_midweek_no_update(value: str) -> bool:
    """
    Convenience helper to check whether a raw midweek option value should be
    treated as an explicit "No update" (leave existing value unchanged).
    """
    return normalize_midweek_option(value) == "No update"

ALL_COLUMNS = [
    "Date",
    "Time",
    "Volunteer Name",
    "Newcomer ID",
    "Newcomer Name",
    "Area",
    "Outstation",
    "Planted in another church",
    "Service Attended",
    "Came for Healing",
    "New Believer",
    "Showing desire to grow in the Lord",
    "Showing interest in being part of HSG",
    "Action Required",
    "Comments",
] + MIDWEEK_COLUMNS


# =====================================================================
# LOAD MULTILINE MESSAGES
# =====================================================================

def load_messages(path: str):
    """
    Aggregate multiline WhatsApp messages into single logical entries.
    A new message starts when a line matches either header regex.
    """
    messages = []
    buffer = ""

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = normalize_unicode_spaces(raw_line.rstrip("\n"))

            if WHATSAPP_REGEX_V2.match(line) or WHATSAPP_REGEX_V1.match(line):
                if buffer:
                    messages.append(buffer)
                buffer = line
            else:
                buffer += "\n" + line

    if buffer:
        messages.append(buffer)

    return messages


# =====================================================================
# PARSE MESSAGE HEADER + BODY
# =====================================================================

def parse_header(message: str):
    """
    Take a full multi-line message and:
      - parse the first line as header (date, time, sender, first-line text)
      - reattach the rest of the lines as the body
    Returns: (date_str_dd_mm_yyyy, time_str, sender, body) or None
    """
    lines = message.splitlines()
    if not lines:
        return None

    header_line = normalize_unicode_spaces(lines[0])
    rest = "\n".join(lines[1:])

    # New format
    m2 = WHATSAPP_REGEX_V2.match(header_line)
    if m2:
        date_str, time_str, sender, first_msg = m2.groups()
        body = first_msg + ("\n" + rest if rest else "")
        date_norm = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
        return date_norm, time_str.strip(), sender.strip(), body.strip()

    # Old format
    m1 = WHATSAPP_REGEX_V1.match(header_line)
    if m1:
        date_str, time_str, sender, first_msg = m1.groups()
        body = first_msg + ("\n" + rest if rest else "")
        return date_str, time_str.strip(), sender.strip(), body.strip()

    return None


# =====================================================================
# BLOCK START DETECTION – robust for bold/plain/numbered
# =====================================================================

BLOCK_START_REGEX = re.compile(
    r"^\s*(?:\d+\.\s*)?\*?Newcomer Name\*?\s*:",
    re.IGNORECASE,
)

# Midweek blocks start with a Newcomer ID line (optionally numbered
# and/or bolded), e.g.:
#   "1. *Newcomer ID*: HSGNC0001"
#   "*Newcomer ID*: HSGNC0002"
#   "Newcomer ID: HSGNC0003"
MIDWEEK_BLOCK_START_REGEX = re.compile(
    r"^\s*(?:\d+\.\s*)?\*?Newcomer ID\*?\s*:",
    re.IGNORECASE,
)


# =====================================================================
# PARSE MULTIPLE UPDATE BLOCKS FROM BODY
# =====================================================================


def _split_blocks_by_start_regex(body: str, start_regex: re.Pattern) -> List[str]:
    """
    Shared helper to split a message body into logical blocks, where each
    block starts with a line that matches the given start_regex.

    This is used for both the regular newcomer template and the midweek
    template so that their block detection behavior stays in sync.
    """
    blocks: List[str] = []
    lines = [normalize_unicode_spaces(l) for l in body.splitlines()]

    current_block_lines: List[str] = []

    for line in lines:
        if start_regex.match(line):
            # Start of a new block.
            if current_block_lines:
                block_text = "\n".join(current_block_lines).strip()
                if block_text:
                    blocks.append(block_text)
            current_block_lines = [line]
        else:
            # Continuation of current block (if any).
            if current_block_lines:
                current_block_lines.append(line)

    # Final trailing block.
    if current_block_lines:
        block_text = "\n".join(current_block_lines).strip()
        if block_text:
            blocks.append(block_text)

    return blocks


def parse_updates(body: str):
    """
    Extract one or more newcomer update blocks from a message body.

    Strategy:
      - Walk line by line.
      - When we see a "Newcomer Name" line (bold / plain / numbered), start a new block.
      - All following lines belong to that block until the next "Newcomer Name" line.
      - For each block, apply FIELD_PATTERNS.
    """
    block_texts = _split_blocks_by_start_regex(body, BLOCK_START_REGEX)
    updates = [extract_fields_from_block(block) for block in block_texts]

    # Filter out completely empty blocks (e.g., if somehow no name or fields).
    updates = [u for u in updates if any(v for v in u.values())]

    return updates


def parse_midweek_blocks(body: str):
    """
    Extract one or more midweek update blocks from a message body.

    Strategy mirrors parse_updates:
      - Walk line by line.
      - When we see a "Newcomer ID" line (bold / plain / numbered),
        start a new midweek block.
      - All following lines belong to that block until the next
        "Newcomer ID" line.
      - Return the raw block texts so downstream tasks can apply
        MIDWEEK_FIELD_PATTERNS to extract individual fields.
    """
    return _split_blocks_by_start_regex(body, MIDWEEK_BLOCK_START_REGEX)


def extract_fields_from_block(block: str):
    """
    Given a single newcomer block text, apply FIELD_PATTERNS to extract values.
    Cleans underscores and "<...>" edit markers.
    """
    update = {}

    for field, pattern in FIELD_PATTERNS.items():
        m = re.search(pattern, block, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
        else:
            val = ""

        # Remove edit markers like "<This message was edited>"
        val = re.sub(r"<.*?>", "", val).strip()

        # Strip underscores that were used for formatting
        val = val.replace("_", "").strip()

        update[field] = val

    return update


def extract_midweek_fields_from_block(block: str) -> Dict[str, str]:
    """
    Given a single midweek block text, apply MIDWEEK_FIELD_PATTERNS
    to extract values for the dedicated midweek template fields.

    This mirrors extract_fields_from_block but targets:
      - Newcomer ID
      - Name
      - Interested in Powerhouse
      - Powerhouse Available
      - Connected to Powerhouse
      - Update

    Basic validation:
      - If the required "Newcomer ID" field is missing or empty,
        return an empty dict so callers can skip or report the block.
    """
    midweek_update: Dict[str, str] = {}

    # Apply the same text clean-up rules used for regular newcomer
    # blocks so behavior stays consistent.
    for field, pattern in MIDWEEK_FIELD_PATTERNS.items():
        m = re.search(pattern, block, re.IGNORECASE)
        if m:
            raw_val = m.group(1)
        else:
            raw_val = ""

        # Normalize unicode/ASCII whitespace.
        val = normalize_unicode_spaces(raw_val)

        # Remove edit markers like "<This message was edited>".
        val = re.sub(r"<.*?>", "", val).strip()

        # Strip underscores that were used for formatting.
        val = val.replace("_", "").strip()

        midweek_update[field] = val

    # Require a Newcomer ID for the block to be considered valid.
    if not midweek_update.get("Newcomer ID"):
        return {}

    return midweek_update


# =====================================================================
# MAIN PARSE FUNCTION
# =====================================================================

def parse_whatsapp_file(path: str, start_date, end_date):
    messages = load_messages(path)
    records = []

    for msg in messages:
        parsed = parse_header(msg)
        if not parsed:
            continue

        date_str, time_str, sender, body = parsed
        time_str = normalize_unicode_spaces(time_str)

        # Build datetime for date range filtering
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %I:%M:%S %p")
        except ValueError:
            dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %I:%M %p")

        if not (start_date <= dt.date() <= end_date):
            continue

        # Extract newcomer update blocks
        updates = parse_updates(body)

        for u in updates:
            records.append({
                "Date": date_str,
                "Time": time_str,
                "Volunteer Name": sender,
                **u,
            })

    return records


def parse_midweek_updates_from_whatsapp_file(
    path: str,
    start_date,
    end_date,
) -> List[Dict[str, str]]:
    """
    Parse midweek update blocks from a WhatsApp export file within a
    given date range.

    This mirrors parse_whatsapp_file but targets the dedicated midweek
    template using:
      - parse_midweek_blocks to split the message body into blocks.
      - extract_midweek_fields_from_block to pull out midweek fields.

    Returns a list of midweek update dicts, each of which is suitable
    for matching against newcomers by Newcomer ID.
    """
    messages = load_messages(path)
    midweek_updates: List[Dict[str, str]] = []

    for msg in messages:
        parsed = parse_header(msg)
        if not parsed:
            continue

        date_str, time_str, sender, body = parsed
        time_str = normalize_unicode_spaces(time_str)

        # Build datetime for date range filtering (same as parse_whatsapp_file).
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %I:%M:%S %p")
        except ValueError:
            dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %I:%M %p")

        if not (start_date <= dt.date() <= end_date):
            continue

        # Extract midweek update blocks from the message body.
        block_texts = parse_midweek_blocks(body)
        for block in block_texts:
            midweek_update = extract_midweek_fields_from_block(block)
            # Skip invalid blocks that are missing a Newcomer ID.
            if not midweek_update:
                continue
            midweek_updates.append(midweek_update)

    return midweek_updates


# =====================================================================
# WRITE CSV
# =====================================================================

def write_csv(records, out_path: str):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_COLUMNS)
        writer.writeheader()
        for r in records:
            writer.writerow(r)


# =====================================================================
# NEWCOMER ID HELPERS
# =====================================================================

NEWCOMERS_SHEET_NAME = "hsg_newcomers_2026.csv"
MIDWEEK_UPDATES_APPLIED_SHEET_NAME = "midweek_updates_applied.csv"
NEWCOMER_ID_PREFIX = "HSGNC"
NEWCOMER_ID_WIDTH = 4


def format_newcomer_id(n: int) -> str:
    """
    Format a newcomer ID like HSGNC0001 given a numeric counter.
    """
    return f"{NEWCOMER_ID_PREFIX}{n:0{NEWCOMER_ID_WIDTH}d}"


def get_last_newcomer_id(sheet_path: str) -> int:
    """
    Read the newcomers sheet (if it exists) and return the highest numeric
    newcomer ID found, or 0 if the sheet does not exist or has no valid IDs.
    """
    if not os.path.exists(sheet_path):
        return 0

    last_id_num = 0

    try:
        with open(sheet_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_id = (row.get("Newcomer ID") or "").strip()
                if not raw_id:
                    continue

                m = re.match(rf"^{NEWCOMER_ID_PREFIX}(\d{{{NEWCOMER_ID_WIDTH}}})$", raw_id)
                if not m:
                    continue

                num = int(m.group(1))
                if num > last_id_num:
                    last_id_num = num
    except FileNotFoundError:
        return 0
    except Exception:
        # Be tolerant of any issues in the existing sheet; just fall back to
        # whatever highest ID we have seen so far.
        return last_id_num

    return last_id_num


def ensure_newcomers_sheet_schema(sheet_path: str) -> None:
    """
    Ensure the newcomers CSV header matches ALL_COLUMNS.

    If the file already exists with an older header (e.g., before midweek
    columns were added), rewrite it with the new header and map existing
    rows into the extended schema so downstream code sees a consistent
    data model.
    """
    if not os.path.exists(sheet_path):
        return

    # Peek at the current header row.
    with open(sheet_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            existing_header = next(reader)
        except StopIteration:
            # Empty file; let append_newcomers_sheet write a fresh header later.
            return

    if existing_header == ALL_COLUMNS:
        # Already on the latest schema.
        return

    # Re-read all rows under the existing header and normalize them
    # into the new schema so we can safely rewrite the file.
    with open(sheet_path, "r", newline="", encoding="utf-8") as f:
        dict_reader = csv.DictReader(f)
        existing_rows = list(dict_reader)

    normalized_rows = []
    for row in existing_rows:
        normalized = {col: (row.get(col) or "") for col in ALL_COLUMNS}
        normalized_rows.append(normalized)

    with open(sheet_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_COLUMNS)
        writer.writeheader()
        for r in normalized_rows:
            writer.writerow(r)


def append_newcomers_sheet(records, sheet_path: str):
    """
    Append the given records to the persistent newcomers sheet, creating it
    with a header row if it does not already exist.
    """
    if not records:
        return

    # If the sheet already exists, make sure its header has been upgraded
    # to the latest ALL_COLUMNS schema before we append new rows.
    ensure_newcomers_sheet_schema(sheet_path)

    file_exists = os.path.exists(sheet_path)

    with open(sheet_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_COLUMNS)
        if not file_exists:
            writer.writeheader()
        for r in records:
            writer.writerow(r)


# =====================================================================
# MIDWEEK NEWCOMER LOOKUP BY NEWCOMER ID
# =====================================================================


def load_newcomers_by_id(sheet_path: str) -> Dict[str, Dict[str, str]]:
    """
    Load the existing newcomers CSV into memory keyed by Newcomer ID.

    This helper is designed for midweek updates:
      - Ensures the sheet schema is upgraded to ALL_COLUMNS before reading.
      - Skips rows that do not have a Newcomer ID.
      - Returns a dict mapping "Newcomer ID" -> row dict.

    Callers can then look up and mutate the row dicts in place before
    writing the dataset back to disk (handled in later tasks).
    """
    if not os.path.exists(sheet_path):
        return {}

    # Make sure the header is on the latest schema before we read.
    ensure_newcomers_sheet_schema(sheet_path)

    newcomers_by_id: Dict[str, Dict[str, str]] = {}

    with open(sheet_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize any stray unicode/ASCII whitespace in the ID so that
            # lookups behave consistently even if the sheet was edited
            # manually or imported/exported through different tools.
            raw_id = row.get("Newcomer ID") or ""
            newcomer_id = normalize_unicode_spaces(raw_id)
            if not newcomer_id:
                continue

            # If duplicate IDs exist, the last one wins. This mirrors
            # how most spreadsheets behave when keyed by ID.
            newcomers_by_id[newcomer_id] = row

    return newcomers_by_id


def match_midweek_updates_to_newcomers(
    midweek_updates: List[Dict[str, str]],
    newcomers_by_id: Dict[str, Dict[str, str]],
    *,
    unmatched_collector: Optional[List[Dict[str, str]]] = None,
) -> List[Tuple[Dict[str, str], Dict[str, str]]]:
    """
    Match parsed midweek updates to existing newcomer records by Newcomer ID.

    Responsibilities for Task 6:
      - Use "Newcomer ID" as the sole lookup key (ignore Name when ID exists).
      - Do not raise if an ID is missing or not found; emit a clear warning
        and skip updating that record.
      - Optionally collect unmatched midweek updates for reporting.

    Returns a list of (midweek_update, newcomer_row) pairs that downstream
    code (Tasks 7–8) can use to actually apply column-level changes.
    """
    matched: List[Tuple[Dict[str, str], Dict[str, str]]] = []

    for update in midweek_updates:
        # Normalize the ID using the same helper as when reading from
        # the newcomers sheet so that matching is resilient to any
        # invisible whitespace differences between sources.
        raw_id = update.get("Newcomer ID") or ""
        newcomer_id = normalize_unicode_spaces(raw_id)

        if not newcomer_id:
            # extract_midweek_fields_from_block should already enforce this,
            # but be defensive so the lookup logic is robust on its own.
            print(
                "WARNING: Midweek update is missing 'Newcomer ID'; "
                "skipping this update."
            )
            if unmatched_collector is not None:
                unmatched_collector.append(update)
            continue

        target_row = newcomers_by_id.get(newcomer_id)
        if target_row is None:
            print(
                f"WARNING: No newcomer found with Newcomer ID '{newcomer_id}' "
                "when applying midweek update; skipping this update."
            )
            if unmatched_collector is not None:
                unmatched_collector.append(update)
            continue

        # At this stage we intentionally ignore the Name field when an ID
        # match is present, relying solely on the ID for record identity.
        matched.append((update, target_row))

    return matched


# =====================================================================
# MIDWEEK COLUMN UPDATE RULES (Task 7)
# =====================================================================


def apply_midweek_update_to_newcomer_row(
    midweek_update: Dict[str, str],
    newcomer_row: Dict[str, str],
) -> None:
    """
    Apply a single midweek update dict to a newcomer row in place.

    Responsibilities for Task 7:
      - Update the dedicated midweek columns from the parsed midweek fields.
      - Treat canonical "No update" options as a no-op for that field.
      - Append free-text Update content into the Midweek Update Notes column
        without overwriting earlier history.
    """
    if not midweek_update:
        return

    # Normalize option-style fields first so we can reliably detect "No update".
    normalized = interpret_midweek_options(midweek_update)

    # Apply option fields into the corresponding newcomer columns.
    for field in MIDWEEK_OPTION_FIELDS:
        value = normalized.get(field)
        if not value:
            continue
        if value == "No update":
            # Explicitly chosen no-op; leave existing value unchanged.
            continue
        newcomer_row[field] = value

    # Handle the free-text Update field, if present. This is stored in the
    # dedicated Midweek Update Notes column, and new content is appended so
    # that earlier follow-up history is preserved.
    raw_update_text = midweek_update.get("Update") or ""
    if not raw_update_text:
        return

    # Treat explicit "No update"/N.A./blank-style answers in the Update field
    # as a no-op as well, to avoid cluttering the notes column with noise.
    if is_midweek_no_update(raw_update_text):
        return

    update_text = normalize_unicode_spaces(raw_update_text)
    if not update_text:
        return

    existing_notes_raw = newcomer_row.get("Midweek Update Notes") or ""
    existing_notes = normalize_unicode_spaces(existing_notes_raw)

    if existing_notes:
        newcomer_row["Midweek Update Notes"] = f"{existing_notes} | {update_text}"
    else:
        newcomer_row["Midweek Update Notes"] = update_text


def apply_midweek_updates_to_newcomers(
    matched_pairs: List[Tuple[Dict[str, str], Dict[str, str]]],
) -> None:
    """
    Apply a sequence of matched midweek updates to their corresponding
    newcomer rows, mutating the newcomer row dicts in place.

    Each element in matched_pairs is a (midweek_update, newcomer_row) tuple
    as returned by match_midweek_updates_to_newcomers.
    """
    for midweek_update, newcomer_row in matched_pairs:
        apply_midweek_update_to_newcomer_row(midweek_update, newcomer_row)


# =====================================================================
# MIDWEEK CSV PERSISTENCE (Task 8)
# =====================================================================


def write_newcomers_sheet_with_midweek_updates(
    newcomers_by_id: Dict[str, Dict[str, str]],
    sheet_path: str,
) -> None:
    """
    Persist the in-memory newcomers dataset (mutated by midweek updates)
    back to the main newcomers CSV on disk.

    Responsibilities for Task 8:
      - Ensure the CSV header matches ALL_COLUMNS (including midweek columns).
      - Preserve the existing row order and any rows that were not part of
        the midweek update set.
      - Keep column order stable and clearly defined via ALL_COLUMNS.
    """
    if not newcomers_by_id:
        # Nothing to persist; either there were no newcomers or no midweek
        # updates were applied.
        return

    if not os.path.exists(sheet_path):
        # If the newcomers sheet does not exist, there is nothing to update.
        # Midweek updates are only meaningful when there is an existing
        # newcomer dataset to apply them to.
        print(
            "WARNING: Newcomers sheet not found when trying to persist "
            "midweek updates; no CSV was written."
        )
        return

    # Ensure the existing sheet is on the latest schema before we read it.
    ensure_newcomers_sheet_schema(sheet_path)

    # Read all existing rows so we can merge in the mutated rows keyed by ID
    # while preserving overall row order.
    with open(sheet_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)

    updated_rows: List[Dict[str, str]] = []
    seen_ids: Set[str] = set()

    for row in existing_rows:
        raw_id = row.get("Newcomer ID") or ""
        newcomer_id = normalize_unicode_spaces(raw_id)

        if newcomer_id and newcomer_id in newcomers_by_id:
            # Use the mutated row from newcomers_by_id as the source of truth
            # for this newcomer, but make sure all columns are present and
            # ordered according to ALL_COLUMNS.
            source_row = newcomers_by_id[newcomer_id]
            merged = {col: (source_row.get(col) or "") for col in ALL_COLUMNS}
        else:
            # Keep the original row but normalize it into the ALL_COLUMNS
            # schema so that any newly introduced columns are present.
            merged = {col: (row.get(col) or "") for col in ALL_COLUMNS}

        updated_rows.append(merged)

        if newcomer_id:
            seen_ids.add(newcomer_id)

    # If newcomers_by_id contains any newcomer IDs that were not present in the
    # existing sheet (for example, if callers injected new newcomers into the
    # in-memory dataset before persisting), append those rows at the end so
    # they are not silently dropped.
    for newcomer_id, source_row in newcomers_by_id.items():
        if not newcomer_id or newcomer_id in seen_ids:
            continue
        merged = {col: (source_row.get(col) or "") for col in ALL_COLUMNS}
        updated_rows.append(merged)

    # Rewrite the sheet with the updated dataset and a stable header.
    with open(sheet_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_COLUMNS)
        writer.writeheader()
        for r in updated_rows:
            writer.writerow(r)


def write_midweek_updates_applied_report(
    matched_pairs: List[Tuple[Dict[str, str], Dict[str, str]]],
    report_path: str,
) -> None:
    """
    Write an auxiliary CSV summarizing each applied midweek update.

    Each row captures:
      - Newcomer ID and canonical newcomer name.
      - The interpreted midweek option values.
      - The raw free-text Update content.
    """
    fieldnames = [
        "Newcomer ID",
        "Newcomer Name",
        "Interested in Powerhouse",
        "Powerhouse Available",
        "Connected to Powerhouse",
        "Update",
    ]

    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for midweek_update, newcomer_row in matched_pairs:
            # Normalize option-style fields to their canonical representations
            # (Yes / No / No update / free-text).
            normalized = interpret_midweek_options(midweek_update)

            # Prefer the newcomer's canonical name from the CSV, but fall back
            # to any Name provided in the midweek template if needed.
            newcomer_id = normalize_unicode_spaces(
                (midweek_update.get("Newcomer ID") or newcomer_row.get("Newcomer ID") or "")
            )
            newcomer_name = (
                newcomer_row.get("Newcomer Name")
                or midweek_update.get("Name")
                or ""
            )

            row = {
                "Newcomer ID": newcomer_id,
                "Newcomer Name": newcomer_name,
                "Interested in Powerhouse": normalized.get("Interested in Powerhouse", ""),
                "Powerhouse Available": normalized.get("Powerhouse Available", ""),
                "Connected to Powerhouse": normalized.get("Connected to Powerhouse", ""),
                "Update": normalize_unicode_spaces(midweek_update.get("Update") or ""),
            }

            writer.writerow(row)


# =====================================================================
# CLI ENTRY
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Parse Followup Update templates from WhatsApp chat export."
    )
    parser.add_argument("--file", required=True, help="Path to WhatsApp .txt file")
    parser.add_argument("--start-date", required=True, help="Start date (DD/MM/YYYY)")
    parser.add_argument("--end-date", required=True, help="End date (DD/MM/YYYY)")
    parser.add_argument("--output", default="followup_output.csv", help="CSV output filename")

    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%d/%m/%Y").date()
    end_date = datetime.strptime(args.end_date, "%d/%m/%Y").date()

    records = parse_whatsapp_file(args.file, start_date, end_date)

    # Determine the newcomers sheet path and assign newcomer IDs
    sheet_path = os.path.join(os.path.dirname(__file__), NEWCOMERS_SHEET_NAME)
    start_id = get_last_newcomer_id(sheet_path)

    for idx, record in enumerate(records):
        record["Newcomer ID"] = format_newcomer_id(start_id + idx + 1)

    write_csv(records, args.output)
    append_newcomers_sheet(records, sheet_path)

    print(f"Done! Parsed {len(records)} follow-up updates.")
    print(f"CSV written to: {args.output}")

    # -----------------------------------------------------------------
    # Task 9: Integrate midweek parsing into the CLI workflow.
    # Always attempt to parse and apply midweek updates from the same
    # WhatsApp export, without changing the CLI interface.
    # -----------------------------------------------------------------
    midweek_updates = parse_midweek_updates_from_whatsapp_file(
        args.file,
        start_date,
        end_date,
    )

    if not midweek_updates:
        # No midweek blocks found in the given date range; preserve
        # existing behavior and simply exit after regular parsing.
        return

    # Load existing newcomers keyed by Newcomer ID (including any rows
    # that were just appended above) so we can apply midweek updates.
    newcomers_by_id = load_newcomers_by_id(sheet_path)

    unmatched_midweek_updates: List[Dict[str, str]] = []
    matched_pairs = match_midweek_updates_to_newcomers(
        midweek_updates,
        newcomers_by_id,
        unmatched_collector=unmatched_midweek_updates,
    )

    if matched_pairs:
        # Mutate the in-memory newcomer rows with midweek changes.
        apply_midweek_updates_to_newcomers(matched_pairs)

        # Persist the updated newcomers sheet and write an auxiliary
        # report summarizing applied midweek updates.
        write_newcomers_sheet_with_midweek_updates(
            newcomers_by_id,
            sheet_path,
        )

        report_path = os.path.join(
            os.path.dirname(__file__),
            MIDWEEK_UPDATES_APPLIED_SHEET_NAME,
        )
        write_midweek_updates_applied_report(matched_pairs, report_path)

        print(f"Applied {len(matched_pairs)} midweek updates to the newcomers sheet.")
        print(f"Midweek updates report written to: {report_path}")

    if unmatched_midweek_updates:
        print(
            f"{len(unmatched_midweek_updates)} midweek updates could not be "
            "matched to an existing Newcomer ID and were skipped."
        )


if __name__ == "__main__":
    main()
