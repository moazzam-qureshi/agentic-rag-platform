"use client";

import { useCallback, useEffect, useState } from "react";
import {
  deleteDocument,
  getJobStatus,
  listDocuments,
  type DocumentRecord,
} from "@/lib/api";

/**
 * Tracks the caller's document list with light polling for any docs still
 * in `pending` or `processing` state.
 */
export function useDocuments() {
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setDocs(await listDocuments());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Light polling while any doc is mid-ingestion. Backs off when all done.
  useEffect(() => {
    const inFlight = docs.filter(
      (d) => d.status === "pending" || d.status === "processing",
    );
    if (inFlight.length === 0) return;

    const interval = setInterval(async () => {
      try {
        const updates = await Promise.all(
          inFlight.map((d) => getJobStatus(d.id)),
        );
        setDocs((prev) =>
          prev.map((d) => {
            const u = updates.find((x) => x.document_id === d.id);
            if (!u) return d;
            return {
              ...d,
              status: u.status,
              page_count: u.page_count,
              error_message: u.error_message,
              progress: u.progress,
            };
          }),
        );
      } catch {
        // ignore transient errors; next tick will retry
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [docs]);

  const remove = useCallback(
    async (id: string) => {
      try {
        await deleteDocument(id);
        setDocs((prev) => prev.filter((d) => d.id !== id));
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [],
  );

  return { docs, loading, error, refresh, remove };
}
