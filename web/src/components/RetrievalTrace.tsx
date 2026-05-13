"use client";

import {
  Languages,
  Search,
  CheckCircle2,
  Loader2,
  FileText,
} from "lucide-react";
import { useChat, type ToolCallTrace } from "@/hooks/useChat";

const TOOL_LABELS: Record<string, string> = {
  translate_query: "Translate query",
  search: "Hybrid search",
};

const TOOL_DESCRIPTIONS: Record<string, string> = {
  translate_query:
    "Detects the query language and translates to English (the index language).",
  search:
    "BM25 + semantic (kNN) over page summaries. Returns full page content for answering.",
};

export function RetrievalTrace() {
  const { traces } = useChat();

  return (
    <div className="flex flex-col gap-3">
      <div className="px-1">
        <h3 className="font-display text-[15px] font-semibold tracking-tight text-fg">
          Retrieval trace
        </h3>
        <p className="mt-1 text-[12.5px] text-fg-faint">
          Live view of the agent&apos;s tool calls and the pages it cites.
        </p>
      </div>

      {traces.length === 0 ? (
        <div className="rounded-md border border-dashed border-border-strong p-3 text-[12.5px] text-fg-faint">
          Ask a question to see the agent&apos;s thinking here.
        </div>
      ) : (
        <ul className="flex flex-col gap-2">
          {traces.map((t) => (
            <TraceItem key={t.id} trace={t} />
          ))}
        </ul>
      )}
    </div>
  );
}

function TraceItem({ trace }: { trace: ToolCallTrace }) {
  const ToolIcon = trace.tool === "translate_query" ? Languages : Search;

  return (
    <li className="rounded-md border border-border bg-bg-elevated p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-[13px] font-medium text-fg">
          <ToolIcon size={13} className="text-accent" />
          {TOOL_LABELS[trace.tool] ?? trace.tool}
        </div>
        {trace.status === "calling" ? (
          <Loader2 size={12} className="animate-spin text-fg-faint" />
        ) : (
          <CheckCircle2
            size={12}
            className="text-[var(--color-status-success)]"
          />
        )}
      </div>

      <p className="mt-1 text-[12px] text-fg-faint leading-relaxed">
        {TOOL_DESCRIPTIONS[trace.tool] ?? ""}
      </p>

      {trace.status === "complete" && trace.tool === "search" ? (
        <div className="mt-2.5">
          <div className="text-[11.5px] text-fg-faint">
            {trace.resultCount ?? 0} result
            {trace.resultCount === 1 ? "" : "s"}
            {trace.documentsSearched.length > 0
              ? ` across ${trace.documentsSearched.length} doc${
                  trace.documentsSearched.length === 1 ? "" : "s"
                }`
              : null}
          </div>

          {trace.citations.length > 0 ? (
            <ul className="mt-1.5 flex flex-col gap-1">
              {trace.citations.slice(0, 5).map((c, i) => (
                <li
                  key={`${trace.id}-${i}`}
                  className="flex items-start gap-1.5 rounded-sm bg-bg-subtle px-2 py-1.5 text-[11.5px] text-fg-muted"
                >
                  <FileText size={11} className="mt-0.5 shrink-0 text-fg-faint" />
                  <div className="min-w-0">
                    <div className="truncate font-medium text-fg" title={c.citation}>
                      {c.citation}
                    </div>
                    {c.summary ? (
                      <div className="mt-0.5 line-clamp-2 text-fg-faint">
                        {c.summary}
                      </div>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}
