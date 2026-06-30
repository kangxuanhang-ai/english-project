import json
import traceback
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.database import get_db
from app.models.conversation import Conversation
from ai.schemas.chat import ChatRequest
from ai.services.chat import stream_chat, get_chat_history
from ai.services.wordbook_short_circuit import WORDBOOK_FEATURE, is_wordbook_intent, iter_wordbook_sse
from ai.rate_limit import limiter

router = APIRouter(prefix="/ai/v1/chat", tags=["chat"])


@router.post("")
@limiter.limit("20/minute")
async def chat(
    request: Request,
    data: ChatRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE 流式聊天。"""
    # 更新对话的 updated_at，让活跃对话排到最前面
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == data.conversationId,
            Conversation.user_id == user["userId"],
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    if data.role != conversation.role:
        raise HTTPException(status_code=400, detail="角色与对话不匹配")

    from sqlalchemy import func
    conversation.updated_at = func.now()
    await db.commit()

    chat_data = data.model_dump()
    chat_data["role"] = conversation.role
    chat_data["userId"] = user["userId"]

    async def _stream():
        emitted = False
        try:
            if (
                chat_data.get("role") == "normal"
                and chat_data.get("userId")
                and is_wordbook_intent(chat_data.get("content", ""))
            ):
                async for chunk in iter_wordbook_sse(
                    role=chat_data["role"],
                    user_id=chat_data["userId"],
                    conversation_id=chat_data["conversationId"],
                    content=chat_data["content"],
                ):
                    if '"type": "done"' in chunk or '"type": "error"' in chunk:
                        emitted = True
                    yield chunk
                return

            async for chunk in stream_chat(chat_data):
                if '"type": "done"' in chunk or '"type": "error"' in chunk:
                    emitted = True
                yield chunk
        except Exception as e:
            traceback.print_exc()
            emitted = True
            try:
                yield f"data: {json.dumps({'type': 'error', 'message': '对话出错，请重试'}, ensure_ascii=False)}\n\n"
            except (GeneratorExit, RuntimeError, asyncio.CancelledError):
                pass
        finally:
            if not emitted:
                try:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'stream interrupted'}, ensure_ascii=False)}\n\n"
                except (GeneratorExit, RuntimeError, asyncio.CancelledError):
                    pass

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/history")
async def history(
    conversationId: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对话历史。"""
    # 归属校验
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversationId,
            Conversation.user_id == user["userId"],
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="对话不存在")

    try:
        history = await get_chat_history(conversationId)
    except Exception:
        raise HTTPException(status_code=500, detail="加载对话历史失败，请稍后重试")
    return {
        "data": {
            "messages": history["messages"],
            "truncated": history["truncated"],
        },
        "code": 200,
        "message": "查询成功",
    }
