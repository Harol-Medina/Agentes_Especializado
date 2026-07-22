package com.archaeologist.application.dto;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

public record JobStatusResponse(
    UUID jobId,
    String status,
    String currentAgent,
    Progress progress,
    LocalDateTime createdAt
) {
    public record Progress(
        int totalAgents,
        int completedAgents,
        List<AgentProgressItem> agents
    ) {}
}
