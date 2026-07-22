"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getJobStatus, type AnalysisJobResponse } from "@/lib/api";

const POLL_INTERVAL_MS = 3_000;

export function useJobPolling(jobId: string) {
  const [job, setJob] = useState<AnalysisJobResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const data = await getJobStatus(jobId);
        if (cancelled) return;

        setJob(data);
        setError(null);
        setIsLoading(false);

        // Stop polling on terminal states
        if (data.status === "completed" || data.status === "failed") {
          stopPolling();
        }
      } catch (err: unknown) {
        if (cancelled) return;
        const message =
          err instanceof Error
            ? err.message
            : typeof err === "object" && err !== null && "message" in err
            ? String((err as { message: string }).message)
            : "Failed to fetch job status";
        setError(message);
        setIsLoading(false);
      }
    }

    // Initial fetch
    poll();

    // Set up interval
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [jobId, stopPolling]);

  return { job, isLoading, error };
}
