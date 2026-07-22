package com.archaeologist.application.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.UUID;

/**
 * Request body for the Chat SSE endpoint.
 *
 * @param projectId the project UUID to query against
 * @param question  the user's question (must not be blank)
 * @param maxChunks maximum number of context chunks to retrieve (defaults to 10)
 */
public record ChatRequest(
    UUID projectId,
    String question,
    @JsonProperty(defaultValue = "10") int maxChunks
) {

    /**
     * Compact constructor with default maxChunks when not provided.
     */
    public ChatRequest {
        if (maxChunks <= 0) {
            maxChunks = 10;
        }
    }
}
