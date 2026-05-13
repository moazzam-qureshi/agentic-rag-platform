import { FileText, MessageSquare, Sparkles } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Badge } from "@/components/Badge";
import { Logo } from "@/components/Logo";

/**
 * Placeholder home page for Phase 4 (design-system check).
 * Phase 5 replaces sidebar/main/rightRail with the real upload + chat flows.
 */
export default function HomePage() {
  return (
    <AppShell
      sidebar={<SidebarPlaceholder />}
      main={<MainPlaceholder />}
      rightRail={<RightRailPlaceholder />}
    />
  );
}

function SidebarPlaceholder() {
  return (
    <div className="flex flex-col gap-4">
      <div className="px-2 pt-1 pb-2">
        <Logo />
      </div>

      <div className="flex flex-col gap-0.5">
        <SidebarHeader label="Your documents" />
        <SidebarEmptyState />
      </div>

      <div className="mt-auto px-2 py-2 text-[12px] text-fg-faint">
        Demo limits: 3 uploads/day, 20 pages/doc. Auto-deleted after 24h.
      </div>
    </div>
  );
}

function SidebarHeader({ label }: { label: string }) {
  return (
    <div className="px-2 pt-1 pb-1 text-[11px] font-medium uppercase tracking-wider text-fg-faint">
      {label}
    </div>
  );
}

function SidebarEmptyState() {
  return (
    <div className="mx-1 mt-1 rounded-md border border-dashed border-border-strong p-3 text-[13px] text-fg-muted">
      <div className="mb-1 flex items-center gap-1.5">
        <FileText size={14} />
        No documents yet
      </div>
      <div className="text-fg-faint">
        Upload a PDF, DOCX, or spreadsheet on the right to get started.
      </div>
    </div>
  );
}

function MainPlaceholder() {
  return (
    <div className="page-prose px-6 py-12 flex flex-col gap-6">
      <div>
        <Badge tone="info" className="mb-3">
          <Sparkles size={11} />
          Demo
        </Badge>
        <h1 className="font-display text-4xl font-semibold tracking-tight text-fg">
          Ask anything about your documents.
        </h1>
        <p className="mt-3 text-fg-muted text-[15px] leading-relaxed">
          Upload a PDF, DOCX, or spreadsheet and DocuAI will read every page
          with a vision model, build a hybrid search index, and answer your
          questions with exact citations.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-bg-elevated p-6">
        <div className="flex items-center gap-2 text-fg-muted">
          <MessageSquare size={16} />
          <span className="text-sm">
            Chat will appear here once Phase 5 wires up the upload + chat flows.
          </span>
        </div>
      </div>
    </div>
  );
}

function RightRailPlaceholder() {
  return (
    <div className="flex flex-col gap-4">
      <div className="px-1">
        <h3 className="font-display text-[15px] font-semibold tracking-tight text-fg">
          Retrieval trace
        </h3>
        <p className="mt-1 text-[12.5px] text-fg-faint">
          Live view of the agent&apos;s tool calls and retrieved citations.
        </p>
      </div>

      <div className="rounded-md border border-dashed border-border-strong p-3 text-[12.5px] text-fg-faint">
        Waiting for the first question…
      </div>
    </div>
  );
}
