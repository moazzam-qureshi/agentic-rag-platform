"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Three-pane Notion-style layout:
 *   ┌──────────┬─────────────────────────┬─────────────┐
 *   │ Sidebar  │ Main                    │ Right rail  │
 *   │  (260px) │ (flex-1)                │  (340px)    │
 *   └──────────┴─────────────────────────┴─────────────┘
 *
 * On mobile (< md) the rails collapse and only the main pane is visible.
 * The sidebar bg is slightly tinted (var(--bg-subtle)) — no hard borders.
 */
export function AppShell({
  sidebar,
  main,
  rightRail,
}: {
  sidebar: ReactNode;
  main: ReactNode;
  rightRail?: ReactNode;
}) {
  return (
    <div className="grid h-dvh w-full grid-cols-1 md:grid-cols-[260px_minmax(0,1fr)] lg:grid-cols-[260px_minmax(0,1fr)_340px]">
      {/* Sidebar */}
      <aside
        className={cn(
          "hidden md:flex md:flex-col",
          "h-dvh overflow-y-auto",
          "bg-bg-subtle",
          "px-3 py-4",
        )}
      >
        {sidebar}
      </aside>

      {/* Main */}
      <main className="h-dvh overflow-y-auto flex flex-col">{main}</main>

      {/* Right rail (optional) */}
      {rightRail ? (
        <aside
          className={cn(
            "hidden lg:flex lg:flex-col",
            "h-dvh overflow-y-auto",
            "bg-bg-elevated border-l border-border",
            "px-4 py-4",
          )}
        >
          {rightRail}
        </aside>
      ) : null}
    </div>
  );
}
