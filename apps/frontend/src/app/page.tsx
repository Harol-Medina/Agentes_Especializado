import { Header } from "@/components/shared/Header";
import { SubmissionForm } from "@/components/shared/SubmissionForm";

export default function HomePage() {
  return (
    <>
      <Header />
      <main className="relative min-h-[calc(100vh-60px)] overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 bg-grid pointer-events-none" aria-hidden="true" />
        <div className="absolute inset-0 hero-glow pointer-events-none" aria-hidden="true" />

        {/* Hero section */}
        <section className="container relative z-10 pt-20 pb-16">
          <div className="grid grid-hero gap-16 items-center" style={{ gridTemplateColumns: "1fr 420px" }}>
            {/* Left column: content */}
            <div className="flex flex-col gap-6 max-w-xl">
              <h1 className="font-display font-bold text-foreground">
                Understand any codebase{" "}
                <span className="text-primary">in minutes</span>
              </h1>
              <p className="font-body text-base text-muted-foreground leading-relaxed">
                Submit a public GitHub repository and let our AI agents analyze its
                architecture, dependencies, quality, and security. Get an interactive
                dependency graph, chat with the code, and export a Kiro modernization spec.
              </p>

              {/* Form */}
              <div className="pt-2">
                <SubmissionForm />
              </div>

              {/* Feature pills */}
              <div className="flex flex-wrap gap-2 pt-2">
                {["Dependency Graph", "AI Chat", "Architecture Report", "Kiro Export"].map(
                  (feature) => (
                    <span
                      key={feature}
                      className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground px-2.5 py-1 rounded-[3px] border border-border bg-muted/40"
                    >
                      {feature}
                    </span>
                  )
                )}
              </div>
            </div>

            {/* Right column: decorative card (hidden at 900px via grid collapse) */}
            <div className="hidden min-[901px]:block">
              <div className="bg-card border border-border rounded-xl p-6 space-y-5">
                {/* Card header */}
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-success shadow-[0_0_6px_#10B981]" />
                  <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                    Analysis Pipeline
                  </span>
                </div>

                {/* Agent steps preview */}
                <div className="space-y-3">
                  {[
                    { name: "Repository Agent", status: "completed", color: "bg-success" },
                    { name: "Architecture Agent", status: "completed", color: "bg-success" },
                    { name: "Quality Agent", status: "running", color: "bg-primary" },
                    { name: "Security Agent", status: "pending", color: "bg-muted-foreground" },
                    { name: "Documentation Agent", status: "pending", color: "bg-muted-foreground" },
                    { name: "Modernization Agent", status: "pending", color: "bg-muted-foreground" },
                    { name: "Kiro Agent", status: "pending", color: "bg-muted-foreground" },
                  ].map((agent) => (
                    <div key={agent.name} className="flex items-center gap-3">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${agent.color} ${
                          agent.status === "running" ? "animate-pulse-slow" : ""
                        }`}
                      />
                      <span className="font-body text-[13px] text-card-foreground flex-1">
                        {agent.name}
                      </span>
                      <span
                        className={`font-mono text-[10px] uppercase tracking-[0.08em] ${
                          agent.status === "completed"
                            ? "text-success"
                            : agent.status === "running"
                            ? "text-primary"
                            : "text-muted-foreground"
                        }`}
                      >
                        {agent.status}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Progress bar */}
                <div className="pt-2">
                  <div className="h-[3px] w-full bg-border rounded-sm overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-sm transition-[width] duration-600 ease-in-out"
                      style={{ width: "35%" }}
                    />
                  </div>
                  <p className="font-mono text-[10px] text-muted-foreground mt-1.5 tracking-wider">
                    2 / 7 AGENTS COMPLETE
                  </p>
                </div>

                {/* Stats row */}
                <div className="grid grid-cols-3 gap-4 pt-3 border-t border-border">
                  {[
                    { label: "Files", value: "347" },
                    { label: "Modules", value: "12" },
                    { label: "LOC", value: "28.4k" },
                  ].map((stat) => (
                    <div key={stat.label} className="text-center">
                      <p className="font-display text-lg font-bold text-foreground">
                        {stat.value}
                      </p>
                      <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                        {stat.label}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
