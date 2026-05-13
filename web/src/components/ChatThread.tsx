"use client";

import { Search, Sparkles, Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { useChat } from "@/hooks/useChat";
import { cn } from "@/lib/cn";

export function ChatThread() {
  const { messages, status, error } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, status]);

  return (
    <div className="flex flex-col gap-6 page-prose w-full">
      {messages.length === 0 ? (
        <EmptyState />
      ) : (
        messages.map((m) => <MessageBubble key={m.id} message={m} />)
      )}

      {status !== "idle" && messages.length > 0 ? (
        <StatusLine status={status} />
      ) : null}

      {error ? (
        <div className="rounded-md bg-[rgba(212,76,71,0.08)] px-3 py-2 text-[13px] text-[var(--color-status-error)]">
          {error}
        </div>
      ) : null}

      <div ref={bottomRef} />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-lg border border-border bg-bg-elevated p-6">
      <div className="mb-2 flex items-center gap-2 text-fg-muted">
        <Sparkles size={16} className="text-accent" />
        <span className="text-sm font-medium">Try asking</span>
      </div>
      <ul className="space-y-1 text-[14.5px] text-fg-muted">
        <li>· What are the main topics covered in this document?</li>
        <li>· Summarize section 3 in three sentences.</li>
        <li>· List every defined term and quote its definition verbatim.</li>
      </ul>
    </div>
  );
}

function StatusLine({ status }: { status: "thinking" | "searching" | "generating" }) {
  const label = {
    thinking: "Thinking…",
    searching: "Searching your documents…",
    generating: "Writing the answer…",
  }[status];

  const Icon = status === "searching" ? Search : Sparkles;

  return (
    <div className="flex items-center gap-2 text-[13px] text-fg-muted">
      {status === "thinking" ? (
        <Loader2 size={13} className="animate-spin" />
      ) : (
        <Icon size={13} className="text-accent" />
      )}
      {label}
    </div>
  );
}

function MessageBubble({
  message,
}: {
  message: { role: "user" | "assistant"; content: string };
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-lg bg-bg-subtle px-3.5 py-2.5 text-[15px] leading-relaxed text-fg">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "prose-styles text-[15px] leading-relaxed text-fg",
        "[&_p]:my-3 first:[&_p]:mt-0",
        "[&_h1]:font-display [&_h1]:text-2xl [&_h1]:font-semibold [&_h1]:mt-6 [&_h1]:mb-3",
        "[&_h2]:font-display [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:mt-5 [&_h2]:mb-2",
        "[&_h3]:font-display [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:mt-4 [&_h3]:mb-2",
        "[&_strong]:font-semibold [&_strong]:text-fg",
        "[&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1 [&_ol]:list-decimal [&_ol]:pl-5",
        "[&_li]:my-0.5",
        "[&_table]:my-3 [&_table]:w-full [&_table]:border-collapse [&_table]:text-[14px]",
        "[&_th]:border [&_th]:border-border-strong [&_th]:bg-bg-subtle [&_th]:px-3 [&_th]:py-1.5 [&_th]:text-left [&_th]:font-medium",
        "[&_td]:border [&_td]:border-border [&_td]:px-3 [&_td]:py-1.5",
        "[&_code]:rounded [&_code]:bg-bg-subtle [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-[13.5px] [&_code]:font-mono",
        "[&_a]:text-accent [&_a]:underline-offset-2 hover:[&_a]:underline",
      )}
    >
      {message.content ? (
        <ReactMarkdown>{message.content}</ReactMarkdown>
      ) : (
        <span className="text-fg-faint">…</span>
      )}
    </div>
  );
}
