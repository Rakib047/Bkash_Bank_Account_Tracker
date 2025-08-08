import re
from datetime import datetime
from typing import Optional, Dict, Any
import pytz
from app.config import settings

class SMSProcessor:
    def __init__(self):
        self.timezone = pytz.timezone(settings.TIMEZONE)
        
        # EBL SMS Patterns
        self.ebl_patterns = [
            # Pattern for "AC xxx is debited/credited with BDT amount"
            r'AC\s+\d+\*+\d+\s+is\s+(debited|credited)\s+with\s+BDT\s+([\d,]+(?:\.\d{2})?)\s+as\s+(.+?)\s+on\s+(\d{2}-[A-Z]{3}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+[AP]M)\s+Balance\s+is\s+BDT\s+([\d,]+(?:\.\d{2})?)',
            
            # Pattern for "Cash WD BDT amount"
            r'Cash\s+WD\s+BDT([\d,]+(?:\.\d{2})?)\s+from\s+(.+?)\s*\.\s*Card\s+\d+\*+\d+\s+on\s+(\d{2}-[A-Za-z]{3}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+[AP]M\s+BST)\.Your\s+A/C\s+\d+\*+\d+\s+Balance\s+BDT\s+([\d,]+(?:\.\d{2})?)',
            
            # Pattern for "Fund Transfer of BDT amount"
            r'Fund\s+Transfer\s+of\s+BDT\s+([\d,]+(?:\.\d{2})?)\s+from\s+(.+?)\s*\.\s*Card\s+\d+\*+\d+\s+on\s+(\d{2}-[A-Za-z]{3}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+[AP]M\s+BST)\.Your\s+A/C\s+\d+\*+\d+\s+Balance\s+BDT\s+([\d,]+(?:\.\d{2})?)'
        ]
        
        # Bkash SMS Patterns
        self.bkash_patterns = [
            # Pattern for "You have received deposit of Tk amount"
            r'You\s+have\s+received\s+deposit\s+of\s+Tk\s+([\d,]+(?:\.\d{2})?)\s+from\s+(.+?)\.\s+Fee\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+Balance\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+TrxID\s+(\w+)\s+at\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})',
            
            # Pattern for "Cash In Tk amount"
            r'Cash\s+In\s+Tk\s+([\d,]+(?:\.\d{2})?)\s+from\s+(\d+)\s+successful\.\s+Fee\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+Balance\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+TrxID\s+(\w+)\s+at\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})',
            
            # Pattern for "Payment Tk amount"
            r'Payment\s+Tk\s+([\d,]+(?:\.\d{2})?)\s+to\s+(\d+)\s+successful\.\s+(?:Ref\s+(.+?)\.\s+)?Fee\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+Balance\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+TrxID\s+(\w+)\s+at\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})'
        ]

    def parse_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse SMS message and extract transaction data"""
        message = message.strip()
        
        # Try EBL patterns first
        if "EBL" in message or "AC " in message:
            return self._parse_ebl_message(message)
        
        # Try Bkash patterns
        elif any(keyword in message for keyword in ["bKash", "Tk ", "TrxID", "Cash In", "Payment"]):
            return self._parse_bkash_message(message)
        
        return None

    def _parse_ebl_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse EBL SMS message"""
        
        # Pattern 1: Debit/Credit transactions
        pattern1 = r'AC\s+\d+\*+\d+\s+is\s+(debited|credited)\s+with\s+BDT\s+([\d,]+(?:\.\d{2})?)\s+as\s+(.+?)\s+on\s+(\d{2}-[A-Z]{3}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+[AP]M)\s+Balance\s+is\s+BDT\s+([\d,]+(?:\.\d{2})?)'
        match = re.search(pattern1, message, re.IGNORECASE)
        if match:
            transaction_type_raw = match.group(1).lower()
            amount = float(match.group(2).replace(',', ''))
            description = match.group(3)
            date_str = match.group(4)
            balance = float(match.group(5).replace(',', ''))
            
            # Determine if it's expense or income
            transaction_type = "expense" if transaction_type_raw == "debited" else "income"
            
            # Skip internal transfers between bKash and EBL
            if "bKash" in description and transaction_type_raw == "debited":
                # This is money going to bKash, don't count as expense
                transaction_type = "transfer_out"
            
            return {
                "platform": "EBL",
                "transaction_type": transaction_type,
                "raw_type": f"EBL {transaction_type_raw}",
                "amount": amount,
                "balance": balance,
                "description": description,
                "date": self._parse_ebl_date(date_str),
                "raw_message": message
            }
        
        # Pattern 2: Cash Withdrawal
        pattern2 = r'Cash\s+WD\s+BDT([\d,]+(?:\.\d{2})?)\s+from\s+(.+?)\s*\.\s*Card\s+\d+\*+\d+\s+on\s+(\d{2}-[A-Za-z]{3}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+[AP]M\s+BST)\.Your\s+A/C\s+\d+\*+\d+\s+Balance\s+BDT\s+([\d,]+(?:\.\d{2})?)'
        match = re.search(pattern2, message, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(',', ''))
            location = match.group(2)
            date_str = match.group(3)
            balance = float(match.group(4).replace(',', ''))
            
            return {
                "platform": "EBL",
                "transaction_type": "expense",
                "raw_type": "EBL Cash Withdrawal",
                "amount": amount,
                "balance": balance,
                "description": f"Cash WD from {location}",
                "date": self._parse_ebl_date_bst(date_str),
                "raw_message": message
            }
        
        # Pattern 3: Fund Transfer
        pattern3 = r'Fund\s+Transfer\s+of\s+BDT\s+([\d,]+(?:\.\d{2})?)\s+from\s+(.+?)\s*\.\s*Card\s+\d+\*+\d+\s+on\s+(\d{2}-[A-Za-z]{3}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+[AP]M\s+BST)\.Your\s+A/C\s+\d+\*+\d+\s+Balance\s+BDT\s+([\d,]+(?:\.\d{2})?)'
        match = re.search(pattern3, message, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(',', ''))
            source = match.group(2)
            date_str = match.group(3)
            balance = float(match.group(4).replace(',', ''))
            
            # This is money coming from bKash to EBL, don't count as income
            transaction_type = "transfer_in" if "bKash" in source else "income"
            
            return {
                "platform": "EBL",
                "transaction_type": transaction_type,
                "raw_type": "EBL Fund Transfer",
                "amount": amount,
                "balance": balance,
                "description": f"Fund Transfer from {source}",
                "date": self._parse_ebl_date_bst(date_str),
                "raw_message": message
            }
        
        return None

    def _parse_bkash_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse Bkash SMS message"""
        
        # Pattern 1: Deposit from VISA Card
        pattern1 = r'You\s+have\s+received\s+deposit\s+of\s+Tk\s+([\d,]+(?:\.\d{2})?)\s+from\s+(.+?)\.\s+Fee\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+Balance\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+TrxID\s+(\w+)\s+at\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})'
        match = re.search(pattern1, message, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(',', ''))
            source = match.group(2)
            fee = float(match.group(3).replace(',', ''))
            balance = float(match.group(4).replace(',', ''))
            trx_id = match.group(5)
            date_str = match.group(6)
            
            # Money from VISA card is income (from EBL to bKash)
            transaction_type = "transfer_in" if "VISA Card" in source else "income"
            
            return {
                "platform": "bKash",
                "transaction_type": transaction_type,
                "raw_type": "bKash Deposit",
                "amount": amount,
                "balance": balance,
                "fee": fee,
                "description": f"Deposit from {source}",
                "transaction_id": trx_id,
                "date": self._parse_bkash_date(date_str),
                "raw_message": message
            }
        
        # Pattern 2: Cash In
        pattern2 = r'Cash\s+In\s+Tk\s+([\d,]+(?:\.\d{2})?)\s+from\s+(\d+)\s+successful\.\s+Fee\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+Balance\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+TrxID\s+(\w+)\s+at\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})'
        match = re.search(pattern2, message, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(',', ''))
            from_number = match.group(2)
            fee = float(match.group(3).replace(',', ''))
            balance = float(match.group(4).replace(',', ''))
            trx_id = match.group(5)
            date_str = match.group(6)
            
            return {
                "platform": "bKash",
                "transaction_type": "income",
                "raw_type": "bKash Cash In",
                "amount": amount,
                "balance": balance,
                "fee": fee,
                "description": f"Cash In from {from_number}",
                "transaction_id": trx_id,
                "date": self._parse_bkash_date(date_str),
                "raw_message": message
            }
        
        # Pattern 3: Payment
        pattern3 = r'Payment\s+Tk\s+([\d,]+(?:\.\d{2})?)\s+to\s+(\d+)\s+successful\.\s+(?:Ref\s+(.+?)\.\s+)?Fee\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+Balance\s+Tk\s+([\d,]+(?:\.\d{2})?)\.\s+TrxID\s+(\w+)\s+at\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})'
        match = re.search(pattern3, message, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(',', ''))
            to_number = match.group(2)
            reference = match.group(3) if match.group(3) else ""
            fee = float(match.group(4).replace(',', ''))
            balance = float(match.group(5).replace(',', ''))
            trx_id = match.group(6)
            date_str = match.group(7)
            
            return {
                "platform": "bKash",
                "transaction_type": "expense",
                "raw_type": "bKash Payment",
                "amount": amount,
                "balance": balance,
                "fee": fee,
                "description": f"Payment to {to_number}" + (f" - {reference}" if reference else ""),
                "transaction_id": trx_id,
                "date": self._parse_bkash_date(date_str),
                "raw_message": message
            }
        
        return None

    def _parse_ebl_date(self, date_str: str) -> datetime:
        """Parse EBL date format: 07-AUG-25 10:02:47 PM"""
        try:
            dt = datetime.strptime(date_str, "%d-%b-%y %I:%M:%S %p")
            return self.timezone.localize(dt)
        except:
            return datetime.now(self.timezone)

    def _parse_ebl_date_bst(self, date_str: str) -> datetime:
        """Parse EBL BST date format: 07-Aug-25 06:38:41 PM BST"""
        try:
            # Remove BST and parse
            clean_date = date_str.replace(" BST", "")
            dt = datetime.strptime(clean_date, "%d-%b-%y %I:%M:%S %p")
            return self.timezone.localize(dt)
        except:
            return datetime.now(self.timezone)

    def _parse_bkash_date(self, date_str: str) -> datetime:
        """Parse bKash date format: 07/08/2025 17:36"""
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M")
            return self.timezone.localize(dt)
        except:
            return datetime.now(self.timezone)