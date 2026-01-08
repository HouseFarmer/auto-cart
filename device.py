import subprocess
import time
import datetime
from fastapi import HTTPException

# Device management functions
def run_adb_command(command):
    """Run ADB command and return result"""
    try:
        full_command = ['adb'] + command
        
        # 只在非设备查询命令时打印调试信息，减少日志冗余
        if not (command == ['devices'] or command == ['devices', '-l']):
            print(f"Executing ADB command: {full_command}")
        
        result = subprocess.run(full_command, capture_output=True, text=True, timeout=10)
        
        # 只在非设备查询命令时打印结果信息
        if not (command == ['devices'] or command == ['devices', '-l']):
            print(f"ADB command result - returncode: {result.returncode}, stdout: '{result.stdout.strip()}', stderr: '{result.stderr.strip()}'")
        
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        print(f"ADB command timeout: {command}")
        return False, "", "ADB command timeout"
    except FileNotFoundError:
        print(f"ADB not found: {command}")
        return False, "", "ADB not found. Please install Android SDK platform tools."
    except Exception as e:
        print(f"ADB command exception: {e}, command: {command}")
        return False, "", str(e)

def get_connected_devices():
    """Get list of connected Android devices"""
    success, stdout, stderr = run_adb_command(['devices'])
    if not success:
        return []

    devices = []
    lines = stdout.strip().split('\n')[1:]  # Skip first line
    for line in lines:
        if line.strip() and not line.startswith('*'):
            parts = line.split('\t')
            if len(parts) >= 2:
                device_id = parts[0]
                status = parts[1]
                if status == 'device':
                    devices.append(device_id)
    return devices

def get_device_info(device_id):
    """Get device information"""
    # First check device status
    success, stdout, stderr = run_adb_command(['devices'])
    device_status = "unknown"

    if success:
        lines = stdout.strip().split('\n')[1:]  # Skip first line
        for line in lines:
            if line.strip().startswith(device_id):
                parts = line.split('\t')
                if len(parts) >= 2:
                    device_status = parts[1]
                break

    info = {
        "id": device_id,
        "connected": device_status == 'device',
        "status": device_status
    }

    # Only get detailed info if device is properly connected
    if device_status == 'device':
        # Get device model
        success, stdout, _ = run_adb_command(['-s', device_id, 'shell', 'getprop', 'ro.product.model'])
        info["model"] = stdout.strip() if success else "Unknown"

        # Get Android version
        success, stdout, _ = run_adb_command(['-s', device_id, 'shell', 'getprop', 'ro.build.version.release'])
        info["version"] = stdout.strip() if success else "Unknown"

        # Get device name
        success, stdout, _ = run_adb_command(['-s', device_id, 'shell', 'getprop', 'ro.product.name'])
        info["name"] = stdout.strip() if success else "Android Device"

        # Check if Portal app is installed
        success, stdout, _ = run_adb_command(['-s', device_id, 'shell', 'pm', 'list', 'packages', 'com.droidrun.portal'])
        info["portal_installed"] = "com.droidrun.portal" in stdout if success else False
    else:
        info["model"] = "Unknown"
        info["version"] = "Unknown"
        info["name"] = f"Device ({device_status})"
        info["portal_installed"] = False

    return info

# API endpoint functions
def list_devices():
    """List all connected and available devices"""
    try:
        devices = get_connected_devices()
        device_list = []
        for device_id in devices:
            device_info = get_device_info(device_id)
            device_list.append(device_info)

        # Also check for devices that might be available but not authorized
        success, stdout, stderr = run_adb_command(['devices'])
        if success:
            lines = stdout.strip().split('\n')[1:]  # Skip first line
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        device_id = parts[0]
                        status = parts[1]
                        # Include devices with any status (device, unauthorized, offline)
                        if device_id not in [d['id'] for d in device_list]:
                            device_list.append({
                                "id": device_id,
                                "connected": status == 'device',
                                "status": status,
                                "name": f"Device ({status})",
                                "model": "Unknown",
                                "version": "Unknown",
                                "portal_installed": False
                            })

        return {"devices": device_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_device_status():
    """Get device connection status"""
    try:
        devices = get_connected_devices()
        if devices:
            device_info = get_device_info(devices[0])
            return device_info
        else:
            return {
                "connected": False,
                "name": "未连接",
                "model": "",
                "version": "",
                "id": ""
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def connect_device(connection_data: dict = None):
    """Connect to Android device via USB or WiFi"""
    try:
        connection_data = connection_data or {}
        ip_address = connection_data.get('ip_address')
        device_id = connection_data.get('device_id')
        connection_type = connection_data.get('type', 'usb')  # 'usb' or 'wifi'

        if connection_type == 'wifi' and ip_address:
            # WiFi connection
            success, stdout, stderr = run_adb_command(['connect', ip_address])
            if success:
                # Wait a moment for connection to establish
                time.sleep(2)
                device_info = get_device_info(ip_address)
                return {"message": f"Connected to {ip_address}", "device": device_info}
            else:
                raise HTTPException(status_code=400, detail=f"Failed to connect: {stderr}")

        elif connection_type == 'usb':
            # USB connection
            if device_id:
                # Try to connect to specific device
                success, stdout, stderr = run_adb_command(['-s', device_id, 'shell', 'echo', 'test'])
                if success:
                    device_info = get_device_info(device_id)
                    return {"message": f"Connected to device {device_id}", "device": device_info}
                else:
                    raise HTTPException(status_code=400, detail=f"Failed to connect to device {device_id}: {stderr}")
            else:
                # General USB connection - restart ADB server and check devices
                success1, _, _ = run_adb_command(['kill-server'])
                success2, _, _ = run_adb_command(['start-server'])

                if success2:
                    # Wait for server to start
                    time.sleep(2)

                    # Check for connected devices
                    devices = get_connected_devices()
                    if devices:
                        device_info = get_device_info(devices[0])
                        return {"message": "Device connected via USB", "device": device_info}
                    else:
                        raise HTTPException(status_code=400, detail="No USB device found. Please ensure USB debugging is enabled and device is connected.")
                else:
                    raise HTTPException(status_code=400, detail="Failed to start ADB server")

        else:
            raise HTTPException(status_code=400, detail="Invalid connection type. Use 'usb' or 'wifi'")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def disconnect_device(device_id: str = None):
    """Disconnect from Android device"""
    try:
        if device_id:
            success, stdout, stderr = run_adb_command(['disconnect', device_id])
        else:
            # Disconnect all devices
            success, stdout, stderr = run_adb_command(['disconnect'])

        if success:
            return {"message": "Device disconnected successfully"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to disconnect: {stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def take_screenshot():
    """Take a screenshot of the device"""
    try:
        # Check if ADB is available
        success, stdout, stderr = run_adb_command(['version'])
        if not success:
            raise HTTPException(status_code=500, detail=f"ADB error: {stderr}")

        # Get connected devices
        devices = get_connected_devices()
        if not devices:
            raise HTTPException(status_code=400, detail="No Android device connected. Please connect a device and enable USB debugging.")

        device_id = devices[0]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshot_{timestamp}.png"
        remote_path = f"/sdcard/{screenshot_path}"

        # Capture screenshot on device
        success, stdout, stderr = run_adb_command([
            '-s', device_id, 'shell', 'screencap', '-p', remote_path
        ])

        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to capture screenshot: {stderr}")

        # Pull the screenshot to local machine
        success2, stdout2, stderr2 = run_adb_command([
            '-s', device_id, 'pull', remote_path, screenshot_path
        ])

        if success2:
            # Clean up remote screenshot
            run_adb_command(['-s', device_id, 'shell', 'rm', remote_path])
            return {"message": f"Screenshot saved as {screenshot_path}"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to pull screenshot: {stderr2}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenshot failed: {str(e)}")

def execute_adb_command_endpoint(command_data: dict):
    """Execute arbitrary ADB command"""
    try:
        command = command_data.get("command", "").strip()
        if not command:
            raise HTTPException(status_code=400, detail="Command cannot be empty")

        # Security check - only allow safe commands
        dangerous_commands = ['rm', 'rmdir', 'del', 'format', 'fdisk', 'mkfs']
        if any(cmd in command.lower() for cmd in dangerous_commands):
            raise HTTPException(status_code=400, detail="Dangerous command not allowed")

        # 处理用户输入的命令，移除可能的"adb"前缀
        command_parts = command.split()
        if command_parts and command_parts[0].lower() == "adb":
            command_parts = command_parts[1:]
            
        if not command_parts:
            raise HTTPException(status_code=400, detail="Command cannot be empty")

        success, stdout, stderr = run_adb_command(command_parts)

        if success:
            return {"message": stdout or "Command executed successfully"}
        else:
            raise HTTPException(status_code=400, detail=f"ADB command failed: {stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
