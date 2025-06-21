import pandas as pd
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os
import argparse
from datetime import datetime
import time

# --- Hardcoded Configuration ---
SENDER_EMAIL = 'support@rwo.life'             
SENDER_PASSWORD = 'fpev xyox aehp weec'             
QR_API_ENDPOINT = 'https://api.qrserver.com/v1/create-qr-code/?size=70x70&data=' 

def generate_qr_code(aggregate):
    """Calls the QR code generation API and returns image bytes."""
    response = requests.post(QR_API_ENDPOINT + aggregate, timeout=10)

    if response.status_code == 200:
        return response.content  # Should be image bytes
    else:
        raise Exception(f"QR generation failed with status {response.status_code}: {response.text}")

def send_email_with_qr(recipient_email, recipient_name, qr_image_bytes, venue_details):
    """Sends an email with the QR code image embedded in the email body and venue details."""
    msg = MIMEMultipart('related')
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = "Holy Spirit Conference 2025 - QR Code"

    venue_details.replace('\n', '<br>')

    # Email body with embedded image reference
    html_body = f"""
    <html>
    <body>
        <p>Dear {recipient_name},</p>
        <p>Thank you for registering for the <strong>Holy Spirit Conference 2025</strong>!<br>
        Please present the following QR code at the venue for entry:</p>
        <p><img src="cid:qr_code_cid" alt="QR Code" style="width:70px;height:70px;"></p>
        <p><strong>Venue Details:</strong><br>
        {venue_details}</p>
        <p>We look forward to seeing you there.</p>
        <p>Sincerely,<br>
        Holy Spirit Generation Church<br>
        RWO Support Team</p>
    </body>
    </html>
    """

    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    msg_alternative.attach(MIMEText(html_body, 'html'))

    # Attach image inline
    img = MIMEImage(qr_image_bytes)
    img.add_header('Content-ID', '<qr_code_cid>')
    img.add_header('Content-Disposition', 'inline', filename="qr_code.png")
    msg.attach(img)

    # Send the email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, [recipient_email], msg.as_string())

def load_id_file(filename):
    if not os.path.exists(filename):
        return set()
    with open(filename, 'r') as f:
        return set(line.strip() for line in f)

def append_to_file(filename, id_val):
    with open(filename, 'a') as f:
        f.write(f"{id_val}\n")

def process_excel_and_send_emails(excel_file_path, retry_errors_only=False, batch_size=10):
    sent_ids = load_id_file('mails_sent.txt')
    error_ids = load_id_file('mail_errors.txt')

    counters = {
        'total': 0,
        'sent': 0,
        'skipped': 0,
        'failed': 0
    }

    try:
        df = pd.read_excel(excel_file_path, engine='openpyxl')

        required_columns = {'ID', 'Name', 'email', 'Aggregate'}
        if not required_columns.issubset(df.columns):
            print(df.columns)
            print(f"Error: The Excel sheet must contain columns: {required_columns}")
            return

        batch_count = 0

        for index, row in df.iterrows():
            counters['total'] += 1
            id_val = str(row['ID'])

            if retry_errors_only and id_val not in error_ids:
                continue
            if not retry_errors_only and id_val in sent_ids:
                counters['skipped'] += 1
                continue

            name = row['Name']
            email = row['email']
            venue_details = 'Holy Spirit Generation Church <br> \
            NC Arena, Near Legacy School and Moto Mind, <br>\
            Kothanur, Bangalore, 560077'
            aggregate = str(row['Aggregate'])

            try:
                qr_bytes = generate_qr_code(aggregate)
            except Exception as e:
                print(f"[{id_val}] QR generation failed for {email}: {e}")
                counters['failed'] += 1
                append_to_file('mail_errors.txt', id_val)
                continue

            try:
                send_email_with_qr(email, name, qr_bytes, venue_details)
                print(f"[{id_val}] Email sent to {email}")
                counters['sent'] += 1
                append_to_file('mails_sent.txt', id_val)
                error_ids.discard(id_val)
            except Exception as e:
                print(f"[{id_val}] Email sending failed to {email}: {e}")
                counters['failed'] += 1
                append_to_file('mail_errors.txt', id_val)

            # Batch control
            batch_count += 1
            if batch_count % batch_size == 0:
                print(f"\nBatch limit reached ({batch_size}). Pausing for 2 minutes...\n")
                time.sleep(120)

    except FileNotFoundError:
        print(f"Error: Excel file not found at {excel_file_path}")
        return
    except Exception as e:
        print(f"An error occurred: {e}")
        return

    # --- Print Summary Report ---
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"""
--- Email Dispatch Summary ({timestamp}) ---
Total rows processed: {counters['total']}
Emails sent successfully: {counters['sent']}
Skipped (already sent): {counters['skipped']}
Failed (QR or Email errors): {counters['failed']}
--------------------------------------------
""".strip())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send QR Code Emails for Event")
    parser.add_argument('--datasheet', required=True, help='Path to Excel file')
    parser.add_argument('--retry-errors', action='store_true', help='Only retry emails that previously failed')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of emails to send per batch')


    args = parser.parse_args()

    process_excel_and_send_emails(
        args.datasheet,
        retry_errors_only=args.retry_errors,
        batch_size=args.batch_size
    )
