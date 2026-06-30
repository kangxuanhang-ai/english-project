from dataclasses import dataclass

from langchain.agents.middleware import ModelRequest, dynamic_prompt


@dataclass
class ChatContext:
    """每请求传入 create_agent astream 的 runtime context。"""

    role: str = "normal"
    base_prompt: str = ""
    search_block: str = ""
    progress_block: str = ""
    external_mcp_block: str = ""
    wordbook_block: str = ""


@dynamic_prompt
def chat_dynamic_prompt(request: ModelRequest) -> str:
    ctx: ChatContext | None = request.runtime.context  # type: ignore[assignment]
    if ctx is None:
        return "You are a helpful assistant."
    parts = [ctx.base_prompt, ctx.search_block, ctx.progress_block, ctx.external_mcp_block, ctx.wordbook_block]
    return "".join(p for p in parts if p)
