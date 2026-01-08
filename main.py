import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import modularized components
import db
from api import core, history, device, config

# Initialize FastAPI app
app = FastAPI(title="DroidRun API", version="1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize database on startup
db.init_db()

# Include all API routers
app.include_router(core.router)
app.include_router(history.router)
app.include_router(device.router)
app.include_router(config.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
