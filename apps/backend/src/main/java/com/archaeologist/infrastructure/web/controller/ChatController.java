package com.archaeologist.infrastructure.web.controller;

import com.archaeologist.application.dto.ChatRequest;
import com.archaeologist.application.dto.ErrorResponse;
import com.archaeologist.infrastructure.client.AnalyzerClient;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;

/**
 * SSE relay endpoint for RAG chat.
 *
 * <p>Proxies the Analyzer's POST /query SSE stream to the Frontend.
 * The Backend does not process or transform the stream — it simply relays it.
 */
@RestController
@RequestMapping("/api/v1/chat")
public class ChatController {

    private final AnalyzerClient analyzerClient;

    public ChatController(AnalyzerClient analyzerClient) {
        this.analyzerClient = analyzerClient;
    }

    /**
     * POST /api/v1/chat — accepts a chat question and streams the RAG response as SSE.
     *
     * @param request contains projectId, question, and optional maxChunks
     * @return SSE stream relayed from the Analyzer service, or 400 on invalid input
     */
    @PostMapping(produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Object chat(@RequestBody ChatRequest request) {
        // Validate projectId is not null
        if (request.projectId() == null) {
            return ResponseEntity
                .badRequest()
                .body(new ErrorResponse("INVALID_REQUEST", "projectId is required"));
        }

        // Validate question is not empty
        if (request.question() == null || request.question().isBlank()) {
            return ResponseEntity
                .badRequest()
                .body(new ErrorResponse("INVALID_REQUEST", "question must not be empty"));
        }

        return analyzerClient.queryChat(
            request.projectId(),
            request.question(),
            request.maxChunks()
        );
    }
}
