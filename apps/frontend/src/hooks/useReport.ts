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
  totalFiles?: number;
  moduleCount: number;
  maxDependencyDepth: number;
}

export interface ArchPattern {
  name: string;
  description?: string;
  confidence?: string;
}

export interface ArchLayer {
  name: string;
  responsibility: string;
  modules?: string;
}

export interface ArchViolation {
  description: string;
  severity?: string;
  affected_modules?: string[];
}

export interface QualityCodeSmell {
  name?: string;
  description?: string;
  severity?: string;
  file?: string;
  location?: string;
}

export interface SecurityVulnerability {
  title?: string;
  description?: string;
  severity?: string;
  file?: string;
  cwe?: string;
  recommendation?: string;
}

export interface ModernizationPhase {
  name?: string;
  description?: string;
  priority?: string;
  effort?: string;
  tasks?: string[];
}

export interface ArchitectureSection {
  summary: string;
  patterns: (ArchPattern | string)[];
  layers: ArchLayer[];
  violations: ArchViolation[];
  recommendations: string[];
}

export interface QualitySection {
  summary: string;
  metrics: Record<string, unknown>;
  codeSmells: QualityCodeSmell[];
  hotspots: Record<string, unknown>[];
  deadCode: Record<string, unknown>[];
}

export interface SecuritySection {
  summary: string;
  vulnerabilities: SecurityVulnerability[];
  recommendations: string[];
}

export interface DocumentationSection {
  summary: string;
  sections: Record<string, unknown>[];
  c4Diagrams: Record<string, unknown>;
}

export interface ModernizationSection {
  summary: string;
  phases: ModernizationPhase[];
  quickWins: string[];
  roadmap: Record<string, unknown>[];
}

export type AgentReportStatus = "completed" | "failed" | "skipped" | "pending";

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
  architecture: ArchitectureSection;
  quality: QualitySection;
  security: SecuritySection;
  documentation: DocumentationSection;
  modernization: ModernizationSection;
  rawReports?: Record<string, unknown>;
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
