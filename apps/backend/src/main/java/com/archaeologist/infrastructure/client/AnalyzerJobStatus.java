package com.archaeologist.infrastructure.client;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.UUID;

/**
 * DTO representing the Analyzer service's job status response.
 *
 * <p>Maps to the JSON returned by GET /jobs/{jobId}:
 * <pre>{
 *   "jobId": "uuid",
 *   "status": "analyzing",
 *   "currentAgent": "quality_agent",
 *   "progress": {
 *     "completedAgents": ["repository_agent", "architecture_agent"],
 *     "currentAgent": "quality_agent",
 *     "pendingAgents": ["security_agent", ...],
 *     "failedAgents": []
 *   }
 * }</pre>
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record AnalyzerJobStatus(
        @JsonProperty("jobId") UUID jobId,
        @JsonProperty("status") String status,
        @JsonProperty("currentAgent") String currentAgent,
        @JsonProperty("progress") Progress progress
) {

    /**
     * Progress breakdown showing agent pipeline state.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Progress(
            @JsonProperty("completedAgents") List<String> completedAgents,
            @JsonProperty("currentAgent") String currentAgent,
            @JsonProperty("pendingAgents") List<String> pendingAgents,
            @JsonProperty("failedAgents") List<String> failedAgents
    ) {}
}
