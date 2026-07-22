"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE_URL } from "@/lib/constants";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export type NodeType = "file" | "class" | "function" | "module" | "package";
export type EdgeType = "import" | "inheritance" | "usage" | "composition";

export interface GraphNode {
  id: string;
  type: NodeType;
  name: string;
  qualifiedName?: string;
  loc: number;
  complexity: number;
  isExternal: boolean;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  metadata: Record<string, unknown>;
}

export interface GraphStats {
  totalNodes: number;
  totalEdges: number;
  filteredNodes: number;
  filteredEdges: number;
}

export interface GraphFilter {
  module?: string;
  edgeType?: EdgeType;
  depth?: number;
}

interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: GraphStats;
}

// ─────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────

export function useGraphData(projectId: string, filters: GraphFilter = {}) {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [stats, setStats] = useState<GraphStats>({
    totalNodes: 0,
    totalEdges: 0,
    filteredNodes: 0,
    filteredEdges: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGraph = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (filters.module) params.set("module", filters.module);
      if (filters.edgeType) params.set("edgeType", filters.edgeType);
      if (filters.depth !== undefined) params.set("depth", String(filters.depth));

      const query = params.toString() ? `?${params.toString()}` : "";
      const res = await fetch(
        `${API_BASE_URL}/v1/projects/${projectId}/graph${query}`
      );

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          (body as { message?: string }).message || `HTTP ${res.status}`
        );
      }

      const data: GraphResponse = await res.json();
      setNodes(data.nodes);
      setEdges(data.edges);
      setStats(data.stats);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch graph data";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, filters.module, filters.edgeType, filters.depth]);

  useEffect(() => {
    if (projectId) {
      fetchGraph();
    }
  }, [projectId, fetchGraph]);

  return { nodes, edges, stats, isLoading, error, refetch: fetchGraph };
}
