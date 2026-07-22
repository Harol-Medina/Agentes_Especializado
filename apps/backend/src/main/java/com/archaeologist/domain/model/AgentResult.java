package com.archaeologist.domain.model;

import java.time.LocalDateTime;
import java.util.UUID;

public record AgentResult(
    UUID id,
    UUID jobId,
    String agentName,
    AgentStatus status,
    String output,
    String errorMessage,
    LocalDateTime startedAt,
    LocalDateTime completedAt,
    int executionOrder
) {}
