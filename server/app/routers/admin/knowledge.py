from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_admin
from app.models.knowledge import KnowledgeDocument
from app.services.knowledge.documents import (
    create_document_upload,
    delete_document,
    get_document,
    list_document_chunks,
    list_documents,
    update_document_title,
)
from app.services.knowledge.ingest import assert_processing_capacity, run_ingestion
from app.services.knowledge.search import search_knowledge
from app.services.knowledge.storage import presigned_download_url

router = APIRouter(prefix="/knowledge", tags=["admin-knowledge"])


class TitleBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.get("/search")
async def admin_search_knowledge(
    q: str = Query(..., min_length=1),
    topK: int = Query(5, ge=1, le=20),
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await search_knowledge(db, q.strip(), top_k=topK)
    return {"data": data, "code": 200, "message": "检索成功"}


@router.post("/upload")
async def admin_upload_knowledge(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await assert_processing_capacity(db)
    raw = await file.read()
    try:
        doc = await create_document_upload(
            db,
            filename=file.filename or "document.txt",
            content_type=file.content_type,
            raw=raw,
            uploaded_by=admin["userId"],
            title=title,
            max_size=settings.knowledge_max_file_size,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(run_ingestion, doc.id)
    return {
        "data": {"id": doc.id, "status": doc.status},
        "code": 200,
        "message": "上传成功，正在处理",
    }


@router.get("")
async def admin_list_knowledge(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await list_documents(db, page=page, page_size=pageSize, keyword=keyword, status=status)
    return {"data": data, "code": 200, "message": "查询成功"}


@router.get("/{doc_id}")
async def admin_get_knowledge(
    doc_id: str,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await get_document(db, doc_id)
    if not data:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"data": data, "code": 200, "message": "查询成功"}


@router.get("/{doc_id}/chunks")
async def admin_knowledge_chunks(
    doc_id: str,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await list_document_chunks(db, doc_id, page=page, page_size=pageSize)
    if data is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"data": data, "code": 200, "message": "查询成功"}


@router.put("/{doc_id}")
async def admin_update_knowledge(
    doc_id: str,
    body: TitleBody,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await update_document_title(db, doc_id, body.title)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not data:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"data": data, "code": 200, "message": "更新成功"}


@router.delete("/{doc_id}")
async def admin_delete_knowledge(
    doc_id: str,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    ok = await delete_document(db, doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"data": None, "code": 200, "message": "删除成功"}


@router.post("/{doc_id}/reindex")
async def admin_reindex_knowledge(
    doc_id: str,
    background_tasks: BackgroundTasks,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    await assert_processing_capacity(db)
    background_tasks.add_task(run_ingestion, doc_id, reindex=True)
    return {"data": {"id": doc_id, "status": "processing"}, "code": 200, "message": "已开始重新索引"}


@router.get("/{doc_id}/download")
async def admin_download_knowledge(
    doc_id: str,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    url = await presigned_download_url(doc.minio_key)
    return {"data": {"url": url}, "code": 200, "message": "获取下载链接成功"}
