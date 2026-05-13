"""OpenSearch store — page-level hybrid retrieval (BM25 + kNN).

Reads side of the indexing pipeline. The worker writes pages here; the agent's
`search` tool reads them.

Combines:
- BM25 over `summary` field (English analyzer)
- kNN over `summary_embedding` (sentence-transformers/all-MiniLM-L6-v2, 384-dim)
- Weighted min-max normalization via OpenSearch search pipeline (70/30)

Returns `full_content` for the LLM to answer from, plus citation metadata.
"""

from functools import lru_cache
from typing import Any

import structlog
from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError
from sentence_transformers import SentenceTransformer

from api.config import settings

logger = structlog.get_logger(__name__)

_embedding_model: SentenceTransformer | None = None


def _get_embedding_model() -> SentenceTransformer:
    """Lazy-load the query embedding model (same one used at index time)."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("loading_embedding_model", model="all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",
        )
        logger.info("embedding_model_loaded")
    return _embedding_model


class PageSearchStore:
    """Read-side accessor for the page-level OpenSearch index."""

    def __init__(self) -> None:
        self.host = settings.opensearch_host
        self.port = settings.opensearch_port
        self.index_name = f"{settings.opensearch_index}_pages"
        self._client: OpenSearch | None = None

    def _get_client(self) -> OpenSearch:
        if self._client is None:
            self._client = OpenSearch(
                hosts=[{"host": self.host, "port": self.port}],
                http_compress=True,
                use_ssl=False,
                verify_certs=False,
                ssl_show_warn=False,
            )
            logger.info(
                "page_store_connected",
                host=self.host,
                port=self.port,
                index=self.index_name,
            )
        return self._client

    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """BM25 + kNN hybrid search on page summaries."""
        client = self._get_client()
        model = _get_embedding_model()

        query_embedding = model.encode(query, convert_to_tensor=False).tolist()

        hybrid_queries = [
            {
                "match": {
                    "summary": {
                        "query": query,
                        "analyzer": "english",
                    }
                }
            },
            {
                "knn": {
                    "summary_embedding": {
                        "vector": query_embedding,
                        "k": k * 2,
                    }
                }
            },
        ]

        search_body: dict[str, Any] = {
            "query": {"hybrid": {"queries": hybrid_queries}},
            "size": k,
            "_source": [
                "document_id",
                "filename",
                "page_number",
                "summary",
                "full_content",
            ],
        }

        if filters:
            filter_clause = self._build_filter_clause(filters)
            if filter_clause:
                search_body["query"]["hybrid"]["filter"] = {"bool": {"filter": filter_clause}}

        try:
            response = client.search(
                index=self.index_name,
                body=search_body,
                params={"search_pipeline": "page-hybrid-search-pipeline"},
            )
        except NotFoundError:
            logger.warning("page_index_not_found", index=self.index_name)
            return []
        except Exception as e:
            logger.error("page_hybrid_search_error", error=str(e))
            # Fallback to BM25 only on any hybrid-search failure
            return self.bm25_search(query, k, filters)

        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append(
                {
                    "summary": source.get("summary", ""),
                    "full_content": source.get("full_content", ""),
                    "page_number": source.get("page_number", 0),
                    "document_id": source.get("document_id", ""),
                    "filename": source.get("filename", ""),
                    "score": hit.get("_score", 0.0),
                }
            )

        logger.info(
            "page_hybrid_search_complete",
            query=query[:50],
            result_count=len(results),
        )

        return results

    def bm25_search(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """BM25-only fallback when hybrid search isn't available."""
        client = self._get_client()

        search_body: dict[str, Any] = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "summary": {
                                    "query": query,
                                    "analyzer": "english",
                                }
                            }
                        }
                    ]
                }
            },
            "size": k,
            "_source": [
                "document_id",
                "filename",
                "page_number",
                "summary",
                "full_content",
            ],
        }

        if filters:
            filter_clause = self._build_filter_clause(filters)
            if filter_clause:
                search_body["query"]["bool"]["filter"] = filter_clause

        try:
            response = client.search(index=self.index_name, body=search_body)
        except NotFoundError:
            logger.warning("page_index_not_found", index=self.index_name)
            return []

        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append(
                {
                    "summary": source.get("summary", ""),
                    "full_content": source.get("full_content", ""),
                    "page_number": source.get("page_number", 0),
                    "document_id": source.get("document_id", ""),
                    "filename": source.get("filename", ""),
                    "score": hit.get("_score", 0.0),
                }
            )

        logger.info(
            "page_bm25_search_complete",
            query=query[:50],
            result_count=len(results),
        )

        return results

    def _build_filter_clause(self, filters: dict | None) -> list[dict] | None:
        if not filters:
            return None

        filter_terms = []

        if "document_id" in filters:
            filter_terms.append({"term": {"document_id": filters["document_id"]}})

        if "filename" in filters:
            filter_terms.append({"term": {"filename": filters["filename"]}})

        if "file_type" in filters:
            filter_terms.append({"term": {"file_type": filters["file_type"]}})

        return filter_terms if filter_terms else None

    def get_page(self, filename: str, page_number: int) -> dict[str, Any] | None:
        """Fetch a single page by filename + page number."""
        client = self._get_client()

        search_body = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"filename": filename}},
                        {"term": {"page_number": page_number}},
                    ]
                }
            },
            "size": 1,
            "_source": True,
        }

        try:
            response = client.search(index=self.index_name, body=search_body)
            hits = response["hits"]["hits"]
            if hits:
                return hits[0]["_source"]
            return None
        except NotFoundError:
            return None

    def list_documents(self) -> list[dict[str, Any]]:
        """List all unique documents in the index."""
        client = self._get_client()

        search_body = {
            "size": 0,
            "aggs": {
                "documents": {
                    "terms": {"field": "document_id", "size": 10000},
                    "aggs": {
                        "filename": {"terms": {"field": "filename", "size": 1}},
                        "page_count": {"cardinality": {"field": "page_number"}},
                    },
                }
            },
        }

        try:
            response = client.search(index=self.index_name, body=search_body)
        except NotFoundError:
            return []

        documents = []
        for bucket in response["aggregations"]["documents"]["buckets"]:
            doc_id = bucket["key"]
            filename_buckets = bucket["filename"]["buckets"]
            filename = filename_buckets[0]["key"] if filename_buckets else ""
            page_count = bucket["page_count"]["value"]
            documents.append(
                {
                    "document_id": doc_id,
                    "filename": filename,
                    "page_count": int(page_count),
                }
            )

        return documents

    def delete_document(self, document_id: str) -> int:
        """Remove all pages for a document. Returns count deleted."""
        client = self._get_client()

        try:
            response = client.delete_by_query(
                index=self.index_name,
                body={"query": {"term": {"document_id": document_id}}},
                refresh=True,
            )
            deleted = response.get("deleted", 0)
            if deleted > 0:
                logger.info("pages_deleted", document_id=document_id, count=deleted)
            return deleted
        except NotFoundError:
            return 0

    def get_stats(self) -> dict[str, Any]:
        client = self._get_client()

        try:
            stats = client.indices.stats(index=self.index_name)
            count = stats["_all"]["primaries"]["docs"]["count"]
            return {"name": self.index_name, "count": count}
        except NotFoundError:
            return {"name": self.index_name, "count": 0}


@lru_cache(maxsize=1)
def get_page_store() -> PageSearchStore:
    """Process-wide singleton accessor."""
    return PageSearchStore()
