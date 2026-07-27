"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE_URL } from "@/lib/constants";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export interface DashboardMetrics {
  totalProjects: number;
  completedProjects: number;
  analyzingProjects: number;
  failedProjects: number;
  queuedProjects: number;
  successRate: number;
  activeAgents: number;
  totalAgents: number;
}

export interface RecentJob {
  id: string;
  repoUrl: string;
  name: string;
  status: string;
  currentAgent: string | null;
  createdAt: string | null;
}

export interface DashboardData {
  metrics: DashboardMetrics;
  recentJobs: RecentJob[];
  systemStatus: "active" | "idle";
}

interface UseDashboardReturn {
  data: DashboardData | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

// ─────────────────────────────────────────────
// Default data (shown when backend is unavailable)
// ─────────────────────────────────────────────

const DEFAULT_DATA: DashboardData = {
  metrics: {
    totalProjects: 0,
    completedProjects: 0,
    analyzingProjects: 0,
    failedProjects: 0,
    queuedProjects: 0,
    successRate: 0,
    activeAgents: 0,
    totalAgents: 7,
  },
  recentJobs: [],
  systemStatus: "idle",
};

// ─────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────

/**
 * Fetches dashboard summary data from GET /api/v1/dashboard.
 * Polls every 10 seconds while the tab is visible.
 * Falls back to default empty data when backend is unavailable.
 */
export function useDashboard(): UseDashboardReturn {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/v1/dashboard`, {
        signal: AbortSignal.timeout(5000),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const json = await res.json();
      setData(json as DashboardData);
      setError(null);
    } catch (err) {
      // Backend not available — use default data without showing error
      // This allows the dashboard to render with zeros instead of an error page
      if (!data) {
        setData(DEFAULT_DATA);
      }
      setError(
        err instanceof Error ? err.message : "Failed to connect to backend"
      );
    } finally {
      setIsLoading(false);
    }
  }, [data]);

  useEffect(() => {
    fetchDashboard();

    // Poll every 10 seconds
    const interval = setInterval(fetchDashboard, 10_000);

    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, isLoading, error, refresh: fetchDashboard };
}
