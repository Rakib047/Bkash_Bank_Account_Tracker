from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime

from app.Service.sms_processor import SMSProcessor
from app.Service.sheets_manager import SheetsManager

logger = logging.getLogger(__name__)

# Initialize services
sms_processor = SMSProcessor()
sheets_manager = SheetsManager()

# Create router
router = APIRouter()

class SMSMessage(BaseModel):
    message: str
    timestamp: Optional[datetime] = None

@router.get("/")
async def root():
    return {"message": "Transaction SMS Processor API", "status": "running"}

@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@router.post("/setup-worksheets")
async def setup_worksheets():
    try:
        logger.info("Setting up Summary and Transaction Details worksheets...")
        sheets_manager._setup_summary_headers()
        sheets_manager._setup_transaction_headers()
        return {"status": "success", "message": "Both worksheets have been set up with proper structure"}
    except Exception as e:
        logger.error(f"Error setting up worksheets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-sms")
async def process_sms(sms: SMSMessage):
    try:
        logger.info(f"Received SMS: {sms.message}")
        
        # Parse the SMS message
        transaction_data = sms_processor.parse_message(sms.message)
        
        if not transaction_data:
            logger.info("SMS not recognized as transaction message")
            return {"status": "ignored", "reason": "Not a transaction message"}
        
        # Log to Google Sheets
        result = await sheets_manager.log_transaction(transaction_data)
        
        logger.info(f"Transaction logged successfully: {transaction_data}")
        return {"status": "success", "data": transaction_data, "sheets_result": result}
        
    except Exception as e:
        logger.error(f"Error processing SMS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/balances")
async def get_current_balances():
    try:
        balances = sheets_manager.get_current_balances()
        return {"status": "success", "data": balances}
    except Exception as e:
        logger.error(f"Error getting balances: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))