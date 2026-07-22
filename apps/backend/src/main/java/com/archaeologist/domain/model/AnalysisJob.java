package com.archaeologist.domain.model;

import java.time.LocalDateTime;
import java.util.UUID;

public record AnalysisJob(
    UUID id,
    String repoUrl,
    JobStatus status,
    String currentAgent,
    LocalDateTime createdAt,
    LocalDateTime updatedAt,
    LocalDateTime completedAt,
    String errorMessage
) {}
