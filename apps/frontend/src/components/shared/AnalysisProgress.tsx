"use client";

import { useState } from "react";
import Link from "next/link";
import { useJobPolling } from "@/hooks/useJobPolling";
import { cancelJob } from "@/lib/api";
import { AGENT_LABELS, type AgentStage } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { AgentStatus } from "@/lib/api";

// ─────────────────────────────────────────────
// Agent list (display order)
// ─────────────────────────────────────────────

const AGENTS: { key: AgentStage; label: string }[] = [
  { key: "repository_agent", label: AGENT_LABELS.repository_agent },
  { key: "architecture_agent", label: AGENT_LABELS.architecture_agent },
  { key: "quality_agent", label: AGENT_LABELS.quality_agent },
  { key: "security_agent", label: AGENT_LABELS.security_agent },
  { key: "documentation_agent", label: AGENT_LABELS.documentation_agent },
  { key: "modernization_agent", label: AGENT_LABELS.modernization_agent },
  { key: "kiro_agent", label: AGENT_LABELS.kiro_agent },
];

// ─────────────────────────────────────────────
// Status helpers
// ─────────────────────────────────────────────

function getStatusDotClass(status: AgentStatus): string {
  switch (status) {
    case "completed":
      return "bg-[#10B981] shadow-[0_0_6px_#10B981]";
    case "running":
      return "bg-primary shadow-[0_0_6px_#F59E0B] animate-status-pulse";
    case "failed":
      return "bg-[#EF4444] shadow-[0_0_6px_#EF4444]";
    case "skipped":
      return "bg-muted-foreground opacity-50";
    case "pending":
    default:
      return "bg-muted-foreground";
  }
}

function getStatusLabelClass(status: AgentStatus): string {
  switch (status) {
    case "completed":
      return "text-[#10B981]";
    case "running":
      return "text-primary";
    case "failed":
      return "text-[#EF4444]";
    case "skipped":
      return "text-muted-foreground opacity-70";
    case "pending":
    default:
      return "text-muted-foreground";
  }
}

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

interface AnalysisProgressProps {
  jobId: string;
}

export function AnalysisProgress({ jobId }: AnalysisProgressProps) {
  const { job, isLoading, error } = useJobPolling(jobId);
  const [cancelling, setCancelling] = useState(false);

  async function handleCancel() {
    setCancelling(true);
    try {
      await cancelJob(jobId);
    } catch {
      // Even if cancel fails, polling will pick up the real status
    } finally {
      setCancelling(false);
    }
  }

  // Loading state
  if (isLoading && !job) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="font-code text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
            Loading analysis...
          </p>
        </div>
      </div>
    );
  }

  // Network error state
  if (error && !job) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="bg-card border border-border rounded-xl p-8 max-w-md text-center space-y-3">
          <div className="w-3 h-3 rounded-full bg-[#EF4444] shadow-[0_0_6px_#EF4444] mx-auto" />
          <h2 className="font-heading text-lg font-bold text-foreground">
            Connection Error
          </h2>
          <p className="font-sans text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  if (!job) return null;

  const completedAgents = job.progress.completedAgents;
  const totalAgents = job.progress.totalAgents;
  const progressPercent = (completedAgents / totalAgents) * 100;

  const isCompleted = job.status === "completed";
  const isFailed = job.status === "failed";
  const isCancelled = job.status === "cancelled";
  const isRunning = !isCompleted && !isFailed && !isCancelled;

  // Build agent status map from response
  const agentStatusMap = new Map(
    job.progress.agents.map((a) => [a.name, a.status])
  );

  return (
    <div className="container relative z-10 pt-12 pb-16">
      <div className="max-w-xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          {isCompleted ? (
            <>
              <div className="w-3 h-3 rounded-full bg-[#10B981] shadow-[0_0_8px_#10B981] mx-auto" />
              <h1 className="font-heading font-bold text-foreground text-2xl pt-2">
                Analysis Complete
              </h1>
              <p className="font-sans text-sm text-muted-foreground">
                Your repository has been analyzed successfully.
              </p>
            </>
          ) : isFailed ? (
            <>
              <div className="w-3 h-3 rounded-full bg-[#EF4444] shadow-[0_0_8px_#EF4444] mx-auto" />
              <h1 className="font-heading font-bold text-foreground text-2xl pt-2">
                Analysis Failed
              </h1>
              <p className="font-sans text-sm text-[#EF4444]">
                An error occurred during the analysis pipeline.
              </p>
            </>
          ) : isCancelled ? (
            <>
              <div className="w-3 h-3 rounded-full bg-[#F97316] shadow-[0_0_8px_#F97316] mx-auto" />
              <h1 className="font-heading font-bold text-foreground text-2xl pt-2">
                Analysis Cancelled
              </h1>
              <p className="font-sans text-sm text-[#F97316]">
                The analysis was cancelled.
              </p>
            </>
          ) : (
            <>
              <div className="w-3 h-3 rounded-full bg-primary shadow-[0_0_8px_#F59E0B] animate-status-pulse mx-auto" />
              <h1 className="font-heading font-bold text-foreground text-2xl pt-2">
                Analyzing repository...
              </h1>
              <p className="font-sans text-sm text-muted-foreground">
                Our AI agents are inspecting the codebase. This may take a few minutes.
              </p>
            </>
          )}
        </div>

        {/* Cancel button (shown only while running) */}
        {isRunning && (
          <div className="flex justify-center">
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-md",
                "border border-[#EF4444]/40 bg-[#EF4444]/10 text-[#EF4444]",
                "font-sans text-xs font-semibold uppercase tracking-wider",
                "hover:bg-[#EF4444]/20 hover:border-[#EF4444]/60 transition-colors duration-150",
                "focus:outline-none focus:ring-2 focus:ring-[#EF4444]/50 focus:ring-offset-2 focus:ring-offset-background",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              {cancelling ? (
                <>
                  <svg
                    className="animate-spin h-3.5 w-3.5"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Cancelling...
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5" aria-hidden="true">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                  Cancel Analysis
                </>
              )}
            </button>
          </div>
        )}

        {/* Progress bar */}
        <div className="space-y-2">
          <div className="h-[3px] w-full bg-border rounded-sm overflow-hidden">
            <div
              className={cn(
                "h-full rounded-sm transition-[width] duration-[600ms] ease-in-out",
                isCompleted ? "bg-[#10B981]" : isFailed ? "bg-[#EF4444]" : "bg-primary"
              )}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <p className="font-code text-[10px] text-muted-foreground tracking-wider">
            {completedAgents} / {totalAgents} AGENTS COMPLETE
          </p>
        </div>

        {/* Agent list card */}
        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "w-2 h-2 rounded-full",
                isCompleted
                  ? "bg-[#10B981] shadow-[0_0_6px_#10B981]"
                  : isFailed
                  ? "bg-[#EF4444] shadow-[0_0_6px_#EF4444]"
                  : "bg-primary shadow-[0_0_6px_#F59E0B] animate-status-pulse"
              )}
            />
            <span className="font-code text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
              Agent Pipeline
            </span>
          </div>

          <div className="space-y-3">
            {AGENTS.map((agent) => {
              const status: AgentStatus =
                agentStatusMap.get(agent.key) ?? "pending";

              return (
                <div key={agent.key} className="flex items-center gap-3">
                  <span
                    className={cn(
                      "w-1.5 h-1.5 rounded-full flex-shrink-0",
                      getStatusDotClass(status)
                    )}
                  />
                  <span className="font-sans text-[13px] text-card-foreground flex-1">
                    {agent.label}
                  </span>
                  <span
                    className={cn(
                      "font-code text-[10px] uppercase tracking-[0.08em]",
                      getStatusLabelClass(status)
                    )}
                  >
                    {status}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Completed: action buttons */}
        {isCompleted && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Link
              href={`/analysis/${jobId}/graph`}
              className={cn(
                "flex items-center justify-center gap-2 px-4 py-3 rounded-md",
                "bg-primary text-primary-foreground",
                "font-sans text-xs font-bold uppercase tracking-wider",
                "hover:opacity-90 transition-opacity duration-150",
                "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"
              )}
            >
              View Dependency Graph
            </Link>
            <Link
              href={`/analysis/${jobId}/chat`}
              className={cn(
                "flex items-center justify-center gap-2 px-4 py-3 rounded-md",
                "border border-border bg-muted/40 text-foreground",
                "font-sans text-xs font-bold uppercase tracking-wider",
                "hover:border-primary/50 hover:text-primary transition-colors duration-150",
                "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"
              )}
            >
              Chat with Code
            </Link>
            <Link
              href={`/analysis/${jobId}/report`}
              className={cn(
                "flex items-center justify-center gap-2 px-4 py-3 rounded-md",
                "border border-border bg-muted/40 text-foreground",
                "font-sans text-xs font-bold uppercase tracking-wider",
                "hover:border-primary/50 hover:text-primary transition-colors duration-150",
                "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"
              )}
            >
              Architecture Report
            </Link>
            <Link
              href={`/analysis/${jobId}/export`}
              className={cn(
                "flex items-center justify-center gap-2 px-4 py-3 rounded-md",
                "border border-border bg-muted/40 text-foreground",
                "font-sans text-xs font-bold uppercase tracking-wider",
                "hover:border-primary/50 hover:text-primary transition-colors duration-150",
                "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"
              )}
            >
              Export Kiro Spec
            </Link>
          </div>
        )}

        {/* Failed: error details */}
        {isFailed && error && (
          <div className="bg-[#EF444410] border border-[#EF444440] rounded-xl p-4">
            <p className="font-code text-[11px] text-[#EF4444]">{error}</p>
          </div>
        )}

        {/* Failed / Cancelled: try again */}
        {(isFailed || isCancelled) && (
          <div className="flex justify-center">
            <Link
              href="/"
              className={cn(
                "flex items-center gap-2 px-6 py-3 rounded-md",
                "bg-primary text-primary-foreground",
                "font-sans text-xs font-bold uppercase tracking-wider",
                "hover:opacity-90 transition-opacity duration-150",
                "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"
              )}
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4" aria-hidden="true">
                <polyline points="1 4 1 10 7 10" />
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
              </svg>
              New Analysis
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
