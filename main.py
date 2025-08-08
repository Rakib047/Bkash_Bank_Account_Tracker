from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logging
from datetime import datetime

from app.sms_processor import SMSProcessor
from app.sheets_manager import SheetsManager
from app.config import settings

app = FastAPI(
    title="Transaction SMS Processor",
    description="Processes Bkash and EBL transaction SMS messages and logs to Google Sheets",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sms_processor = SMSProcessor()
sheets_manager = SheetsManager()

class SMSMessage(BaseModel):
    message: str
    timestamp: Optional[datetime] = None

@app.get("/")
async def root():
    return {"message": "Transaction SMS Processor API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/fix-sheet-headers")
async def fix_sheet_headers():
    try:
        logger.info("Manually fixing sheet headers...")
        sheets_manager._setup_headers()
        return {"status": "success", "message": "Sheet headers have been reset and realigned"}
    except Exception as e:
        logger.error(f"Error fixing sheet headers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-sms")
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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )