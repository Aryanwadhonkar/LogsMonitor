import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Async Log Monitor")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
print(f"Connecting to MongoDB at: {MONGO_URI}")

# Global DB variables
db = None
logs_collection = None

@app.on_event("startup")
async def startup_db_client():
    global db, logs_collection
    try:
        client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        # Check connection
        await client.server_info()
        db = client.log_database
        logs_collection = db.logs
        print("✅ MongoDB connection established")
    except Exception as e:
        print(f"⚠️ MongoDB connection failed: {e}")
        print("Running in memory-only mode (logs will not be persisted)")

# Static files and Templates
# Ensure paths are relative to the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend/static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend/templates"))

class LogEntry(BaseModel):
    level: str
    message: str
    source: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # Connection might be closed
                pass
        # Clean up dead connections
        self.active_connections = [c for c in self.active_connections if c.client_state.value == 1]

manager = ConnectionManager()

# --- ROUTES ---

@app.get("/")
async def get_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/logs")
async def create_log(log: LogEntry):
    # Use model_dump() for Pydantic V2 compatibility
    log_dict = log.model_dump() if hasattr(log, "model_dump") else log.dict()
    log_dict["timestamp"] = datetime.utcnow().isoformat()
    
    print(f"[SERVER] Received log from {log.source}: [{log.level}] {log.message}")
    
    if logs_collection is not None:
        try:
            await logs_collection.insert_one(log_dict.copy())
        except Exception as e:
            print(f"[SERVER] MongoDB Insert Error: {e}")
    
    # Remove _id if it was added by MongoDB before broadcasting
    log_dict.pop("_id", None)
    await manager.broadcast(json.dumps(log_dict))
    
    return {"status": "success", "data": log_dict}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@app.get("/history")
async def get_history(limit: int = 50):
    if logs_collection is None:
        return []
    try:
        logs = await logs_collection.find().sort("timestamp", -1).to_list(limit)
        for log in logs:
            log["_id"] = str(log["_id"])
        return logs
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
