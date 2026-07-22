"use client";

import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export interface Metric {
  label: string;
  value: string | number;
  color?: string;
}

export interface MetricsGridProps {
  metrics: Metric[];
  className?: string;
}

// ─────────────────────────────────────────────
// MetricsGrid
// ─────────────────────────────────────────────

export function MetricsGrid({ metrics, className }: MetricsGridProps) {
  return (
    <div
      className={cn(
        "grid gap-4",
        className
      )}
      style={{
        gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
      }}
    >
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className="bg-card border border-border rounded-xl p-4 flex flex-col items-start gap-1"
        >
          <span
            className="font-display text-[28px] font-bold leading-tight"
            style={{ color: metric.color ?? "var(--primary)" }}
          >
            {metric.value}
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
            {metric.label}
          </span>
        </div>
      ))}
    </div>
  );
}
