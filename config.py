import json
import os
from fastapi import HTTPException

# Global configuration storage
app_config = {
    "llmProvider": "DeepSeek",
    "llmModel": "deepseek-chat",
    "llmTemperature": 0.1,
    "enableVision": True,
    "enableReasoning": False,
    "maxSteps": 20
}

# Configuration management functions
def save_config(config: dict):
    """Save application configuration"""
    try:
        global app_config
        app_config.update(config)

        # Save to file (optional)
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(app_config, f, indent=2, ensure_ascii=False)

        return {"message": "Configuration saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_config():
    """Get application configuration"""
    try:
        # Try to load configuration from file
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                app_config.update(file_config)
        except FileNotFoundError:
            pass

        return app_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
