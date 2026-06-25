"""发送一封测试邮件，验证 SMTP 配置。用法: uv run python scripts/test_email.py recipient@example.com"""

import asyncio
import sys

from shared.email_client import send_email


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/test_email.py <to_email>")
        sys.exit(1)
    to = sys.argv[1]
    ok = await send_email(
        to,
        "English 平台邮件测试",
        "<p>如果你收到这封邮件，说明 SMTP 配置正确。</p>",
    )
    if ok:
        print(f"已发送至 {to}")
    else:
        print("发送失败，请检查 EMAIL_* 配置与服务端日志")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
