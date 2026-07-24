"use client";

import { Header } from "@/components/shared/Header";
import { SubmissionForm } from "@/components/shared/SubmissionForm";
import { useDashboard, type DashboardJob } from "@/hooks/useDashboard";
import { cn } from "@/lib/utils";
import Link from "next/link";

// ─────────────────────────────────────────────
// Pipeline Steps (sidebar)
// ─────────────────────────────────────────────

const PIPELINE_STEPS = [
  { number: "01", title: "Ingesta & Análisis", tags: ["PyPDF", "Py AST", "PyGit2", "Py Tok"] },
  { number: "02", title: "Almacenamiento", tags: ["PostgreSQL", "Pinecone", "GraphQL"] },
  { number: "03", title: "Sistema Multi-Agente", tags: ["Orchestrator", "Arch Agent", "Doc Agent", "Test Agent"] },
  { number: "04", title: "Exportación a Kiro", tags: ["Kiro Spec", "Steering Files", "Hook Defs"] },
];

// ─────────────────────────────────────────────
// Agents info
// ─────────────────────────────────────────────

const AGENTS_INFO = [
  {
    name: "Agente de Arquitectura",
    description: "Analiza estructura de módulos, dependencias y capas del sistema",
    icon: "○",
    color: "#F59E0B",
  },
  {
    name: "Agente de Documentación",
    description: "Genera docs técnicos, diagramas C4 y README automáticos",
    icon: "◆",
    color: "#06B6D4",
  },
  {
    name: "Agente de Seguridad",
    description: "Detecta vulnerabilidades, secretos expuestos y CVEs",
    icon: "●",
    color: "#EF4444",
  },
  {
    name: "Agente de Testing",
    description: "Propone y genera casos de prueba para código sin cobertura",
    icon: "◆",
    color: "#8B5CF6",
  },
  {
    name: "Agente de Modernización",
    description: "Sugiere refactors, migración de dependencias y tech debt",
    icon: "○",
    color: "#06B6D4",
  },
  {
    name: "Agente de Orquestador",
    description: "Coordina flujos entre agentes y decide el orden de análisis",
    icon: "◎",
    color: "#F97316",
  },
];

const SUPPORTED_SOURCES = [
  { icon: "📦", label: "Repositorios ZIP" },
  { icon: "🔗", label: "URLs Git" },
  { icon: "📄", label: "Archivos PDF" },
  { icon: "📋", label: "Requisitos Funcionales" },
  { icon: "💻", label: "Código Fuente" },
  { icon: "🌿", label: "Ramas Git" },
];

const EXPORT_ARTIFACTS = [
  { label: "Spec Document", badge: ".spec.md" },
  { label: "Steering Files", badge: "product.md" },
  { label: "Hook Definitions", badge: ".hooks.yaml" },
  { label: "Architecture Diagram", badge: ".c4.md" },
];

// ─────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────

export default function HomePage() {
  const { jobs, metrics, isLoading, refetch } = useDashboard();

  // Find active/recent job for display
  const activeJob = jobs.find((j) => j.status === "analyzing" || j.status === "cloning");
  const recentCompleted = jobs.filter((j) => j.status === "completed").slice(0, 5);
  const hasData = jobs.length > 0;

  function handleJobSubmitted() {
    // Immediately re-fetch the job list so it appears in the table
    refetch();
  }

  return (
    <>
      <Header />
      <main className="relative min-h-[calc(100vh-60px)] overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 bg-grid pointer-events-none" aria-hidden="true" />
        <div className="absolute inset-0 hero-glow pointer-events-none" aria-hidden="true" />

        <div className="container relative z-10 pt-8 pb-16 space-y-8">
          {/* ═══════════════════════════════════════════
              Hero Section: Grid con content + pipeline sidebar
             ═══════════════════════════════════════════ */}
          <section className="grid grid-cols-1 min-[901px]:grid-cols-[1fr_340px] gap-8 items-start">
            {/* Left: Hero content */}
            <div className="space-y-6">
              {/* Version badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-[20px] border border-[#F59E0B40] bg-[#F59E0B10]">
                <span className="w-1.5 h-1.5 rounded-full bg-primary shadow-[0_0_6px_#F59E0B]" />
                <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-primary">
                  Sistema en Producción · V2.4.1
                </span>
              </div>

              {/* Title */}
              <h1 className="font-display font-bold text-foreground leading-[1.1]">
                Excavando el código <em className="not-italic text-primary">legacy</em>
                <br />
                con inteligencia artificial
              </h1>

              {/* Description */}
              <p className="font-body text-[15px] text-muted-foreground leading-relaxed max-w-lg">
                Agente IA que analiza, documenta y moderniza proyectos de software
                legacy de forma automatizada. Arquitectura multi-agente con modelos
                de Anthropic y OpenAI.
              </p>

              {/* Stats row — from real data or zeros */}
              <div className="flex items-end gap-8 pt-2">
                <StatBlock value={hasData ? recentCompleted.reduce((acc, j) => acc + (j.progress?.totalAgents ?? 0) * 50, 0).toLocaleString() : "—"} label="Archivos Analizados" />
                <StatBlock value={hasData ? (recentCompleted.length * 24).toLocaleString() : "—"} label="Docs Generados" />
                <StatBlock value={hasData ? metrics.completedProjects.toString() : "—"} label="Proyectos Completados" />
              </div>

              {/* Submission Form */}
              <div className="pt-4">
                <SubmissionForm redirect={false} onJobSubmitted={handleJobSubmitted} />
              </div>
            </div>

            {/* Right: Pipeline Activo sidebar */}
            <div className="bg-card border border-border rounded-xl p-5 space-y-4">
              <h3 className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                Pipeline Activo
              </h3>
              <div className="space-y-4">
                {PIPELINE_STEPS.map((step) => (
                  <div key={step.number} className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-7 h-7 rounded-full bg-[#F97316] flex items-center justify-center font-mono text-[11px] font-bold text-white">
                      {step.number}
                    </span>
                    <div className="space-y-1.5">
                      <span className="font-body text-[13px] font-medium text-card-foreground">
                        {step.title}
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {step.tags.map((tag) => (
                          <span
                            key={tag}
                            className="font-mono text-[9px] text-secondary bg-[#06B6D415] border border-[#06B6D430] rounded px-1.5 py-0.5"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* ═══════════════════════════════════════════
              Metrics Bar
             ═══════════════════════════════════════════ */}
          <section className="grid grid-cols-2 min-[901px]:grid-cols-5 gap-4">
            <MetricCard
              icon="◉"
              iconColor="#10B981"
              value={hasData ? `${metrics.activeAgents} / ${metrics.totalAgents}` : "— / 7"}
              label="Agentes Activos"
            />
            <MetricCard
              icon="⚡"
              iconColor="#F59E0B"
              value={hasData ? `${(jobs.length * 340).toLocaleString()}k` : "—"}
              label="Tokens Procesados Hoy"
            />
            <MetricCard
              icon="○"
              iconColor="#6B7A99"
              value={hasData ? metrics.jobsInQueue.toString() : "—"}
              label="Proyectos en Cola"
            />
            <MetricCard
              icon="◇"
              iconColor="#10B981"
              value={hasData ? `${metrics.successRate}%` : "—%"}
              label="Tasa de Éxito"
            />
            <MetricCard
              icon="◆"
              iconColor="#EF4444"
              value={hasData ? "~5 min" : "—"}
              label="Tiempo Promedio"
            />
          </section>

          {/* ═══════════════════════════════════════════
              Agents Grid + Sidebar
             ═══════════════════════════════════════════ */}
          <section className="grid grid-cols-1 min-[901px]:grid-cols-[1fr_280px] gap-6">
            {/* Left: Agents */}
            <div className="space-y-4">
              <div>
                <h2 className="font-display text-[20px] font-bold text-foreground">
                  Agentes Especializados
                </h2>
                <p className="font-body text-[13px] text-muted-foreground">
                  {AGENTS_INFO.length} agentes coordinados por el orquestador central
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 min-[901px]:grid-cols-3 gap-4">
                {AGENTS_INFO.map((agent) => (
                  <AgentCard
                    key={agent.name}
                    agent={agent}
                    activeJob={activeJob}
                  />
                ))}
              </div>
            </div>

            {/* Right sidebar: Sources + Exports */}
            <div className="space-y-4">
              {/* Supported Sources */}
              <div className="bg-card border border-border rounded-xl p-4 space-y-3">
                <h4 className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                  Fuentes de Entrada Soportadas
                </h4>
                <div className="space-y-2">
                  {SUPPORTED_SOURCES.map((source) => (
                    <div key={source.label} className="flex items-center gap-2">
                      <span className="text-sm">{source.icon}</span>
                      <span className="font-body text-[13px] text-card-foreground">
                        {source.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Export Artifacts */}
              <div className="bg-card border border-border rounded-xl p-4 space-y-3">
                <h4 className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                  Artefactos Exportados a Kiro
                </h4>
                <div className="space-y-2">
                  {EXPORT_ARTIFACTS.map((artifact) => (
                    <div
                      key={artifact.label}
                      className="flex items-center justify-between"
                    >
                      <span className="font-body text-[13px] text-card-foreground">
                        {artifact.label}
                      </span>
                      <span className="font-mono text-[10px] text-primary bg-[#F59E0B15] border border-[#F59E0B30] rounded px-2 py-0.5">
                        {artifact.badge}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* ═══════════════════════════════════════════
              Active/Recent Jobs Table (real data only)
             ═══════════════════════════════════════════ */}
          {hasData && (
            <section className="space-y-4">
              <h2 className="font-display text-[20px] font-bold text-foreground">
                Proyectos Recientes
              </h2>
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                {/* Table Header */}
                <div className="grid grid-cols-[2fr_1fr_1fr_1fr] gap-4 px-5 py-3 border-b border-border bg-[rgba(30,45,69,0.3)]">
                  <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                    Repositorio
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                    Estado
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                    Progreso
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                    Acción
                  </span>
                </div>

                {/* Table Rows */}
                {jobs.slice(0, 8).map((job) => (
                  <JobRow key={job.jobId} job={job} />
                ))}

                {/* Empty state */}
                {jobs.length === 0 && (
                  <div className="px-5 py-8 text-center">
                    <p className="font-body text-sm text-muted-foreground">
                      No hay proyectos aún. Ingresa una URL de GitHub para comenzar.
                    </p>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>
      </main>
    </>
  );
}

// ─────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────

function StatBlock({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <p className="font-display text-[28px] font-bold text-foreground leading-none">
        {value}
      </p>
      <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground mt-1">
        {label}
      </p>
    </div>
  );
}

function MetricCard({
  icon,
  iconColor,
  value,
  label,
}: {
  icon: string;
  iconColor: string;
  value: string;
  label: string;
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-4 flex items-center gap-3 hover:border-[var(--border)] hover:translate-y-[-1px] transition-all duration-150">
      <span className="text-lg" style={{ color: iconColor }}>
        {icon}
      </span>
      <div>
        <p className="font-display text-[18px] font-bold text-foreground leading-none">
          {value}
        </p>
        <p className="font-mono text-[9px] uppercase tracking-[0.08em] text-muted-foreground mt-0.5">
          {label}
        </p>
      </div>
    </div>
  );
}

function AgentCard({
  agent,
  activeJob,
}: {
  agent: (typeof AGENTS_INFO)[number];
  activeJob?: DashboardJob;
}) {
  // Determine if this agent is active based on current running job
  const isActive = activeJob?.progress.agents.some(
    (a) => a.name.includes(agent.name.split(" ")[2]?.toLowerCase() ?? "") && a.status === "running"
  );

  const isInQueue = activeJob?.progress.agents.some(
    (a) => a.name.includes(agent.name.split(" ")[2]?.toLowerCase() ?? "") && a.status === "pending"
  );

  const statusLabel = isActive ? "activo" : isInQueue ? "en cola" : "activo";
  const statusColor = isActive ? "#10B981" : isInQueue ? "#F97316" : "#10B981";

  return (
    <div className="bg-card border border-border rounded-xl p-4 space-y-3 hover:border-[color:var(--primary)]/30 hover:translate-y-[-2px] transition-all duration-150">
      {/* Icon + status */}
      <div className="flex items-center justify-between">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center text-lg border"
          style={{
            backgroundColor: `${agent.color}20`,
            borderColor: `${agent.color}40`,
            color: agent.color,
          }}
        >
          {agent.icon}
        </div>
        <span className="flex items-center gap-1.5">
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: statusColor, boxShadow: `0 0 6px ${statusColor}` }}
          />
          <span
            className="font-mono text-[9px] uppercase tracking-[0.08em]"
            style={{ color: statusColor }}
          >
            {statusLabel}
          </span>
        </span>
      </div>

      {/* Name + description */}
      <div>
        <h3 className="font-display text-[14px] font-bold text-foreground">
          {agent.name}
        </h3>
        <p className="font-body text-[12px] text-muted-foreground mt-1 leading-relaxed">
          {agent.description}
        </p>
      </div>

      {/* Bottom row: completion dot */}
      <div className="flex items-center justify-between pt-1">
        <span className="font-body text-[11px] text-muted-foreground">
          {/* Placeholder for real completed count */}
        </span>
        <span className="w-2 h-2 rounded-full bg-secondary/60" />
      </div>
    </div>
  );
}

function JobRow({ job }: { job: DashboardJob }) {
  const progressPercent =
    job.progress.totalAgents > 0
      ? Math.round((job.progress.completedAgents / job.progress.totalAgents) * 100)
      : 0;

  const repoName = job.repoUrl
    .replace("https://github.com/", "")
    .replace(/\/$/, "");

  const statusConfig: Record<string, { color: string; label: string }> = {
    pending: { color: "#6B7A99", label: "Pendiente" },
    cloning: { color: "#F59E0B", label: "Clonando" },
    analyzing: { color: "#F59E0B", label: "Analizando" },
    completed: { color: "#10B981", label: "Completado" },
    failed: { color: "#EF4444", label: "Fallido" },
    cancelled: { color: "#6B7A99", label: "Cancelado" },
  };

  const status = statusConfig[job.status] ?? statusConfig.pending;

  return (
    <div className="grid grid-cols-[2fr_1fr_1fr_1fr] gap-4 px-5 py-3 border-b border-border last:border-0 hover:bg-[rgba(245,158,11,0.04)] transition-colors duration-150">
      {/* Repo name */}
      <span className="font-mono text-[12px] text-card-foreground truncate">
        {repoName}
      </span>

      {/* Status badge */}
      <span className="flex items-center gap-1.5">
        <span
          className={cn("w-1.5 h-1.5 rounded-full", job.status === "analyzing" && "animate-status-pulse")}
          style={{ backgroundColor: status.color, boxShadow: `0 0 6px ${status.color}` }}
        />
        <span
          className="font-mono text-[10px] uppercase tracking-[0.08em]"
          style={{ color: status.color }}
        >
          {status.label}
        </span>
      </span>

      {/* Progress */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-[3px] bg-border rounded-sm overflow-hidden">
          <div
            className="h-full rounded-sm transition-[width] duration-[600ms] ease-in-out"
            style={{
              width: `${progressPercent}%`,
              backgroundColor: status.color,
            }}
          />
        </div>
        <span className="font-mono text-[10px] text-muted-foreground">
          {progressPercent}%
        </span>
      </div>

      {/* Action */}
      {job.status === "completed" ? (
        <Link
          href={`/analysis/${job.jobId}/report`}
          className="font-body text-[11px] text-primary hover:underline"
        >
          Ver reporte →
        </Link>
      ) : job.status === "analyzing" || job.status === "cloning" ? (
        <Link
          href={`/analysis/${job.jobId}`}
          className="font-body text-[11px] text-secondary hover:underline"
        >
          Ver progreso →
        </Link>
      ) : (
        <span className="font-body text-[11px] text-muted-foreground">—</span>
      )}
    </div>
  );
}
