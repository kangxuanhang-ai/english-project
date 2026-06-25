import logging

from fastapi import HTTPException
from langchain_text_splitters import RecursiveCharacterTextSplitter
from nanoid import generate
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.knowledge import DocumentStatus, KnowledgeChunk, KnowledgeDocument
from app.services.knowledge.embedding import embed_texts, estimate_tokens
from app.services.knowledge.parser import parse_document
from app.services.knowledge.storage import download_bytes

logger = logging.getLogger(__name__)


async def assert_processing_capacity(db: AsyncSession) -> None:
    count = await db.scalar(
        select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.status == DocumentStatus.PROCESSING.value
        )
    )
    if (count or 0) >= 3:
        raise HTTPException(status_code=429, detail="同时处理的文档已达上限，请稍后重试")


async def _set_failed(db: AsyncSession, doc: KnowledgeDocument, message: str) -> None:
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id))
    doc.status = DocumentStatus.FAILED.value
    doc.error_message = message[:500]
    doc.chunk_count = 0
    await db.commit()


async def run_ingestion(document_id: str, *, reindex: bool = False) -> None:
    async with async_session() as db:
        result = await db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return

        try:
            doc.status = DocumentStatus.PROCESSING.value
            doc.error_message = None
            await db.commit()

            if reindex:
                await db.execute(
                    delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id)
                )
                await db.commit()

            raw = await download_bytes(doc.minio_key)
            text = parse_document(doc.filename, raw).strip()
            if not text:
                await _set_failed(db, doc, "文档内容为空")
                return

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.knowledge_chunk_size,
                chunk_overlap=settings.knowledge_chunk_overlap,
            )
            chunks = [c.strip() for c in splitter.split_text(text) if c.strip()]
            if not chunks:
                await _set_failed(db, doc, "文档内容为空")
                return

            batch_size = 16
            all_rows: list[KnowledgeChunk] = []
            for start in range(0, len(chunks), batch_size):
                batch = chunks[start : start + batch_size]
                try:
                    vectors = await embed_texts(batch)
                except ValueError as e:
                    if "维度不匹配" in str(e):
                        await _set_failed(db, doc, "Embedding 维度不匹配")
                    else:
                        await _set_failed(db, doc, str(e))
                    return

                for i, (content, vector) in enumerate(zip(batch, vectors)):
                    idx = start + i
                    all_rows.append(
                        KnowledgeChunk(
                            id=generate(size=20),
                            document_id=doc.id,
                            chunk_index=idx,
                            content=content,
                            embedding=vector,
                            token_count=estimate_tokens(content),
                        )
                    )

            for row in all_rows:
                db.add(row)
            doc.status = DocumentStatus.READY.value
            doc.chunk_count = len(all_rows)
            doc.error_message = None
            await db.commit()
        except Exception as e:
            logger.exception("ingestion failed doc=%s", document_id)
            await db.rollback()
            result = await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if doc:
                await _set_failed(db, doc, str(e))
