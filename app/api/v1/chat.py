from fastapi import APIRouter
from app.models.schemas import ChatRequest
from app.agents.personal_chief import search_recipes, get_messages, clear_messages
from fastapi.responses import StreamingResponse
from app.common.logger import logger


router = APIRouter()


@router.post("/chat/stream")
async def chat_endpoint(request: ChatRequest):
    """流式对话"""
    return StreamingResponse(
        search_recipes(request.message, request.image_url, request.thread_id),
        media_type="text/event-stream"
    )


@router.get("/chat/messages")
async def get_chat_messages(thread_id: str):
    messages = get_messages(thread_id)
    return {"messages": messages}


@router.delete("/chat/messages")
async def clear_chat_messages(thread_id: str):
    clear_messages(thread_id)
    return {"success": True}