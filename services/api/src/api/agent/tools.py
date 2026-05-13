"""Tools the RAG agent can call: translate_query, search."""

from typing import Any

import structlog
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from api.config import settings
from api.db.opensearch_store import get_page_store

logger = structlog.get_logger(__name__)


@tool
def translate_query(
    text: str,
    source_language: str = "auto",
    target_language: str = "en",
) -> dict[str, Any]:
    """
    Translate a user query into English before searching the knowledge base.

    Use this tool FIRST whenever the user's question is not in English. The
    knowledge base is indexed in English, so queries must be translated before
    searching.

    Args:
        text: The text to translate.
        source_language: Source language code ("auto" by default).
        target_language: Target language code ("en" by default).

    Returns:
        Dict with the original and translated text plus detected language.
    """
    model = ChatOpenAI(
        model=settings.openrouter_chat_model,
        temperature=0,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        max_tokens=settings.llm_max_tokens_default,
    )

    messages = [
        {
            "role": "system",
            "content": (
                f"Translate the following text to {target_language}.\n\n"
                "Rules:\n"
                "- Preserve product codes, model numbers, and technical terms exactly "
                "as-is (e.g., ARTX-MI, TYPE-A, ARGS-LI).\n"
                "- Only translate natural language parts.\n"
                "- Return ONLY the translation, nothing else.\n"
                f"- If text is already in {target_language}, return it unchanged."
            ),
        },
        {"role": "user", "content": text},
    ]

    response = model.invoke(messages)
    translated = response.text.strip()

    logger.info(
        "query_translated",
        original=text[:100],
        translated=translated[:100],
        source_lang=source_language,
        target_lang=target_language,
    )

    return {
        "original": text,
        "translated": translated,
        "source_language": source_language,
        "target_language": target_language,
    }


@tool
def search(keywords: str, num_results: int = 10) -> dict[str, Any]:
    """
    Search the knowledge base using hybrid retrieval (BM25 + semantic).

    IMPORTANT: pass keywords, not full sentences.

    Hybrid search combines:
    - BM25: exact keyword matching for product codes and specific terms.
    - Semantic: vector similarity for synonyms and paraphrases.

    Examples:
    - User: "What are the features of ARTX-LID (TYPE-B)?"
      → search(keywords="ARTX-LID TYPE-B features")
    - User: "Tell me about the company's warranty policy"
      → search(keywords="warranty policy")
    - User: "What certifications does the product have?"
      → search(keywords="certifications standards compliance")

    Args:
        keywords: Space-separated keywords. Include entity names, section
                  types, and relevant terms.
        num_results: Number of results to return (1-15, default 10).

    Returns:
        Dict with retrieved page snippets and citation metadata.
    """
    num_results = min(max(num_results, 1), 15)

    # Strip parentheses for cleaner matching
    clean_keywords = keywords.replace("(", "").replace(")", "")

    logger.info(
        "hybrid_search",
        keywords=keywords,
        clean_keywords=clean_keywords,
        num_results=num_results,
    )

    store = get_page_store()

    try:
        results = store.hybrid_search(query=clean_keywords, k=num_results)
    except Exception as e:
        logger.warning("hybrid_search_failed_fallback_to_bm25", error=str(e))
        results = store.bm25_search(query=clean_keywords, k=num_results)

    if not results:
        return {
            "results": [],
            "result_count": 0,
            "message": "No results found. Try different keywords.",
        }

    formatted_results = []
    for r in results:
        formatted_results.append(
            {
                "content": r["full_content"],
                "citation": f"{r['filename']}, Page {r['page_number']}",
                "summary": r["summary"],
            }
        )

    documents = list({r["filename"] for r in results})

    logger.info(
        "page_search_complete",
        keywords=keywords,
        result_count=len(results),
        documents=documents,
    )

    return {
        "result_count": len(formatted_results),
        "results": formatted_results,
        "documents_searched": documents,
    }
