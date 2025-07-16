"""Startup script for ASO Agent Service."""

import os
import uvicorn
from dotenv import load_dotenv

from src.service.settings import settings

def main():
    """Run the ASO Agent Service."""
    # Load environment variables
    load_dotenv()
    
    # Log startup info
    print(f"🚀 Starting ASO Agent Service")
    print(f"📍 Host: {settings.HOST}")
    print(f"🔌 Port: {settings.PORT}")
    print(f"🤖 Available models: {settings.available_models}")
    print(f"🗄️  Database: {settings.DATABASE_TYPE} ({settings.SQLITE_DB_PATH})")
    
    # Start the server
    uvicorn.run(
        "src.service.service:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()