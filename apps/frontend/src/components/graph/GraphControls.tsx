"use client";

import { cn } from "@/lib/utils";
import type { NodeType, EdgeType, GraphStats } from "@/hooks/useGraphData";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export interface GraphFilters {
  nodeTypes: Set<NodeType>;
  edgeTypes: Set<EdgeType>;
  searchQuery: string;
  depth: number;
}

interface GraphControlsProps {
  filters: GraphFilters;
  onFiltersChange: (filters: GraphFilters) => void;
  stats: GraphStats;
}

// ─────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────

const NODE_TYPE_OPTIONS: { value: NodeType; label: string; color: string }[] = [
  { value: "file", label: "File", color: "#6B7A99" },
  { value: "class", label: "Class", color: "#8B5CF6" },
  { value: "function", label: "Function", color: "#06B6D4" },
  { value: "module", label: "Module", color: "#F59E0B" },
  { value: "package", label: "Package", color: "#10B981" },
];

const EDGE_TYPE_OPTIONS: { value: EdgeType; label: string; color: string }[] = [
  { value: "import", label: "Import", color: "#6B7A99" },
  { value: "inheritance", label: "Inheritance", color: "#8B5CF6" },
  { value: "usage", label: "Usage", color: "#06B6D4" },
  { value: "composition", label: "Composition", color: "#F97316" },
];

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

export function GraphControls({
  filters,
  onFiltersChange,
  stats,
}: GraphControlsProps) {
  function toggleNodeType(type: NodeType) {
    const next = new Set(filters.nodeTypes);
    if (next.has(type)) {
      next.delete(type);
    } else {
      next.add(type);
    }
    onFiltersChange({ ...filters, nodeTypes: next });
  }

  function toggleEdgeType(type: EdgeType) {
    const next = new Set(filters.edgeTypes);
    if (next.has(type)) {
      next.delete(type);
    } else {
      next.add(type);
    }
    onFiltersChange({ ...filters, edgeTypes: next });
  }

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    onFiltersChange({ ...filters, searchQuery: e.target.value });
  }

  function handleDepthChange(e: React.ChangeEvent<HTMLInputElement>) {
    onFiltersChange({ ...filters, depth: Number(e.target.value) });
  }

  return (
    <aside
      className={cn(
        "w-[280px] min-w-[280px] h-full overflow-y-auto",
        "bg-card border-r border-border rounded-xl",
        "p-4 flex flex-col gap-5"
      )}
    >
      {/* Search */}
      <div>
        <label className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-2 block">
          Search
        </label>
        <input
          type="text"
          placeholder="Filter by name..."
          value={filters.searchQuery}
          onChange={handleSearchChange}
          className={cn(
            "w-full px-3 py-2 text-[13px] font-body",
            "bg-background border border-border rounded-[6px]",
            "text-foreground placeholder:text-muted-foreground",
            "focus:outline-none focus:ring-2 focus:ring-ring"
          )}
        />
      </div>

      {/* Node Types */}
      <div>
        <label className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-2 block">
          Node Types
        </label>
        <div className="flex flex-col gap-1.5">
          {NODE_TYPE_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className="flex items-center gap-2 cursor-pointer group"
            >
              <input
                type="checkbox"
                checked={filters.nodeTypes.has(opt.value)}
                onChange={() => toggleNodeType(opt.value)}
                className="sr-only"
              />
              <span
                className={cn(
                  "w-3.5 h-3.5 rounded-[3px] border-2 flex items-center justify-center transition-colors",
                  filters.nodeTypes.has(opt.value)
                    ? "border-transparent"
                    : "border-border group-hover:border-muted-foreground"
                )}
                style={{
                  backgroundColor: filters.nodeTypes.has(opt.value)
                    ? opt.color
                    : "transparent",
                }}
              >
                {filters.nodeTypes.has(opt.value) && (
                  <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                    <path
                      d="M1.5 4L3.5 6L6.5 2"
                      stroke="#080D18"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </span>
              <span className="font-body text-[13px] text-card-foreground">
                {opt.label}
              </span>
              <span
                className="ml-auto w-2 h-2 rounded-full"
                style={{ backgroundColor: opt.color }}
              />
            </label>
          ))}
        </div>
      </div>

      {/* Edge Types */}
      <div>
        <label className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-2 block">
          Edge Types
        </label>
        <div className="flex flex-col gap-1.5">
          {EDGE_TYPE_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className="flex items-center gap-2 cursor-pointer group"
            >
              <input
                type="checkbox"
                checked={filters.edgeTypes.has(opt.value)}
                onChange={() => toggleEdgeType(opt.value)}
                className="sr-only"
              />
              <span
                className={cn(
                  "w-3.5 h-3.5 rounded-[3px] border-2 flex items-center justify-center transition-colors",
                  filters.edgeTypes.has(opt.value)
                    ? "border-transparent"
                    : "border-border group-hover:border-muted-foreground"
                )}
                style={{
                  backgroundColor: filters.edgeTypes.has(opt.value)
                    ? opt.color
                    : "transparent",
                }}
              >
                {filters.edgeTypes.has(opt.value) && (
                  <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                    <path
                      d="M1.5 4L3.5 6L6.5 2"
                      stroke="#080D18"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </span>
              <span className="font-body text-[13px] text-card-foreground">
                {opt.label}
              </span>
              <span
                className="ml-auto w-2.5 h-0.5 rounded-full"
                style={{ backgroundColor: opt.color }}
              />
            </label>
          ))}
        </div>
      </div>

      {/* Depth Slider */}
      <div>
        <label className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-2 block">
          Depth: {filters.depth}
        </label>
        <input
          type="range"
          min={1}
          max={10}
          value={filters.depth}
          onChange={handleDepthChange}
          className="w-full accent-primary"
        />
        <div className="flex justify-between font-mono text-[10px] text-muted-foreground mt-1">
          <span>1</span>
          <span>10</span>
        </div>
      </div>

      {/* Stats */}
      <div className="mt-auto pt-4 border-t border-border">
        <label className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-2 block">
          Statistics
        </label>
        <div className="grid grid-cols-2 gap-2">
          <StatItem label="Nodes" value={stats.totalNodes} />
          <StatItem label="Edges" value={stats.totalEdges} />
          <StatItem label="Filtered N" value={stats.filteredNodes} />
          <StatItem label="Filtered E" value={stats.filteredEdges} />
        </div>
      </div>
    </aside>
  );
}

function StatItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col">
      <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
        {label}
      </span>
      <span className="font-display text-sm font-bold text-foreground">
        {value}
      </span>
    </div>
  );
}
