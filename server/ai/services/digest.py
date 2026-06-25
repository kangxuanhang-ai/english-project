import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from langgraph.prebuilt import create_react_agent
from markdown2 import markdown

from app.database import async_session
from app.models.user import User
from app.models.word_book import WordBook, WordBookRecord
from ai.services.llm import get_llm
from shared.email_client import send_email

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def handle_email_digest():
    """
    定时任务：扫描用户，生成 AI 报告，延迟发送邮件。
    对应 NestJS DigestService.handleEmailDigest。
    """
    logger.info("定时任务执行了")

    # 在循环外创建 LLM 实例（避免重复创建 HTTP 连接）
    model = get_llm()
    agent = create_react_agent(model=model, tools=[])

    async with async_session() as db:
        # 筛选高质量用户
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        user_result = await db.execute(
            select(User).where(
                User.is_timing_task.is_(True),
                User.timing_task_time != "",
                User.email.isnot(None),
                User.word_book_records.any(
                    WordBookRecord.created_at >= today_start,
                    WordBookRecord.created_at < tomorrow_start,
                ),
            )
        )
        users = user_result.scalars().all()

        for user in users:
            # 查询用户今日单词记录
            records_result = await db.execute(
                select(WordBookRecord)
                .where(
                    WordBookRecord.user_id == user.id,
                    WordBookRecord.created_at >= today_start,
                    WordBookRecord.created_at < tomorrow_start,
                )
            )
            records = records_result.scalars().all()

            if not records:
                continue

            # 查询今日学习的具体单词
            words_result = await db.execute(
                select(WordBook.word)
                .join(WordBookRecord, WordBookRecord.word_id == WordBook.id)
                .where(
                    WordBookRecord.user_id == user.id,
                    WordBookRecord.created_at >= today_start,
                    WordBookRecord.created_at < tomorrow_start,
                )
                .limit(50)
            )
            today_words = [row[0] for row in words_result.all()]
            words_text = ", ".join(today_words) if today_words else "无"

            # 生成报告
            word_count = user.word_number
            report_prompt = f"用户 {user.name} 今日学习了 {len(records)} 个单词：{words_text}，累计掌握 {word_count} 个单词。请生成一份简短的单词记忆报告。"

            try:
                ai_result = await agent.ainvoke(
                    {"messages": [{"role": "user", "content": report_prompt}]}
                )
                content = ai_result["messages"][-1].content
            except Exception as e:
                logger.error(f"AI report generation failed: {e}")
                continue

            if content:
                html = markdown(content)

                # 计算延迟发送时间
                try:
                    hour, minute, second = map(int, user.timing_task_time.split(":"))
                    target = datetime.now().replace(
                        hour=hour, minute=minute, second=second, microsecond=0
                    )
                    delay = (target - datetime.now()).total_seconds()
                    if delay < 0:
                        delay += 86400  # 明天那个时间
                except ValueError:
                    delay = 0

                # 延迟发送邮件
                if delay > 0:
                    scheduler.add_job(
                        send_email,
                        "date",
                        run_date=datetime.now() + timedelta(seconds=delay),
                        args=[user.email, "单词记忆报告", html],
                    )
                else:
                    await send_email(user.email, "单词记忆报告", html)


def start_scheduler():
    """启动定时任务调度器"""
    scheduler.add_job(
        handle_email_digest,
        CronTrigger(hour=0, minute=0, second=0),  # 每天 00:00:00
        id="daily_digest",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started: daily digest at 00:00:00")
