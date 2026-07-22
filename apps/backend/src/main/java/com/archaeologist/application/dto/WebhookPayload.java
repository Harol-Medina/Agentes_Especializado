package com.archaeologist.application.dto;

import java.util.Map;
import java.util.UUID;

public record WebhookPayload(
    UUID jobId,
    String status,
    UUID projectId,
    Map<String, String> agentsStatus
) {}
