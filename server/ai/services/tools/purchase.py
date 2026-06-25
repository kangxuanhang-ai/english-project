# server/ai/services/tools/purchase.py
import json
import re
from typing import Optional
from langchain_core.tools import tool
from sqlalchemy import select

from app.database import async_session
from app.models.course import Course, CourseRecord
from app.services.pay import _find_pending_payment
from ai.services.conversation_recommend_cache import get_conversation_recommend


def _course_to_dict(course: Course, purchased: bool) -> dict:
    return {
        "id": course.id,
        "name": course.name,
        "value": course.value,
        "description": course.description,
        "teacher": course.teacher,
        "url": course.url,
        "price": f"{course.price:.2f}",
        "purchased": purchased,
    }


def _format_purchase_payload(block: dict) -> str:
    readable = block.get("message") or ""
    payload = json.dumps(block, ensure_ascii=False)
    return f"{readable}\n\n__PURCHASE_JSON__\n{payload}\n__END_PURCHASE_JSON__"


def _title_matches(name: str, query: str) -> bool:
    a = (name or "").lower().strip()
    b = (query or "").lower().strip()
    if not a or not b:
        return False
    return b in a or a in b


async def _is_purchased(db, user_id: str, course_id: str) -> bool:
    result = await db.execute(
        select(CourseRecord).where(
            CourseRecord.user_id == user_id,
            CourseRecord.course_id == course_id,
            CourseRecord.is_purchased.is_(True),
        )
    )
    return result.scalar_one_or_none() is not None


async def _load_course(db, course_id: str) -> Course | None:
    result = await db.execute(select(Course).where(Course.id == course_id))
    return result.scalar_one_or_none()


async def _resolve_course_by_recommend_entry(db, user_id: str, entry: dict) -> Course | None:
    course_id = entry.get("course_id")
    title = entry.get("title") or ""
    if course_id:
        course = await _load_course(db, course_id)
        if course:
            return course
    if title:
        result = await db.execute(
            select(Course).where(Course.name.ilike(f"%{title}%")).limit(5)
        )
        courses = result.scalars().all()
        for c in courses:
            if _title_matches(c.name, title):
                return c
        if len(courses) == 1:
            return courses[0]
    return None


def _parse_ordinal_index(text: str) -> int | None:
    """从「第二个 / 第2个」等话术解析 1-based 序号。"""
    compact = (text or "").replace(" ", "")
    m = re.search(r"第([1-3一二三四两])个", compact)
    if not m:
        return None
    token = m.group(1)
    mapping = {"1": 1, "2": 2, "3": 3, "一": 1, "二": 2, "两": 2, "三": 3, "四": 3}
    return mapping.get(token)


async def _resolve_by_index(
    db, user_id: str, conversation_id: str, index: int
) -> tuple[Course | None, str, list[str]]:
    block = await get_conversation_recommend(conversation_id)
    if not block or not block.get("courses"):
        return None, "当前对话还没有推荐课程，请先让我为你推荐课程。", []
    courses = block["courses"]
    titles = [c.get("title") or "" for c in courses]
    if index < 1 or index > len(courses):
        return None, f"推荐列表只有 {len(courses)} 门课，请选择 1 到 {len(courses)} 之间的序号。", titles
    entry = courses[index - 1]
    course = await _resolve_course_by_recommend_entry(db, user_id, entry)
    if not course:
        return None, "未能匹配到该推荐课程，请尝试说出完整课程名称。", titles
    return course, "", titles


async def _resolve_by_name(
    db, user_id: str, conversation_id: str, course_name: str
) -> tuple[Course | None, str]:
    block = await get_conversation_recommend(conversation_id)
    if block and block.get("courses"):
        for entry in block["courses"]:
            if _title_matches(entry.get("title") or "", course_name):
                course = await _resolve_course_by_recommend_entry(db, user_id, entry)
                if course:
                    return course, ""

    result = await db.execute(
        select(Course).where(Course.name.ilike(f"%{course_name.strip()}%")).limit(5)
    )
    matches = result.scalars().all()
    exact = [c for c in matches if _title_matches(c.name, course_name)]
    if len(exact) == 1:
        return exact[0], ""
    if len(exact) > 1:
        names = "、".join(c.name for c in exact[:3])
        return None, f"找到多门相似课程（{names}），请说得更具体一些。"
    if len(matches) == 1:
        return matches[0], ""
    if len(matches) > 1:
        names = "、".join(c.name for c in matches[:3])
        return None, f"找到多门相似课程（{names}），请说得更具体一些。"
    return None, f"没有找到与「{course_name}」匹配的课程。"


async def _build_purchase_block(user_id: str, course: Course) -> dict:
    async with async_session() as db:
        purchased = await _is_purchased(db, user_id, course.id)
        if purchased:
            return {
                "action": "already_owned",
                "message": f"你已经购买过「{course.name}」，可以直接去学习。",
                "course": _course_to_dict(course, True),
            }
        pending = await _find_pending_payment(db, user_id, course.id)
        if pending:
            return {
                "action": "resume_pay",
                "message": f"你有一笔「{course.name}」的待支付订单，可以继续完成支付。",
                "course": _course_to_dict(course, False),
            }
        return {
            "action": "confirm",
            "message": f"即将购买「{course.name}」（¥{course.price:.2f}），请确认。",
            "course": _course_to_dict(course, False),
        }


def make_course_purchase(user_id: str, conversation_id: str):
    """返回绑定了 user_id 与 conversation_id 的 course_purchase 工具"""

    @tool
    async def course_purchase(
        index: Optional[int] = None,
        course_name: Optional[str] = None,
    ) -> str:
        """帮用户购买课程。
        用户说「买第一个」→ index=1；「买第二个/第2个」→ index=2；「买第三个」→ index=3。
        说课程全名时用 course_name。不要用 course_name 传「第一个/第二个」等序号。"""
        if index is not None and course_name:
            block = {
                "action": "not_found",
                "message": "请只使用序号或课程名称其中一种方式指定要购买的课程。",
            }
            return _format_purchase_payload(block)

        if index is None and course_name:
            ordinal = _parse_ordinal_index(course_name)
            if ordinal is not None:
                index = ordinal
                course_name = None

        selected_index: int | None = None
        recommend_titles: list[str] = []

        async with async_session() as db:
            if index is not None:
                selected_index = index
                course, err, recommend_titles = await _resolve_by_index(
                    db, user_id, conversation_id, index
                )
            elif course_name:
                course, err = await _resolve_by_name(
                    db, user_id, conversation_id, course_name
                )
            else:
                block = {
                    "action": "not_found",
                    "message": "请告诉我要买第几个推荐课程，或说出课程名称。",
                }
                return _format_purchase_payload(block)

            if not course:
                block = {"action": "not_found", "message": err}
                return _format_purchase_payload(block)

        block = await _build_purchase_block(user_id, course)
        if selected_index is not None:
            block["selected_index"] = selected_index
        if recommend_titles:
            block["recommend_titles"] = recommend_titles
        return _format_purchase_payload(block)

    return course_purchase
