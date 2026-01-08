from fastapi import APIRouter, HTTPException
import db

router = APIRouter()

# History endpoints
@router.get("/history", response_model=list[db.HistoryItem])
async def get_history_records():
    """Get all history records"""
    try:
        history = db.get_history()
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history/{history_id}")
async def delete_history_record(history_id: int):
    """Delete a specific history record"""
    try:
        db.delete_history(history_id)
        return {"message": "History record deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history")
async def delete_all_history():
    """Delete all history records"""
    try:
        db.delete_all_history()
        return {"message": "All history records deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))