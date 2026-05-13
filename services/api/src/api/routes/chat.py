"""POST /chat — SSE-streamed agent response with retrieval-trace events."""

import json
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.agent.memory import PostgresMemory
from api.agent.rag_agent import get_agent
from api.db.session import get_async_session, get_db
from shared.guardrails.client_ip import get_client_ip

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """POST /chat payload."""

    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Stream the agent's response as newline-delimited JSON events.

    Event types:
    - session     {session_id}                          (one per stream)
    - status      {status: "searching"|"generating"}    (UI hints)
    - tool_call   {tool, args}                          (trace-panel)
    - tool_result {tool, summary, citations}            (trace-panel)
    - messages    {content: <token>}                    (assistant tokens)
    - done        {}                                    (terminal)
    - error       {error: <message>}                    (terminal on failure)
    """
    client_ip = get_client_ip(request)
    session_id = payload.session_id or str(uuid4())
    memory = PostgresMemory(db, session_id)

    # All DB work BEFORE the streaming response, so the Depends-injected
    # session is still valid. Inside generate(), use a fresh session.
    await memory.get_or_create_session(client_ip=client_ip)
    history = await memory.get_messages()
    await memory.add_message("user", payload.message)

    if not history:
        title = payload.message[:100] + "..." if len(payload.message) > 100 else payload.message
        await memory.update_session_title(title)

    await db.commit()

    logger.info(
        "chat_request",
        session_id=session_id,
        message_length=len(payload.message),
        client_ip=client_ip,
    )

    messages = history + [HumanMessage(content=payload.message)]

    async def generate():
        full_response = ""
        is_searching = False
        has_started_response = False
        # Capture tool-call chunks so we can emit them when the call resolves.
        pending_tool_calls: dict[str, dict] = {}

        try:
            yield (
                json.dumps(
                    {
                        "event": "session",
                        "data": {"session_id": session_id},
                    }
                )
                + "\n"
            )

            agent = get_agent()

            async for stream_mode, data in agent.astream(
                {"messages": messages},
                stream_mode=["messages", "updates"],
            ):
                if stream_mode == "updates":
                    # `updates` mode fires after each graph node. For the
                    # tools node we get the structured tool messages back,
                    # which is the only place we get the actual returned
                    # citations/content.
                    for node_name, node_state in data.items():
                        if node_name != "tools":
                            continue
                        tool_messages = node_state.get("messages", [])
                        for tool_msg in tool_messages:
                            tool_name = getattr(tool_msg, "name", "unknown")
                            raw_content = getattr(tool_msg, "content", "")
                            # Tool content comes back as JSON string from LangChain;
                            # parse for the retrieval-trace UI.
                            try:
                                parsed = (
                                    json.loads(raw_content)
                                    if isinstance(raw_content, str)
                                    else raw_content
                                )
                            except Exception:
                                parsed = {"raw": str(raw_content)[:500]}

                            # Reshape for the UI: it cares about citations
                            # and the doc names that were searched.
                            citations = []
                            if isinstance(parsed, dict):
                                for r in parsed.get("results", []) or []:
                                    if isinstance(r, dict) and "citation" in r:
                                        citations.append(
                                            {
                                                "citation": r["citation"],
                                                "summary": r.get("summary", ""),
                                            }
                                        )

                            yield (
                                json.dumps(
                                    {
                                        "event": "tool_result",
                                        "data": {
                                            "tool": tool_name,
                                            "result_count": (
                                                parsed.get("result_count", 0)
                                                if isinstance(parsed, dict)
                                                else 0
                                            ),
                                            "citations": citations[:10],
                                            "documents_searched": (
                                                parsed.get("documents_searched", [])
                                                if isinstance(parsed, dict)
                                                else []
                                            ),
                                        },
                                    }
                                )
                                + "\n"
                            )
                    continue

                # stream_mode == "messages"
                token, metadata = data

                # Skip tool-node messages here — handled in `updates` above.
                if metadata.get("langgraph_node") == "tools":
                    continue

                # Tool-call invocation: emit a `tool_call` event as soon as
                # the agent commits to invoking a tool.
                tool_call_chunks = getattr(token, "tool_call_chunks", None)
                if tool_call_chunks:
                    if not is_searching:
                        is_searching = True
                        yield (
                            json.dumps(
                                {
                                    "event": "status",
                                    "data": {"status": "searching"},
                                }
                            )
                            + "\n"
                        )

                    for chunk in tool_call_chunks:
                        idx = chunk.get("index")
                        if idx is None:
                            continue
                        entry = pending_tool_calls.setdefault(
                            idx,
                            {"name": "", "args": ""},
                        )
                        if chunk.get("name"):
                            entry["name"] = chunk["name"]
                        if chunk.get("args"):
                            entry["args"] += chunk["args"]

                        # When we have a name we can emit the tool_call event;
                        # args may keep streaming but the UI just needs the name.
                        if entry["name"] and not entry.get("emitted"):
                            entry["emitted"] = True
                            yield (
                                json.dumps(
                                    {
                                        "event": "tool_call",
                                        "data": {"tool": entry["name"]},
                                    }
                                )
                                + "\n"
                            )
                    continue

                # Actual assistant text — stream it.
                text_content = None
                if hasattr(token, "text") and token.text:
                    text_content = token.text
                elif hasattr(token, "content") and isinstance(token.content, str) and token.content:
                    text_content = token.content

                if text_content:
                    if not has_started_response and is_searching:
                        yield (
                            json.dumps(
                                {
                                    "event": "status",
                                    "data": {"status": "generating"},
                                }
                            )
                            + "\n"
                        )
                        has_started_response = True

                    full_response += text_content
                    yield (
                        json.dumps(
                            {
                                "event": "messages",
                                "data": {"content": text_content},
                            }
                        )
                        + "\n"
                    )

            yield (
                json.dumps(
                    {
                        "event": "done",
                        "data": {},
                    }
                )
                + "\n"
            )

            logger.info(
                "chat_response_complete",
                session_id=session_id,
                response_length=len(full_response),
            )

        except Exception as e:
            logger.error(
                "chat_error",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            yield (
                json.dumps(
                    {
                        "event": "error",
                        "data": {"error": str(e)},
                    }
                )
                + "\n"
            )

        # Persist the assistant message after streaming, in a fresh session
        # (the Depends() session lifecycle has already ended by here).
        if full_response:
            try:
                async with get_async_session() as save_db:
                    save_memory = PostgresMemory(save_db, session_id)
                    await save_memory.add_message("assistant", full_response)
                    await save_db.commit()
            except Exception as e:
                logger.error(
                    "failed_to_save_assistant_response",
                    session_id=session_id,
                    error=str(e),
                    exc_info=True,
                )

    return StreamingResponse(generate(), media_type="application/x-ndjson")
