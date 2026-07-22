package com.archaeologist.infrastructure.web.controller;

import com.archaeologist.application.dto.ErrorResponse;
import com.archaeologist.domain.model.AnalysisJob;
import com.archaeologist.domain.model.JobStatus;
import com.archaeologist.infrastructure.client.AnalyzerClient;
import com.archaeologist.infrastructure.client.GraphData;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.util.UUID;

/**
 * Exposes the dependency graph for a project.
 * Proxies requests to the Analyzer service's GET /graph/{projectId} endpoint.
 */
@RestController
@RequestMapping("/api/v1/graph")
public class GraphController {

    private final AnalyzerClient analyzerClient;
    private final AnalysisJobController analysisJobController;

    public GraphController(AnalyzerClient analyzerClient, AnalysisJobController analysisJobController) {
        this.analyzerClient = analyzerClient;
        this.analysisJobController = analysisJobController;
    }

    /**
     * GET /api/v1/graph/{projectId} — retrieves the dependency graph.
     * Proxies directly to the Analyzer service with optional filter params.
     *
     * @param projectId project UUID (same as jobId in MVP)
     * @param module    optional module filter
     * @param edgeType  optional edge type filter (import, inheritance, usage, composition)
     * @param depth     optional depth limit
     * @return GraphData from the Analyzer service
     */
    @GetMapping("/{projectId}")
    public Mono<ResponseEntity<?>> getGraph(
            @PathVariable UUID projectId,
            @RequestParam(required = false) String module,
            @RequestParam(required = false) String edgeType,
            @RequestParam(required = false) Integer depth) {

        // Verify the project/job exists and analysis is complete
        Map<UUID, AnalysisJob> jobStore = analysisJobController.getJobStore();
        AnalysisJob job = jobStore.get(projectId);

        if (job == null) {
            return Mono.just(ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(new ErrorResponse("PROJECT_NOT_FOUND", "Project not found")));
        }

        if (job.status() != JobStatus.COMPLETED) {
            return Mono.just(ResponseEntity
                .status(HttpStatus.CONFLICT)
                .body(new ErrorResponse("ANALYSIS_NOT_COMPLETE",
                    "Graph is available after analysis completes. Current status: " + job.status().name().toLowerCase())));
        }

        return analyzerClient.getGraph(projectId, module, edgeType, depth)
            .map(graphData -> ResponseEntity.ok((Object) graphData))
            .onErrorResume(AnalyzerClient.AnalyzerClientException.class, ex -> {
                if (ex.getErrorType() == AnalyzerClient.ErrorType.NOT_FOUND) {
                    return Mono.just(ResponseEntity
                        .status(HttpStatus.NOT_FOUND)
                        .body(new ErrorResponse("PROJECT_NOT_FOUND", "Graph data not found for this project")));
                }
                return Mono.just(ResponseEntity
                    .status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(new ErrorResponse("INTERNAL_ERROR", "Failed to retrieve graph data: " + ex.getMessage())));
            });
    }
}
