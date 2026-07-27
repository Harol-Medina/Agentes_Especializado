import { Header } from "@/components/shared/Header";

/* ─────────────────────────────────────────────────────────────────────────────
   Data — adapted to the real Software Archaeologist project
   ───────────────────────────────────────────────────────────────────────────── */

const pipelineStages = [
  {
    id: "01",
    name: "Ingesta & Análisis",
    tags: ["GitPython", "Tree-sitter", "JavaParser", "AST"],
  },
  {
    id: "02",
    name: "Almacenamiento",
    tags: ["PostgreSQL", "pgvector", "asyncpg"],
  },
  {
    id: "03",
    name: "Sistema Multi-Agente",
    tags: ["Orchestrator", "Arch Agent", "Quality Agent", "Security Agent"],
  },
  {
    id: "04",
    name: "Exportación a Kiro",
    tags: ["Kiro Spec", "Steering Files", "Hook Defs"],
  },
];

const metrics = [
  { value: "7/7", label: "Agentes Activos", color: "text-[#10B981]", icon: "●" },
  { value: "2.4M", label: "Tokens Procesados", color: "text-primary", icon: "⚡" },
  { value: "4", label: "Proyectos en Cola", color: "text-secondary", icon: "○" },
  { value: "98.7%", label: "Tasa de Éxito", color: "text-[#10B981]", icon: "○" },
  { value: "14 min", label: "Tiempo Promedio", color: "text-[#F97316]", icon: "▲" },
];

const agents = [
  {
    name: "Agente de Arquitectura",
    description: "Analiza estructura de módulos, dependencias y capas del sistema",
    tasks: 142,
    status: "activo" as const,
    color: "#06B6D4",
    icon: "◇",
  },
  {
    name: "Agente de Documentación",
    description: "Genera docs técnicos, diagramas C4 y README automáticos",
    tasks: 89,
    status: "activo" as const,
    color: "#10B981",
    icon: "◆",
  },
  {
    name: "Agente de Seguridad",
    description: "Detecta vulnerabilidades, secretos expuestos y CVEs",
    tasks: 34,
    status: "activo" as const,
    color: "#EF4444",
    icon: "●",
  },
  {
    name: "Agente de Calidad",
    description: "Propone métricas, code smells y complejidad ciclomática",
    tasks: 67,
    status: "activo" as const,
    color: "#8B5CF6",
    icon: "◆",
  },
  {
    name: "Agente de Modernización",
    description: "Sugiere refactors, migración de dependencias y tech debt",
    tasks: 57,
    status: "activo" as const,
    color: "#10B981",
    icon: "◎",
  },
  {
    name: "Agente de Kiro",
    description: "Genera Specs, Tasks y Hooks importables en Kiro IDE",
    tasks: 312,
    status: "activo" as const,
    color: "#F97316",
    icon: "◎",
  },
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

const recentProjects = [
  {
    name: "crm-legacy-2019",
    language: "Java",
    langColor: "#F59E0B",
    files: 1842,
    agents: 5,
    status: "completo" as const,
    progress: 100,
  },
  {
    name: "billing-monolith",
    language: "PHP",
    langColor: "#8B5CF6",
    files: 673,
    agents: 3,
    status: "analizando" as const,
    progress: 62,
  },
  {
    name: "inventory-api-v1",
    language: "Python",
    langColor: "#06B6D4",
    files: 289,
    agents: 4,
    status: "analizando" as const,
    progress: 38,
  },
  {
    name: "auth-service-old",
    language: "Node.js",
    langColor: "#10B981",
    files: 154,
    agents: 2,
    status: "en cola" as const,
    progress: 0,
  },
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
   Page Component
   ───────────────────────────────────────────────────────────────────────────── */

export default function HomePage() {
  return (
    <>
      <Header />
      <main className="relative min-h-[calc(100vh-60px)] overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 bg-grid pointer-events-none" aria-hidden="true" />
        <div className="absolute inset-0 hero-glow pointer-events-none" aria-hidden="true" />

        {/* ═══════════════════════════════════════════════════════════════════
            HERO SECTION
            ═══════════════════════════════════════════════════════════════════ */}
        <section className="container relative z-10 pt-12 pb-10">
          <div className="grid gap-10 lg:gap-16 items-start" style={{ gridTemplateColumns: "1fr" }}>
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-10 lg:gap-12">
              {/* Left: Hero content */}
              <div className="flex flex-col gap-5">
                {/* System status pill */}
                <div className="inline-flex items-center gap-2 self-start px-3 py-1.5 rounded-full border border-[#10B981]/30 bg-[#10B981]/10">
                  <span className="w-2 h-2 rounded-full bg-[#10B981] shadow-[0_0_6px_#10B981] animate-status-pulse" />
                  <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#10B981]">
                    Sistema en Producción · V2.4.1
                  </span>
                </div>

                {/* Headline */}
                <h1 className="font-display font-bold text-foreground leading-[1.1]">
                  Excavando el código{" "}
                  <span className="italic text-primary">legacy</span>
                  <br />
                  con inteligencia artificial
                </h1>

                {/* Description */}
                <p className="font-body text-[15px] text-muted-foreground leading-relaxed max-w-lg">
                  Agente IA que analiza, documenta y moderniza proyectos de software
                  legacy de forma automatizada. Arquitectura multi-agente con modelos
                  de Amazon Bedrock (Claude Sonnet).
                </p>

                {/* Stat counters */}
                <div className="flex flex-wrap gap-8 pt-4">
                  <div>
                    <p className="font-display text-[28px] font-bold text-primary">48,291</p>
                    <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                      Archivos Analizados
                    </p>
                  </div>
                  <div>
                    <p className="font-display text-[28px] font-bold text-secondary">1,847</p>
                    <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                      Docs Generados
                    </p>
                  </div>
                  <div>
                    <p className="font-display text-[28px] font-bold text-foreground">23</p>
                    <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                      Proyectos Completados
                    </p>
                  </div>
                </div>
              </div>

              {/* Right: Pipeline Activo card */}
              <div className="hidden lg:block">
                <div className="bg-card border border-border rounded-xl p-5 space-y-4">
                  <h3 className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                    Pipeline Activo
                  </h3>

                  <div className="space-y-4">
                    {pipelineStages.map((stage) => (
                      <div key={stage.id} className="flex items-start gap-3">
                        <span className="font-mono text-[11px] font-medium text-primary bg-primary/15 px-1.5 py-0.5 rounded shrink-0">
                          {stage.id}
                        </span>
                        <div className="flex flex-col gap-1.5">
                          <span className="font-body text-[13px] font-medium text-card-foreground">
                            {stage.name}
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {stage.tags.map((tag) => (
                              <span
                                key={tag}
                                className="font-mono text-[9px] tracking-wider text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded-[3px]"
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
              </div>
            </div>
          </div>
        </section>

        {/* ═══════════════════════════════════════════════════════════════════
            METRICS BAR
            ═══════════════════════════════════════════════════════════════════ */}
        <section className="container relative z-10 pb-12">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 border-y border-border py-6">
            {metrics.map((metric) => (
              <div key={metric.label} className="flex items-center gap-3">
                <span className={`text-lg ${metric.color}`}>{metric.icon}</span>
                <div>
                  <p className={`font-display text-xl font-bold ${metric.color}`}>
                    {metric.value}
                  </p>
                  <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                    {metric.label}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ═══════════════════════════════════════════════════════════════════
            AGENTES ESPECIALIZADOS
            ═══════════════════════════════════════════════════════════════════ */}
        <section id="agentes" className="container relative z-10 pb-16">
          <div className="mb-6">
            <h2 className="font-display text-xl font-bold text-foreground">
              Agentes Especializados
            </h2>
            <p className="font-body text-[13px] text-muted-foreground mt-1">
              7 agentes coordinados por el orquestador central
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-8">
            {/* Agents grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {agents.map((agent) => (
                <div
                  key={agent.name}
                  className="bg-card border border-border rounded-lg p-5 hover:border-[color:var(--hover-color)] hover:-translate-y-0.5 transition-all duration-150 group"
                  style={{ "--hover-color": agent.color } as React.CSSProperties}
                >
                  {/* Card header */}
                  <div className="flex items-center justify-between mb-3">
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center text-lg"
                      style={{
                        backgroundColor: `${agent.color}20`,
                        border: `1px solid ${agent.color}40`,
                      }}
                    >
                      <span style={{ color: agent.color }}>{agent.icon}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span
                        className="w-[6px] h-[6px] rounded-full shadow-[0_0_6px_var(--dot-color)] animate-status-pulse"
                        style={{
                          backgroundColor: agent.status === "activo" ? "#10B981" : "#6B7A99",
                          "--dot-color": agent.status === "activo" ? "#10B981" : "transparent",
                        } as React.CSSProperties}
                      />
                      <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#10B981]">
                        {agent.status}
                      </span>
                    </div>
                  </div>

                  {/* Card body */}
                  <h3 className="font-display text-[15px] font-bold text-card-foreground mb-1.5">
                    {agent.name}
                  </h3>
                  <p className="font-body text-[12px] text-muted-foreground leading-relaxed mb-4">
                    {agent.description}
                  </p>

                  {/* Card footer */}
                  <div className="flex items-center justify-between pt-3 border-t border-border">
                    <span className="font-mono text-[10px] text-muted-foreground tracking-wider">
                      {agent.tasks} tareas completadas
                    </span>
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: agent.color }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Right sidebar */}
            <div className="space-y-6">
              {/* Fuentes de Entrada */}
              <div className="bg-card border border-border rounded-lg p-5">
                <h4 className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-4">
                  Fuentes de Entrada Soportadas
                </h4>
                <div className="space-y-3">
                  {inputSources.map((source) => (
                    <div key={source.label} className="flex items-center gap-3">
                      <span className="text-sm">{source.icon}</span>
                      <span className="font-body text-[13px] text-card-foreground">
                        {source.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Artefactos Exportados */}
              <div className="bg-card border border-border rounded-lg p-5">
                <h4 className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-4">
                  Artefactos Exportados a Kiro
                </h4>
                <div className="space-y-3">
                  {kiroArtifacts.map((artifact) => (
                    <div key={artifact.name} className="flex items-center justify-between">
                      <span className="font-body text-[13px] text-card-foreground">
                        {artifact.name}
                      </span>
                      <span className="font-mono text-[10px] text-[#10B981] bg-[#10B981]/10 px-2 py-0.5 rounded">
                        {artifact.file}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Export button */}
                <button className="w-full mt-5 font-body text-[12px] font-semibold tracking-[0.04em] text-secondary border border-secondary/40 bg-secondary/10 px-4 py-2.5 rounded hover:bg-secondary/20 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-secondary/50">
                  Exportar a Kiro →
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* ═══════════════════════════════════════════════════════════════════
            PROYECTOS RECIENTES
            ═══════════════════════════════════════════════════════════════════ */}
        <section id="proyectos" className="container relative z-10 pb-16">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="font-display text-xl font-bold text-foreground">
                Proyectos Recientes
              </h2>
              <p className="font-body text-[13px] text-muted-foreground mt-1">
                Repositorios legacy en análisis o completados
              </p>
            </div>
            <button className="font-body text-[12px] font-medium text-muted-foreground border border-border px-3 py-1.5 rounded hover:text-foreground hover:border-muted-foreground transition-colors duration-150">
              Ver todos →
            </button>
          </div>

          {/* Table (desktop) */}
          <div className="hidden lg:block bg-card border border-border rounded-lg overflow-hidden">
            {/* Table header */}
            <div className="grid grid-cols-[1fr_100px_80px_70px_120px_140px] gap-4 px-5 py-3 bg-[rgba(30,45,69,0.3)] border-b border-border">
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                Repositorio
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground text-center">
                Lenguaje
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground text-center">
                Archivos
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground text-center">
                Agentes
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                Estado
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground text-right">
                Progreso
              </span>
            </div>

            {/* Table rows */}
            {recentProjects.map((project) => (
              <div
                key={project.name}
                className="grid grid-cols-[1fr_100px_80px_70px_120px_140px] gap-4 px-5 py-4 border-b border-border last:border-b-0 hover:bg-[rgba(245,158,11,0.04)] transition-colors duration-150 items-center"
              >
                <span className="font-mono text-[13px] text-card-foreground">
                  {project.name}
                </span>
                <span className="text-center">
                  <span
                    className="font-mono text-[10px] px-2 py-0.5 rounded"
                    style={{
                      color: project.langColor,
                      backgroundColor: `${project.langColor}15`,
                    }}
                  >
                    {project.language}
                  </span>
                </span>
                <span className="font-body text-[13px] text-muted-foreground text-center">
                  {project.files.toLocaleString()}
                </span>
                <span className="font-body text-[13px] text-muted-foreground text-center">
                  {project.agents}
                </span>
                <div className="flex items-center gap-2">
                  <span
                    className="w-[6px] h-[6px] rounded-full"
                    style={{
                      backgroundColor:
                        project.status === "completo"
                          ? "#10B981"
                          : project.status === "analizando"
                          ? "#F59E0B"
                          : "#6B7A99",
                      boxShadow:
                        project.status === "completo"
                          ? "0 0 6px #10B981"
                          : project.status === "analizando"
                          ? "0 0 6px #F59E0B"
                          : "none",
                    }}
                  />
                  <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                    {project.status}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-[3px] bg-border rounded-sm overflow-hidden">
                    <div
                      className="h-full rounded-sm transition-[width] duration-[600ms] ease-in-out"
                      style={{
                        width: `${project.progress}%`,
                        backgroundColor:
                          project.status === "completo"
                            ? "#10B981"
                            : project.status === "analizando"
                            ? "#F59E0B"
                            : "#6B7A99",
                      }}
                    />
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground w-8 text-right">
                    {project.progress}%
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Mobile: card view for projects */}
          <div className="lg:hidden space-y-3">
            {recentProjects.map((project) => (
              <div
                key={project.name}
                className="bg-card border border-border rounded-lg p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[13px] text-card-foreground">
                    {project.name}
                  </span>
                  <span
                    className="font-mono text-[10px] px-2 py-0.5 rounded"
                    style={{
                      color: project.langColor,
                      backgroundColor: `${project.langColor}15`,
                    }}
                  >
                    {project.language}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-muted-foreground">
                  <span className="font-mono text-[11px]">{project.files} archivos</span>
                  <span className="font-mono text-[11px]">{project.agents} agentes</span>
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-[5px] h-[5px] rounded-full"
                      style={{
                        backgroundColor:
                          project.status === "completo"
                            ? "#10B981"
                            : project.status === "analizando"
                            ? "#F59E0B"
                            : "#6B7A99",
                      }}
                    />
                    <span className="font-mono text-[10px] uppercase tracking-[0.08em]">
                      {project.status}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-[3px] bg-border rounded-sm overflow-hidden">
                    <div
                      className="h-full rounded-sm"
                      style={{
                        width: `${project.progress}%`,
                        backgroundColor:
                          project.status === "completo"
                            ? "#10B981"
                            : project.status === "analizando"
                            ? "#F59E0B"
                            : "#6B7A99",
                      }}
                    />
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {project.progress}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ═══════════════════════════════════════════════════════════════════
            STACK TECNOLÓGICO
            ═══════════════════════════════════════════════════════════════════ */}
        <section className="container relative z-10 pb-16">
          <div className="mb-6">
            <h2 className="font-display text-xl font-bold text-foreground">
              Stack Tecnológico
            </h2>
            <p className="font-body text-[13px] text-muted-foreground mt-1">
              Tecnologías integradas en el pipeline del agente
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            {techStack.map((tech) => (
              <div
                key={tech.name}
                className="flex items-center gap-2 bg-muted/50 border border-border px-3 py-2 rounded-md hover:border-muted-foreground transition-colors duration-150"
              >
                <span className="font-body text-[13px] font-medium text-card-foreground">
                  {tech.name}
                </span>
                <span
                  className="font-mono text-[9px] uppercase tracking-[0.08em] px-1.5 py-0.5 rounded-[3px]"
                  style={{
                    color: tech.color,
                    backgroundColor: `${tech.color}15`,
                  }}
                >
                  {tech.category}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* ═══════════════════════════════════════════════════════════════════
            FOOTER
            ═══════════════════════════════════════════════════════════════════ */}
        <footer className="container relative z-10 pb-8 pt-8 border-t border-border">
          <p className="font-mono text-[11px] text-muted-foreground text-center tracking-wider">
            Software Archaeologist · Hecho con ♥ · Powered by Amazon Bedrock + Kiro
          </p>
        </footer>
      </main>
    </>
  );
}
