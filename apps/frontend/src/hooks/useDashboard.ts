"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { API_BASE_URL } from "@/lib/constants";
import type { AgentStatus } from "@/lib/api";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export interface DashboardJob {
  jobId: string;
  repoUrl: string;
  status: "pending" | "cloning" | "analyzing" | "completed" | "failed" | "cancelled";
  currentAgent: string | null;
  progress: {
    totalAgents: number;
    completedAgents: number;
    agents: { name: string; status: AgentStatus }[];
  };
  createdAt: string;
}

export interface DashboardMetrics {
  activeAgents: number;
  totalAgents: number;
  jobsInQueue: number;
  completedProjects: number;
  successRate: number;
}

// ─────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────

const POLL_INTERVAL_MS = 4_000;

export function useDashboard() {
  const [jobs, setJobs] = useState<DashboardJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/v1/jobs`);
      if (!res.ok) {
        // If endpoint doesn't exist yet, return empty
        if (res.status === 404) {
          setJobs([]);
          setIsLoading(false);
          return;
        }
        throw new Error(`Failed to fetch jobs (${res.status})`);
      }
      const data = await res.json();
      // Backend may return { jobs: [...] } or [...] directly
      const jobsList = Array.isArray(data) ? data : (data.jobs ?? []);
      setJobs(jobsList);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Connection error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    intervalRef.current = setInterval(fetchJobs, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchJobs]);

  // Computed metrics from real data
  const metrics: DashboardMetrics = {
    activeAgents: jobs.filter((j) => j.status === "analyzing").reduce(
      (acc, j) => acc + j.progress.agents.filter((a) => a.status === "running").length,
      0
    ),
    totalAgents: 7,
    jobsInQueue: jobs.filter((j) => j.status === "pending" || j.status === "cloning").length,
    completedProjects: jobs.filter((j) => j.status === "completed").length,
    successRate: jobs.length > 0
      ? (() => {
          const terminal = jobs.filter((j) => j.status === "completed" || j.status === "failed").length;
          if (terminal === 0) return 0;
          return Math.round(
            (jobs.filter((j) => j.status === "completed").length / terminal) * 100
          );
        })()
      : 0,
  };

  return { jobs, metrics, isLoading, error, refetch: fetchJobs };
}
