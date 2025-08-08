import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, Any, List
import logging
import json
import os
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)

class SheetsManager:
    def __init__(self):
        self.gc = None
        self.spreadsheet = None
        self.summary_worksheet = None
        self.transactions_worksheet = None
        self._setup_sheets_client()

    def _setup_sheets_client(self):
        """Setup Google Sheets client with service account"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'):
                service_account_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))
                creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
            else:
                creds = Credentials.from_service_account_file(
                    settings.GOOGLE_SERVICE_ACCOUNT_PATH, 
                    scopes=scope
                )
            
            self.gc = gspread.authorize(creds)
            self.spreadsheet = self.gc.open_by_key(settings.GOOGLE_SHEETS_ID)
            
            # Setup Summary worksheet
            try:
                self.summary_worksheet = self.spreadsheet.worksheet("Summary")
            except gspread.exceptions.WorksheetNotFound:
                self.summary_worksheet = self.spreadsheet.add_worksheet(
                    title="Summary", 
                    rows=100, 
                    cols=10
                )
                self._setup_summary_headers()
            
            # Setup Transaction Details worksheet
            try:
                self.transactions_worksheet = self.spreadsheet.worksheet("Transaction Details")
            except gspread.exceptions.WorksheetNotFound:
                self.transactions_worksheet = self.spreadsheet.add_worksheet(
                    title="Transaction Details", 
                    rows=1000, 
                    cols=15
                )
                self._setup_transaction_headers()
            
            logger.info("Google Sheets client setup successful")
            
        except Exception as e:
            logger.error(f"Failed to setup Google Sheets client: {str(e)}")
            raise

    def _setup_summary_headers(self):
        """Setup Summary worksheet with simple 2-column structure"""
        self.summary_worksheet.clear()
        
        # Set headers
        headers = ["Metric", "Amount"]
        self.summary_worksheet.append_row(headers)
        
        # Set up the five summary rows
        summary_rows = [
            ["Monthly Expense", "=SUMIFS('Transaction Details'!E:E,'Transaction Details'!A:A,\">=\"&DATE(YEAR(TODAY()),MONTH(TODAY()),1),'Transaction Details'!A:A,\"<\"&DATE(YEAR(TODAY()),MONTH(TODAY())+1,1),'Transaction Details'!D:D,\"expense\")"],
            ["Today's Expense", "=SUMIFS('Transaction Details'!E:E,'Transaction Details'!A:A,TODAY(),'Transaction Details'!D:D,\"expense\")"],
            ["Total Available Amount", "0"],  # Will be updated programmatically
            ["bKash Total Balance", "0"],  # Will be updated programmatically
            ["EBL Total Balance", "0"]  # Will be updated programmatically
        ]
        
        for row in summary_rows:
            self.summary_worksheet.append_row(row)

    def _setup_transaction_headers(self):
        """Setup Transaction Details worksheet headers"""
        self.transactions_worksheet.clear()
        
        headers = [
            "Date", "Time", "Platform", "Transaction Type", "Transaction Amount", 
            "Balance After", "Description", "Fee", "Transaction ID", "Raw Message"
        ]
        
        self.transactions_worksheet.append_row(headers)

    async def log_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, str]:
        """Log transaction to Transaction Details worksheet"""
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
            
            # Add to Transaction Details worksheet
            self.transactions_worksheet.append_row(row_data)
            
            # Update total available amount in Summary
            await self._update_total_available()
            
            logger.info(f"Transaction logged to Google Sheets: {transaction_data['platform']} - {transaction_data['amount']}")
            
            return {"status": "success", "message": "Transaction logged successfully"}
            
        except Exception as e:
            logger.error(f"Failed to log transaction to Google Sheets: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _update_total_available(self):
        """Update the total available amount and individual balances in Summary worksheet"""
        try:
            # Get all transaction data
            all_values = self.transactions_worksheet.get_all_values()
            
            if len(all_values) < 2:  # No data besides headers
                return
            
            # Find latest balances for each platform
            ebl_balance = 0
            bkash_balance = 0
            
            # Go through transactions from newest to oldest
            for row in reversed(all_values[1:]):  # Skip headers
                if len(row) >= 6:  # Ensure we have enough columns
                    platform = row[2]  # Platform column
                    try:
                        balance = float(row[5]) if row[5] else 0  # Balance After column
                        if platform == "EBL" and ebl_balance == 0:
                            ebl_balance = balance
                        elif platform == "bKash" and bkash_balance == 0:
                            bkash_balance = balance
                        
                        # Stop when we have both balances
                        if ebl_balance > 0 and bkash_balance > 0:
                            break
                    except (ValueError, IndexError):
                        continue
            
            total_available = ebl_balance + bkash_balance
            
            # Update all balance fields in Summary
            self.summary_worksheet.update_cell(4, 2, total_available)  # Row 4: Total Available Amount
            self.summary_worksheet.update_cell(5, 2, bkash_balance)    # Row 5: bKash Total Balance
            self.summary_worksheet.update_cell(6, 2, ebl_balance)      # Row 6: EBL Total Balance
            
            logger.info(f"Updated balances - Total: {total_available}, EBL: {ebl_balance}, bKash: {bkash_balance}")
            
        except Exception as e:
            logger.error(f"Failed to update balances: {str(e)}")

    def get_current_balances(self) -> Dict[str, float]:
        """Get current balances and expenses from Summary worksheet"""
        try:
            # Get values from Summary worksheet
            summary_values = self.summary_worksheet.get_all_values()
            
            result = {
                "monthly_expense": 0,
                "today_expense": 0,
                "total_available": 0,
                "bkash_balance": 0,
                "ebl_balance": 0
            }
            
            # Parse the summary data (skip header row)
            for i, row in enumerate(summary_values[1:], 1):
                if len(row) >= 2:
                    metric = row[0]
                    try:
                        amount = float(row[1]) if row[1] else 0
                        if metric == "Monthly Expense":
                            result["monthly_expense"] = amount
                        elif metric == "Today's Expense":
                            result["today_expense"] = amount
                        elif metric == "Total Available Amount":
                            result["total_available"] = amount
                        elif metric == "bKash Total Balance":
                            result["bkash_balance"] = amount
                        elif metric == "EBL Total Balance":
                            result["ebl_balance"] = amount
                    except (ValueError, IndexError):
                        continue
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get current balances: {str(e)}")
            return {
                "monthly_expense": 0,
                "today_expense": 0,
                "total_available": 0,
                "bkash_balance": 0,
                "ebl_balance": 0
            }