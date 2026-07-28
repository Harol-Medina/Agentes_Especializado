"use client";

import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export interface ReportSectionProps {
  title: string;
  status?: "completed" | "failed" | "skipped" | "pending" | "running";
  children: React.ReactNode;
  className?: string;
}

// ─────────────────────────────────────────────
// Status Badge
// ─────────────────────────────────────────────

const statusConfig: Record<
  string,
  { label: string; color: string; dotColor: string }
> = {
  completed: {
    label: "Completed",
    color: "text-[#10B981]",
    dotColor: "bg-[#10B981]",
  },
  failed: {
    label: "Failed",
    color: "text-[#EF4444]",
    dotColor: "bg-[#EF4444]",
  },
  skipped: {
    label: "Skipped",
    color: "text-muted-foreground",
    dotColor: "bg-muted-foreground",
  },
};

function StatusBadge({ status }: { status: string }) {
  const config = statusConfig[status] ?? statusConfig.skipped;

  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={cn("w-1.5 h-1.5 rounded-full", config.dotColor)}
        style={{ boxShadow: `0 0 6px currentColor` }}
      />
      <span
        className={cn(
          "font-code text-[10px] uppercase tracking-[0.08em]",
          config.color
        )}
      >
        {config.label}
      </span>
    </span>
  );
}

// ─────────────────────────────────────────────
// ReportSection
// ─────────────────────────────────────────────

export function ReportSection({
  title,
  status,
  children,
  className,
}: ReportSectionProps) {
  return (
    <section
      className={cn(
        "bg-card border border-border rounded-xl p-6 animate-fade-in",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-heading text-[20px] font-bold text-foreground">
          {title}
        </h3>
        {status && <StatusBadge status={status} />}
      </div>

      {/* Content */}
      {status === "failed" ? (
        <p className="text-muted-foreground text-sm italic">
          Analysis incomplete — this agent failed during execution.
        </p>
      ) : status === "skipped" ? (
        <p className="text-muted-foreground text-sm italic">
          This section was skipped due to missing prerequisites.
        </p>
      ) : (
        <div className="space-y-3">{children}</div>
      )}
    </section>
  );
}
