from nanoid import generate
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.word_book import WordBook, WordBookRecord


def _word_to_item(word: WordBook, record: WordBookRecord) -> dict:
    return {
        "wordId": word.id,
        "word": word.word,
        "phonetic": word.phonetic,
        "definition": word.definition,
        "translation": word.translation,
        "pos": word.pos,
        "isMaster": record.is_master,
        "createdAt": record.created_at.isoformat() if record.created_at else None,
    }


async def list_my_words(
    db: AsyncSession,
    user_id: str,
    status: str,
    page: int,
    page_size: int,
) -> dict:
    """分页列出用户生词本。status: learning | mastered"""
    is_master = status == "mastered"
    filters = (
        WordBookRecord.user_id == user_id,
        WordBookRecord.is_master.is_(is_master),
    )

    count_result = await db.execute(
        select(func.count(WordBookRecord.id))
        .select_from(WordBookRecord)
        .where(*filters)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    rows = await db.execute(
        select(WordBookRecord, WordBook)
        .join(WordBook, WordBook.id == WordBookRecord.word_id)
        .where(*filters)
        .order_by(WordBookRecord.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = [_word_to_item(word, record) for record, word in rows.all()]
    return {"list": items, "total": total}


async def add_words(db: AsyncSession, user_id: str, words: list[str]) -> dict:
    """按单词字符串加入生词本（is_master=False）。"""
    cleaned = [w.lower().strip() for w in words if w and w.strip()]
    if not cleaned:
        return {"added": [], "skipped": [], "message": "未提供有效单词"}

    result = await db.execute(select(WordBook).where(WordBook.word.in_(cleaned)))
    entries = {entry.word: entry for entry in result.scalars().all()}

    added: list[str] = []
    skipped: list[str] = []

    for word in cleaned:
        entry = entries.get(word)
        if not entry:
            skipped.append(f"{word}: 词库中不存在")
            continue

        existing = await db.execute(
            select(WordBookRecord).where(
                WordBookRecord.user_id == user_id,
                WordBookRecord.word_id == entry.id,
            )
        )
        record = existing.scalar_one_or_none()
        if record:
            if record.is_master:
                skipped.append(f"{word}: 已掌握，无法加入复习")
            else:
                skipped.append(f"{word}: 已在复习中")
            continue

        db.add(
            WordBookRecord(
                id=generate(size=20),
                word_id=entry.id,
                user_id=user_id,
                is_master=False,
            )
        )
        added.append(word)

    if added:
        await db.commit()

    return {"added": added, "skipped": skipped}


async def mark_mastered(
    db: AsyncSession,
    user_id: str,
    *,
    word_ids: list[str] | None = None,
    words: list[str] | None = None,
) -> dict:
    """标记掌握：新建或从复习中升级，仅对新掌握词递增 word_number。"""
    target_ids: list[str] = list(word_ids or [])

    if words:
        cleaned = [w.lower().strip() for w in words if w and w.strip()]
        if cleaned:
            result = await db.execute(select(WordBook).where(WordBook.word.in_(cleaned)))
            target_ids.extend(entry.id for entry in result.scalars().all())

    target_ids = list(dict.fromkeys(target_ids))
    if not target_ids:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        return {"wordNumber": user.word_number if user else 0, "newlyMastered": 0}

    records_result = await db.execute(
        select(WordBookRecord).where(
            WordBookRecord.user_id == user_id,
            WordBookRecord.word_id.in_(target_ids),
        )
    )
    existing = {r.word_id: r for r in records_result.scalars().all()}

    newly_mastered = 0
    for word_id in target_ids:
        record = existing.get(word_id)
        if record is None:
            db.add(
                WordBookRecord(
                    id=generate(size=20),
                    word_id=word_id,
                    user_id=user_id,
                    is_master=True,
                )
            )
            newly_mastered += 1
        elif not record.is_master:
            record.is_master = True
            newly_mastered += 1

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user and newly_mastered:
        user.word_number += newly_mastered
        await db.flush()
        await db.commit()
        await db.refresh(user)
        return {"wordNumber": user.word_number, "newlyMastered": newly_mastered}

    if newly_mastered:
        await db.commit()

    return {
        "wordNumber": user.word_number if user else 0,
        "newlyMastered": newly_mastered,
    }


async def remove_word(db: AsyncSession, user_id: str, word_id: str) -> dict:
    """从生词本移除（仅 is_master=False）。"""
    result = await db.execute(
        select(WordBookRecord).where(
            WordBookRecord.user_id == user_id,
            WordBookRecord.word_id == word_id,
            WordBookRecord.is_master.is_(False),
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return {"removed": False, "message": "未找到可删除的复习中词条"}

    await db.delete(record)
    await db.commit()
    return {"removed": True}
