# Conference Registration System

This is a Google Apps Script-based registration system for the Voice of Apostles conference at Holy Spirit Generation church.

## Features

### Registration Tab
- **QR Code Scanning**: Scan attendee QR codes to mark them as registered
- **Manual Lookup**: Search for attendees by name, phone, email, or QR code
- **Always Visible Lookup**: The lookup section is always visible for easy access
- **Registration Status**: Shows whether an attendee is already registered or not

### Admin Tab
- **Spot Registration**: Register new attendees on the spot with all required information
- **Register & Mark Registered**: Option to immediately mark new registrations as registered
- **Lookup & Management**: Search existing attendees and manage their registration status
- **Food Payment Tracking**: Toggle food payment status for attendees

### Stats Tab
- **Total Registered**: Count of all registered attendees
- **With Food**: Count of registered attendees who have food included
- **Geographic Breakdown**: Separate counts for Bangalore and outstation attendees

## How It Works

1. **Registration Process**: 
   - Scan QR codes or manually lookup attendees
   - Mark them as registered (one-time activity)
   - System prevents duplicate registrations

2. **Data Storage**:
   - Uses Google Sheets as the backend
   - Registration status stored in "Registration" column
   - All attendee data maintained in the same spreadsheet

3. **ID Generation**:
   - New attendees get sequential VOA IDs (VOA1, VOA2, etc.)
   - Aggregate codes are auto-generated via formulas

## Setup

1. Deploy the Google Apps Script code to your Google account
2. Update the `SPREADSHEET_ID` constant with your Google Sheet ID
3. Ensure your spreadsheet has the required headers as defined in the `HEADERS` array
4. Set the appropriate church and conference names in the constants

## Required Spreadsheet Headers

The spreadsheet must have these columns in the exact order:
- ID
- Name
- Gender
- Age
- Phone
- Email
- Church Name
- Type of Member
- City
- State
- Country
- Aggregate
- QR Code
- Food Included
- Paid for Food

The system will automatically add a "Registration" column when needed.

## Usage

1. **For Registration**: Use the Registration tab to scan QR codes or lookup attendees
2. **For Admin Tasks**: Use the Admin tab for spot registration and management
3. **For Statistics**: Use the Stats tab to view registration counts and breakdowns

The system is designed to be simple and efficient for conference registration management.

