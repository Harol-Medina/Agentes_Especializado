package com.archaeologist.application.dto;

import java.util.UUID;

public record JobSubmissionResponse(
    UUID jobId,
    String status,
    String message
) {}
