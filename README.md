# Transaction SMS Processor

A FastAPI backend service that processes Bkash and EBL transaction SMS messages and automatically logs them to Google Sheets with balance tracking and expense calculations.

## Features

- ✅ Parses Bkash and EBL transaction SMS messages
- ✅ Categorizes transactions (income, expense, transfers)
- ✅ Automatically logs to Google Sheets
- ✅ Real-time balance tracking for both platforms
- ✅ Daily and monthly expense calculations
- ✅ Production-ready FastAPI application
- ✅ Simple deployment configuration

## Project Structure

```
PythonProject/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── service_account.json   # Google Service Account credentials (you'll create this)
└── app/
    ├── __init__.py
    ├── config.py          # Configuration management
    ├── sms_processor.py   # SMS parsing logic
    └── sheets_manager.py  # Google Sheets integration
```

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
cd /path/to/your/project
pip install -r requirements.txt
```

### 2. Google Sheets Setup

#### A. Create a Google Sheet
1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new spreadsheet
3. Name it something like "Transaction Tracker"
4. Copy the sheet ID from the URL (the long string between `/d/` and `/edit`)
   - URL: `https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit`
   - ID: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`

#### B. Create Google Service Account
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API" and enable it
   - Also enable "Google Drive API"
4. Create Service Account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the details and create
5. Generate Key:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create New Key" > "JSON"
   - Download the JSON file and rename it to `service_account.json`
   - Place it in your project root directory

#### C. Share Sheet with Service Account
1. Open your Google Sheet
2. Click "Share" button
3. Add the service account email (found in the JSON file as `client_email`)
4. Give it "Editor" permissions

### 3. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Google Sheets Configuration  
GOOGLE_SHEETS_ID=your_google_sheet_id_here
GOOGLE_SERVICE_ACCOUNT_PATH=service_account.json
WORKSHEET_NAME=Transactions

# Timezone
TIMEZONE=Asia/Dhaka
```

### 4. Test the Application

Run locally to test:

```bash
python main.py
```

The API will be available at `http://localhost:8000`

Test with a sample SMS:

```bash
curl -X POST "http://localhost:8000/process-sms" \
-H "Content-Type: application/json" \
-d '{
  "message": "You have received deposit of Tk 1,000.00 from VISA Card. Fee Tk 0.00. Balance Tk 1,022.94. TrxID CH68AABJH6 at 06/08/2025 09:11"
}'
```

## Deployment Options

### Option 1: Railway (Recommended - Free Tier)

1. Create account at [Railway](https://railway.app)
2. Install Railway CLI: `npm install -g @railway/cli`
3. Login: `railway login`
4. Deploy: `railway deploy`
5. Set environment variables in Railway dashboard

### Option 2: Render (Free Tier)

1. Create account at [Render](https://render.com)
2. Connect your GitHub repository
3. Create a new Web Service
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `python main.py`
6. Add environment variables in Render dashboard

### Option 3: Heroku (Paid)

1. Install Heroku CLI
2. Create Heroku app: `heroku create your-app-name`
3. Set environment variables: `heroku config:set GOOGLE_SHEETS_ID=your_id`
4. Deploy: `git push heroku main`

### Option 4: DigitalOcean App Platform

1. Create account at [DigitalOcean](https://cloud.digitalocean.com)
2. Create new App from GitHub repository
3. Configure environment variables
4. Deploy

## SMS Integration

For automatic SMS processing from your iPhone, you'll need:

1. **IFTTT or Shortcuts app** to forward SMS messages to your API endpoint
2. **Webhook setup** to send POST requests to `https://your-domain.com/process-sms`

### Using iOS Shortcuts:
1. Create a new shortcut that triggers on SMS received
2. Filter for messages containing "bKash" or "EBL"
3. Send HTTP POST request to your API endpoint with the SMS content

## API Endpoints

### `POST /process-sms`
Process a transaction SMS message.

**Request Body:**
```json
{
  "message": "SMS message content",
  "timestamp": "2025-08-08T10:30:00Z" // optional
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "platform": "bKash",
    "transaction_type": "income",
    "amount": 1000.0,
    "balance": 1022.94,
    "description": "Deposit from VISA Card"
  }
}
```

### `GET /health`
Health check endpoint.

### `GET /`
API status endpoint.

## Google Sheets Format

The application will create columns in your sheet:

| Date | Time | Platform | Transaction Type | Transaction Amount | Balance After | Description | Fee | Transaction ID | Raw Message |
|------|------|----------|------------------|-------------------|---------------|-------------|-----|----------------|-------------|
| 2025-08-08 | 17:36:00 | bKash | income | 1000.00 | 1022.94 | Deposit from VISA Card | 0.00 | CH68AABJH6 | Raw SMS text |

**Summary columns (automatically calculated):**
- Current Amount in EBL
- Current Amount in bKash  
- Current Total Amount
- Today's Expense
- Monthly Expense

## Transaction Categories

### Bkash
- **Income**: Cash In from phone numbers, deposits from cards
- **Expense**: Payments to phone numbers, cash out
- **Transfer**: Money movement between EBL and bKash (not counted as expense)

### EBL  
- **Income**: Credited amounts (money coming in)
- **Expense**: Debited amounts (money going out)
- **Transfer**: Money movement between EBL and bKash (not counted as expense)

## Monitoring

Check logs for processing status:
- Successful transactions will be logged with details
- Failed parsing attempts will be logged but ignored
- Google Sheets errors will be logged and returned in API response

## Troubleshooting

### Common Issues:

1. **Google Sheets Permission Error**
   - Ensure service account email is added to the sheet with Editor permissions
   - Check that both Google Sheets API and Google Drive API are enabled

2. **SMS Not Parsing**
   - Check if the SMS format matches the expected patterns
   - Look at application logs for parsing attempts
   - SMS formats may change - update regex patterns in `sms_processor.py`

3. **Environment Variables**
   - Ensure all required environment variables are set in your deployment platform
   - For local testing, make sure `.env` file exists and is properly formatted

4. **Deployment Issues**
   - Check that `service_account.json` is included in your deployment
   - Verify all dependencies are installed
   - Check platform-specific logs for startup errors

## What You Need Next

1. **Set up Google Service Account** and download the JSON key
2. **Create and share Google Sheet** with your service account
3. **Deploy to your preferred platform** (Railway recommended for free hosting)
4. **Set up iPhone SMS forwarding** using Shortcuts app or IFTTT
5. **Test with real SMS messages** to ensure parsing works correctly

The application is production-ready and will handle your transaction SMS processing automatically once deployed and configured!