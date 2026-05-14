"use client";

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
            <h1 className="font-display text-3xl font-semibold tracking-tight text-fg">
              Ask anything across your documents.
            </h1>
            <p className="mt-3 text-[15px] leading-relaxed text-fg-muted">
              Upload one PDF or many. DocuAI reads every page with a vision
              model, builds a single hybrid search index across all of them,
              and answers your questions with exact citations — even when the
              evidence is spread across multiple files.
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
            DocuAI searches across every document you&rsquo;ve uploaded and
            cites the exact pages it pulled from. Press Enter to send ·
            Shift+Enter for a new line.
          </p>
        </div>
      </div>
    </div>
  );
}
