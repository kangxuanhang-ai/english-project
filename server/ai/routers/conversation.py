import traceback

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.database import get_db
from app.models.conversation import Conversation
from ai.rate_limit import limiter
from ai.schemas.conversation import CreateConversationRequest, GenerateTitleRequest
from ai.services.chat import get_checkpointer

router = APIRouter(prefix="/ai/v1/chat/conversations", tags=["conversations"])


@router.post("")
async def create_conversation(
    data: CreateConversationRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新建对话。"""
    conversation = Conversation(
        user_id=user["userId"],
        role=data.role,
        title="新对话",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return {
        "data": {
            "id": conversation.id,
            "role": conversation.role,
            "title": conversation.title,
            "createdAt": conversation.created_at.isoformat() if conversation.created_at else None,
            "updatedAt": conversation.updated_at.isoformat() if conversation.updated_at else None,
        },
        "code": 200,
        "message": "创建成功",
    }


@router.get("")
async def list_conversations(
    role: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取某角色的对话列表，按 updated_at 降序。"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user["userId"], Conversation.role == role)
        .order_by(Conversation.updated_at.desc())
        .limit(200)
    )
    conversations = result.scalars().all()
    return {
        "data": [
            {
                "id": c.id,
                "role": c.role,
                "title": c.title,
                "createdAt": c.created_at.isoformat() if c.created_at else None,
                "updatedAt": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in conversations
        ],
        "code": 200,
        "message": "查询成功",
    }


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除对话（级联清除 LangGraph 消息）。"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user["userId"],
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 先删 LangGraph 消息
    try:
        checkpointer = await get_checkpointer()
        await checkpointer.adelete_thread(conversation_id)
    except Exception:
        traceback.print_exc()  # LangGraph 删除失败不阻塞记录删除

    # 再删数据库记录
    await db.delete(conversation)
    await db.commit()
    return {"data": None, "code": 200, "message": "删除成功"}


@router.post("/title")
@limiter.limit("10/minute")
async def generate_conversation_title(
    request: Request,
    data: GenerateTitleRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成对话标题。"""
    from ai.services.chat import generate_title

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == data.conversationId,
            Conversation.user_id == user["userId"],
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    title = await generate_title(data.firstMessage)
    conversation.title = title
    await db.commit()
    await db.refresh(conversation)
    return {
        "data": {"id": conversation.id, "title": conversation.title},
        "code": 200,
        "message": "生成成功",
    }
