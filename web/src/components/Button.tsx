"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const buttonStyles = cva(
  "inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-soft focus-visible:ring-offset-1 focus-visible:ring-offset-bg",
  {
    variants: {
      variant: {
        // Solid Notion-blue primary
        primary:
          "bg-accent text-white hover:bg-accent-hover shadow-sm",
        // Subtle ghost — main nav, list affordances
        ghost: "text-fg hover-surface",
        // Outline — secondary CTAs
        outline:
          "border border-border-strong bg-bg-elevated text-fg hover:bg-bg-subtle",
        // Destructive
        danger:
          "text-[var(--color-status-error)] hover:bg-[rgba(212,76,71,0.08)]",
      },
      size: {
        sm: "h-7 px-2 text-[13px]",
        md: "h-8 px-3 text-sm",
        lg: "h-10 px-4 text-[15px]",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonStyles> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonStyles({ variant, size }), className)}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";
