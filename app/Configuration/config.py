import os
from typing import Optional
from pathlib import Path

# Load .env file if it exists
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ.setdefault(key, value)

class Settings:
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Google Sheets Configuration
    GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")
    GOOGLE_SERVICE_ACCOUNT_PATH: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH", "service_account.json")
    WORKSHEET_NAME: str = os.getenv("WORKSHEET_NAME", "Transactions")
    
    # Transaction Processing
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Dhaka")
    
    def __init__(self):
        # Only validate in production, not during development
        if not self.DEBUG and not self.GOOGLE_SHEETS_ID:
            raise ValueError("GOOGLE_SHEETS_ID environment variable is required")

settings = Settings()