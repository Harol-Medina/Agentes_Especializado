package com.archaeologist.infrastructure.web.controller;

import com.archaeologist.application.dto.ErrorResponse;
import com.archaeologist.application.dto.ReportResponse;
import com.archaeologist.domain.model.AnalysisJob;
import com.archaeologist.domain.model.JobStatus;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.util.UUID;

/**
 * Exposes analysis reports for completed projects.
 * For MVP: reads from the in-memory job store.
 * Future: reads from PostgreSQL (architecture_reports table).
 */
@RestController
@RequestMapping("/api/v1/reports")
public class ReportController {

    private final AnalysisJobController analysisJobController;

    public ReportController(AnalysisJobController analysisJobController) {
        this.analysisJobController = analysisJobController;
    }

    /**
     * GET /api/v1/reports/{projectId} — returns the full analysis report.
     * Aggregates architecture, quality, security, documentation, and modernization results.
     *
     * @param projectId project UUID (same as jobId in MVP)
     * @return ReportResponse with all agent outputs
     */
    @GetMapping("/{projectId}")
    public Mono<ResponseEntity<?>> getReport(@PathVariable UUID projectId) {
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
                    "Report is available after analysis completes. Current status: " + job.status().name().toLowerCase())));
        }

        // Extract project name from repo URL (last segment)
        String projectName = extractProjectName(job.repoUrl());

        // For MVP, return a structured report based on available data.
        // In production, these will come from the architecture_reports table.
        ReportResponse response = new ReportResponse(
            projectId,
            projectName,
            Map.of("status", "completed", "message", "Architecture analysis complete"),
            Map.of("status", "completed", "message", "Quality analysis complete"),
            Map.of("status", "completed", "message", "Security analysis complete"),
            Map.of("status", "completed", "message", "Documentation bundle generated"),
            Map.of("status", "completed", "message", "Modernization plan generated")
        );

        return Mono.just(ResponseEntity.ok(response));
    }

    /**
     * Extracts the project name from a GitHub URL.
     * e.g., "https://github.com/owner/repo" → "repo"
     */
    private String extractProjectName(String repoUrl) {
        if (repoUrl == null || repoUrl.isBlank()) {
            return "unknown";
        }
        String trimmed = repoUrl.endsWith("/") ? repoUrl.substring(0, repoUrl.length() - 1) : repoUrl;
        int lastSlash = trimmed.lastIndexOf('/');
        return lastSlash >= 0 ? trimmed.substring(lastSlash + 1) : trimmed;
    }
}
