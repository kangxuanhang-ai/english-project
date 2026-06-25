"""清除 langchain 数据库中的聊天历史"""
import asyncio
import sys
sys.path.insert(0, ".")

from ai.services.llm import create_checkpoint

async def main():
    checkpointer = await create_checkpoint()
    user_id = input("输入用户 ID: ").strip()
    if not user_id:
        print("未输入用户 ID，跳过")
        return
    for role in ["normal", "master", "business", "qilinge", "xiaoman", "oral"]:
        thread_id = f"{user_id}-{role}"
        try:
            await checkpointer.adelete_thread({"configurable": {"thread_id": thread_id}})
            print(f"✓ 已清除: {thread_id}")
        except Exception as e:
            print(f"✗ {thread_id}: {e}")
    print("\n完成！请重新测试语法检查")

asyncio.run(main())
