"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useReport } from "@/hooks/useReport";
import { ReportSection } from "./ReportSection";
import { MetricsGrid, type Metric } from "./MetricsGrid";
import { MermaidDiagram } from "./MermaidDiagram";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

interface ArchitectureReportProps {
  projectId: string;
}

type ReportTab =
  | "architecture"
  | "quality"
  | "dead_code"
  | "security"
  | "roadmap"
  | "c4_diagrams"
  | "documentation"
  | "modernization";

const TABS: { id: ReportTab; label: string; agent: string }[] = [
  { id: "architecture", label: "Architecture", agent: "architecture_agent" },
  { id: "quality", label: "Quality", agent: "quality_agent" },
  { id: "dead_code", label: "Dead Code", agent: "quality_agent" },
  { id: "security", label: "Security", agent: "security_agent" },
  { id: "c4_diagrams", label: "C4 Diagrams", agent: "documentation_agent" },
  { id: "roadmap", label: "Roadmap", agent: "modernization_agent" },
  { id: "documentation", label: "Docs", agent: "documentation_agent" },
  { id: "modernization", label: "Plan", agent: "modernization_agent" },
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
          <span className="font-sans text-sm">Loading report...</span>
        </div>
      </div>
    );
  }

  // ─── Error State ───
  if (error) {
    return (
      <div className="container py-12">
        <div className="bg-card border border-[#EF4444]/40 rounded-xl p-6 text-center">
          <p className="text-[#EF4444] font-sans text-sm">{error}</p>
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
        <h2 className="font-heading text-[20px] font-bold text-foreground mb-1">
          {report.projectName}
        </h2>
        <p className="font-sans text-[13px] text-muted-foreground">
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
              "px-4 py-2 font-sans text-[13px] font-medium transition-colors duration-150 border-b-2 -mb-px",
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
        {activeTab === "dead_code" && (
          <DeadCodeTab report={report} />
        )}
        {activeTab === "security" && (
          <SecurityTab report={report} />
        )}
        {activeTab === "roadmap" && (
          <RoadmapTab report={report} />
        )}
        {activeTab === "c4_diagrams" && (
          <C4DiagramsTab report={report} />
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
  const arch = report.architecture;

  return (
    <div className="space-y-6">
      {/* Summary */}
      {arch?.summary && (
        <ReportSection title="Architecture Summary" status={report.agentsStatus.architecture_agent}>
          <p className="font-sans text-sm text-card-foreground leading-relaxed">
            {arch.summary}
          </p>
        </ReportSection>
      )}

      {/* Patterns */}
      {arch?.patterns && arch.patterns.length > 0 && (
        <ReportSection title="Detected Patterns" status={report.agentsStatus.architecture_agent}>
          <div className="space-y-2">
            {arch.patterns.map((pattern, idx) => {
              const p = typeof pattern === "string" ? { name: pattern } : pattern;
              return (
                <div
                  key={idx}
                  className="flex items-start gap-3 py-2 border-b border-border last:border-0"
                >
                  <span className="mt-0.5 w-2 h-2 rounded-full bg-primary shadow-[0_0_6px_var(--primary)] flex-shrink-0" />
                  <div className="flex-1">
                    <span className="font-sans text-sm text-foreground font-medium">
                      {p.name}
                    </span>
                    {p.description && (
                      <p className="font-sans text-[12px] text-muted-foreground mt-0.5">
                        {p.description}
                      </p>
                    )}
                  </div>
                  {p.confidence && (
                    <span className="font-code text-[10px] text-[#10B981] bg-[#10B98115] border border-[#10B98140] rounded px-2 py-0.5">
                      {p.confidence}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </ReportSection>
      )}

      {/* Layers / Modules */}
      <ReportSection title="Architectural Layers" status={report.agentsStatus.architecture_agent}>
        {(arch?.layers && arch.layers.length > 0) || report.modules.length > 0 ? (
          <div className="space-y-2">
            {(arch?.layers && arch.layers.length > 0 ? arch.layers : report.modules).map((layer, idx) => (
              <div
                key={idx}
                className="py-3 border-b border-border last:border-0"
              >
                <div className="flex items-center justify-between">
                  <span className="font-sans text-sm text-foreground font-medium">
                    {layer.name}
                  </span>
                  {"modules" in layer && layer.modules && (
                    <span className="font-code text-[10px] text-muted-foreground">
                      {layer.modules}
                    </span>
                  )}
                </div>
                <p className="font-sans text-[12px] text-muted-foreground mt-0.5">
                  {layer.responsibility}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm">No layers detected.</p>
        )}
      </ReportSection>

      {/* Violations */}
      {arch?.violations && arch.violations.length > 0 && (
        <ReportSection title="Architecture Violations" status={report.agentsStatus.architecture_agent}>
          <div className="space-y-2">
            {arch.violations.map((v, idx) => (
              <div
                key={idx}
                className="flex items-start gap-3 py-2 border-b border-border last:border-0"
              >
                <span
                  className={cn(
                    "mt-0.5 w-2 h-2 rounded-full flex-shrink-0",
                    v.severity === "high"
                      ? "bg-[#EF4444] shadow-[0_0_6px_#EF4444]"
                      : v.severity === "medium"
                      ? "bg-[#F97316] shadow-[0_0_6px_#F97316]"
                      : "bg-[#F59E0B] shadow-[0_0_6px_#F59E0B]"
                  )}
                />
                <div className="flex-1">
                  <p className="font-sans text-sm text-card-foreground">
                    {v.description}
                  </p>
                  {v.affected_modules && v.affected_modules.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {v.affected_modules.map((mod) => (
                        <span
                          key={mod}
                          className="font-code text-[10px] text-muted-foreground bg-muted rounded px-1.5 py-0.5"
                        >
                          {mod}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                {v.severity && (
                  <span
                    className={cn(
                      "font-code text-[10px] uppercase tracking-wide rounded px-2 py-0.5",
                      v.severity === "high"
                        ? "text-[#EF4444] bg-[#EF444415] border border-[#EF444440]"
                        : v.severity === "medium"
                        ? "text-[#F97316] bg-[#F9731615] border border-[#F9731640]"
                        : "text-[#F59E0B] bg-[#F59E0B15] border border-[#F59E0B40]"
                    )}
                  >
                    {v.severity}
                  </span>
                )}
              </div>
            ))}
          </div>
        </ReportSection>
      )}

      {/* Recommendations */}
      {arch?.recommendations && arch.recommendations.length > 0 && (
        <ReportSection title="Recommendations" status={report.agentsStatus.architecture_agent}>
          <ul className="space-y-2">
            {arch.recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-secondary flex-shrink-0" />
                <span className="font-sans text-sm text-card-foreground">{rec}</span>
              </li>
            ))}
          </ul>
        </ReportSection>
      )}

      {/* Dependencies (kept as before) */}
      {(report.dependencies.internal.length > 0 || report.dependencies.external.length > 0) && (
        <ReportSection title="Dependencies" status={report.agentsStatus.architecture_agent}>
          <div className="space-y-4">
            {report.dependencies.external.length > 0 && (
              <div>
                <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-2">
                  External Dependencies
                </h4>
                <div className="flex flex-wrap gap-2">
                  {report.dependencies.external.map((dep) => (
                    <span
                      key={dep.name}
                      className="font-code text-[11px] text-secondary bg-[#06B6D415] border border-[#06B6D440] rounded px-2 py-0.5"
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
            {report.dependencies.internal.length > 0 && (
              <div>
                <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-2">
                  Internal Relationships
                </h4>
                <div className="space-y-1">
                  {report.dependencies.internal.slice(0, 10).map((dep, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 text-sm text-card-foreground"
                    >
                      <span className="font-code text-[11px]">{dep.from}</span>
                      <span className="text-muted-foreground">→</span>
                      <span className="font-code text-[11px]">{dep.to}</span>
                      {dep.type && (
                        <span className="font-code text-[10px] text-muted-foreground bg-muted rounded px-1.5 py-0.5">
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
      )}

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
                  <span className="font-sans text-sm text-foreground font-medium">
                    {comp.name}
                  </span>
                  <p className="font-sans text-[12px] text-muted-foreground">
                    {comp.responsibility}
                  </p>
                </div>
                <span className="font-code text-[10px] text-primary bg-[#F59E0B15] rounded px-2 py-0.5">
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
        <span className="font-sans text-sm text-card-foreground">Total Lines of Code</span>
        <span className="font-code text-[11px] text-foreground">
          {report.metrics.totalLoc.toLocaleString()}
        </span>
      </div>
      <div className="flex items-center justify-between py-2 border-b border-border">
        <span className="font-sans text-sm text-card-foreground">Module Count</span>
        <span className="font-code text-[11px] text-foreground">
          {report.metrics.moduleCount}
        </span>
      </div>
      <div className="flex items-center justify-between py-2">
        <span className="font-sans text-sm text-card-foreground">Max Dependency Depth</span>
        <span className="font-code text-[11px] text-foreground">
          {report.metrics.maxDependencyDepth}
        </span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Dead Code Tab (V2-4.2)
// ─────────────────────────────────────────────

function DeadCodeTab({
  report,
}: {
  report: NonNullable<ReturnType<typeof useReport>["report"]>;
}) {
  const [filterConfidence, setFilterConfidence] = useState<string>("all");

  // Dead code data comes from quality_report.dead_code (populated by backend)
  // For now we use any available data from the report, or show placeholder
  const deadCodeItems: Array<{
    name: string;
    node_type: string;
    file_path: string;
    confidence: string;
    reason: string;
  }> = (report as any).deadCode ?? [];

  const filtered =
    filterConfidence === "all"
      ? deadCodeItems
      : deadCodeItems.filter((item) => item.confidence === filterConfidence);

  const highCount = deadCodeItems.filter((i) => i.confidence === "high").length;
  const medCount = deadCodeItems.filter((i) => i.confidence === "medium").length;
  const lowCount = deadCodeItems.filter((i) => i.confidence === "low").length;

  return (
    <div className="space-y-6">
      <ReportSection title="Dead Code Detection" status={report.agentsStatus.quality_agent}>
        {/* Summary metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-muted/30 border border-border rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-foreground">{deadCodeItems.length}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Total</p>
          </div>
          <div className="bg-[#EF444410] border border-[#EF444430] rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-[#EF4444]">{highCount}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">High</p>
          </div>
          <div className="bg-[#F59E0B10] border border-[#F59E0B30] rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-primary">{medCount}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Medium</p>
          </div>
          <div className="bg-[#6B7A9910] border border-[#6B7A9930] rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-muted-foreground">{lowCount}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Low</p>
          </div>
        </div>

        {/* Filter */}
        <div className="flex gap-2 mb-4">
          {["all", "high", "medium", "low"].map((level) => (
            <button
              key={level}
              onClick={() => setFilterConfidence(level)}
              className={cn(
                "font-code text-[10px] uppercase tracking-[0.08em] px-3 py-1.5 rounded-md transition-colors duration-150",
                filterConfidence === level
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/50 text-muted-foreground border border-border hover:text-foreground"
              )}
            >
              {level}
            </button>
          ))}
        </div>

        {/* Results */}
        {filtered.length > 0 ? (
          <div className="space-y-2">
            {filtered.map((item, idx) => (
              <div
                key={idx}
                className="flex items-start gap-3 py-3 border-b border-border last:border-0"
              >
                <span
                  className={cn(
                    "font-code text-[9px] uppercase tracking-wider px-2 py-0.5 rounded shrink-0 mt-0.5",
                    item.confidence === "high" && "bg-[#EF444415] text-[#EF4444]",
                    item.confidence === "medium" && "bg-[#F59E0B15] text-primary",
                    item.confidence === "low" && "bg-muted text-muted-foreground"
                  )}
                >
                  {item.confidence}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-sans text-sm text-foreground font-medium truncate">
                      {item.name}
                    </span>
                    <span className="font-code text-[9px] text-muted-foreground bg-muted rounded px-1.5 py-0.5 shrink-0">
                      {item.node_type}
                    </span>
                  </div>
                  <p className="font-code text-[11px] text-muted-foreground truncate">{item.file_path}</p>
                  <p className="font-sans text-[12px] text-muted-foreground mt-0.5">{item.reason}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm text-center py-8">
            {deadCodeItems.length === 0
              ? "No dead code candidates detected — or analysis is still running."
              : "No items match the selected filter."}
          </p>
        )}
      </ReportSection>
    </div>
  );
}

// ─────────────────────────────────────────────
// Security Tab (V2-5.2) — Semgrep findings
// ─────────────────────────────────────────────

function SecurityTab({
  report,
}: {
  report: NonNullable<ReturnType<typeof useReport>["report"]>;
}) {
  // Security data from security_report.semgrep + security_report.vulnerabilities
  const semgrep: {
    findings?: Array<{
      rule_id: string;
      message: string;
      severity: string;
      file_path: string;
      start_line: number;
      category: string;
      fix_suggestion?: string;
    }>;
    total_findings?: number;
    critical_count?: number;
    high_count?: number;
    medium_count?: number;
    low_count?: number;
    scan_status?: string;
  } = (report as any).semgrep ?? {};

  const findings = semgrep.findings ?? [];

  const severityColor: Record<string, string> = {
    critical: "#EF4444",
    high: "#F97316",
    medium: "#F59E0B",
    low: "#6B7A99",
  };

  return (
    <div className="space-y-6">
      <ReportSection title="Security Findings" status={report.agentsStatus.security_agent}>
        {/* Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
          <div className="bg-muted/30 border border-border rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-foreground">{semgrep.total_findings ?? 0}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Total</p>
          </div>
          <div className="bg-[#EF444410] border border-[#EF444430] rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-[#EF4444]">{semgrep.critical_count ?? 0}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Critical</p>
          </div>
          <div className="bg-[#F9731610] border border-[#F9731630] rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-[#F97316]">{semgrep.high_count ?? 0}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">High</p>
          </div>
          <div className="bg-[#F59E0B10] border border-[#F59E0B30] rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-primary">{semgrep.medium_count ?? 0}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Medium</p>
          </div>
          <div className="bg-[#6B7A9910] border border-[#6B7A9930] rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-muted-foreground">{semgrep.low_count ?? 0}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Low</p>
          </div>
        </div>

        {/* Scan status */}
        {semgrep.scan_status && semgrep.scan_status !== "success" && (
          <div className="bg-[#F59E0B10] border border-[#F59E0B30] rounded-md p-3 mb-4">
            <p className="font-code text-[11px] text-primary">
              Scan status: {semgrep.scan_status}
            </p>
          </div>
        )}

        {/* Findings list */}
        {findings.length > 0 ? (
          <div className="space-y-3">
            {findings.map((finding, idx) => (
              <div
                key={idx}
                className="bg-card border border-border rounded-lg p-4 space-y-2"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="font-code text-[9px] uppercase tracking-wider px-2 py-0.5 rounded"
                    style={{
                      color: severityColor[finding.severity] ?? "#6B7A99",
                      backgroundColor: `${severityColor[finding.severity] ?? "#6B7A99"}15`,
                    }}
                  >
                    {finding.severity}
                  </span>
                  <span className="font-code text-[10px] text-muted-foreground bg-muted rounded px-1.5 py-0.5">
                    {finding.category}
                  </span>
                </div>
                <p className="font-sans text-sm text-card-foreground">{finding.message}</p>
                <p className="font-code text-[11px] text-muted-foreground">
                  {finding.file_path}:{finding.start_line}
                </p>
                {finding.fix_suggestion && (
                  <div className="bg-[#10B98110] border border-[#10B98130] rounded p-2 mt-2">
                    <p className="font-code text-[10px] uppercase tracking-wider text-[#10B981] mb-1">Remediation</p>
                    <p className="font-sans text-[12px] text-card-foreground">{finding.fix_suggestion}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm text-center py-8">
            No security findings — either the scan hasn&apos;t run or no issues were detected.
          </p>
        )}
      </ReportSection>
    </div>
  );
}

// ─────────────────────────────────────────────
// Roadmap Tab (V2-6.2)
// ─────────────────────────────────────────────

function RoadmapTab({
  report,
}: {
  report: NonNullable<ReturnType<typeof useReport>["report"]>;
}) {
  // Roadmap data from modernization_plan.roadmap
  const roadmap: Array<{
    sprint: number;
    actions: Array<{
      action: string;
      justification: string;
      estimated_hours: number;
      category: string;
    }>;
  }> = (report as any).roadmap ?? [];

  const categoryColor: Record<string, string> = {
    dead_code: "#EF4444",
    security: "#F97316",
    dependencies: "#06B6D4",
    decoupling: "#8B5CF6",
    refactoring: "#F59E0B",
    testing: "#10B981",
  };

  const totalHours = roadmap.reduce(
    (sum, sprint) => sum + sprint.actions.reduce((s, a) => s + (a.estimated_hours || 0), 0),
    0
  );

  return (
    <div className="space-y-6">
      <ReportSection title="Modernization Roadmap" status={report.agentsStatus.modernization_agent}>
        {/* Summary */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="bg-muted/30 border border-border rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-foreground">{roadmap.length}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Sprints</p>
          </div>
          <div className="bg-muted/30 border border-border rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-primary">
              {roadmap.reduce((sum, s) => sum + s.actions.length, 0)}
            </p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Actions</p>
          </div>
          <div className="bg-muted/30 border border-border rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-secondary">{totalHours}h</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Estimated</p>
          </div>
        </div>

        {/* Sprint table */}
        {roadmap.length > 0 ? (
          <div className="space-y-4">
            {roadmap.map((sprint) => (
              <div key={sprint.sprint} className="bg-card border border-border rounded-lg overflow-hidden">
                {/* Sprint header */}
                <div className="bg-[rgba(30,45,69,0.3)] px-4 py-2 border-b border-border">
                  <span className="font-code text-[11px] uppercase tracking-[0.08em] text-foreground font-medium">
                    Sprint {sprint.sprint}
                  </span>
                  <span className="font-code text-[10px] text-muted-foreground ml-3">
                    {sprint.actions.length} actions &middot;{" "}
                    {sprint.actions.reduce((s, a) => s + (a.estimated_hours || 0), 0)}h estimated
                  </span>
                </div>

                {/* Actions */}
                <div className="divide-y divide-border">
                  {sprint.actions.map((action, idx) => (
                    <div key={idx} className="px-4 py-3 flex items-start gap-3">
                      <span
                        className="font-code text-[9px] uppercase tracking-wider px-2 py-0.5 rounded shrink-0 mt-0.5"
                        style={{
                          color: categoryColor[action.category] ?? "#6B7A99",
                          backgroundColor: `${categoryColor[action.category] ?? "#6B7A99"}15`,
                        }}
                      >
                        {action.category}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-sans text-sm text-card-foreground">{action.action}</p>
                        {action.justification && (
                          <p className="font-sans text-[12px] text-muted-foreground mt-0.5">
                            {action.justification}
                          </p>
                        )}
                      </div>
                      <span className="font-code text-[10px] text-muted-foreground shrink-0">
                        {action.estimated_hours}h
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm text-center py-8">
            No roadmap available — the modernization agent hasn&apos;t generated sprint plans yet.
          </p>
        )}
      </ReportSection>
    </div>
  );
}


// ─────────────────────────────────────────────
// C4 Diagrams Tab (V2-9.2)
// ─────────────────────────────────────────────

function C4DiagramsTab({
  report,
}: {
  report: NonNullable<ReturnType<typeof useReport>["report"]>;
}) {
  const [activeLevel, setActiveLevel] = useState<"context" | "container" | "component">("context");

  // C4 data from documentation_bundle.c4_diagrams
  const c4: {
    context?: string;
    container?: string;
    component?: string;
  } = (report as any).c4Diagrams ?? {};

  const levels = [
    { id: "context" as const, label: "Context", description: "System + external actors" },
    { id: "container" as const, label: "Container", description: "Apps + databases + services" },
    { id: "component" as const, label: "Component", description: "Modules within containers" },
  ];

  const currentChart = c4[activeLevel] ?? "";

  return (
    <div className="space-y-6">
      <ReportSection title="C4 Architecture Diagrams" status={report.agentsStatus.documentation_agent}>
        {/* Level selector */}
        <div className="flex gap-2 mb-6">
          {levels.map((level) => (
            <button
              key={level.id}
              onClick={() => setActiveLevel(level.id)}
              className={cn(
                "flex flex-col items-start px-4 py-2.5 rounded-lg border transition-colors duration-150",
                activeLevel === level.id
                  ? "bg-primary/10 border-primary/40 text-primary"
                  : "bg-muted/30 border-border text-muted-foreground hover:text-foreground hover:border-muted-foreground"
              )}
            >
              <span className="font-sans text-[13px] font-medium">{level.label}</span>
              <span className="font-code text-[9px] uppercase tracking-wider opacity-70">
                {level.description}
              </span>
            </button>
          ))}
        </div>

        {/* Diagram render */}
        {currentChart ? (
          <MermaidDiagram
            chart={currentChart}
            title={`C4 ${activeLevel.charAt(0).toUpperCase() + activeLevel.slice(1)} Diagram`}
            id={`c4-${activeLevel}`}
          />
        ) : (
          <div className="bg-muted/20 border border-border rounded-lg p-8 text-center">
            <p className="font-sans text-sm text-muted-foreground">
              No C4 diagram available for this level — the documentation agent hasn&apos;t generated it yet.
            </p>
          </div>
        )}
      </ReportSection>
    </div>
  );
}
