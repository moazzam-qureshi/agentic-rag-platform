/**
 * Typed API client for the DocuAI FastAPI backend.
 *
 * In production (Coolify), web and api are reachable on the same domain
 * — the frontend hits relative URLs like `/api/upload` which Coolify
 * routes to the api container. In local dev, NEXT_PUBLIC_API_BASE_URL
 * points at http://localhost:8000.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

// ===== Types =====

export type DocumentStatus =
  | "pending"
  | "processing"
  | "indexed"
  | "failed"
  | "deleted";

export interface IngestionProgress {
  /** Pages whose VLM extraction has completed. */
  pages_done: number;
  /** Total pages detected in the document. 0 until the parser has opened it. */
  total_pages: number;
}

export interface DocumentRecord {
  id: string;
  filename: string;
  status: DocumentStatus;
  page_count: number;
  created_at: string;
  expires_at: string | null;
  error_message: string | null;
  /** Live ingestion progress merged in by the poller; absent on the
   *  initial /documents fetch. */
  progress?: IngestionProgress;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  page_count_estimate: number;
  status: DocumentStatus;
  message_id: string;
}

export interface ProcessingLogLine {
  level: "debug" | "info" | "warning" | "error";
  message: string;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface JobStatusResponse {
  document_id: string;
  filename: string;
  status: DocumentStatus;
  /** Final page count after indexing (0 while in progress). */
  page_count: number;
  error_message: string | null;
  /** Live progress derived from worker callbacks. */
  progress: IngestionProgress;
  logs: ProcessingLogLine[];
}

export type ChatStreamEvent =
  | { event: "session"; data: { session_id: string } }
  | { event: "status"; data: { status: "searching" | "generating" } }
  | { event: "tool_call"; data: { tool: string } }
  | {
      event: "tool_result";
      data: {
        tool: string;
        result_count: number;
        citations: { citation: string; summary: string }[];
        documents_searched: string[];
      };
    }
  | { event: "messages"; data: { content: string } }
  | { event: "done"; data: Record<string, never> }
  | { event: "error"; data: { error: string } };

// ===== Endpoints =====

export async function uploadDocument(
  file: File,
  turnstileToken: string,
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("turnstile_token", turnstileToken);

  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const detail = await safeError(res);
    throw new Error(detail);
  }

  return res.json();
}

export async function listDocuments(): Promise<DocumentRecord[]> {
  const res = await fetch(`${API_BASE}/documents`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await safeError(res));
  const body = (await res.json()) as { documents: DocumentRecord[] };
  return body.documents;
}

export async function deleteDocument(documentId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await safeError(res));
}

export async function getJobStatus(
  documentId: string,
): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/jobs/${documentId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await safeError(res));
  return res.json();
}

/**
 * Stream a chat response as parsed events. Yields each event as the
 * backend produces it.
 */
export async function* streamChat(args: {
  message: string;
  sessionId?: string;
  signal?: AbortSignal;
}): AsyncGenerator<ChatStreamEvent> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      message: args.message,
      session_id: args.sessionId,
    }),
    signal: args.signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(await safeError(res));
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // ndjson — one event per line
      let nlIdx: number;
      while ((nlIdx = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, nlIdx).trim();
        buffer = buffer.slice(nlIdx + 1);
        if (!line) continue;
        try {
          yield JSON.parse(line) as ChatStreamEvent;
        } catch (e) {
          console.warn("chat stream parse error", line, e);
        }
      }
    }

    // Flush remainder
    const tail = buffer.trim();
    if (tail) {
      try {
        yield JSON.parse(tail) as ChatStreamEvent;
      } catch {
        /* ignore */
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ===== Helpers =====

async function safeError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return (
      body.detail ||
      body.message ||
      body.error ||
      `${res.status} ${res.statusText}`
    );
  } catch {
    return `${res.status} ${res.statusText}`;
  }
}
