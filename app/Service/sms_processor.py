import re
from datetime import datetime
from typing import Optional, Dict, Any
import pytz
from app.Configuration.config import settings

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
            
            # Determine transaction type based on your definitions
            transaction_type = self._categorize_ebl_transaction(transaction_type_raw, description)
            
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
            
            # Categorize Fund Transfer based on your definitions
            transaction_type = "bkash_bank_internal" if "bKash" in source else "income"
            
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
            
            # Categorize based on your definitions
            transaction_type = self._categorize_bkash_transaction(message, f"Deposit from {source}")
            
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
                "transaction_type": "income",  # Cash In is always income
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

    def _categorize_ebl_transaction(self, transaction_type_raw: str, description: str) -> str:
        """Categorize EBL transactions based on your definitions"""
        description_lower = description.lower()
        
        # Check for EBL EXPENSE keywords
        if any(keyword in description_lower for keyword in ["cash wd", "purchase"]) or transaction_type_raw == "debited":
            # Check if it's an internal transfer to bKash
            if "bkash" in description_lower:
                return "bkash_bank_internal"
            return "expense"
        
        # Check for EBL INCOME keywords  
        elif transaction_type_raw == "credited":
            return "income"
            
        return "unknown"

    def _categorize_bkash_transaction(self, message: str, description: str) -> str:
        """Categorize bKash transactions based on your definitions"""
        message_lower = message.lower()
        description_lower = description.lower()
        
        # Check for bKash EXPENSE keywords
        if any(keyword in message_lower for keyword in ["payment", "cash out", "send money"]):
            return "expense"
        
        # Check for bKash INCOME keywords
        elif "cash in" in message_lower:
            return "income"
        
        # Check for bKash INTERNAL TRANSFER keywords
        elif "received deposit" in message_lower:
            return "bkash_bank_internal"
        elif "bkash to bank" in message_lower:
            return "bkash_bank_internal"
            
        return "unknown"