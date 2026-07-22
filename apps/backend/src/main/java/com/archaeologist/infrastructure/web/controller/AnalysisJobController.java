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

    private final GitHubUrlValidator urlValidator;
    private final JobQueueService jobQueueService;

    // In-memory job store (MVP) — full persistence comes in a later task
    private final Map<UUID, AnalysisJob> jobStore = new ConcurrentHashMap<>();

    public AnalysisJobController(GitHubUrlValidator urlValidator, JobQueueService jobQueueService) {
        this.urlValidator = urlValidator;
        this.jobQueueService = jobQueueService;
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
     * GET /api/v1/jobs/{jobId} — returns current job status with agent progress.
     */
    @GetMapping("/{jobId}")
    public Mono<ResponseEntity<?>> getJobStatus(@PathVariable UUID jobId) {
        AnalysisJob job = jobStore.get(jobId);

        if (job == null) {
            return Mono.just(ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(new ErrorResponse("JOB_NOT_FOUND", "Analysis job not found")));
        }

        // Build agent progress list with default pipeline agents
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

        return Mono.just(ResponseEntity.ok(response));
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
