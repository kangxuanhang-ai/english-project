"""Phase 0 冒烟：word_lookup + mark_mastered 三态（需本地 DB）。"""
import asyncio

from app.database import async_session
from app.services.word_lookup import lookup_words
from app.services.my_words import add_words, list_my_words, mark_mastered, remove_word
from sqlalchemy import select
from app.models.user import User


async def main() -> None:
    async with async_session() as db:
        user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
        if not user:
            print("SKIP: no users in database")
            return
        uid = user.id
        print(f"user: {uid}")

        words = await lookup_words(db, ["abandon"])
        print("lookup:", words[0].get("word") or words[0])

        added = await add_words(db, uid, ["abandon"])
        print("add_words:", added)

        listed = await list_my_words(db, uid, "learning", 1, 10)
        print("learning count:", listed["total"])

        if listed["list"]:
            wid = listed["list"][0]["wordId"]
            m1 = await mark_mastered(db, uid, word_ids=[wid])
            print("mark 1:", m1)
            m2 = await mark_mastered(db, uid, word_ids=[wid])
            print("mark 2 (idempotent):", m2)

            listed2 = await list_my_words(db, uid, "mastered", 1, 10)
            print("mastered count:", listed2["total"])

        print("OK")


if __name__ == "__main__":
    asyncio.run(main())
