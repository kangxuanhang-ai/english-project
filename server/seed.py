"""从 NestJS seed.ts 迁移过来的数据初始化脚本。
运行方式: cd server && uv run python seed.py

词库 CSV：默认 server/data/ecdict.sample.csv（演示用少量词条）；
完整词库可通过环境变量 ECDICT_CSV_PATH 指向 ecdict.csv。
"""

import asyncio
import csv
import sys
import os

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from nanoid import generate
from sqlalchemy import select

from app.database import async_session
from app.models.course import Course
from app.models.user import User
from app.models.word_book import WordBook

# 管理员账号（登录密码明文 admin123，前端 MD5 后提交）
ADMIN_PHONE = "13800000000"
ADMIN_PASSWORD_HASH = "$2b$12$.P/JH06U4sdoAFQ4AiSXXOSJSmTfWXOlgKu0TnAbuoocdxwrDI9d6"

# === 课程数据（来自 seed.ts）===
# 托福/雅思价格为答辩演示用异常高价，演示时请勿发起真实支付。
COURSES = [
    {
        "name": "高考单词",
        "value": "gk",
        "description": "覆盖高考大纲核心词汇，按考频与题型分类，助力考前冲刺提分。",
        "teacher": "小余同学",
        "url": "/course/gk.png",
        "price": 100,
    },
    {
        "name": "中考单词",
        "value": "zk",
        "description": "紧扣中考考纲，初中三年词汇一站式掌握，打好英语基础。",
        "teacher": "小满zs",
        "url": "/course/zk.png",
        "price": 35,
    },
    {
        "name": "GRE单词",
        "value": "gre",
        "description": "GRE 核心词汇与同反义词拓展，适合留学备考与高阶阅读。",
        "teacher": "初心哥",
        "url": "/course/gre.png",
        "price": 80,
    },
    {
        "name": "托福词汇",
        "value": "toefl",
        "description": "托福听说读写高频词 + 学术场景词汇，提升备考效率。",
        "teacher": "枫竹",
        "url": "/course/toefl.png",
        "price": 80000,
    },  # 演示价，勿真实支付
    {
        "name": "雅思词汇",
        "value": "ielts",
        "description": "雅思考试常考词汇与同义替换，兼顾移民与留学需求。",
        "teacher": "ouka",
        "url": "/course/ielts.png",
        "price": 7000,
    },  # 演示价，答辩慎用
    {
        "name": "大学英语六级单词",
        "value": "cet6",
        "description": "六级大纲词汇与真题高频词，配合阅读与写作场景记忆。",
        "teacher": "章政",
        "url": "/course/cet6.png",
        "price": 5,
    },
    {
        "name": "大学英语四级单词",
        "value": "cet4",
        "description": "四级核心词汇与考点搭配，适合在校生系统备考。",
        "teacher": "小余同学",
        "url": "/course/cet4.png",
        "price": 8,
    },
    {
        "name": "考研单词",
        "value": "ky",
        "description": "考研英语一/二通用词汇，结合真题与长难句场景记忆。",
        "teacher": "远方",
        "url": "/course/ky.png",
        "price": 9.99,
    },
]

_DEFAULT_CSV = os.path.join(os.path.dirname(__file__), "data", "ecdict.sample.csv")
CSV_PATH = os.environ.get("ECDICT_CSV_PATH", _DEFAULT_CSV)
BATCH_SIZE = 2000


def parse_tag_to_boolean(tag_value: str) -> dict:
    tags = tag_value.split() if tag_value else []
    return {
        "zk": "zk" in tags,
        "gk": "gk" in tags,
        "cet4": "cet4" in tags,
        "cet6": "cet6" in tags,
        "ky": "ky" in tags,
        "toefl": "toefl" in tags,
        "ielts": "ielts" in tags,
        "gre": "gre" in tags,
    }


async def seed_courses(db):
    """插入课程数据"""
    existing = await db.execute(select(Course.id).limit(1))
    if existing.scalar():
        print("课程表已有数据，跳过。")
        return

    for item in COURSES:
        course = Course(
            id=generate(size=20),
            name=item["name"],
            value=item["value"],
            description=item["description"],
            teacher=item["teacher"],
            url=item["url"],
            price=item["price"],
        )
        db.add(course)
    await db.commit()
    print(f"课程插入完成，共 {len(COURSES)} 条。")


async def seed_word_book(db):
    """从 CSV 插入词书数据"""
    existing = await db.execute(select(WordBook.id).limit(1))
    if existing.scalar():
        print("词书表已有数据，跳过。")
        return

    if not os.path.exists(CSV_PATH):
        print(f"错误: 词库 CSV 不存在: {CSV_PATH}", file=sys.stderr)
        print(
            "请放置 ecdict.csv 或设置 ECDICT_CSV_PATH，或使用内置 server/data/ecdict.sample.csv。",
            file=sys.stderr,
        )
        sys.exit(1)

    total = 0
    batch = []

    with open(CSV_PATH, "r", encoding="gbk", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            boolean_fields = parse_tag_to_boolean(row.get("tag", ""))
            batch.append(
                {
                    "id": generate(size=20),
                    "word": row.get("word", ""),
                    "phonetic": row.get("phonetic") or None,
                    "definition": row.get("definition") or None,
                    "translation": row.get("translation") or None,
                    "pos": row.get("pos") or None,
                    "collins": row.get("collins") or None,
                    "oxford": row.get("oxford") or None,
                    "tag": row.get("tag") or None,
                    "bnc": row.get("bnc") or None,
                    "frq": row.get("frq") or None,
                    "exchange": row.get("exchange") or None,
                    **boolean_fields,
                }
            )

            if len(batch) >= BATCH_SIZE:
                db.add_all([WordBook(**item) for item in batch])
                await db.commit()
                total += len(batch)
                print(f"已插入 {total} 条词汇...")
                batch.clear()

    if batch:
        db.add_all([WordBook(**item) for item in batch])
        await db.commit()
        total += len(batch)

    print(f"词书插入完成，共 {total} 条。")


async def seed_admin(db):
    """预置或提升管理员账号"""
    result = await db.execute(select(User).where(User.phone == ADMIN_PHONE))
    user = result.scalar_one_or_none()
    if user:
        if user.role != "admin":
            user.role = "admin"
            await db.commit()
            print(f"已将现有用户 {ADMIN_PHONE} 提升为管理员。")
        else:
            print("管理员账号已存在，跳过。")
        return

    admin = User(
        id=generate(size=20),
        name="管理员",
        phone=ADMIN_PHONE,
        email=None,
        password=ADMIN_PASSWORD_HASH,
        role="admin",
    )
    db.add(admin)
    await db.commit()
    print(f"管理员账号已创建：手机号 {ADMIN_PHONE}，初始密码 admin123")


async def main():
    try:
        async with async_session() as db:
            await seed_admin(db)
            await seed_courses(db)
            await seed_word_book(db)
    except Exception as e:
        print(f"Seed 失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
