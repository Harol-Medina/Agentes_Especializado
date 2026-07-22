package com.archaeologist.application.dto;

import java.util.Map;
import java.util.UUID;

/**
 * Response DTO for the architecture report endpoint.
 * Contains aggregated analysis results from all pipeline agents.
 */
public record ReportResponse(
    UUID projectId,
    String projectName,
    Map<String, Object> architectureReport,
    Map<String, Object> qualityReport,
    Map<String, Object> securityReport,
    Map<String, Object> documentationBundle,
    Map<String, Object> modernizationPlan
) {}
