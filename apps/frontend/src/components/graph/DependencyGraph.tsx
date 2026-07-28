"use client";

import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import dynamic from "next/dynamic";
import { cn } from "@/lib/utils";
import { useGraphData } from "@/hooks/useGraphData";
import { GraphControls, type GraphFilters } from "./GraphControls";
import type { NodeType, EdgeType, GraphNode, GraphEdge } from "@/hooks/useGraphData";

// Dynamically import react-force-graph-2d (no SSR)
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

// ─────────────────────────────────────────────
// Color maps
// ─────────────────────────────────────────────

const NODE_COLORS: Record<NodeType, string> = {
  file: "#6B7A99",
  class: "#8B5CF6",
  function: "#06B6D4",
  module: "#F59E0B",
  package: "#10B981",
};

const EDGE_COLORS: Record<EdgeType, string> = {
  import: "#6B7A99",
  inheritance: "#8B5CF6",
  usage: "#06B6D4",
  composition: "#F97316",
};

// ─────────────────────────────────────────────
// Helper: scale node size by LOC (log scale)
// ─────────────────────────────────────────────

function nodeSize(loc: number): number {
  if (loc <= 0) return 4;
  return Math.max(4, Math.min(20, 3 + Math.log2(loc + 1) * 1.5));
}

// ─────────────────────────────────────────────
// Types for react-force-graph-2d
// ─────────────────────────────────────────────

interface ForceGraphNode {
  id: string;
  name: string;
  type: NodeType;
  loc: number;
  complexity: number;
  isExternal: boolean;
  x?: number;
  y?: number;
}

interface ForceGraphEdge {
  source: string;
  target: string;
  type: EdgeType;
}

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

interface DependencyGraphProps {
  projectId: string;
}

export function DependencyGraph({ projectId }: DependencyGraphProps) {
  const [filters, setFilters] = useState<GraphFilters>({
    nodeTypes: new Set<NodeType>(["file", "class", "function", "module", "package"]),
    edgeTypes: new Set<EdgeType>(["import", "inheritance", "usage", "composition"]),
    searchQuery: "",
    depth: 5,
  });

  const [hoveredNode, setHoveredNode] = useState<ForceGraphNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  const { nodes, edges, stats, isLoading, error } = useGraphData(projectId, {
    depth: filters.depth,
  });

  // Resize observer
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Filter nodes
  const filteredNodes = useMemo(() => {
    return nodes.filter((node) => {
      if (!filters.nodeTypes.has(node.type)) return false;
      if (
        filters.searchQuery &&
        !node.name.toLowerCase().includes(filters.searchQuery.toLowerCase())
      )
        return false;
      return true;
    });
  }, [nodes, filters.nodeTypes, filters.searchQuery]);

  // Filter edges
  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    return edges.filter((edge) => {
      if (!filters.edgeTypes.has(edge.type)) return false;
      if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) return false;
      return true;
    });
  }, [edges, filteredNodes, filters.edgeTypes]);

  // Connected nodes to selected
  const connectedIds = useMemo(() => {
    if (!selectedNode) return new Set<string>();
    const ids = new Set<string>([selectedNode]);
    for (const edge of filteredEdges) {
      const src = typeof edge.source === "string" ? edge.source : (edge.source as unknown as ForceGraphNode).id;
      const tgt = typeof edge.target === "string" ? edge.target : (edge.target as unknown as ForceGraphNode).id;
      if (src === selectedNode) ids.add(tgt);
      if (tgt === selectedNode) ids.add(src);
    }
    return ids;
  }, [selectedNode, filteredEdges]);

  // Graph data
  const graphData = useMemo(
    () => ({
      nodes: filteredNodes.map((n) => ({
        id: n.id,
        name: n.name,
        type: n.type,
        loc: n.loc,
        complexity: n.complexity,
        isExternal: n.isExternal,
      })),
      links: filteredEdges.map((e) => ({
        source: e.source,
        target: e.target,
        type: e.type,
      })),
    }),
    [filteredNodes, filteredEdges]
  );

  // Computed stats for the controls panel
  const computedStats = useMemo(
    () => ({
      totalNodes: stats.totalNodes || nodes.length,
      totalEdges: stats.totalEdges || edges.length,
      filteredNodes: filteredNodes.length,
      filteredEdges: filteredEdges.length,
    }),
    [stats, nodes.length, edges.length, filteredNodes.length, filteredEdges.length]
  );

  // Node paint
  const paintNode = useCallback(
    (node: ForceGraphNode, ctx: CanvasRenderingContext2D) => {
      const size = nodeSize(node.loc);
      const color = NODE_COLORS[node.type] || "#6B7A99";
      const isSelected = selectedNode === node.id;
      const isConnected = connectedIds.has(node.id);
      const dimmed = selectedNode && !isConnected;

      ctx.beginPath();
      ctx.arc(node.x ?? 0, node.y ?? 0, size, 0, 2 * Math.PI);

      if (node.isExternal) {
        // External: dashed border, gray fill, different opacity
        ctx.fillStyle = dimmed ? "rgba(107, 122, 153, 0.15)" : "rgba(107, 122, 153, 0.4)";
        ctx.fill();
        ctx.setLineDash([2, 2]);
        ctx.strokeStyle = dimmed ? "rgba(107, 122, 153, 0.3)" : "#6B7A99";
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.setLineDash([]);
      } else {
        ctx.fillStyle = dimmed
          ? `${color}33`
          : isSelected
          ? color
          : `${color}CC`;
        ctx.fill();

        if (isSelected) {
          ctx.strokeStyle = "#F0F4FF";
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      }

      // Label — always show for non-dimmed nodes
      if (!dimmed) {
        const fontSize = Math.max(4, Math.min(8, size * 0.8));
        ctx.font = `${fontSize}px JetBrains Mono, monospace`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = isSelected
          ? "rgba(240, 244, 255, 1)"
          : "rgba(240, 244, 255, 0.9)";
        const label = node.name.length > 25 ? `${node.name.slice(0, 23)}…` : node.name;
        ctx.fillText(label, node.x ?? 0, (node.y ?? 0) + size + 3);
      }
    },
    [selectedNode, connectedIds]
  );

  // Edge paint
  const paintLink = useCallback(
    (link: ForceGraphEdge, ctx: CanvasRenderingContext2D) => {
      const src = link.source as unknown as ForceGraphNode;
      const tgt = link.target as unknown as ForceGraphNode;
      if (!src.x || !src.y || !tgt.x || !tgt.y) return;

      const color = EDGE_COLORS[link.type] || "#6B7A99";
      const srcId = src.id;
      const tgtId = tgt.id;
      const isConnectedEdge =
        selectedNode && (connectedIds.has(srcId) && connectedIds.has(tgtId));
      const dimmed = selectedNode && !isConnectedEdge;

      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.strokeStyle = dimmed ? `${color}22` : `${color}88`;
      ctx.lineWidth = dimmed ? 0.3 : 0.8;
      ctx.stroke();
    },
    [selectedNode, connectedIds]
  );

  const handleNodeHover = useCallback(
    (node: ForceGraphNode | null, event?: MouseEvent) => {
      setHoveredNode(node);
      if (node && event) {
        setTooltipPos({ x: event.clientX, y: event.clientY });
      }
    },
    []
  );

  const handleNodeClick = useCallback((node: ForceGraphNode) => {
    setSelectedNode((prev) => (prev === node.id ? null : node.id));
  }, []);

  // Loading / error states
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="font-code text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
            Loading graph...
          </span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="font-sans text-[13px] text-[#EF4444]">{error}</p>
          <p className="font-code text-[10px] text-muted-foreground mt-1">
            Failed to load dependency graph
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full min-h-0 overflow-hidden">
      {/* Sidebar Controls */}
      <GraphControls
        filters={filters}
        onFiltersChange={setFilters}
        stats={computedStats}
      />

      {/* Graph Canvas */}
      <div
        ref={containerRef}
        className="flex-1 relative bg-background min-h-0 min-w-0"
      >
        <ForceGraph2D
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          nodeCanvasObject={paintNode as never}
          linkCanvasObject={paintLink as never}
          onNodeHover={handleNodeHover as never}
          onNodeClick={handleNodeClick as never}
          nodeId="id"
          linkSource="source"
          linkTarget="target"
          backgroundColor="#080D18"
          cooldownTicks={100}
          enableZoomInteraction={true}
          enablePanInteraction={true}
        />

        {/* Tooltip */}
        {hoveredNode && (
          <div
            className={cn(
              "fixed z-50 pointer-events-none",
              "bg-card border border-border rounded-[6px]",
              "px-3 py-2.5 shadow-lg max-w-xs"
            )}
            style={{
              left: tooltipPos.x + 12,
              top: tooltipPos.y + 12,
            }}
          >
            <p className="font-sans text-[13px] font-semibold text-foreground">
              {hoveredNode.name}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <span
                className="font-code text-[10px] uppercase tracking-[0.08em] px-1.5 py-0.5 rounded-[3px]"
                style={{
                  backgroundColor: `${NODE_COLORS[hoveredNode.type]}20`,
                  color: NODE_COLORS[hoveredNode.type],
                }}
              >
                {hoveredNode.type}
              </span>
              {hoveredNode.isExternal && (
                <span className="font-code text-[10px] uppercase tracking-[0.08em] text-muted-foreground bg-muted px-1.5 py-0.5 rounded-[3px]">
                  external
                </span>
              )}
            </div>
            <div className="flex gap-3 mt-1.5">
              <span className="font-code text-[10px] text-muted-foreground">
                LOC: <span className="text-foreground">{hoveredNode.loc}</span>
              </span>
              <span className="font-code text-[10px] text-muted-foreground">
                Complexity:{" "}
                <span className="text-foreground">{hoveredNode.complexity}</span>
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
