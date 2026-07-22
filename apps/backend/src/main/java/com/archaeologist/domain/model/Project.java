package com.archaeologist.domain.model;

import java.time.LocalDateTime;
import java.util.UUID;

public record Project(
    UUID id,
    UUID jobId,
    String repoUrl,
    String name,
    String language,
    String framework,
    int totalFiles,
    int totalLoc,
    LocalDateTime createdAt
) {}
