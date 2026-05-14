"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { getSession, streamChat, type ChatStreamEvent } from "@/lib/api";

const SESSION_STORAGE_KEY = "docuai.session_id";

// ===== Types =====

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export interface ToolCallTrace {
  id: string;
  tool: string;
  status: "calling" | "complete";
  resultCount?: number;
  citations: { citation: string; summary: string }[];
  documentsSearched: string[];
}

export type ChatStatus = "idle" | "thinking" | "searching" | "generating";

// ===== Context =====

interface ChatContextValue {
  sessionId: string | null;
  messages: ChatMessage[];
  status: ChatStatus;
  traces: ToolCallTrace[];
  error: string | null;
  send: (text: string) => Promise<void>;
  reset: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

// ===== Provider =====

export function ChatProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionIdState] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStatus>("idle");
  const [traces, setTraces] = useState<ToolCallTrace[]>([]);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Wrap setter so every sessionId update mirrors to localStorage. Pulled
  // through to applyStreamEvent below via setters.setSessionId.
  const setSessionId = useCallback((id: string | null) => {
    setSessionIdState(id);
    if (typeof window === "undefined") return;
    if (id) {
      window.localStorage.setItem(SESSION_STORAGE_KEY, id);
    } else {
      window.localStorage.removeItem(SESSION_STORAGE_KEY);
    }
  }, []);

  // Rehydrate from localStorage on mount: if there's a persisted sessionId,
  // try to fetch its messages and restore the conversation. A 404 means
  // the session was reaped (24h cleanup) or belongs to another IP — clear
  // the stale id and start fresh.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (!stored) return;

    let cancelled = false;
    (async () => {
      try {
        const session = await getSession(stored);
        if (cancelled) return;
        setSessionIdState(session.session_id);
        setMessages(
          session.messages.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
          })),
        );
      } catch {
        if (cancelled) return;
        // Session expired / unknown / cross-IP — drop it and let the next
        // send() create a fresh one.
        window.localStorage.removeItem(SESSION_STORAGE_KEY);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || status !== "idle") return;
      setError(null);

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: text.trim(),
      };
      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        userMsg,
        { id: assistantId, role: "assistant", content: "" },
      ]);
      setStatus("thinking");

      const abort = new AbortController();
      abortRef.current = abort;

      try {
        // Capture session id from the FIRST yielded event without depending
        // on the closure value (which would be stale).
        let currentSession = sessionId;

        for await (const evt of streamChat({
          message: text.trim(),
          sessionId: currentSession ?? undefined,
          signal: abort.signal,
        })) {
          applyStreamEvent(
            evt,
            assistantId,
            {
              setSessionId: (id) => {
                currentSession = id;
                setSessionId(id);
              },
              setStatus,
              setMessages,
              setTraces,
              setError,
            },
          );
        }
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setError((e as Error).message);
      } finally {
        abortRef.current = null;
        setStatus("idle");
      }
    },
    [sessionId, status],
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setSessionId(null);
    setMessages([]);
    setTraces([]);
    setStatus("idle");
    setError(null);
  }, []);

  return (
    <ChatContext.Provider
      value={{ sessionId, messages, status, traces, error, send, reset }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error("useChat must be used inside <ChatProvider>");
  }
  return ctx;
}

// ===== Event-handling helpers (kept out of the body for readability) =====

function applyStreamEvent(
  evt: ChatStreamEvent,
  assistantId: string,
  setters: {
    setSessionId: (id: string) => void;
    setStatus: (s: ChatStatus) => void;
    setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
    setTraces: React.Dispatch<React.SetStateAction<ToolCallTrace[]>>;
    setError: (e: string | null) => void;
  },
) {
  switch (evt.event) {
    case "session":
      setters.setSessionId(evt.data.session_id);
      break;
    case "status":
      setters.setStatus(evt.data.status);
      break;
    case "tool_call":
      setters.setTraces((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          tool: evt.data.tool,
          status: "calling",
          citations: [],
          documentsSearched: [],
        },
      ]);
      break;
    case "tool_result":
      setters.setTraces((prev) => {
        // Match the most recent pending trace for this tool, or append.
        const idx = [...prev].reverse().findIndex(
          (t) => t.tool === evt.data.tool && t.status === "calling",
        );
        if (idx === -1) {
          return [
            ...prev,
            {
              id: crypto.randomUUID(),
              tool: evt.data.tool,
              status: "complete",
              resultCount: evt.data.result_count,
              citations: evt.data.citations,
              documentsSearched: evt.data.documents_searched,
            },
          ];
        }
        const realIdx = prev.length - 1 - idx;
        const updated = [...prev];
        updated[realIdx] = {
          ...updated[realIdx],
          status: "complete",
          resultCount: evt.data.result_count,
          citations: evt.data.citations,
          documentsSearched: evt.data.documents_searched,
        };
        return updated;
      });
      break;
    case "messages":
      setters.setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: m.content + evt.data.content }
            : m,
        ),
      );
      break;
    case "error":
      setters.setError(evt.data.error);
      break;
    case "done":
      // no-op; the for-await loop ends and the finally block resets status.
      break;
  }
}
