"use client";

import { Badge } from "@/components/Badge";
import { ChatThread } from "@/components/ChatThread";
import { Composer } from "@/components/Composer";
import { useChat } from "@/hooks/useChat";

export function ChatPanel() {
  const { messages, status, send } = useChat();
  const busy = status !== "idle";

  return (
    <div className="flex h-full flex-col">
      {/* Hero — visible until the first message arrives */}
      {messages.length === 0 ? (
        <header className="border-b border-border px-6 py-8">
          <div className="page-prose w-full">
            <Badge tone="info" className="mb-3">
              Beta
            </Badge>
            <h1 className="font-display text-3xl font-semibold tracking-tight text-fg">
              Ask anything about your documents.
            </h1>
            <p className="mt-3 text-[15px] leading-relaxed text-fg-muted">
              Upload a PDF, DOCX, or spreadsheet on the left. DocuAI reads
              every page with a vision model, builds a hybrid search index,
              and answers your questions with exact citations.
            </p>
          </div>
        </header>
      ) : null}

      <div className="flex-1 overflow-y-auto px-6 py-8">
        <ChatThread />
      </div>

      <div className="border-t border-border bg-bg px-6 py-4">
        <div className="page-prose w-full">
          <Composer onSend={send} busy={busy} />
          <p className="mt-2 px-1 text-[11.5px] text-fg-faint">
            DocuAI grounds every answer in your uploaded documents. Press Enter
            to send · Shift+Enter for a new line.
          </p>
        </div>
      </div>
    </div>
  );
}
