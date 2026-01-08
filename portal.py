import os
import urllib.request
from fastapi import HTTPException
from device import get_connected_devices, run_adb_command

async def download_portal_apk():
    """Download DroidRun Portal APK file"""
    portal_url = "https://github.com/droidrun/droidrun-portal/releases/download/v0.4.7/droidrun-portal-v0.4.7.apk"
    portal_path = "droidrun-portal.apk"
    # Check if file already exists
    if os.path.exists(portal_path):
        return portal_path
    try:
        print(f"Downloading DroidRun Portal APK from {portal_url}")
        urllib.request.urlretrieve(portal_url, portal_path)
        print("Download completed")
        return portal_path
    except Exception as e:
        print(f"Download failed: {e}")
        # Try alternative download location
         

async def install_portal(portal_path: str = None):
    """Install DroidRun Portal app on device"""
    try:
        devices = get_connected_devices()
        if not devices:
            raise HTTPException(status_code=400, detail="No device connected")

        device_id = devices[0]

        # Use provided path or download automatically
        if not portal_path:
            portal_path = await download_portal_apk()

        # Check if APK file exists
        if not os.path.exists(portal_path):
            raise HTTPException(status_code=400, detail="Portal APK file not found")

        print(f"Installing Portal APK on device {device_id}")
        success, stdout, stderr = run_adb_command(['-s', device_id, 'install', '-r', portal_path])

        if success:
            return {"message": "Portal app installed successfully", "device": device_id}
        else:
            raise HTTPException(status_code=400, detail=f"Installation failed: {stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
