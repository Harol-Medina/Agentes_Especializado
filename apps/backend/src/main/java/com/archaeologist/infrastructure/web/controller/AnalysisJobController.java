package com.archaeologist.infrastructure.web.controller;

import com.archaeologist.application.dto.AgentProgressItem;
import com.archaeologist.application.dto.ErrorResponse;
import com.archaeologist.application.dto.JobStatusResponse;
import com.archaeologist.application.dto.JobSubmissionRequest;
import com.archaeologist.application.dto.JobSubmissionResponse;
import com.archaeologist.domain.model.AnalysisJob;
import com.archaeologist.domain.model.JobStatus;
import com.archaeologist.domain.service.GitHubUrlValidator;
import com.archaeologist.domain.service.JobQueueService;
import com.archaeologist.infrastructure.client.AnalyzerClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@RestController
@RequestMapping("/api/v1/jobs")
public class AnalysisJobController {

    private static final Logger log = LoggerFactory.getLogger(AnalysisJobController.class);

    private final GitHubUrlValidator urlValidator;
    private final JobQueueService jobQueueService;
    private final AnalyzerClient analyzerClient;
    private final String webhookBaseUrl;

    // In-memory job store (MVP) — full persistence comes in a later task
    private final Map<UUID, AnalysisJob> jobStore = new ConcurrentHashMap<>();

    public AnalysisJobController(
            GitHubUrlValidator urlValidator,
            JobQueueService jobQueueService,
            AnalyzerClient analyzerClient,
            @Value("${app.webhook-base-url:http://backend:8080}") String webhookBaseUrl) {
        this.urlValidator = urlValidator;
        this.jobQueueService = jobQueueService;
        this.analyzerClient = analyzerClient;
        this.webhookBaseUrl = webhookBaseUrl;
    }

    @PostMapping
    public Mono<ResponseEntity<?>> submitJob(@RequestBody JobSubmissionRequest request) {
        // Quick format check before async validation
        if (!urlValidator.isValidFormat(request.repoUrl())) {
            return Mono.just(ResponseEntity
                .badRequest()
                .body(new ErrorResponse("INVALID_URL",
                    "The provided URL is not a valid public GitHub repository.")));
        }

        // Check if system is busy (single-slot queue)
        if (jobQueueService.isBusy()) {
            return Mono.just(ResponseEntity
                .status(HttpStatus.CONFLICT)
                .body(new ErrorResponse("SYSTEM_BUSY",
                    "An analysis is currently in progress. Please try again later.")));
        }

        // Validate URL via GitHub API (accessibility + size check)
        return urlValidator.validate(request.repoUrl())
            .map(result -> {
                if (!result.valid()) {
                    return ResponseEntity
                        .badRequest()
                        .body((Object) new ErrorResponse(result.errorCode(), result.errorMessage()));
                }

                // Create the job
                UUID jobId = UUID.randomUUID();
                LocalDateTime now = LocalDateTime.now();

                // Try to acquire the processing slot (thread-safe)
                if (!jobQueueService.tryAcquire(jobId)) {
                    return ResponseEntity
                        .status(HttpStatus.CONFLICT)
                        .body((Object) new ErrorResponse("SYSTEM_BUSY",
                            "An analysis is currently in progress. Please try again later."));
                }

                // Store the job in memory
                AnalysisJob job = new AnalysisJob(
                    jobId,
                    request.repoUrl().trim(),
                    JobStatus.PENDING,
                    null,
                    now,
                    now,
                    null,
                    null
                );
                jobStore.put(jobId, job);

                // Dispatch analysis to the Analyzer service (fire-and-forget)
                String webhookUrl = webhookBaseUrl + "/api/webhooks/analysis-complete";
                analyzerClient.triggerAnalysis(jobId, request.repoUrl().trim(), webhookUrl)
                    .doOnSuccess(v -> {
                        log.info("Analysis dispatched to Analyzer — job_id={}", jobId);
                        // Update job status to ANALYZING so progressive endpoints work
                        AnalysisJob analyzingJob = new AnalysisJob(
                            jobId,
                            request.repoUrl().trim(),
                            JobStatus.ANALYZING,
                            "repository_agent",
                            now,
                            LocalDateTime.now(),
                            null,
                            null
                        );
                        jobStore.put(jobId, analyzingJob);
                    })
                    .doOnError(err -> {
                        log.error("Failed to dispatch analysis to Analyzer — job_id={}, error={}", jobId, err.getMessage());
                        // Mark job as failed and release the slot
                        AnalysisJob failedJob = new AnalysisJob(
                            jobId,
                            request.repoUrl().trim(),
                            JobStatus.FAILED,
                            null,
                            now,
                            LocalDateTime.now(),
                            null,
                            "Failed to connect to analyzer service: " + err.getMessage()
                        );
                        jobStore.put(jobId, failedJob);
                        jobQueueService.release(jobId);
                    })
                    .subscribe();

                return ResponseEntity
                    .status(HttpStatus.ACCEPTED)
                    .body((Object) new JobSubmissionResponse(
                        jobId,
                        "pending",
                        "Analysis queued"
                    ));
            });
    }

    /**
     * GET /api/v1/jobs — returns all jobs in the store (most recent first).
     */
    @GetMapping
    public ResponseEntity<?> listJobs() {
        List<Map<String, Object>> result = jobStore.values().stream()
            .sorted((a, b) -> b.createdAt().compareTo(a.createdAt()))
            .map(job -> {
                List<AgentProgressItem> agents = buildAgentProgressList(job);
                int completedAgents = (int) agents.stream()
                    .filter(a -> "completed".equals(a.status()))
                    .count();

                Map<String, Object> entry = new java.util.LinkedHashMap<>();
                entry.put("jobId", job.id().toString());
                entry.put("repoUrl", job.repoUrl());
                entry.put("status", job.status().name().toLowerCase());
                entry.put("currentAgent", job.currentAgent());
                entry.put("progress", Map.of(
                    "totalAgents", agents.size(),
                    "completedAgents", completedAgents,
                    "agents", agents.stream()
                        .map(a -> Map.of("name", a.name(), "status", a.status()))
                        .toList()
                ));
                entry.put("createdAt", job.createdAt() != null ? job.createdAt().toString() : null);
                return entry;
            })
            .toList();

        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/v1/jobs/{jobId} — returns current job status with agent progress.
     */
    @GetMapping("/{jobId}")
    public Mono<ResponseEntity<?>> getJobStatus(@PathVariable UUID jobId) {
        AnalysisJob job = jobStore.get(jobId);

        if (job != null) {
            return Mono.just(buildJobStatusResponse(job));
        }

        // Job not in local store — check the analyzer (handles backend restart)
        return analyzerClient.getJobStatus(jobId)
            .<ResponseEntity<?>>map(analyzerStatus -> {
                // Reconstruct local job from analyzer response
                JobStatus status = mapAnalyzerStatus(analyzerStatus.status());
                AnalysisJob reconstructed = new AnalysisJob(
                    jobId,
                    "",
                    status,
                    analyzerStatus.currentAgent(),
                    java.time.LocalDateTime.now(),
                    java.time.LocalDateTime.now(),
                    status == JobStatus.COMPLETED ? java.time.LocalDateTime.now() : null,
                    null
                );
                jobStore.put(jobId, reconstructed);
                return buildJobStatusResponse(reconstructed);
            })
            .onErrorResume(ex -> Mono.just(ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(new ErrorResponse("JOB_NOT_FOUND", "Analysis job not found"))));
    }

    private ResponseEntity<?> buildJobStatusResponse(AnalysisJob job) {
        List<AgentProgressItem> agents = buildAgentProgressList(job);
        int completedAgents = (int) agents.stream()
            .filter(a -> "completed".equals(a.status()))
            .count();

        JobStatusResponse response = new JobStatusResponse(
            job.id(),
            job.status().name().toLowerCase(),
            job.currentAgent(),
            new JobStatusResponse.Progress(
                agents.size(),
                completedAgents,
                agents
            ),
            job.createdAt()
        );

        return ResponseEntity.ok(response);
    }

    private JobStatus mapAnalyzerStatus(String status) {
        if (status == null) return JobStatus.PENDING;
        return switch (status.toLowerCase()) {
            case "completed" -> JobStatus.COMPLETED;
            case "failed" -> JobStatus.FAILED;
            case "cancelled" -> JobStatus.CANCELLED;
            case "analyzing" -> JobStatus.ANALYZING;
            case "cloning" -> JobStatus.CLONING;
            default -> JobStatus.PENDING;
        };
    }

    /**
     * DELETE /api/v1/jobs/{jobId} — cancel a running analysis job.
     */
    @DeleteMapping("/{jobId}")
    public Mono<ResponseEntity<?>> cancelJob(@PathVariable UUID jobId) {
        AnalysisJob job = jobStore.get(jobId);

        if (job == null) {
            return Mono.just(ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(new ErrorResponse("JOB_NOT_FOUND", "Analysis job not found")));
        }

        // Only cancel jobs that are still running
        if (job.status() == JobStatus.COMPLETED || job.status() == JobStatus.FAILED
                || job.status() == JobStatus.CANCELLED) {
            return Mono.just(ResponseEntity
                .status(HttpStatus.CONFLICT)
                .body(new ErrorResponse("JOB_TERMINAL",
                    "Job is already in terminal state: " + job.status().name().toLowerCase())));
        }

        // Send cancel request to the analyzer
        return analyzerClient.cancelJob(jobId)
            .<ResponseEntity<?>>map(result -> {
                // Update local job status
                AnalysisJob cancelledJob = new AnalysisJob(
                    job.id(),
                    job.repoUrl(),
                    JobStatus.CANCELLED,
                    null,
                    job.createdAt(),
                    java.time.LocalDateTime.now(),
                    null,
                    "Cancelled by user"
                );
                jobStore.put(jobId, cancelledJob);

                // Release the processing slot
                jobQueueService.release(jobId);
                log.info("Job {} cancelled and slot released", jobId);

                return ResponseEntity.ok(result);
            })
            .onErrorResume(ex -> {
                // Even if analyzer cancel fails, mark locally as cancelled
                AnalysisJob cancelledJob = new AnalysisJob(
                    job.id(),
                    job.repoUrl(),
                    JobStatus.CANCELLED,
                    null,
                    job.createdAt(),
                    java.time.LocalDateTime.now(),
                    null,
                    "Cancelled by user (analyzer notification failed)"
                );
                jobStore.put(jobId, cancelledJob);
                jobQueueService.release(jobId);
                log.warn("Job {} cancelled locally but analyzer notification failed: {}", jobId, ex.getMessage());

                return Mono.just(ResponseEntity.ok(java.util.Map.of(
                    "jobId", jobId.toString(),
                    "cancelled", true,
                    "message", "Job cancelled"
                )));
            });
    }

    /**
     * Builds the agent progress list based on current job state.
     * Uses the fixed pipeline order of 7 agents.
     */
    private List<AgentProgressItem> buildAgentProgressList(AnalysisJob job) {
        List<String> pipelineAgents = List.of(
            "repository_agent",
            "architecture_agent",
            "quality_agent",
            "security_agent",
            "documentation_agent",
            "modernization_agent",
            "kiro_agent"
        );

        String currentAgent = job.currentAgent();

        // If job is pending or completed/failed, return static list
        if (job.status() == JobStatus.PENDING) {
            return pipelineAgents.stream()
                .map(name -> new AgentProgressItem(name, "pending"))
                .toList();
        }

        if (job.status() == JobStatus.COMPLETED) {
            return pipelineAgents.stream()
                .map(name -> new AgentProgressItem(name, "completed"))
                .toList();
        }

        if (job.status() == JobStatus.FAILED) {
            return pipelineAgents.stream()
                .map(name -> new AgentProgressItem(name, "failed"))
                .toList();
        }

        if (job.status() == JobStatus.CANCELLED) {
            return pipelineAgents.stream()
                .map(name -> new AgentProgressItem(name, "cancelled"))
                .toList();
        }

        // For cloning/analyzing states, compute progress based on current agent
        boolean passedCurrent = false;
        List<AgentProgressItem> result = new java.util.ArrayList<>();

        for (String agentName : pipelineAgents) {
            if (passedCurrent) {
                result.add(new AgentProgressItem(agentName, "pending"));
            } else if (agentName.equals(currentAgent)) {
                result.add(new AgentProgressItem(agentName, "running"));
                passedCurrent = true;
            } else {
                result.add(new AgentProgressItem(agentName, "completed"));
            }
        }

        // If no current agent matched (e.g., cloning state), all are pending
        if (!passedCurrent && currentAgent == null) {
            return pipelineAgents.stream()
                .map(name -> new AgentProgressItem(name, "pending"))
                .toList();
        }

        return result;
    }

    /**
     * Provides read access to the in-memory job store (for other components/tests).
     */
    public Map<UUID, AnalysisJob> getJobStore() {
        return jobStore;
    }
}
