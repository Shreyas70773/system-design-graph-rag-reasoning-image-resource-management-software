"""Run the server from this script"""
import os
import sys

# Ensure we're in the backend directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from app.main import app
import uvicorn

if __name__ == "__main__":
    print("Starting server on port 8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
