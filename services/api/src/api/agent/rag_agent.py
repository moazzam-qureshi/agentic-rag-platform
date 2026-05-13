"""RAG agent — LangGraph-based, with `translate_query` and `search` tools."""

from typing import Any

import structlog
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from api.agent.prompts import RAG_SYSTEM_PROMPT
from api.agent.tools import search, translate_query
from api.config import settings

logger = structlog.get_logger(__name__)

# Single agent cached process-wide. The model is pinned via config, so there's
# no need for the runtime-model-switching cache the reference project had.
_agent: Any | None = None


def clear_agent_cache() -> None:
    """Drop the cached agent — used if model config changes in dev."""
    global _agent
    _agent = None
    logger.info("agent_cache_cleared")


def _create_llm() -> ChatOpenAI:
    logger.info("creating_llm", model=settings.openai_model)
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=0,
        api_key=settings.openai_api_key,
        streaming=True,
        max_tokens=settings.llm_max_tokens_default,
    )


def get_agent():
    """Build and cache the RAG agent."""
    global _agent

    if _agent is not None:
        return _agent

    logger.info("creating_rag_agent", model=settings.openai_model)

    tools = [translate_query, search]

    _agent = create_agent(
        model=_create_llm(),
        tools=tools,
        system_prompt=RAG_SYSTEM_PROMPT,
    )

    logger.info(
        "rag_agent_created",
        model=settings.openai_model,
        tools=[t.name for t in tools],
    )

    return _agent
