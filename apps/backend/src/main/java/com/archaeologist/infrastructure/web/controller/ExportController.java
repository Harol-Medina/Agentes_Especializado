package com.archaeologist.infrastructure.web.controller;

import com.archaeologist.application.dto.ErrorResponse;
import com.archaeologist.domain.model.AnalysisJob;
import com.archaeologist.domain.model.JobStatus;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.util.UUID;

/**
 * Handles export of Kiro spec artifacts as downloadable markdown files.
 * For MVP: generates a placeholder Kiro spec from job data.
 * Future: reads from PostgreSQL (kiro_specs table).
 */
@RestController
@RequestMapping("/api/v1/export")
public class ExportController {

    private final AnalysisJobController analysisJobController;

    public ExportController(AnalysisJobController analysisJobController) {
        this.analysisJobController = analysisJobController;
    }

    /**
     * GET /api/v1/export/kiro/{projectId} — returns the Kiro spec as a downloadable markdown file.
     * Content-Type: text/markdown
     * Content-Disposition: attachment; filename="kiro-spec-{project}.md"
     *
     * @param projectId project UUID (same as jobId in MVP)
     * @return Markdown content with download headers
     */
    @GetMapping(value = "/kiro/{projectId}", produces = "text/markdown")
    public Mono<ResponseEntity<?>> exportKiroSpec(@PathVariable UUID projectId) {
        Map<UUID, AnalysisJob> jobStore = analysisJobController.getJobStore();
        AnalysisJob job = jobStore.get(projectId);

        if (job == null) {
            return Mono.just(ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .contentType(MediaType.APPLICATION_JSON)
                .body(new ErrorResponse("PROJECT_NOT_FOUND", "Project not found")));
        }

        if (job.status() != JobStatus.COMPLETED) {
            return Mono.just(ResponseEntity
                .status(HttpStatus.CONFLICT)
                .contentType(MediaType.APPLICATION_JSON)
                .body(new ErrorResponse("ANALYSIS_NOT_COMPLETE",
                    "Kiro spec is available after analysis completes. Current status: " + job.status().name().toLowerCase())));
        }

        // Extract project name for the filename
        String projectName = extractProjectName(job.repoUrl());

        // For MVP, generate a template Kiro spec.
        // In production, this content comes from the kiro_specs table (written by Kiro_Agent).
        String kiroSpec = generateKiroSpec(projectName, job.repoUrl());

        return Mono.just(ResponseEntity
            .ok()
            .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"kiro-spec-" + projectName + ".md\"")
            .contentType(MediaType.parseMediaType("text/markdown"))
            .body(kiroSpec));
    }

    /**
     * Generates a Kiro spec template for the MVP.
     * In production, this is replaced by the actual Kiro_Agent output from the database.
     */
    private String generateKiroSpec(String projectName, String repoUrl) {
        return """
            ---
            name: "Modernización de %s"
            version: 1.0
            ---
            
            # Requirements
            
            - REQ-1: Analyze repository structure and dependencies
            - REQ-2: Generate architecture documentation
            - REQ-3: Identify modernization opportunities
            
            # Design
            
            ## Current Architecture
            
            Analysis of repository: %s
            
            ### Language & Framework
            - Detected during analysis pipeline
            
            ### Module Structure
            - Module structure analysis completed
            
            ### Dependencies
            - Dependency graph generated
            
            ## Proposed Architecture
            
            - Modernization recommendations pending full pipeline results
            
            ### Priority Actions
            - Review architecture report for specific recommendations
            
            # Tasks
            
            - [ ] TASK-1: Review architecture analysis results
            - [ ] TASK-2: Address quality findings
            - [ ] TASK-3: Implement security recommendations
            """.formatted(projectName, repoUrl);
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
