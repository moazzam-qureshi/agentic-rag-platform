"use client";

import {
  CheckCircle2,
  FileText,
  Loader2,
  AlertCircle,
  Trash2,
  Clock,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/Badge";
import type { DocumentRecord } from "@/lib/api";
import { cn } from "@/lib/cn";

interface DocumentListProps {
  docs: DocumentRecord[];
  loading: boolean;
  onDelete: (id: string) => Promise<void>;
}

export function DocumentList({ docs, loading, onDelete }: DocumentListProps) {
  if (loading && docs.length === 0) {
    return (
      <div className="mx-1 mt-1 flex items-center gap-1.5 rounded-md px-2 py-2 text-[13px] text-fg-faint">
        <Loader2 size={14} className="animate-spin" />
        Loading…
      </div>
    );
  }

  if (docs.length === 0) {
    return (
      <div className="mx-1 mt-1 rounded-md border border-dashed border-border-strong p-3 text-[13px] text-fg-muted">
        <div className="mb-1 flex items-center gap-1.5">
          <FileText size={14} />
          No documents yet
        </div>
        <div className="text-fg-faint">
          Upload one or more PDFs — DocuAI searches across all of them.
        </div>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-0.5">
      {docs.map((doc) => (
        <DocItem key={doc.id} doc={doc} onDelete={onDelete} />
      ))}
    </ul>
  );
}

function DocItem({
  doc,
  onDelete,
}: {
  doc: DocumentRecord;
  onDelete: (id: string) => Promise<void>;
}) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await onDelete(doc.id);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <li
      className={cn(
        "group mx-1 flex items-start gap-2 rounded-md px-2 py-1.5",
        "hover-surface",
      )}
    >
      <StatusIcon status={doc.status} />

      <div className="min-w-0 flex-1">
        <div className="truncate text-[13px] text-fg" title={doc.filename}>
          {doc.filename}
        </div>
        <div className="mt-0.5 flex items-center gap-1.5">
          <StatusBadge
            status={doc.status}
            pageCount={doc.page_count}
            progress={doc.progress}
          />
        </div>
        {doc.status === "processing" && doc.progress?.total_pages ? (
          <ProgressBar
            done={doc.progress.pages_done}
            total={doc.progress.total_pages}
          />
        ) : null}
        {doc.error_message ? (
          <div className="mt-1 truncate text-[11.5px] text-[var(--color-status-error)]">
            {doc.error_message}
          </div>
        ) : null}
      </div>

      <button
        onClick={handleDelete}
        disabled={deleting}
        title="Delete"
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

function StatusIcon({ status }: { status: DocumentRecord["status"] }) {
  switch (status) {
    case "pending":
      return <Clock size={14} className="mt-0.5 shrink-0 text-fg-faint" />;
    case "processing":
      return (
        <Loader2 size={14} className="mt-0.5 shrink-0 text-accent animate-spin" />
      );
    case "indexed":
      return (
        <CheckCircle2
          size={14}
          className="mt-0.5 shrink-0 text-[var(--color-status-success)]"
        />
      );
    case "failed":
      return (
        <AlertCircle
          size={14}
          className="mt-0.5 shrink-0 text-[var(--color-status-error)]"
        />
      );
    default:
      return <FileText size={14} className="mt-0.5 shrink-0 text-fg-faint" />;
  }
}

function StatusBadge({
  status,
  pageCount,
  progress,
}: {
  status: DocumentRecord["status"];
  pageCount: number;
  progress?: DocumentRecord["progress"];
}) {
  switch (status) {
    case "pending":
      return <Badge tone="neutral">queued</Badge>;
    case "processing":
      if (progress?.total_pages) {
        return (
          <Badge tone="info">
            indexing… {progress.pages_done} / {progress.total_pages}
          </Badge>
        );
      }
      return <Badge tone="info">indexing…</Badge>;
    case "indexed":
      return (
        <Badge tone="success">
          {pageCount} {pageCount === 1 ? "page" : "pages"}
        </Badge>
      );
    case "failed":
      return <Badge tone="error">failed</Badge>;
    case "deleted":
      return <Badge tone="neutral">deleted</Badge>;
    default:
      return null;
  }
}

function ProgressBar({ done, total }: { done: number; total: number }) {
  const pct = total === 0 ? 0 : Math.min(100, Math.round((done / total) * 100));
  return (
    <div
      className="mt-1.5 h-[3px] w-full overflow-hidden rounded-full bg-[var(--color-border)]"
      role="progressbar"
      aria-valuenow={done}
      aria-valuemin={0}
      aria-valuemax={total}
    >
      <div
        className="h-full bg-accent transition-[width] duration-200 ease-out"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
