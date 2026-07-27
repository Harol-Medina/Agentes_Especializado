"use client";

import { Header } from "@/components/shared/Header";
import { SubmissionForm } from "@/components/shared/SubmissionForm";
import { useDashboard } from "@/hooks/useDashboard";
import { cn } from "@/lib/utils";

/* ─────────────────────────────────────────────────────────────────────────────
   Static data (agents, pipeline, tech stack — these don't change per request)
   ───────────────────────────────────────────────────────────────────────────── */

const pipelineStages = [
  { id: "01", name: "Ingesta & Análisis", tags: ["GitPython", "Tree-sitter", "JavaParser", "AST"] },
  { id: "02", name: "Almacenamiento", tags: ["PostgreSQL", "pgvector", "asyncpg"] },
  { id: "03", name: "Sistema Multi-Agente", tags: ["Orchestrator", "Arch Agent", "Quality Agent", "Security Agent"] },
  { id: "04", name: "Exportación a Kiro", tags: ["Kiro Spec", "Steering Files", "Hook Defs"] },
];

const agents = [
  { name: "Agente de Arquitectura", description: "Analiza estructura de módulos, dependencias y capas del sistema", color: "#06B6D4", icon: "◇" },
  { name: "Agente de Documentación", description: "Genera docs técnicos, diagramas C4 y README automáticos", color: "#10B981", icon: "◆" },
  { name: "Agente de Seguridad", description: "Detecta vulnerabilidades, secretos expuestos y CVEs", color: "#EF4444", icon: "●" },
  { name: "Agente de Calidad", description: "Propone métricas, code smells y complejidad ciclomática", color: "#8B5CF6", icon: "◆" },
  { name: "Agente de Modernización", description: "Sugiere refactors, migración de dependencias y tech debt", color: "#10B981", icon: "◎" },
  { name: "Agente de Kiro", description: "Genera Specs, Tasks y Hooks importables en Kiro IDE", color: "#F97316", icon: "◎" },
];

const inputSources = [
  { icon: "📁", label: "Repositorios ZIP" },
  { icon: "🔗", label: "URLs Git" },
  { icon: "📄", label: "Archivos PDF" },
  { icon: "📋", label: "Requisitos Funcionales" },
  { icon: "💻", label: "Código Fuente" },
  { icon: "🌿", label: "Ramas Git" },
];

const kiroArtifacts = [
  { name: "Spec Document", file: ".spec.md" },
  { name: "Steering Files", file: "product.md" },
  { name: "Hook Definitions", file: ".hooks.yaml" },
  { name: "Architecture Diagram", file: ".c4.md" },
];

const techStack = [
  { name: "FastAPI", category: "Backend", color: "#10B981" },
  { name: "Spring Boot", category: "Backend", color: "#10B981" },
  { name: "PostgreSQL", category: "Datos", color: "#06B6D4" },
  { name: "pgvector", category: "Vectores", color: "#06B6D4" },
  { name: "Claude Sonnet", category: "LLM", color: "#8B5CF6" },
  { name: "Titan Embed", category: "LLM", color: "#8B5CF6" },
  { name: "AWS", category: "Cloud", color: "#F97316" },
  { name: "Kiro", category: "Exportación", color: "#F59E0B" },
  { name: "Tree-sitter", category: "Parsing", color: "#EF4444" },
  { name: "Next.js", category: "Frontend", color: "#06B6D4" },
  { name: "GitPython", category: "VCS", color: "#10B981" },
  { name: "React Flow", category: "Grafo", color: "#F59E0B" },
];

/* ─────────────────────────────────────────────────────────────────────────────
   Page Component (Dynamic — consumes /api/v1/dashboard)
   ───────────────────────────────────────────────────────────────────────────── */

export default function HomePage() {
  const { data, isLoading, error } = useDashboard();

  const metrics = data?.metrics;
  const recentJobs = data?.recentJobs ?? [];
  const systemStatus = data?.systemStatus ?? "idle";

  return (
    <>
      <Header />
      <main className="relative min-h-[calc(100vh-60px)] overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 bg-grid pointer-events-none" aria-hidden="true" />
        <div className="absolute inset-0 hero-glow pointer-events-none" aria-hidden="true" />

        {/* ═══ HERO ═══ */}
        <section className="container relative z-10 pt-12 pb-10">
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-10 lg:gap-12">
            {/* Left: Hero content */}
            <div className="flex flex-col gap-5">
              {/* System status pill (dynamic) */}
              <div className={cn(
                "inline-flex items-center gap-2 self-start px-3 py-1.5 rounded-full border",
                systemStatus === "active"
                  ? "border-[#10B981]/30 bg-[#10B981]/10"
                  : "border-border bg-muted/30"
              )}>
                <span className={cn(
                  "w-2 h-2 rounded-full",
                  systemStatus === "active"
                    ? "bg-[#10B981] shadow-[0_0_6px_#10B981] animate-status-pulse"
                    : "bg-muted-foreground"
                )} />
                <span className={cn(
                  "font-code text-[10px] uppercase tracking-[0.08em]",
                  systemStatus === "active" ? "text-[#10B981]" : "text-muted-foreground"
                )}>
                  {systemStatus === "active" ? "Analizando" : "Sistema Listo"} · V2.4.1
                </span>
              </div>

              {/* Headline */}
              <h1 className="font-heading font-bold text-foreground leading-[1.1]">
                Excavando el código{" "}
                <span className="italic text-primary">legacy</span>
                <br />
                con inteligencia artificial
              </h1>

              {/* Description */}
              <p className="font-sans text-[15px] text-muted-foreground leading-relaxed max-w-lg">
                Agente IA que analiza, documenta y moderniza proyectos de software
                legacy de forma automatizada. Arquitectura multi-agente con modelos
                de Amazon Bedrock (Claude Sonnet).
              </p>

              {/* Dynamic stat counters */}
              <div className="flex flex-wrap gap-8 pt-4">
                <div>
                  <p className="font-heading text-[28px] font-bold text-primary">
                    {metrics?.completedProjects ?? 0}
                  </p>
                  <p className="font-code text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                    Proyectos Completados
                  </p>
                </div>
                <div>
                  <p className="font-heading text-[28px] font-bold text-secondary">
                    {metrics?.analyzingProjects ?? 0}
                  </p>
                  <p className="font-code text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                    En Análisis
                  </p>
                </div>
                <div>
                  <p className="font-heading text-[28px] font-bold text-foreground">
                    {metrics?.totalProjects ?? 0}
                  </p>
                  <p className="font-code text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                    Total Proyectos
                  </p>
                </div>
              </div>

              {/* Submission form */}
              <div className="pt-4">
                <SubmissionForm />
              </div>
            </div>

            {/* Right: Pipeline Activo card */}
            <div className="hidden lg:block">
              <div className="bg-card border border-border rounded-xl p-5 space-y-4">
                <h3 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                  Pipeline Activo
                </h3>
                <div className="space-y-4">
                  {pipelineStages.map((stage) => (
                    <div key={stage.id} className="flex items-start gap-3">
                      <span className="font-code text-[11px] font-medium text-primary bg-primary/15 px-1.5 py-0.5 rounded shrink-0">
                        {stage.id}
                      </span>
                      <div className="flex flex-col gap-1.5">
                        <span className="font-sans text-[13px] font-medium text-card-foreground">
                          {stage.name}
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {stage.tags.map((tag) => (
                            <span key={tag} className="font-code text-[9px] tracking-wider text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded-[3px]">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ═══ METRICS BAR (dynamic) ═══ */}
        <section className="container relative z-10 pb-12">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 border-y border-border py-6">
            <MetricItem
              icon="●" color="text-[#10B981]"
              value={`${metrics?.activeAgents ?? 0}/${metrics?.totalAgents ?? 7}`}
              label="Agentes Activos"
            />
            <MetricItem
              icon="⚡" color="text-primary"
              value={`${metrics?.totalProjects ?? 0}`}
              label="Proyectos Totales"
            />
            <MetricItem
              icon="○" color="text-secondary"
              value={`${metrics?.queuedProjects ?? 0}`}
              label="En Cola"
            />
            <MetricItem
              icon="○" color="text-[#10B981]"
              value={`${metrics?.successRate ?? 0}%`}
              label="Tasa de Éxito"
            />
            <MetricItem
              icon="▲" color="text-[#F97316]"
              value={`${metrics?.failedProjects ?? 0}`}
              label="Fallidos"
            />
          </div>

          {/* Connection indicator */}
          {error && (
            <div className="mt-3 flex items-center gap-2 justify-center">
              <span className="w-1.5 h-1.5 rounded-full bg-[#F97316]" />
              <span className="font-code text-[10px] text-muted-foreground">
                Backend no disponible — datos en modo offline
              </span>
            </div>
          )}
        </section>

        {/* ═══ AGENTES ═══ */}
        <section id="agentes" className="container relative z-10 pb-16">
          <div className="mb-6">
            <h2 className="font-heading text-xl font-bold text-foreground">Agentes Especializados</h2>
            <p className="font-sans text-[13px] text-muted-foreground mt-1">7 agentes coordinados por el orquestador central</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-8">
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {agents.map((agent) => (
                <div
                  key={agent.name}
                  className="bg-card border border-border rounded-lg p-5 hover:-translate-y-0.5 transition-all duration-150"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center text-lg"
                      style={{ backgroundColor: `${agent.color}20`, border: `1px solid ${agent.color}40` }}
                    >
                      <span style={{ color: agent.color }}>{agent.icon}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={cn(
                        "w-[6px] h-[6px] rounded-full",
                        systemStatus === "active"
                          ? "bg-[#10B981] shadow-[0_0_6px_#10B981] animate-status-pulse"
                          : "bg-muted-foreground"
                      )} />
                      <span className={cn(
                        "font-code text-[10px] uppercase tracking-[0.08em]",
                        systemStatus === "active" ? "text-[#10B981]" : "text-muted-foreground"
                      )}>
                        {systemStatus === "active" ? "activo" : "idle"}
                      </span>
                    </div>
                  </div>
                  <h3 className="font-heading text-[15px] font-bold text-card-foreground mb-1.5">{agent.name}</h3>
                  <p className="font-sans text-[12px] text-muted-foreground leading-relaxed">{agent.description}</p>
                </div>
              ))}
            </div>

            {/* Right sidebar */}
            <div className="space-y-6">
              <div className="bg-card border border-border rounded-lg p-5">
                <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-4">Fuentes de Entrada Soportadas</h4>
                <div className="space-y-3">
                  {inputSources.map((source) => (
                    <div key={source.label} className="flex items-center gap-3">
                      <span className="text-sm">{source.icon}</span>
                      <span className="font-sans text-[13px] text-card-foreground">{source.label}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-card border border-border rounded-lg p-5">
                <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-4">Artefactos Exportados a Kiro</h4>
                <div className="space-y-3">
                  {kiroArtifacts.map((artifact) => (
                    <div key={artifact.name} className="flex items-center justify-between">
                      <span className="font-sans text-[13px] text-card-foreground">{artifact.name}</span>
                      <span className="font-code text-[10px] text-[#10B981] bg-[#10B981]/10 px-2 py-0.5 rounded">{artifact.file}</span>
                    </div>
                  ))}
                </div>
                <button className="w-full mt-5 font-sans text-[12px] font-semibold tracking-[0.04em] text-secondary border border-secondary/40 bg-secondary/10 px-4 py-2.5 rounded hover:bg-secondary/20 transition-colors duration-150">
                  Exportar a Kiro →
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* ═══ PROYECTOS RECIENTES (dynamic) ═══ */}
        <section id="proyectos" className="container relative z-10 pb-16">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="font-heading text-xl font-bold text-foreground">Proyectos Recientes</h2>
              <p className="font-sans text-[13px] text-muted-foreground mt-1">Repositorios legacy en análisis o completados</p>
            </div>
          </div>

          {recentJobs.length > 0 ? (
            <>
              {/* Desktop table */}
              <div className="hidden lg:block bg-card border border-border rounded-lg overflow-hidden">
                <div className="grid grid-cols-[1fr_120px_120px] gap-4 px-5 py-3 bg-[rgba(30,45,69,0.3)] border-b border-border">
                  <span className="font-code text-[10px] uppercase tracking-[0.08em] text-muted-foreground">Repositorio</span>
                  <span className="font-code text-[10px] uppercase tracking-[0.08em] text-muted-foreground text-center">Estado</span>
                  <span className="font-code text-[10px] uppercase tracking-[0.08em] text-muted-foreground text-center">Agente Actual</span>
                </div>
                {recentJobs.map((job) => (
                  <a
                    key={job.id}
                    href={`/analysis/${job.id}`}
                    className="grid grid-cols-[1fr_120px_120px] gap-4 px-5 py-4 border-b border-border last:border-b-0 hover:bg-[rgba(245,158,11,0.04)] transition-colors duration-150 items-center"
                  >
                    <span className="font-code text-[13px] text-card-foreground">{job.name}</span>
                    <div className="flex items-center justify-center gap-2">
                      <span className={cn("w-[6px] h-[6px] rounded-full", statusDotColor(job.status))} />
                      <span className="font-code text-[10px] uppercase tracking-[0.08em] text-muted-foreground">{job.status}</span>
                    </div>
                    <span className="font-code text-[10px] text-muted-foreground text-center">
                      {job.currentAgent ?? "—"}
                    </span>
                  </a>
                ))}
              </div>

              {/* Mobile cards */}
              <div className="lg:hidden space-y-3">
                {recentJobs.map((job) => (
                  <a
                    key={job.id}
                    href={`/analysis/${job.id}`}
                    className="block bg-card border border-border rounded-lg p-4 space-y-2 hover:border-primary/30 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-code text-[13px] text-card-foreground">{job.name}</span>
                      <div className="flex items-center gap-1.5">
                        <span className={cn("w-[5px] h-[5px] rounded-full", statusDotColor(job.status))} />
                        <span className="font-code text-[10px] uppercase tracking-[0.08em] text-muted-foreground">{job.status}</span>
                      </div>
                    </div>
                    {job.currentAgent && (
                      <p className="font-code text-[10px] text-muted-foreground">Agente: {job.currentAgent}</p>
                    )}
                  </a>
                ))}
              </div>
            </>
          ) : (
            <div className="bg-card border border-border rounded-lg p-10 text-center">
              <p className="font-sans text-sm text-muted-foreground">
                {isLoading ? "Cargando proyectos..." : "No hay proyectos aún. Envía un repositorio para comenzar."}
              </p>
            </div>
          )}
        </section>

        {/* ═══ STACK TECNOLÓGICO ═══ */}
        <section className="container relative z-10 pb-16">
          <div className="mb-6">
            <h2 className="font-heading text-xl font-bold text-foreground">Stack Tecnológico</h2>
            <p className="font-sans text-[13px] text-muted-foreground mt-1">Tecnologías integradas en el pipeline del agente</p>
          </div>
          <div className="flex flex-wrap gap-3">
            {techStack.map((tech) => (
              <div key={tech.name} className="flex items-center gap-2 bg-muted/50 border border-border px-3 py-2 rounded-md hover:border-muted-foreground transition-colors duration-150">
                <span className="font-sans text-[13px] font-medium text-card-foreground">{tech.name}</span>
                <span className="font-code text-[9px] uppercase tracking-[0.08em] px-1.5 py-0.5 rounded-[3px]" style={{ color: tech.color, backgroundColor: `${tech.color}15` }}>{tech.category}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ═══ FOOTER ═══ */}
        <footer className="container relative z-10 pb-8 pt-8 border-t border-border">
          <p className="font-code text-[11px] text-muted-foreground text-center tracking-wider">
            Software Archaeologist · Hecho con ♥ · Powered by Amazon Bedrock + Kiro
          </p>
        </footer>
      </main>
    </>
  );
}

/* ─── Helper components ─── */

function MetricItem({ icon, color, value, label }: { icon: string; color: string; value: string; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className={`text-lg ${color}`}>{icon}</span>
      <div>
        <p className={`font-heading text-xl font-bold ${color}`}>{value}</p>
        <p className="font-code text-[10px] uppercase tracking-[0.08em] text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

function statusDotColor(status: string): string {
  switch (status) {
    case "completed": return "bg-[#10B981] shadow-[0_0_6px_#10B981]";
    case "analyzing":
    case "cloning": return "bg-primary shadow-[0_0_6px_#F59E0B] animate-status-pulse";
    case "failed": return "bg-[#EF4444] shadow-[0_0_6px_#EF4444]";
    case "pending": return "bg-muted-foreground";
    default: return "bg-muted-foreground";
  }
}
