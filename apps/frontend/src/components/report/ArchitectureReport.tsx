"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useReport } from "@/hooks/useReport";
import { ReportSection } from "./ReportSection";
import { MetricsGrid, type Metric } from "./MetricsGrid";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

interface ArchitectureReportProps {
  projectId: string;
}

type ReportTab =
  | "architecture"
  | "quality"
  | "security"
  | "documentation"
  | "modernization";

const TABS: { id: ReportTab; label: string; agent: string }[] = [
  { id: "architecture", label: "Architecture", agent: "architecture_agent" },
  { id: "quality", label: "Quality", agent: "quality_agent" },
  { id: "security", label: "Security", agent: "security_agent" },
  { id: "documentation", label: "Documentation", agent: "documentation_agent" },
  { id: "modernization", label: "Modernization", agent: "modernization_agent" },
];

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

export function ArchitectureReport({ projectId }: ArchitectureReportProps) {
  const { report, isLoading, error } = useReport(projectId);
  const [activeTab, setActiveTab] = useState<ReportTab>("architecture");

  // ─── Loading State ───
  if (isLoading) {
    return (
      <div className="container py-12">
        <div className="flex items-center justify-center gap-3 text-muted-foreground">
          <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="font-body text-sm">Loading report...</span>
        </div>
      </div>
    );
  }

  // ─── Error State ───
  if (error) {
    return (
      <div className="container py-12">
        <div className="bg-card border border-[#EF4444]/40 rounded-xl p-6 text-center">
          <p className="text-[#EF4444] font-body text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!report) return null;

  // ─── Build metrics ───
  const metrics: Metric[] = [
    { label: "Total LOC", value: report.metrics.totalLoc.toLocaleString(), color: "var(--primary)" },
    { label: "Modules", value: report.metrics.moduleCount, color: "var(--secondary)" },
    { label: "Max Depth", value: report.metrics.maxDependencyDepth, color: "#8B5CF6" },
    { label: "Language", value: report.language.name, color: "#10B981" },
    { label: "Framework", value: report.framework.name, color: "#F97316" },
  ];

  return (
    <div className="container py-8 space-y-8">
      {/* Report Header */}
      <div>
        <h2 className="font-display text-[20px] font-bold text-foreground mb-1">
          {report.projectName}
        </h2>
        <p className="font-body text-[13px] text-muted-foreground">
          {report.language.name} {report.language.version} &middot;{" "}
          {report.framework.name} {report.framework.version}
        </p>
      </div>

      {/* Metrics Grid */}
      <MetricsGrid metrics={metrics} />

      {/* Tab Navigation */}
      <nav
        className="flex gap-1 border-b border-border"
        role="tablist"
        aria-label="Report sections"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-4 py-2 font-body text-[13px] font-medium transition-colors duration-150 border-b-2 -mb-px",
              activeTab === tab.id
                ? "text-primary border-primary"
                : "text-muted-foreground border-transparent hover:text-foreground"
            )}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Tab Content */}
      <div
        id={`panel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={activeTab}
      >
        {activeTab === "architecture" && (
          <ArchitectureTab report={report} />
        )}
        {activeTab === "quality" && (
          <ReportSection
            title="Quality Analysis"
            status={report.agentsStatus.quality_agent}
          >
            <QualityContent report={report} />
          </ReportSection>
        )}
        {activeTab === "security" && (
          <ReportSection
            title="Security Analysis"
            status={report.agentsStatus.security_agent}
          >
            <p className="text-card-foreground text-sm">
              Security findings from static analysis and vulnerability detection.
            </p>
          </ReportSection>
        )}
        {activeTab === "documentation" && (
          <ReportSection
            title="Documentation"
            status={report.agentsStatus.documentation_agent}
          >
            <p className="text-card-foreground text-sm">
              Generated documentation bundle and coverage report.
            </p>
          </ReportSection>
        )}
        {activeTab === "modernization" && (
          <ReportSection
            title="Modernization Plan"
            status={report.agentsStatus.modernization_agent}
          >
            <p className="text-card-foreground text-sm">
              Refactoring recommendations and prioritized action plan.
            </p>
          </ReportSection>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Architecture Tab
// ─────────────────────────────────────────────

function ArchitectureTab({
  report,
}: {
  report: NonNullable<ReturnType<typeof useReport>["report"]>;
}) {
  return (
    <div className="space-y-6">
      {/* Modules */}
      <ReportSection
        title="Modules"
        status={report.agentsStatus.architecture_agent}
      >
        {report.modules.length > 0 ? (
          <div className="space-y-2">
            {report.modules.map((mod) => (
              <div
                key={mod.name}
                className="flex items-center justify-between py-2 border-b border-border last:border-0"
              >
                <div>
                  <span className="font-body text-sm text-foreground font-medium">
                    {mod.name}
                  </span>
                  <p className="font-body text-[12px] text-muted-foreground">
                    {mod.responsibility}
                  </p>
                </div>
                <span className="font-mono text-[10px] text-muted-foreground uppercase tracking-wide">
                  {mod.loc.toLocaleString()} loc
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm">No modules detected.</p>
        )}
      </ReportSection>

      {/* Dependencies */}
      <ReportSection title="Dependencies" status={report.agentsStatus.architecture_agent}>
        <div className="space-y-4">
          {/* External */}
          {report.dependencies.external.length > 0 && (
            <div>
              <h4 className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-2">
                External Dependencies
              </h4>
              <div className="flex flex-wrap gap-2">
                {report.dependencies.external.map((dep) => (
                  <span
                    key={dep.name}
                    className="font-mono text-[11px] text-secondary bg-[#06B6D415] border border-[#06B6D440] rounded px-2 py-0.5"
                  >
                    {dep.name}
                    {dep.version && (
                      <span className="text-muted-foreground ml-1">
                        @{dep.version}
                      </span>
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Internal */}
          {report.dependencies.internal.length > 0 && (
            <div>
              <h4 className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-2">
                Internal Relationships
              </h4>
              <div className="space-y-1">
                {report.dependencies.internal.slice(0, 10).map((dep, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 text-sm text-card-foreground"
                  >
                    <span className="font-mono text-[11px]">{dep.from}</span>
                    <span className="text-muted-foreground">→</span>
                    <span className="font-mono text-[11px]">{dep.to}</span>
                    {dep.type && (
                      <span className="font-mono text-[10px] text-muted-foreground bg-muted rounded px-1.5 py-0.5">
                        {dep.type}
                      </span>
                    )}
                  </div>
                ))}
                {report.dependencies.internal.length > 10 && (
                  <p className="text-[11px] text-muted-foreground italic">
                    +{report.dependencies.internal.length - 10} more relationships
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </ReportSection>

      {/* Components */}
      {report.components.length > 0 && (
        <ReportSection title="Key Components" status={report.agentsStatus.architecture_agent}>
          <div className="space-y-2">
            {report.components.map((comp) => (
              <div
                key={comp.name}
                className="flex items-center justify-between py-2 border-b border-border last:border-0"
              >
                <div>
                  <span className="font-body text-sm text-foreground font-medium">
                    {comp.name}
                  </span>
                  <p className="font-body text-[12px] text-muted-foreground">
                    {comp.responsibility}
                  </p>
                </div>
                <span className="font-mono text-[10px] text-primary bg-[#F59E0B15] rounded px-2 py-0.5">
                  {comp.module}
                </span>
              </div>
            ))}
          </div>
        </ReportSection>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// Quality Tab Content
// ─────────────────────────────────────────────

function QualityContent({
  report,
}: {
  report: NonNullable<ReturnType<typeof useReport>["report"]>;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between py-2 border-b border-border">
        <span className="font-body text-sm text-card-foreground">Total Lines of Code</span>
        <span className="font-mono text-[11px] text-foreground">
          {report.metrics.totalLoc.toLocaleString()}
        </span>
      </div>
      <div className="flex items-center justify-between py-2 border-b border-border">
        <span className="font-body text-sm text-card-foreground">Module Count</span>
        <span className="font-mono text-[11px] text-foreground">
          {report.metrics.moduleCount}
        </span>
      </div>
      <div className="flex items-center justify-between py-2">
        <span className="font-body text-sm text-card-foreground">Max Dependency Depth</span>
        <span className="font-mono text-[11px] text-foreground">
          {report.metrics.maxDependencyDepth}
        </span>
      </div>
    </div>
  );
}
