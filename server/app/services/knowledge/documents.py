from nanoid import generate
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import DocumentStatus, KnowledgeChunk, KnowledgeDocument
from app.services.knowledge.parser import default_title, validate_upload
from app.services.knowledge.storage import delete_object, make_key, upload_bytes


def _doc_item(doc: KnowledgeDocument) -> dict:
    return {
        "id": doc.id,
        "title": doc.title,
        "filename": doc.filename,
        "mimeType": doc.mime_type,
        "fileSize": doc.file_size,
        "status": doc.status if isinstance(doc.status, str) else doc.status.value,
        "chunkCount": doc.chunk_count,
        "errorMessage": doc.error_message,
        "uploadedBy": doc.uploaded_by,
        "createdAt": doc.created_at.isoformat() if doc.created_at else None,
        "updatedAt": doc.updated_at.isoformat() if doc.updated_at else None,
    }


async def list_documents(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    status: str | None = None,
) -> dict:
    query = select(KnowledgeDocument)
    count_query = select(func.count(KnowledgeDocument.id))

    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        cond = KnowledgeDocument.title.ilike(kw)
        query = query.where(cond)
        count_query = count_query.where(cond)

    if status:
        try:
            st = DocumentStatus(status)
            query = query.where(KnowledgeDocument.status == st.value)
            count_query = count_query.where(KnowledgeDocument.status == st.value)
        except ValueError:
            pass

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(KnowledgeDocument.created_at.desc()).offset(offset).limit(page_size)
    )
    docs = result.scalars().all()
    return {"list": [_doc_item(d) for d in docs], "total": total}


async def get_document(db: AsyncSession, doc_id: str) -> dict | None:
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    return _doc_item(doc) if doc else None


async def create_document_upload(
    db: AsyncSession,
    *,
    filename: str,
    content_type: str | None,
    raw: bytes,
    uploaded_by: str,
    title: str | None,
    max_size: int,
) -> KnowledgeDocument:
    validate_upload(filename, content_type, len(raw), max_size)
    doc_id = generate(size=20)
    key = make_key(doc_id, filename)
    await upload_bytes(key, raw, content_type or "application/octet-stream")

    doc = KnowledgeDocument(
        id=doc_id,
        title=(title or default_title(filename))[:200],
        filename=filename,
        mime_type=content_type or "application/octet-stream",
        file_size=len(raw),
        minio_key=key,
        status=DocumentStatus.PENDING.value,
        chunk_count=0,
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def update_document_title(db: AsyncSession, doc_id: str, title: str) -> dict | None:
    title = title.strip()
    if not title or len(title) > 200:
        raise ValueError("标题必填且不超过 200 字符")
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return None
    doc.title = title
    await db.commit()
    await db.refresh(doc)
    return _doc_item(doc)


async def delete_document(db: AsyncSession, doc_id: str) -> bool:
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return False
    minio_key = doc.minio_key
    await db.delete(doc)
    await db.commit()
    await delete_object(minio_key)
    return True


async def list_document_chunks(
    db: AsyncSession, doc_id: str, *, page: int = 1, page_size: int = 20
) -> dict | None:
    exists = await db.scalar(
        select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.id == doc_id)
    )
    if not exists:
        return None
    total = (
        await db.execute(
            select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.document_id == doc_id)
        )
    ).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == doc_id)
        .order_by(KnowledgeChunk.chunk_index)
        .offset(offset)
        .limit(page_size)
    )
    chunks = result.scalars().all()
    return {
        "list": [
            {
                "chunkIndex": c.chunk_index,
                "content": c.content,
                "tokenCount": c.token_count,
            }
            for c in chunks
        ],
        "total": total,
    }
