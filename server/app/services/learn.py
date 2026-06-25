from nanoid import generate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, CourseRecord
from app.models.word_book import WordBook, WordBookRecord
from app.models.user import User

# 课程类型白名单（防止动态属性访问注入）
VALID_COURSE_TYPES = {"gk", "zk", "gre", "toefl", "ielts", "cet6", "cet4", "ky"}


async def get_word_list(db: AsyncSession, course_id: str, user_id: str) -> list:
    """
    获取课程单词列表（排除已掌握的）。
    对应 NestJS LearnService.getWordList。
    """
    # 验证用户已购买课程
    result = await db.execute(
        select(CourseRecord)
        .options(selectinload(CourseRecord.course))
        .where(
            CourseRecord.user_id == user_id,
            CourseRecord.course_id == course_id,
            CourseRecord.is_purchased.is_(True),
        )
        .join(CourseRecord.course)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError("非法请求")

    course_type = record.course.value  # gk, zk, etc.

    # 白名单校验课程类型
    if course_type not in VALID_COURSE_TYPES:
        raise ValueError("无效的课程类型")

    # 查询未掌握的单词
    # 需要排除已有 WordBookRecord 的单词
    subquery = (
        select(WordBookRecord.word_id)
        .where(WordBookRecord.user_id == user_id)
        .scalar_subquery()
    )

    stmt = (
        select(WordBook)
        .where(
            getattr(WordBook, course_type).is_(True),
            WordBook.id.notin_(subquery),
        )
        .order_by(WordBook.frq.desc())
        .limit(10)
    )

    words_result = await db.execute(stmt)
    words = words_result.scalars().all()

    return [
        {
            "id": w.id,
            "word": w.word,
            "phonetic": w.phonetic,
            "definition": w.definition,
            "translation": w.translation,
            "pos": w.pos,
            "collins": w.collins,
            "oxford": w.oxford,
            "tag": w.tag,
            "bnc": w.bnc,
            "frq": w.frq,
            "exchange": w.exchange,
        }
        for w in words
    ]


async def save_word_master(db: AsyncSession, word_ids: list[str], user_id: str) -> dict:
    """
    标记单词为已掌握。
    对应 NestJS LearnService.saveWordMaster。
    """
    # 过滤已标记的单词（防止重复标记导致 word_number 虚增）
    existing_result = await db.execute(
        select(WordBookRecord.word_id).where(
            WordBookRecord.user_id == user_id,
            WordBookRecord.word_id.in_(word_ids),
        )
    )
    existing_word_ids = {row[0] for row in existing_result.all()}
    new_word_ids = [wid for wid in word_ids if wid not in existing_word_ids]

    if not new_word_ids:
        # 所有单词都已标记，直接返回当前数量
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        return {"wordNumber": user.word_number if user else 0}

    # 批量创建 WordBookRecord（仅新单词）
    for word_id in new_word_ids:
        record = WordBookRecord(
            id=generate(size=20),
            word_id=word_id,
            user_id=user_id,
            is_master=True,
        )
        db.add(record)

    await db.flush()

    # 更新用户单词数量（仅新增数量）
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.word_number += len(new_word_ids)
        await db.flush()
        await db.commit()
        await db.refresh(user)
        return {"wordNumber": user.word_number}

    await db.commit()
    return {"wordNumber": 0}
