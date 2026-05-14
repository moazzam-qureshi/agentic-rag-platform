"use client";

import { Loader2, MessageSquare, Trash2 } from "lucide-react";
import { useState } from "react";
import { useChat } from "@/hooks/useChat";
import type { SessionListItem } from "@/lib/api";
import { cn } from "@/lib/cn";

interface ConversationListProps {
  sessions: SessionListItem[];
  loading: boolean;
  onDelete: (id: string) => Promise<void>;
}

export function ConversationList({
  sessions,
  loading,
  onDelete,
}: ConversationListProps) {
  const { sessionId, loadSession, reset } = useChat();

  if (loading && sessions.length === 0) {
    return (
      <div className="mx-1 mt-1 flex items-center gap-1.5 rounded-md px-2 py-2 text-[13px] text-fg-faint">
        <Loader2 size={14} className="animate-spin" />
        Loading…
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="mx-1 mt-1 rounded-md border border-dashed border-border-strong p-3 text-[13px] text-fg-muted">
        <div className="mb-1 flex items-center gap-1.5">
          <MessageSquare size={14} />
          No conversations yet
        </div>
        <div className="text-fg-faint">
          Ask a question to start one.
        </div>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-0.5">
      {sessions.map((s) => (
        <ConversationItem
          key={s.id}
          session={s}
          isActive={s.id === sessionId}
          onSelect={async () => {
            // No-op if it's already the active one.
            if (s.id === sessionId) return;
            await loadSession(s.id);
          }}
          onDelete={async () => {
            await onDelete(s.id);
            // If we just nuked the active conversation, return to a
            // fresh blank chat so the panel doesn't keep showing the
            // dead messages.
            if (s.id === sessionId) reset();
          }}
        />
      ))}
    </ul>
  );
}

function ConversationItem({
  session,
  isActive,
  onSelect,
  onDelete,
}: {
  session: SessionListItem;
  isActive: boolean;
  onSelect: () => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete(e: React.MouseEvent) {
    // Don't also fire the row-level click → loadSession.
    e.stopPropagation();
    setDeleting(true);
    try {
      await onDelete();
    } finally {
      setDeleting(false);
    }
  }

  const title = session.title?.trim() || "Untitled conversation";

  return (
    <li
      className={cn(
        "group mx-1 flex items-center gap-2 rounded-md px-2 py-1.5",
        "cursor-pointer hover-surface",
        isActive && "bg-[rgba(35,131,226,0.07)] hover:bg-[rgba(35,131,226,0.1)]",
      )}
      onClick={() => void onSelect()}
    >
      <MessageSquare
        size={13}
        className={cn(
          "mt-0.5 shrink-0",
          isActive ? "text-accent" : "text-fg-faint",
        )}
      />

      <div
        className={cn(
          "min-w-0 flex-1 truncate text-[13px]",
          isActive ? "text-fg" : "text-fg-muted",
        )}
        title={title}
      >
        {title}
      </div>

      <button
        onClick={handleDelete}
        disabled={deleting}
        title="Delete conversation"
        className="opacity-0 group-hover:opacity-100 text-fg-faint hover:text-[var(--color-status-error)] transition-opacity disabled:opacity-50"
      >
        {deleting ? (
          <Loader2 size={13} className="animate-spin" />
        ) : (
          <Trash2 size={13} />
        )}
      </button>
    </li>
  );
}
