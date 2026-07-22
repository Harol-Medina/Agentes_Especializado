"use client";

import { useState, useEffect } from "react";
import { API_BASE_URL } from "@/lib/constants";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export interface ReportModule {
  name: string;
  responsibility: string;
  loc: number;
}

export interface ReportComponent {
  name: string;
  module: string;
  responsibility: string;
}

export interface ReportDependency {
  from?: string;
  to?: string;
  type?: string;
  name?: string;
  version?: string;
}

export interface ReportMetrics {
  totalLoc: number;
  moduleCount: number;
  maxDependencyDepth: number;
}

export type AgentReportStatus = "completed" | "failed" | "skipped";

export interface ArchitectureReportData {
  projectName: string;
  language: { name: string; version: string };
  framework: { name: string; version: string };
  modules: ReportModule[];
  dependencies: {
    internal: ReportDependency[];
    external: ReportDependency[];
  };
  components: ReportComponent[];
  metrics: ReportMetrics;
  agentsStatus: Record<string, AgentReportStatus>;
  incompleteSections: string[];
}

// ─────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────

export function useReport(projectId: string) {
  const [report, setReport] = useState<ArchitectureReportData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchReport() {
      try {
        setIsLoading(true);
        setError(null);

        const res = await fetch(
          `${API_BASE_URL}/v1/projects/${projectId}/report`
        );

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(
            (body as { message?: string }).message ??
              `Failed to fetch report (${res.status})`
          );
        }

        const data = (await res.json()) as ArchitectureReportData;
        if (!cancelled) {
          setReport(data);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to fetch report"
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchReport();

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  return { report, isLoading, error };
}
