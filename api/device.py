from fastapi import APIRouter, Body, HTTPException
import device
import portal

router = APIRouter()

# Device management endpoints
@router.get("/devices")
async def list_devices():
    """List all connected and available devices"""
    return device.list_devices()

@router.get("/device/status")
async def get_device_status():
    """Get device connection status"""
    return device.get_device_status()

@router.post("/device/connect")
async def connect_device(connection_data: dict = Body(None)):
    """Connect to Android device via USB or WiFi"""
    return device.connect_device(connection_data)

@router.post("/device/disconnect")
async def disconnect_device(device_id: str = None):
    """Disconnect from Android device"""
    return device.disconnect_device(device_id)

@router.get("/device/screenshot")
async def take_screenshot():
    """Take a screenshot of the device"""
    return device.take_screenshot()

@router.post("/device/adb")
async def execute_adb_command_endpoint(command_data: dict):
    """Execute arbitrary ADB command"""
    return device.execute_adb_command_endpoint(command_data)

# Portal installation endpoint
@router.post("/device/install-portal")
async def install_portal(portal_path: str = None):
    """Install DroidRun Portal app on device"""
    return await portal.install_portal(portal_path)