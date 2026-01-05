import re
import csv
import argparse
from datetime import datetime

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

ALL_COLUMNS = [
    "Date",
    "Time",
    "Volunteer Name",
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
]


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


# =====================================================================
# PARSE MULTIPLE UPDATE BLOCKS FROM BODY
# =====================================================================

def parse_updates(body: str):
    """
    Extract one or more newcomer update blocks from a message body.

    Strategy:
      - Walk line by line.
      - When we see a "Newcomer Name" line (bold / plain / numbered), start a new block.
      - All following lines belong to that block until the next "Newcomer Name" line.
      - For each block, apply FIELD_PATTERNS.
    """
    updates = []
    lines = [normalize_unicode_spaces(l) for l in body.splitlines()]

    current_block_lines = []

    for line in lines:
        if BLOCK_START_REGEX.match(line):
            # Start of a new block
            if current_block_lines:
                block_text = "\n".join(current_block_lines).strip()
                if "Newcomer Name" in block_text:
                    updates.append(extract_fields_from_block(block_text))
            current_block_lines = [line]
        else:
            # Continuation of current block (if any)
            if current_block_lines:
                current_block_lines.append(line)

    # Last block
    if current_block_lines:
        block_text = "\n".join(current_block_lines).strip()
        if "Newcomer Name" in block_text:
            updates.append(extract_fields_from_block(block_text))

    # Filter out completely empty blocks (e.g., if somehow no name)
    updates = [u for u in updates if any(v for v in u.values())]

    return updates


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
    write_csv(records, args.output)

    print(f"Done! Parsed {len(records)} follow-up updates.")
    print(f"CSV written to: {args.output}")


if __name__ == "__main__":
    main()
