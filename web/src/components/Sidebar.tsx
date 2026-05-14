"use client";

import { MessageSquarePlus } from "lucide-react";
import { useEffect, useRef } from "react";

function GithubMark({ size = 12 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.9.58.11.79-.25.79-.56v-2.17c-3.2.7-3.87-1.36-3.87-1.36-.52-1.33-1.27-1.68-1.27-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.76 2.68 1.25 3.34.96.1-.74.4-1.25.73-1.54-2.55-.29-5.23-1.27-5.23-5.66 0-1.25.45-2.27 1.18-3.07-.12-.29-.51-1.46.11-3.04 0 0 .96-.31 3.15 1.17a10.93 10.93 0 015.74 0c2.19-1.48 3.15-1.17 3.15-1.17.62 1.58.23 2.75.11 3.04.74.8 1.18 1.82 1.18 3.07 0 4.4-2.69 5.37-5.25 5.65.41.36.78 1.06.78 2.14v3.17c0 .31.21.68.79.56A11.5 11.5 0 0023.5 12C23.5 5.65 18.35.5 12 .5z" />
    </svg>
  );
}
import { Button } from "@/components/Button";
import { ConversationList } from "@/components/ConversationList";
import { DocumentList } from "@/components/DocumentList";
import { Logo } from "@/components/Logo";
import { UploadButton } from "@/components/UploadButton";
import { useChat } from "@/hooks/useChat";
import { useDocuments } from "@/hooks/useDocuments";
import { useSessions } from "@/hooks/useSessions";

export function Sidebar() {
  const { docs, loading, refresh, remove } = useDocuments();
  const { reset, sessionId, status } = useChat();
  const {
    sessions,
    loading: sessionsLoading,
    refresh: refreshSessions,
    remove: removeSession,
  } = useSessions();

  // Refresh the sidebar's conversation list whenever a chat finishes
  // streaming (status returns to "idle" after being non-idle), so a brand
  // new conversation appears immediately and existing titles update.
  const wasActive = useRef(false);
  useEffect(() => {
    if (status !== "idle") {
      wasActive.current = true;
      return;
    }
    if (wasActive.current) {
      wasActive.current = false;
      void refreshSessions();
    }
  }, [status, refreshSessions]);

  // Also refresh when the sessionId changes (covers initial rehydration
  // and the user-clicked "switch conversation" path).
  useEffect(() => {
    if (sessionId) void refreshSessions();
  }, [sessionId, refreshSessions]);

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center justify-between px-2 pt-1 pb-1">
        <Logo />
      </div>

      <div className="px-1">
        <UploadButton onUploaded={refresh} />
      </div>

      <div className="px-1">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start"
          onClick={reset}
        >
          <MessageSquarePlus size={14} />
          New conversation
        </Button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto">
        <div className="flex flex-col gap-0.5">
          <SectionHeader label="Your documents" />
          <DocumentList docs={docs} loading={loading} onDelete={remove} />
        </div>

        <div className="flex flex-col gap-0.5">
          <SectionHeader label="Conversations" />
          <ConversationList
            sessions={sessions}
            loading={sessionsLoading}
            onDelete={removeSession}
          />
        </div>
      </div>

      <div className="flex flex-col gap-2 px-2 py-2">
        <a
          href="https://github.com/moazzam-qureshi/agentic-rag-platform"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-[12.5px] text-fg-muted hover:text-fg"
        >
          <GithubMark size={12} />
          View source on GitHub
        </a>
        <div className="text-[11px] text-fg-faint leading-relaxed">
          Demo limits: 3 uploads/day, 20 pages/doc. Auto-deleted after 24h.
        </div>
      </div>
    </div>
  );
}

function SectionHeader({ label }: { label: string }) {
  return (
    <div className="px-2 pt-1 pb-1 text-[11px] font-medium uppercase tracking-wider text-fg-faint">
      {label}
    </div>
  );
}
