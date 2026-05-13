"use client";

import { Upload, Loader2 } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@/components/Button";
import { uploadDocument } from "@/lib/api";
import { getTurnstileToken } from "@/lib/turnstile";

interface UploadButtonProps {
  onUploaded: () => void;
}

const ACCEPT = ".pdf";

export function UploadButton({ onUploaded }: UploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onPick(file: File) {
    setError(null);
    setBusy(true);
    try {
      const token = await getTurnstileToken();
      await uploadDocument(file, token);
      onUploaded();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Button
        variant="primary"
        size="sm"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
        className="w-full"
      >
        {busy ? (
          <>
            <Loader2 size={14} className="animate-spin" />
            Uploading…
          </>
        ) : (
          <>
            <Upload size={14} />
            Upload document
          </>
        )}
      </Button>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void onPick(f);
        }}
      />

      {error ? (
        <div className="rounded-md bg-[rgba(212,76,71,0.08)] px-2 py-1.5 text-[12px] text-[var(--color-status-error)]">
          {error}
        </div>
      ) : (
        <div className="px-1 text-[11.5px] text-fg-faint">
          PDF · up to 20 pages
        </div>
      )}
    </div>
  );
}
