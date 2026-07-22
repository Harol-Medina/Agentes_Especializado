"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE_URL } from "@/lib/constants";

// ─────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────

export function useKiroExport(projectId: string) {
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const downloadUrl = `${API_BASE_URL}/v1/projects/${projectId}/kiro-spec`;

  const fetchMarkdown = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${API_BASE_URL}/v1/projects/${projectId}/kiro-spec`,
        {
          headers: { Accept: "text/markdown" },
        }
      );

      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(body || `HTTP ${res.status}`);
      }

      const text = await res.text();
      setMarkdown(text);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch Kiro spec";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      fetchMarkdown();
    }
  }, [projectId, fetchMarkdown]);

  return { markdown, isLoading, error, downloadUrl };
}
