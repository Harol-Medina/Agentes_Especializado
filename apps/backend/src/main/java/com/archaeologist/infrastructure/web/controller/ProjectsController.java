package com.archaeologist.infrastructure.web.controller;

import com.archaeologist.application.dto.ErrorResponse;
import com.archaeologist.domain.model.AnalysisJob;
import com.archaeologist.domain.model.JobStatus;
import com.archaeologist.infrastructure.client.AnalyzerClient;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.util.UUID;

/**
 * Serves project results (graph, report, kiro-spec) at the paths
 * expected by the frontend: /api/v1/projects/{projectId}/...
 *
 * Proxies requests to the Analyzer service endpoints.
 * The projectId is the same as the jobId in the MVP.
 */
@RestController
@RequestMapping("/api/v1/projects")
public class ProjectsController {

    private final AnalyzerClient analyzerClient;
    private final AnalysisJobController analysisJobController;

    public ProjectsController(AnalyzerClient analyzerClient, AnalysisJobController analysisJobController) {
        this.analyzerClient = analyzerClient;
        this.analysisJobController = analysisJobController;
    }

    /**
     * GET /api/v1/projects/{projectId}/graph — dependency graph.
     */
    @GetMapping("/{projectId}/graph")
    public Mono<ResponseEntity<?>> getGraph(
            @PathVariable UUID projectId,
            @RequestParam(required = false) String module,
            @RequestParam(required = false) String edgeType,
            @RequestParam(required = false) Integer depth) {

        ResponseEntity<?> error = verifyCompleted(projectId);
        if (error != null) {
            return Mono.just(error);
        }

        return analyzerClient.getGraph(projectId, module, edgeType, depth)
            .<ResponseEntity<?>>map(data -> ResponseEntity.ok(data))
            .onErrorResume(AnalyzerClient.AnalyzerClientException.class, ex -> handleAnalyzerError(ex));
    }

    /**
     * GET /api/v1/projects/{projectId}/report — consolidated analysis report.
     */
    @GetMapping("/{projectId}/report")
    public Mono<ResponseEntity<?>> getReport(@PathVariable UUID projectId) {

        ResponseEntity<?> error = verifyCompleted(projectId);
        if (error != null) {
            return Mono.just(error);
        }

        return analyzerClient.getReport(projectId)
            .<ResponseEntity<?>>map(data -> ResponseEntity.ok(data))
            .onErrorResume(AnalyzerClient.AnalyzerClientException.class, ex -> handleAnalyzerError(ex));
    }

    /**
     * GET /api/v1/projects/{projectId}/kiro-spec — Kiro specification.
     * Supports Accept: text/markdown for raw markdown response.
     */
    @GetMapping("/{projectId}/kiro-spec")
    public Mono<ResponseEntity<?>> getKiroSpec(
            @PathVariable UUID projectId,
            @RequestHeader(value = "Accept", defaultValue = "application/json") String accept) {

        ResponseEntity<?> error = verifyCompleted(projectId);
        if (error != null) {
            return Mono.just(error);
        }

        if (accept.contains("text/markdown")) {
            return analyzerClient.getKiroSpecMarkdown(projectId)
                .<ResponseEntity<?>>map(markdown -> ResponseEntity.ok()
                    .contentType(MediaType.valueOf("text/markdown"))
                    .body(markdown))
                .onErrorResume(AnalyzerClient.AnalyzerClientException.class, ex -> handleAnalyzerError(ex));
        }

        return analyzerClient.getKiroSpec(projectId)
            .<ResponseEntity<?>>map(data -> ResponseEntity.ok(data))
            .onErrorResume(AnalyzerClient.AnalyzerClientException.class, ex -> handleAnalyzerError(ex));
    }

    // --- Helpers ---

    /**
     * Verifies the job exists and has completed. Returns a ResponseEntity
     * error if not, or null if verification passes.
     */
    private ResponseEntity<?> verifyCompleted(UUID projectId) {
        Map<UUID, AnalysisJob> jobStore = analysisJobController.getJobStore();
        AnalysisJob job = jobStore.get(projectId);

        if (job == null) {
            return ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(new ErrorResponse("PROJECT_NOT_FOUND", "Project not found"));
        }

        if (job.status() != JobStatus.COMPLETED) {
            return ResponseEntity
                .status(HttpStatus.CONFLICT)
                .body(new ErrorResponse("ANALYSIS_NOT_COMPLETE",
                    "Results are available after analysis completes. Current status: " + job.status().name().toLowerCase()));
        }

        return null;
    }

    private Mono<ResponseEntity<?>> handleAnalyzerError(AnalyzerClient.AnalyzerClientException ex) {
        if (ex.getErrorType() == AnalyzerClient.ErrorType.NOT_FOUND) {
            return Mono.just(ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(new ErrorResponse("NOT_FOUND", "Requested data not found")));
        }
        if (ex.getErrorType() == AnalyzerClient.ErrorType.CONFLICT) {
            return Mono.just(ResponseEntity
                .status(HttpStatus.CONFLICT)
                .body(new ErrorResponse("NOT_READY", "Analysis has not completed yet")));
        }
        return Mono.just(ResponseEntity
            .status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(new ErrorResponse("SERVICE_ERROR", "Failed to retrieve data: " + ex.getMessage())));
    }
}
