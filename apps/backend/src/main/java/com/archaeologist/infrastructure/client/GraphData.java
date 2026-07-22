package com.archaeologist.infrastructure.client;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * DTO representing the Analyzer service's graph data response.
 *
 * <p>Maps to the JSON returned by GET /graph/{projectId}:
 * <pre>{
 *   "projectId": "uuid",
 *   "nodes": [...],
 *   "edges": [...],
 *   "stats": { "totalNodes": 45, "totalEdges": 78, ... }
 * }</pre>
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record GraphData(
        @JsonProperty("projectId") UUID projectId,
        @JsonProperty("nodes") List<GraphNode> nodes,
        @JsonProperty("edges") List<GraphEdge> edges,
        @JsonProperty("stats") Stats stats
) {

    /**
     * A node in the dependency graph.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record GraphNode(
            @JsonProperty("id") UUID id,
            @JsonProperty("type") String type,
            @JsonProperty("name") String name,
            @JsonProperty("qualifiedName") String qualifiedName,
            @JsonProperty("filePath") String filePath,
            @JsonProperty("loc") int loc,
            @JsonProperty("complexity") int complexity,
            @JsonProperty("metadata") Map<String, Object> metadata
    ) {}

    /**
     * An edge (relationship) in the dependency graph.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record GraphEdge(
            @JsonProperty("id") UUID id,
            @JsonProperty("source") UUID source,
            @JsonProperty("target") UUID target,
            @JsonProperty("type") String type,
            @JsonProperty("metadata") Map<String, Object> metadata
    ) {}

    /**
     * Statistics about the graph query result.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Stats(
            @JsonProperty("totalNodes") int totalNodes,
            @JsonProperty("totalEdges") int totalEdges,
            @JsonProperty("filteredNodes") int filteredNodes,
            @JsonProperty("filteredEdges") int filteredEdges
    ) {}
}
