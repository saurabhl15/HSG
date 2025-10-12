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
SENDER_EMAIL = 'conference@rwo.life'             
SENDER_PASSWORD = 'cxof yvss uslj ttxj'             
QR_API_ENDPOINT = 'https://api.qrserver.com/v1/create-qr-code/?size=70x70&data=' 

def generate_qr_code(aggregate):
    """Calls the QR code generation API and returns image bytes."""
    response = requests.post(QR_API_ENDPOINT + aggregate, timeout=10)

    if response.status_code == 200:
        return response.content  # Should be image bytes
    else:
        raise Exception(f"QR generation failed with status {response.status_code}: {response.text}")

def send_vip_vip_email_with_qr(recipient_email, recipient_name, qr_image_bytes, venue_details, band_color):
    """Sends a VIP/VVIP email with the QR code image embedded in the email body and venue details."""
    msg = MIMEMultipart('related')
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = "Voice of Apostles Conference 2025 - VIP/VVIP QR Code"

    venue_details = venue_details.replace('\n', '<br>')

    # VIP/VVIP Email body with embedded image reference
    html_body = f"""
    <html>
    <body style="margin:0;padding:0;background-color:#f5f7fb;font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', Arial, sans-serif; color:#1f2937;">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background-color:#f5f7fb;padding:24px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" role="presentation" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.08);overflow:hidden;">
                <tr>
                  <td style="padding:28px 28px 8px 28px;background:linear-gradient(135deg,#0ea5e9 0%, #2563eb 100%);color:#ffffff;">
                    <h2 style="margin:0;font-size:22px;line-height:28px;font-weight:700;">Your VIP/VVIP Conference QR Code</h2>
                    <p style="margin:6px 0 0 0;font-size:14px;opacity:0.95;">Please carry a valid Government Photo ID</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:24px 28px 8px 28px;">
                    <p style="margin:0 0 12px 0;font-size:16px;">Dear <strong>{recipient_name}</strong>,</p>
                    <p style="margin:0 0 14px 0;font-size:15px;line-height:22px;">Kindly present the QR Code with your Identify Card (Any Govt. Photo ID Proof).</p>
                    <div style="margin:18px 0;padding:18px;border:1px dashed #d1d5db;border-radius:10px;background:#f9fafb;text-align:center;">
                      <img src="cid:qr_code_cid" alt="QR Code" style="width:140px;height:140px;display:inline-block;" />
                      <div style="margin-top:10px;font-size:12px;color:#6b7280;">Show this QR at the Registration Counter</div>
                    </div>
                    <p style="margin:0 0 10px 0;font-size:15px;line-height:22px;text-align:justify;">You will get the <strong style="color:{band_color};">{band_color}</strong> Colour Bands from the Registration Counters 6 and 7 on sharing your Registration details/QR.</p>
                    <p style="margin:0 0 10px 0;font-size:15px;line-height:22px;text-align:justify;"><strong>Note:</strong> Please take care of the Bands provided throughout the conference as you will have to pay the registration fee again in case you lose it or request for replacement. Bands are water resistant and lasts up to 10 days once tied up.</p>
                    <p style="margin:0 0 10px 0;font-size:15px;line-height:22px;text-align:justify;">Hospitality Team has been assigned for you and help you to locate the designated seats during the Conference. Kindly reach out to Rushali - 7349667797</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 28px 24px 28px;">
                    <p style="margin:16px 0 6px 0;font-size:15px;">Love and Regards,</p>
                    <p style="margin:0 0 14px 0;font-weight:700;font-size:15px;color:#111827;">Apostle Dr. P.S. Rambabu</p>
                    <div style="padding:14px 16px;background:#f3f4f6;border-radius:10px;border:1px solid #e5e7eb;">
                      <div style="font-size:14px;line-height:22px;color:#374151;">
                        {venue_details}
                      </div>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
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

def send_email_with_qr(recipient_email, recipient_name, qr_image_bytes, venue_details):
    """Sends an email with the QR code image embedded in the email body and venue details."""
    msg = MIMEMultipart('related')
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = "Voice of Apostles Conference 2025 - QR Code"

    venue_details = venue_details.replace('\n', '<br>')

    # Email body with embedded image reference
    html_body = f"""
    <html>
    <body style="margin:0;padding:0;background-color:#f5f7fb;font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', Arial, sans-serif; color:#1f2937;">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background-color:#f5f7fb;padding:24px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" role="presentation" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.08);overflow:hidden;">
                <tr>
                  <td style="padding:28px 28px 8px 28px;background:linear-gradient(135deg,#0ea5e9 0%, #2563eb 100%);color:#ffffff;">
                    <h2 style="margin:0;font-size:22px;line-height:28px;font-weight:700;">Your Conference QR Code</h2>
                    <p style="margin:6px 0 0 0;font-size:14px;opacity:0.95;">Please carry a valid Government Photo ID</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:24px 28px 8px 28px;">
                    <p style="margin:0 0 12px 0;font-size:16px;">Dear <strong>{recipient_name}</strong>,</p>
                    <p style="margin:0 0 14px 0;font-size:15px;line-height:22px;">Kindly present the QR Code with your Identity Card (any Govt. Photo ID proof).</p>
                    <div style="margin:18px 0;padding:18px;border:1px dashed #d1d5db;border-radius:10px;background:#f9fafb;text-align:center;">
                      <img src="cid:qr_code_cid" alt="QR Code" style="width:140px;height:140px;display:inline-block;" />
                      <div style="margin-top:10px;font-size:12px;color:#6b7280;">Show this QR at the Registration Counter</div>
                    </div>
                    <p style="margin:0 0 10px 0;font-size:15px;line-height:22px;text-align:justify;">You will get a band from the Registration Counter after sharing your QR code. Please take care of the bands throughout the conference as you will have to pay the registration fee again in case you lose it or require a replacement. Bands are water-resistant and last up to 10 days once tied.</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 28px 24px 28px;">
                    <p style="margin:16px 0 6px 0;font-size:15px;">Love and Regards,</p>
                    <p style="margin:0 0 14px 0;font-weight:700;font-size:15px;color:#111827;">Apostle Dr. P.S. Rambabu</p>
                    <div style="padding:14px 16px;background:#f3f4f6;border-radius:10px;border:1px solid #e5e7eb;">
                      <div style="font-size:14px;line-height:22px;color:#374151;">
                        {venue_details}
                      </div>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
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

def send_confirmation_email(recipient_email, recipient_name, venue_details):
    """Sends a confirmation email without QR code."""
    msg = MIMEMultipart('alternative')
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = "Voice of Apostle 2025 - Apostolic Commision and Impartation"

    venue_details = venue_details.replace('\n', '<br>')

    # Email body for confirmation
    html_body = f"""
    <html>
    <body style="margin:0;padding:0;background-color:#f5f7fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,Cantarell,'Helvetica Neue',Arial,sans-serif;color:#1f2937;">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background-color:#f5f7fb;padding:24px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" role="presentation" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.08);overflow:hidden;">
                <tr>
                  <td style="padding:28px 28px 18px 28px;background:linear-gradient(135deg,#2563eb 0%, #1d4ed8 100%);color:#ffffff;">
                    <h2 style="margin:0;font-size:22px;line-height:28px;font-weight:700;">Voice of Apostles 2025</h2>
                  </td>
                </tr>
                <tr>
                  <td style="padding:28px;">
                    <p style="margin:0 0 16px 0;font-size:16px;line-height:24px;">Dear <strong>{recipient_name}</strong>,</p>
                    <p style="margin:0 0 16px 0;font-size:15px;line-height:22px;text-align:justify;">Thanks for attending the Voice of Apostles 2025 conference.</p>
                    <p style="margin:0 0 20px 0;font-size:15px;line-height:22px;text-align:justify;">Please click the link below to download the Message attached <strong>"Apostolic Commission and Impartation"</strong>.</p>
                    <div style="margin:0 0 24px 0;text-align:center;">
                      <a href="https://drive.google.com/file/d/1c5c7ZTvxoqK2VWQ5-xanwU0onbBguiHA/view?usp=sharing" style="display:inline-block;padding:14px 26px;background:#2563eb;color:#ffffff;text-decoration:none;font-weight:600;border-radius:9999px;">Download Message</a>
                    </div>
                    <p style="margin:0 0 24px 0;font-size:15px;line-height:22px;text-align:justify;">Love and Regards,<br>Apostle Dr. P.S. Rambabu</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, 'html'))

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

def process_excel_and_send_emails(excel_file_path, retry_errors_only=False, batch_size=10, confirmation_only=False):
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

        # For confirmation-only mode, we don't need the Aggregate column
        if confirmation_only:
            required_columns = {'ID', 'Name', 'Email', 'Registration'}
        else:
            required_columns = {'ID', 'Name', 'Email', 'Aggregate'}
            
        if not required_columns.issubset(df.columns):
            print(df.columns)
            print(f"Error: The Excel sheet must contain columns: {required_columns}")
            return

        batch_count = 0

        for index, row in df.iterrows():
            counters['total'] += 1
            id_val = str(row['ID'])

            # Check if this is a VIP or VVIP
            is_vip = False
            band_color = ""
            
            # Check for VIP/VVIP columns if they exist
            if 'VIPs' in df.columns and pd.notna(row['VIPs']) and str(row['VIPs']).lower() in ['yes', 'true', '1']:
                is_vip = True
                band_color = "green"
            elif 'VVIPs' in df.columns and pd.notna(row['VVIPs']) and str(row['VVIPs']).lower() in ['yes', 'true', '1']:
                is_vip = True
                band_color = "yellow"

            if retry_errors_only and id_val not in error_ids:
                continue
            # Skip VIPs/VVIPs in retry errors mode
            if retry_errors_only and is_vip:
                counters['skipped'] += 1
                continue
            if not retry_errors_only and id_val in sent_ids:
                counters['skipped'] += 1
                continue

            name = row['Name']
            email = row['Email']
            registered_value = str(row.get('Registration', '')).strip().lower() if 'Registration' in df.columns else ''
            venue_details = 'NEW CREATION MINISTRIES<br> \
            No. 3, Byrathi Village,<br> \
            Bidarahalli Hobli, Kothanur,<br> \
            Near Legacy School & Moto Mind,<br> \
            Bangalore - 560077, Karnataka, India'

            if confirmation_only:
                if registered_value not in ['yes', 'y', 'true', '1']:
                    counters['skipped'] += 1
                    print(f"[{id_val}] Skipped {email} - Registered status is '{row.get('Registration', '')}'")
                    continue
                # Send confirmation email without QR code
                try:
                    send_confirmation_email(email, name, venue_details)
                    print(f"[{id_val}] Confirmation email sent to {email}")
                    counters['sent'] += 1
                    append_to_file('mails_sent.txt', id_val)
                    error_ids.discard(id_val)
                except Exception as e:
                    print(f"[{id_val}] Confirmation email sending failed to {email}: {e}")
                    counters['failed'] += 1
                    append_to_file('mail_errors.txt', id_val)
            else:
                # Original QR code logic
                aggregate = str(row['Aggregate'])

                try:
                    qr_bytes = generate_qr_code(aggregate)
                except Exception as e:
                    print(f"[{id_val}] QR generation failed for {email}: {e}")
                    counters['failed'] += 1
                    append_to_file('mail_errors.txt', id_val)
                    continue

                try:
                    if is_vip:
                        send_vip_vip_email_with_qr(email, name, qr_bytes, venue_details, band_color)
                        print(f"[{id_val}] VIP/VVIP Email with QR sent to {email} (Band Color: {band_color})")
                    else:
                        send_email_with_qr(email, name, qr_bytes, venue_details)
                        print(f"[{id_val}] Email with QR sent to {email}")
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
                print(f"\nBatch limit reached ({batch_size}). Pausing for 0 seconds...\n")
                time.sleep(0)

    except FileNotFoundError:
        print(f"Error: Excel file not found at {excel_file_path}")
        return
    except Exception as e:
        print(f"An error occurred: {e}")
        return

    # --- Print Summary Report ---
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    email_type = "Confirmation emails" if confirmation_only else "QR Code emails"
    print(f"""
--- {email_type} Dispatch Summary ({timestamp}) ---
Total rows processed: {counters['total']}
Emails sent successfully: {counters['sent']}
Skipped (already sent): {counters['skipped']}
Failed (QR or Email errors): {counters['failed']}
--------------------------------------------
""".strip())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send QR Code or Confirmation Emails for Event")
    parser.add_argument('--datasheet', required=True, help='Path to Excel file')
    parser.add_argument('--retry-errors', action='store_true', help='Only retry emails that previously failed')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of emails to send per batch')
    parser.add_argument('--confirmation-only', action='store_true', help='Send confirmation emails without QR codes')


    args = parser.parse_args()

    process_excel_and_send_emails(
        args.datasheet,
        retry_errors_only=args.retry_errors,
        batch_size=args.batch_size,
        confirmation_only=args.confirmation_only
    )
