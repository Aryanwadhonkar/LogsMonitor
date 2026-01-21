import asyncio
import httpx
import random
import time
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use API_URL from environment or default to localhost
API_URL = os.getenv("API_URL", "http://localhost:8000/logs")

LOG_LEVELS = ["INFO", "DEBUG", "WARNING", "ERROR"]
SOURCES = ["auth-service", "payment-gateway", "inventory-api", "frontend-app"]

async def send_log(client, log_data):
    try:
        response = await client.post(API_URL, json=log_data)
        if response.status_code == 200:
            print(f"✅ Sent: [{log_data['level']}] {log_data['message'][:50]}...")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ Connection Error: {e}")

async def run_random_simulator(client):
    MESSAGES = [
        "User login successful",
        "Database connection timeout",
        "Cache cleared",
        "Invalid API key provided",
        "Transaction processed",
        "High CPU usage detected",
        "New user registered",
        "Failed to fetch resource"
    ]
    print(f"🚀 Starting Random Log Simulator (Target: {API_URL})")
    while True:
        log_data = {
            "level": random.choice(LOG_LEVELS),
            "message": random.choice(MESSAGES),
            "source": random.choice(SOURCES)
        }
        await send_log(client, log_data)
        await asyncio.sleep(random.uniform(0.5, 2.0))

async def run_file_simulator(client, file_path):
    print(f"📂 Starting File Log Simulator (Reading: {file_path})")
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    # Open file and move to end (like tail -f)
    with open(file_path, 'r') as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue
            
            line = line.strip()
            if line:
                # Simple parsing: assume format "LEVEL: Message" or just "Message"
                level = "INFO"
                message = line
                for l in LOG_LEVELS:
                    if line.upper().startswith(f"{l}:"):
                        level = l
                        message = line[len(l)+1:].strip()
                        break
                
                log_data = {
                    "level": level,
                    "message": message,
                    "source": "file-monitor"
                }
                await send_log(client, log_data)

async def main():
    async with httpx.AsyncClient() as client:
        # Check if a file path was provided as an argument
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            await run_file_simulator(client, file_path)
        else:
            await run_random_simulator(client)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping simulator...")
