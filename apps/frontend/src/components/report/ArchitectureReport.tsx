"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useReport } from "@/hooks/useReport";
import { useRouter } from "next/navigation";
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
  const router = useRouter();

  const failedAgents = report
    ? Object.entries(report.agentsStatus).filter(([, s]) => s === "failed").map(([name]) => name)
    : [];

  async function handleReanalyze() {
    if (!report) return;
    // Navigate to home — user can re-submit the same repo
    // The repo URL isn't in the report, so we redirect to start a new analysis
    router.push("/");
  }

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

      {/* Failed agents banner */}
      {failedAgents.length > 0 && (
        <div className="flex items-center justify-between bg-[#EF444410] border border-[#EF444430] rounded-lg px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#EF4444] shadow-[0_0_6px_#EF4444]" />
            <span className="font-sans text-sm text-card-foreground">
              {failedAgents.length} agent{failedAgents.length > 1 ? "s" : ""} failed
            </span>
            <span className="font-code text-[10px] text-muted-foreground">
              ({failedAgents.map((a) => a.replace("_agent", "")).join(", ")})
            </span>
          </div>
          <button
            onClick={handleReanalyze}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md",
              "bg-primary text-primary-foreground",
              "font-sans text-xs font-semibold uppercase tracking-wider",
              "hover:opacity-90 transition-opacity duration-150"
            )}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3" aria-hidden="true">
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
            Re-analyze
          </button>
        </div>
      )}

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
            {report.documentation?.summary ? (
              <div className="space-y-4">
                <p className="font-sans text-sm text-card-foreground leading-relaxed">
                  {report.documentation.summary}
                </p>
                {report.documentation.sections && report.documentation.sections.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                      Generated Sections
                    </h4>
                    {report.documentation.sections.map((section, idx) => (
                      <div key={idx} className="flex items-center gap-2 py-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] flex-shrink-0" />
                        <span className="font-sans text-sm text-card-foreground">
                          {(section as Record<string, unknown>).title as string || (section as Record<string, unknown>).name as string || `Section ${idx + 1}`}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">
                Documentation bundle not yet generated.
              </p>
            )}
          </ReportSection>
        )}
        {activeTab === "modernization" && (
          <ReportSection
            title="Modernization Plan"
            status={report.agentsStatus.modernization_agent}
          >
            {report.modernization?.summary ? (
              <div className="space-y-4">
                <p className="font-sans text-sm text-card-foreground leading-relaxed">
                  {report.modernization.summary}
                </p>
                {report.modernization.phases && report.modernization.phases.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                      Phases ({report.modernization.phases.length})
                    </h4>
                    {report.modernization.phases.map((phase, idx) => (
                      <div key={idx} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                        <span className="font-sans text-sm text-card-foreground">
                          {phase.name || `Phase ${idx + 1}`}
                        </span>
                        <div className="flex gap-2">
                          {phase.priority && (
                            <span className="font-code text-[9px] text-primary bg-[#F59E0B15] rounded px-2 py-0.5">
                              {phase.priority}
                            </span>
                          )}
                          {phase.effort && (
                            <span className="font-code text-[9px] text-muted-foreground bg-muted rounded px-2 py-0.5">
                              {phase.effort}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">
                Modernization plan not yet generated.
              </p>
            )}
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
                </div>
                <p className="font-sans text-[12px] text-muted-foreground mt-0.5">
                  {layer.responsibility}
                </p>
                {"modules" in layer && layer.modules && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {String(layer.modules).split(/[,\n]/).map((mod) => mod.trim()).filter(Boolean).map((mod, mi) => (
                      <span
                        key={mi}
                        className="font-code text-[10px] text-secondary bg-[#06B6D410] border border-[#06B6D430] rounded px-1.5 py-0.5 break-all"
                      >
                        {mod.split(".").pop()}
                      </span>
                    ))}
                  </div>
                )}
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
  const quality = report.quality;

  return (
    <div className="space-y-4">
      {/* Summary */}
      {quality?.summary && (
        <p className="font-sans text-sm text-card-foreground leading-relaxed mb-4">
          {quality.summary}
        </p>
      )}

      {/* Metrics */}
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
        <div className="flex items-center justify-between py-2 border-b border-border">
          <span className="font-sans text-sm text-card-foreground">Max Dependency Depth</span>
          <span className="font-code text-[11px] text-foreground">
            {report.metrics.maxDependencyDepth}
          </span>
        </div>
      </div>

      {/* Code Smells */}
      {quality?.codeSmells && quality.codeSmells.length > 0 && (
        <div className="mt-4">
          <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-3">
            Code Smells ({quality.codeSmells.length})
          </h4>
          <div className="space-y-2">
            {quality.codeSmells.slice(0, 15).map((smell, idx) => (
              <div key={idx} className="flex items-start gap-3 py-2 border-b border-border last:border-0">
                <span className={cn(
                  "font-code text-[9px] uppercase tracking-wider px-2 py-0.5 rounded shrink-0 mt-0.5",
                  (smell.severity === "high") && "bg-[#EF444415] text-[#EF4444]",
                  (smell.severity === "medium") && "bg-[#F59E0B15] text-primary",
                  (!smell.severity || smell.severity === "low") && "bg-muted text-muted-foreground",
                )}>
                  {smell.severity || "info"}
                </span>
                <div className="flex-1 min-w-0">
                  <span className="font-sans text-sm text-foreground">{smell.name || smell.description}</span>
                  {smell.file && (
                    <p className="font-code text-[11px] text-muted-foreground truncate">{smell.file}</p>
                  )}
                </div>
              </div>
            ))}
            {quality.codeSmells.length > 15 && (
              <p className="text-[11px] text-muted-foreground italic">
                +{quality.codeSmells.length - 15} more code smells
              </p>
            )}
          </div>
        </div>
      )}

      {/* Hotspots */}
      {quality?.hotspots && quality.hotspots.length > 0 && (
        <div className="mt-4">
          <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-3">
            Complexity Hotspots
          </h4>
          <div className="space-y-2">
            {quality.hotspots.slice(0, 10).map((hotspot, idx) => (
              <div key={idx} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                <span className="font-sans text-sm text-card-foreground truncate">
                  {(hotspot as Record<string, unknown>).name as string || (hotspot as Record<string, unknown>).file as string || `Hotspot ${idx + 1}`}
                </span>
                <span className="font-code text-[10px] text-[#F97316] bg-[#F9731615] rounded px-2 py-0.5">
                  {(hotspot as Record<string, unknown>).complexity as string || (hotspot as Record<string, unknown>).score as string || "high"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
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

  // Dead code data comes from quality report
  const deadCodeItems: Array<{
    name: string;
    node_type: string;
    file_path: string;
    confidence: string;
    reason: string;
  }> = (report.quality?.deadCode ?? []) as any;

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
  // Security data from report.security
  const secData = report.security;
  const vulnerabilities = secData?.vulnerabilities ?? [];

  const severityColor: Record<string, string> = {
    critical: "#EF4444",
    high: "#F97316",
    medium: "#F59E0B",
    low: "#6B7A99",
  };

  const critCount = vulnerabilities.filter((v) => v.severity === "critical").length;
  const highCount = vulnerabilities.filter((v) => v.severity === "high").length;
  const medCount = vulnerabilities.filter((v) => v.severity === "medium").length;
  const lowCount = vulnerabilities.filter((v) => v.severity === "low").length;

  return (
    <div className="space-y-6">
      <ReportSection title="Security Analysis" status={report.agentsStatus.security_agent}>
        {/* Summary */}
        {secData?.summary && (
          <p className="font-sans text-sm text-card-foreground leading-relaxed mb-4">
            {secData.summary}
          </p>
        )}

        {/* Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
          <div className="bg-muted/30 border border-border rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-foreground">{vulnerabilities.length}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Total</p>
          </div>
          <div className="bg-[#EF444410] border border-[#EF444430] rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-[#EF4444]">{critCount}</p>
            <p className="font-code text-[9px] uppercase tracking-[0.08em] text-muted-foreground">Critical</p>
          </div>
          <div className="bg-[#F9731610] border border-[#F9731630] rounded-md p-3 text-center">
            <p className="font-heading text-lg font-bold text-[#F97316]">{highCount}</p>
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

        {/* Vulnerabilities list */}
        {vulnerabilities.length > 0 ? (
          <div className="space-y-3">
            {vulnerabilities.map((vuln, idx) => (
              <div key={idx} className="bg-card border border-border rounded-lg p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <span
                    className="font-code text-[9px] uppercase tracking-wider px-2 py-0.5 rounded"
                    style={{
                      color: severityColor[vuln.severity || "low"] ?? "#6B7A99",
                      backgroundColor: `${severityColor[vuln.severity || "low"] ?? "#6B7A99"}15`,
                    }}
                  >
                    {vuln.severity || "info"}
                  </span>
                  {vuln.cwe && (
                    <span className="font-code text-[10px] text-muted-foreground bg-muted rounded px-1.5 py-0.5">
                      {vuln.cwe}
                    </span>
                  )}
                </div>
                <p className="font-sans text-sm font-medium text-foreground">{vuln.title || vuln.description}</p>
                {vuln.title && vuln.description && (
                  <p className="font-sans text-[12px] text-muted-foreground">{vuln.description}</p>
                )}
                {vuln.file && (
                  <p className="font-code text-[11px] text-muted-foreground">{vuln.file}</p>
                )}
                {vuln.recommendation && (
                  <div className="bg-[#10B98110] border border-[#10B98130] rounded p-2 mt-2">
                    <p className="font-code text-[10px] uppercase tracking-wider text-[#10B981] mb-1">Fix</p>
                    <p className="font-sans text-[12px] text-card-foreground">{vuln.recommendation}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm text-center py-8">
            No security vulnerabilities detected — or the security agent hasn&apos;t completed.
          </p>
        )}

        {/* Recommendations */}
        {secData?.recommendations && secData.recommendations.length > 0 && (
          <div className="mt-4">
            <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-3">
              Recommendations
            </h4>
            <ul className="space-y-2">
              {secData.recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[#10B981] flex-shrink-0" />
                  <span className="font-sans text-sm text-card-foreground">{rec}</span>
                </li>
              ))}
            </ul>
          </div>
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
  // Roadmap data from modernization report
  const mod = report.modernization;
  const phases = mod?.phases ?? [];
  const quickWins = mod?.quickWins ?? [];

  return (
    <div className="space-y-6">
      <ReportSection title="Modernization Roadmap" status={report.agentsStatus.modernization_agent}>
        {/* Summary */}
        {mod?.summary && (
          <p className="font-sans text-sm text-card-foreground leading-relaxed mb-4">
            {mod.summary}
          </p>
        )}

        {/* Quick Wins */}
        {quickWins.length > 0 && (
          <div className="mb-6">
            <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-[#10B981] mb-3">
              Quick Wins
            </h4>
            <ul className="space-y-2">
              {quickWins.map((win, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[#10B981] flex-shrink-0" />
                  <span className="font-sans text-sm text-card-foreground">{typeof win === "string" ? win : JSON.stringify(win)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Phases */}
        {phases.length > 0 ? (
          <div className="space-y-4">
            {phases.map((phase, idx) => (
              <div key={idx} className="bg-card border border-border rounded-lg overflow-hidden">
                <div className="bg-[rgba(30,45,69,0.3)] px-4 py-2 border-b border-border flex items-center justify-between">
                  <span className="font-code text-[11px] uppercase tracking-[0.08em] text-foreground font-medium">
                    {phase.name || `Phase ${idx + 1}`}
                  </span>
                  <div className="flex gap-2">
                    {phase.priority && (
                      <span className="font-code text-[9px] text-primary bg-[#F59E0B15] rounded px-2 py-0.5">
                        {phase.priority}
                      </span>
                    )}
                    {phase.effort && (
                      <span className="font-code text-[9px] text-muted-foreground bg-muted rounded px-2 py-0.5">
                        {phase.effort}
                      </span>
                    )}
                  </div>
                </div>
                <div className="px-4 py-3">
                  {phase.description && (
                    <p className="font-sans text-sm text-card-foreground mb-2">{phase.description}</p>
                  )}
                  {phase.tasks && phase.tasks.length > 0 && (
                    <ul className="space-y-1">
                      {phase.tasks.map((task, ti) => (
                        <li key={ti} className="flex items-start gap-2">
                          <span className="mt-1.5 w-1 h-1 rounded-full bg-muted-foreground flex-shrink-0" />
                          <span className="font-sans text-[12px] text-muted-foreground">{task}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm text-center py-8">
            No modernization roadmap available — the modernization agent hasn&apos;t completed.
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

  // C4 data from documentation report
  const c4: Record<string, unknown> = (report.documentation?.c4Diagrams ?? {}) as Record<string, unknown>;

  const levels = [
    { id: "context" as const, label: "Context", description: "System + external actors" },
    { id: "container" as const, label: "Container", description: "Apps + databases + services" },
    { id: "component" as const, label: "Component", description: "Modules within containers" },
  ];

  const currentChart = (c4[activeLevel] as string) ?? "";

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
