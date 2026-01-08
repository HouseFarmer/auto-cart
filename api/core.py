import asyncio
import queue
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import action
import log
import db

router = APIRouter()

# 动作请求模型
class ActionRequest(BaseModel):
    action: str
    scenario: str = None

# 根端点
@router.get("/")
async def root():
    """根端点"""
    return {"message": "DroidRun API is running"}

# 动作执行端点
@router.post("/stream-execute")
async def stream_execute_action(request: ActionRequest):
    """执行手机动作并流式传输日志"""
    if not request.action.strip():
        raise HTTPException(status_code=400, detail="动作不能为空")
    
    try:
        action_text = request.action.strip()
        
        # 创建日志队列和完成事件
        log_queue = asyncio.Queue()
        done_event = asyncio.Event()
        
        # 创建执行动作的任务
        execution_task = asyncio.create_task(
            action.stream_execute_droidrun_action(action_text, log_queue, done_event, request.scenario)
        )
        
        async def generate_logs():
            """生成可用的日志"""
            # 开始流式传输日志
            async for log_line in log.log_generator(log_queue, done_event):
                # 包装成JSON格式并添加SSE前缀
                log_json = {"log": log_line}
                yield f"data: {json.dumps(log_json)}\n\n"
            
            # 等待执行完成
            result = await execution_task
            
            # 保存到历史记录
            db.add_history(
                action=action_text,
                success=result["success"],
                reason=result["reason"]
            )
        
        # 启动流式响应
        return StreamingResponse(
            generate_logs(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))