import logging
import os

from ai.config import ai_settings

logger = logging.getLogger(__name__)


def configure_langsmith_tracing() -> None:
    """仅当 API key 存在时启用 LangSmith tracing；失败不抛异常。"""
    key = (ai_settings.langchain_api_key or os.getenv("LANGCHAIN_API_KEY") or "").strip()
    if not key:
        logger.info("LangSmith tracing disabled: LANGCHAIN_API_KEY not set")
        return
    os.environ.setdefault("LANGCHAIN_API_KEY", key)
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    project = (ai_settings.langchain_project or "english-chat").strip()
    os.environ.setdefault("LANGCHAIN_PROJECT", project)
    logger.info("LangSmith tracing enabled for project=%s", project)
