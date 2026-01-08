from fastapi import APIRouter
import config

router = APIRouter()

# Configuration endpoints
@router.post("/config")
async def save_config(config_data: dict):
    """Save application configuration"""
    return config.save_config(config_data)

@router.get("/config")
async def get_config():
    """Get application configuration"""
    return config.get_config()