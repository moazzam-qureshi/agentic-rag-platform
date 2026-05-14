"use client";

import { useCallback, useEffect, useState } from "react";
import {
  deleteSession,
  listSessions,
  type SessionListItem,
} from "@/lib/api";

/**
 * Tracks the caller's chat sessions for the sidebar list.
 *
 * Two integration points with the chat hook:
 *  - call refresh() right after a new conversation is created or a
 *    message lands, so the sidebar reflects the latest title/order
 *  - call remove(id) when the user clicks the trash icon
 */
export function useSessions() {
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setSessions(await listSessions());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const remove = useCallback(
    async (id: string) => {
      try {
        await deleteSession(id);
        setSessions((prev) => prev.filter((s) => s.id !== id));
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [],
  );

  return { sessions, loading, error, refresh, remove };
}
