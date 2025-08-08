import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, Any, List
import logging
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)

class SheetsManager:
    def __init__(self):
        self.gc = None
        self.worksheet = None
        self._setup_sheets_client()

    def _setup_sheets_client(self):
        """Setup Google Sheets client with service account"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_file(
                settings.GOOGLE_SERVICE_ACCOUNT_PATH, 
                scopes=scope
            )
            
            self.gc = gspread.authorize(creds)
            spreadsheet = self.gc.open_by_key(settings.GOOGLE_SHEETS_ID)
            
            # Try to get existing worksheet or create new one
            try:
                self.worksheet = spreadsheet.worksheet(settings.WORKSHEET_NAME)
            except gspread.exceptions.WorksheetNotFound:
                self.worksheet = spreadsheet.add_worksheet(
                    title=settings.WORKSHEET_NAME, 
                    rows=1000, 
                    cols=20
                )
                self._setup_headers()
            
            logger.info("Google Sheets client setup successful")
            
        except Exception as e:
            logger.error(f"Failed to setup Google Sheets client: {str(e)}")
            raise

    def _setup_headers(self):
        """Setup column headers for the worksheet"""
        headers = [
            "Date", "Time", "Platform", "Transaction Type", "Transaction Amount", 
            "Balance After", "Description", "Fee", "Transaction ID", "Raw Message",
            "", "Current Amount in EBL", "Current Amount in bKash", 
            "Current Total Amount", "Today's Expense", "Monthly Expense"
        ]
        
        self.worksheet.append_row(headers)
        
        # Set up summary formulas in the first data row
        summary_formulas = [
            "", "", "", "", "", "", "", "", "", "",  # Empty cells for transaction data
            "",  # Separator
            "=SUMIF(C:C,\"EBL\",F:F)",  # Current Amount in EBL (sum of EBL balances, latest)
            "=SUMIF(C:C,\"bKash\",F:F)",  # Current Amount in bKash (sum of bKash balances, latest)
            "=L2+M2",  # Current Total Amount
            f"=SUMIFS(E:E,A:A,TODAY(),D:D,\"expense\")",  # Today's Expense
            f"=SUMIFS(E:E,A:A,\">=\"&DATE(YEAR(TODAY()),MONTH(TODAY()),1),A:A,\"<\"&DATE(YEAR(TODAY()),MONTH(TODAY())+1,1),D:D,\"expense\")"  # Monthly Expense
        ]
        
        self.worksheet.append_row(summary_formulas)

    async def log_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, str]:
        """Log transaction to Google Sheets"""
        try:
            # Prepare row data
            date_obj = transaction_data.get("date", datetime.now())
            row_data = [
                date_obj.strftime("%Y-%m-%d"),  # Date
                date_obj.strftime("%H:%M:%S"),  # Time
                transaction_data.get("platform", ""),  # Platform
                transaction_data.get("transaction_type", ""),  # Transaction Type
                transaction_data.get("amount", 0),  # Transaction Amount
                transaction_data.get("balance", 0),  # Balance After
                transaction_data.get("description", ""),  # Description
                transaction_data.get("fee", 0),  # Fee
                transaction_data.get("transaction_id", ""),  # Transaction ID
                transaction_data.get("raw_message", "")  # Raw Message
            ]
            
            # Add to worksheet
            self.worksheet.append_row(row_data)
            
            # Update summary calculations
            await self._update_summary_calculations()
            
            logger.info(f"Transaction logged to Google Sheets: {transaction_data['platform']} - {transaction_data['amount']}")
            
            return {"status": "success", "message": "Transaction logged successfully"}
            
        except Exception as e:
            logger.error(f"Failed to log transaction to Google Sheets: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _update_summary_calculations(self):
        """Update summary calculations for current balances and expenses"""
        try:
            # Get all data
            all_values = self.worksheet.get_all_values()
            
            if len(all_values) < 3:  # Headers + Summary + at least one transaction
                return
            
            # Find latest balances for each platform
            ebl_balance = 0
            bkash_balance = 0
            
            for row in reversed(all_values[2:]):  # Skip headers and summary row
                if row[2] == "EBL" and ebl_balance == 0:  # Platform column
                    ebl_balance = float(row[5]) if row[5] else 0  # Balance column
                elif row[2] == "bKash" and bkash_balance == 0:
                    bkash_balance = float(row[5]) if row[5] else 0
                
                if ebl_balance > 0 and bkash_balance > 0:
                    break
            
            # Update summary row (row 2)
            summary_row = 2
            self.worksheet.update_cell(summary_row, 12, ebl_balance)  # Current Amount in EBL
            self.worksheet.update_cell(summary_row, 13, bkash_balance)  # Current Amount in bKash
            self.worksheet.update_cell(summary_row, 14, ebl_balance + bkash_balance)  # Total Amount
            
        except Exception as e:
            logger.error(f"Failed to update summary calculations: {str(e)}")

    def get_current_balances(self) -> Dict[str, float]:
        """Get current balances for both platforms"""
        try:
            summary_row_values = self.worksheet.row_values(2)
            
            return {
                "ebl_balance": float(summary_row_values[11]) if len(summary_row_values) > 11 and summary_row_values[11] else 0,
                "bkash_balance": float(summary_row_values[12]) if len(summary_row_values) > 12 and summary_row_values[12] else 0,
                "total_balance": float(summary_row_values[13]) if len(summary_row_values) > 13 and summary_row_values[13] else 0,
                "today_expense": float(summary_row_values[14]) if len(summary_row_values) > 14 and summary_row_values[14] else 0,
                "monthly_expense": float(summary_row_values[15]) if len(summary_row_values) > 15 and summary_row_values[15] else 0
            }
        except Exception as e:
            logger.error(f"Failed to get current balances: {str(e)}")
            return {
                "ebl_balance": 0,
                "bkash_balance": 0,
                "total_balance": 0,
                "today_expense": 0,
                "monthly_expense": 0
            }