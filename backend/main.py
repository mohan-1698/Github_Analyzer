"""
GitHub Growth Analyzer Backend Entry Point

Run this file to start the FastAPI server:
    python main.py

Or from the project root:
    python -m backend.main
"""

import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "auth.main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Disabled to prevent state dict from being cleared
    )
