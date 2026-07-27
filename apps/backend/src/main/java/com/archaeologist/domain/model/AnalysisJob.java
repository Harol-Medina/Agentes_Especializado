package com.archaeologist.domain.model;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Domain model representing a repository analysis job.
 *
 * <p>Mutable to allow in-place status updates within the ConcurrentHashMap store.
 * Thread-safety is handled by the map's atomic operations (compute/replace).
 */
public class AnalysisJob {

    private final UUID id;
    private final String repoUrl;
    private final LocalDateTime createdAt;

    private volatile JobStatus status;
    private volatile String currentAgent;
    private volatile LocalDateTime updatedAt;
    private volatile LocalDateTime completedAt;
    private volatile String errorMessage;

    public AnalysisJob(UUID id, String repoUrl, JobStatus status, String currentAgent,
                       LocalDateTime createdAt, LocalDateTime updatedAt,
                       LocalDateTime completedAt, String errorMessage) {
        this.id = id;
        this.repoUrl = repoUrl;
        this.status = status;
        this.currentAgent = currentAgent;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.completedAt = completedAt;
        this.errorMessage = errorMessage;
    }

    /**
     * Factory: create a new pending job.
     */
    public static AnalysisJob createPending(UUID id, String repoUrl) {
        LocalDateTime now = LocalDateTime.now();
        return new AnalysisJob(id, repoUrl, JobStatus.PENDING, null, now, now, null, null);
    }

    // ─── Getters ───

    public UUID id() { return id; }
    public String repoUrl() { return repoUrl; }
    public JobStatus status() { return status; }
    public String currentAgent() { return currentAgent; }
    public LocalDateTime createdAt() { return createdAt; }
    public LocalDateTime updatedAt() { return updatedAt; }
    public LocalDateTime completedAt() { return completedAt; }
    public String errorMessage() { return errorMessage; }

    // ─── Mutators (for in-place updates within ConcurrentHashMap) ───

    public void updateStatus(JobStatus newStatus) {
        this.status = newStatus;
        this.updatedAt = LocalDateTime.now();
        if (newStatus == JobStatus.COMPLETED || newStatus == JobStatus.FAILED || newStatus == JobStatus.CANCELLED) {
            this.completedAt = LocalDateTime.now();
        }
    }

    public void setCurrentAgent(String agent) {
        this.currentAgent = agent;
        this.updatedAt = LocalDateTime.now();
    }

    public void setErrorMessage(String message) {
        this.errorMessage = message;
        this.updatedAt = LocalDateTime.now();
    }
}
