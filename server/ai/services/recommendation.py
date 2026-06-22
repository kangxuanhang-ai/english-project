"""AI 课程推荐与个性化学习计划服务。"""
import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.user import User
from app.models.word_book import WordBook, WordBookRecord
from app.models.course import Course, CourseRecord
from ai.services.llm import get_llm

logger = logging.getLogger(__name__)

_recommend_cache: dict[str, dict] = {}
CACHE_TTL = 24 * 60 * 60
VALID_COURSE_TYPES = {"gk", "zk", "gre", "toefl", "ielts", "cet6", "cet4", "ky"}

def get_default_recommendation() -> dict:
    """返回一份全新的默认推荐结果，避免共享可变对象。"""
    return {
        "courses": [
            {
                "course_id": None,
                "title": "大学英语四级单词",
                "reason": "CET4 是最基础的英语考试，适合所有学习者起步",
                "match_score": 1.0,
            }
        ],
        "daily_plan": {
            "new_words_per_day": 20,
            "review_frequency": "每3天复习一次",
            "estimated_completion": "约3个月",
        },
        "summary": "欢迎开始英语学习之旅！建议从 CET4 基础词汇开始，循序渐进。",
    }


async def _query_user_data(db: AsyncSession, user_id: str) -> dict:
    """查询用户学习数据，构建用户画像。"""
    # 查询用户基本信息
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {}

    # 查询各课程类型已掌握单词数量
    category_mastered: dict[str, int] = {}
    category_total: dict[str, int] = {}

    for course_type in VALID_COURSE_TYPES:
        # 该类别下已掌握的单词数
        mastered_result = await db.execute(
            select(func.count(WordBookRecord.id))
            .join(WordBook, WordBook.id == WordBookRecord.word_id)
            .where(
                WordBookRecord.user_id == user_id,
                WordBookRecord.is_master.is_(True),
                getattr(WordBook, course_type).is_(True),
            )
        )
        mastered_count = mastered_result.scalar() or 0
        category_mastered[course_type] = mastered_count

        # 该类别下的单词总数
        total_result = await db.execute(
            select(func.count(WordBook.id)).where(
                getattr(WordBook, course_type).is_(True)
            )
        )
        total_count = total_result.scalar() or 0
        category_total[course_type] = total_count

    # 查询已购买的课程
    purchased_result = await db.execute(
        select(Course)
        .join(CourseRecord, CourseRecord.course_id == Course.id)
        .where(
            CourseRecord.user_id == user_id,
            CourseRecord.is_purchased.is_(True),
        )
    )
    purchased_courses = purchased_result.scalars().all()

    # 查询所有可用课程
    all_courses_result = await db.execute(select(Course))
    all_courses = all_courses_result.scalars().all()

    return {
        "user": user,
        "category_mastered": category_mastered,
        "category_total": category_total,
        "purchased_courses": purchased_courses,
        "all_courses": all_courses,
    }


def _build_prompt(user_data: dict) -> str:
    """构建 LLM 提示词，包含用户画像和课程信息。"""
    user = user_data["user"]
    category_mastered = user_data["category_mastered"]
    category_total = user_data["category_total"]
    purchased_courses = user_data["purchased_courses"]
    all_courses = user_data["all_courses"]

    # 构建分类掌握率文本
    mastery_lines = []
    for course_type in VALID_COURSE_TYPES:
        mastered = category_mastered.get(course_type, 0)
        total = category_total.get(course_type, 0)
        rate = round(mastered / total * 100, 1) if total > 0 else 0
        mastery_lines.append(f"- {course_type}: 已掌握 {mastered}/{total} 词，掌握率 {rate}%")
    mastery_text = "\n".join(mastery_lines)

    # 构建已购课程文本
    purchased_ids = {c.id for c in purchased_courses}
    if purchased_courses:
        purchased_text = "、".join(c.name for c in purchased_courses)
    else:
        purchased_text = "暂无"

    # 构建全部课程列表文本（排除已购）
    course_lines = []
    for c in all_courses:
        purchased_tag = " [已购]" if c.id in purchased_ids else ""
        course_lines.append(
            f"- id={c.id}, 名称={c.name}, 类型={c.value}, "
            f"教师={c.teacher}, 价格={c.price}{purchased_tag}"
        )
    course_text = "\n".join(course_lines)

    return f"""你是一位专业的英语学习规划师。请根据以下用户数据，推荐最适合的课程并制定个性化学习计划。

## 用户基本信息
- 用户名：{user.name}
- 累计掌握单词数：{user.word_number}
- 连续学习天数：{user.day_number}

## 各类别词汇掌握情况
{mastery_text}

## 已购课程
{purchased_text}

## 可选课程列表
{course_text}

## 要求
请返回严格的 JSON 格式（不要包含任何其他文字），结构如下：
{{
    "courses": [
        {{
            "course_id": "课程ID（从可选课程列表中选，或 null）",
            "title": "课程名称",
            "reason": "推荐理由（简要说明为什么适合该用户）",
            "match_score": 0.95
        }}
    ],
    "daily_plan": {{
        "new_words_per_day": 20,
        "review_frequency": "每N天复习一次",
        "estimated_completion": "预计完成时间"
    }},
    "summary": "整体学习建议摘要（50字以内）"
}}

注意：
1. 优先推荐用户尚未购买且掌握率较低的课程类别
2. 已购课程如果掌握率不高，也可以推荐继续学习
3. 推荐 1-3 门课程，按匹配度从高到低排列
4. match_score 取值范围 0-1，根据用户当前水平和课程难度匹配程度打分
5. daily_plan 参数根据用户当前学习节奏合理建议"""


def _parse_llm_output(raw: str) -> dict:
    """解析 LLM 输出的 JSON，带回退策略。"""
    # 策略1：直接解析
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    # 策略2：从代码块中提取 JSON
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except (json.JSONDecodeError, TypeError):
            pass

    # 策略3：尝试找到第一个 { 和最后一个 } 之间的内容
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(raw[first_brace : last_brace + 1])
        except (json.JSONDecodeError, TypeError):
            pass

    # 所有策略失败，返回默认推荐
    logger.warning(f"Failed to parse LLM output, using default recommendation. Raw: {raw[:200]}")
    return get_default_recommendation()


def _get_cached(user_id: str) -> dict | None:
    """获取缓存的推荐结果。"""
    cached = _recommend_cache.get(user_id)
    if not cached:
        return None
    timestamp = cached.get("timestamp", 0)
    now = datetime.now(timezone.utc).timestamp()
    if now - timestamp > CACHE_TTL:
        del _recommend_cache[user_id]
        return None
    return cached.get("data")


def _set_cache(user_id: str, data: dict) -> None:
    """设置推荐结果缓存。"""
    _recommend_cache[user_id] = {
        "data": data,
        "timestamp": datetime.now(timezone.utc).timestamp(),
    }


def clear_cache(user_id: str) -> None:
    """清除指定用户的推荐缓存。"""
    _recommend_cache.pop(user_id, None)


async def get_recommendation(user_id: str, force: bool = False) -> dict:
    """
    获取用户课程推荐与个性化学习计划。

    主流程：检查缓存 -> 查询数据 -> 冷启动判断 -> 构建提示词 -> 调用 LLM -> 解析 -> 缓存 -> 返回。
    """
    # 检查缓存
    if not force:
        cached = _get_cached(user_id)
        if cached is not None:
            logger.info(f"Recommendation cache hit for user {user_id}")
            return cached

    try:
        async with async_session() as db:
            # 查询用户数据
            user_data = await _query_user_data(db, user_id)

            if not user_data:
                logger.info(f"User {user_id} not found, returning default recommendation")
                return get_default_recommendation()

            user = user_data["user"]

            # 冷启动判断：新用户没有学习记录时直接返回默认推荐
            if user.word_number == 0 and user.day_number == 0:
                logger.info(f"Cold start for user {user_id}, returning default recommendation")
                default = get_default_recommendation()
                _set_cache(user_id, default)
                return default

            # 构建提示词
            prompt = _build_prompt(user_data)

            # 调用 LLM
            model = get_llm(deep_think=False)
            response = await model.ainvoke(prompt)
            raw_output = response.content if hasattr(response, "content") else str(response)

            # 解析 LLM 输出
            result = _parse_llm_output(raw_output)

            # 确保基本字段存在（使用新副本，避免共享可变对象）
            defaults = get_default_recommendation()
            result.setdefault("courses", defaults["courses"])
            result.setdefault("daily_plan", defaults["daily_plan"])
            result.setdefault("summary", defaults["summary"])

            # 缓存结果
            _set_cache(user_id, result)
            logger.info(f"Recommendation generated and cached for user {user_id}")

            return result

    except Exception as e:
        logger.error(f"Failed to get recommendation for user {user_id}: {e}")
        return get_default_recommendation()
