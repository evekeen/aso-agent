"""Startup script for Streamlit frontend."""

import os
import subprocess
import sys
from dotenv import load_dotenv

def main():
    """Run the Streamlit frontend."""
    # Load environment variables
    load_dotenv()
    
    # Set default agent URL if not specified
    if not os.getenv("AGENT_URL"):
        os.environ["AGENT_URL"] = "http://localhost:8080"
    
    print(f"🌐 Starting Streamlit ASO Agent Frontend")
    print(f"🔗 Agent Service URL: {os.getenv('AGENT_URL')}")
    print(f"📱 Open your browser and go to: http://localhost:8501")
    
    # Run streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "src/streamlit_app.py",
        "--server.address=0.0.0.0",
        "--server.port=8501"
    ])

if __name__ == "__main__":
    main()