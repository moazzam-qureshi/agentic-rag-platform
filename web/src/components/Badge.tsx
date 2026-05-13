"use client";

import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const badgeStyles = cva(
  "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium leading-none",
  {
    variants: {
      tone: {
        neutral: "bg-bg-subtle text-fg-muted",
        info: "bg-accent-soft text-[var(--color-accent-hover)]",
        success: "bg-[rgba(68,131,97,0.12)] text-[var(--color-status-success)]",
        warning: "bg-[rgba(203,145,47,0.14)] text-[var(--color-status-warning)]",
        error: "bg-[rgba(212,76,71,0.12)] text-[var(--color-status-error)]",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeStyles> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeStyles({ tone }), className)} {...props} />;
}
