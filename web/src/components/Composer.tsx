"use client";

import { ArrowUp, Loader2 } from "lucide-react";
import { useState, type KeyboardEvent } from "react";
import { cn } from "@/lib/cn";

interface ComposerProps {
  onSend: (text: string) => void;
  busy: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function Composer({
  onSend,
  busy,
  disabled = false,
  placeholder = "Ask anything about your documents…",
}: ComposerProps) {
  const [value, setValue] = useState("");

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || busy || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const canSend = value.trim().length > 0 && !busy && !disabled;

  return (
    <div
      className={cn(
        "relative rounded-xl border border-border bg-bg-elevated",
        "focus-within:border-border-strong focus-within:shadow-sm",
        "transition-shadow",
      )}
    >
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={2}
        className={cn(
          "w-full resize-none bg-transparent",
          "px-4 pt-3 pb-12 text-[15px] leading-relaxed text-fg",
          "placeholder:text-fg-faint",
          "focus:outline-none",
          "disabled:opacity-60",
        )}
      />

      <div className="absolute bottom-2.5 right-2.5">
        <button
          onClick={submit}
          disabled={!canSend}
          className={cn(
            "inline-flex h-8 w-8 items-center justify-center rounded-full",
            "transition-colors",
            canSend
              ? "bg-accent text-white hover:bg-accent-hover"
              : "bg-bg-subtle text-fg-faint cursor-not-allowed",
          )}
          aria-label="Send message"
        >
          {busy ? (
            <Loader2 size={15} className="animate-spin" />
          ) : (
            <ArrowUp size={16} />
          )}
        </button>
      </div>
    </div>
  );
}
