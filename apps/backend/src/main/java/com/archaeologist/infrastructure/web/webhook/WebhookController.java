package com.archaeologist.infrastructure.web.webhook;

import com.archaeologist.application.dto.ErrorResponse;
import com.archaeologist.application.dto.WebhookPayload;
import com.archaeologist.domain.model.AnalysisJob;
import com.archaeologist.domain.model.JobStatus;
import com.archaeologist.domain.service.JobQueueService;
import com.archaeologist.infrastructure.config.WebhookConfig;
import com.archaeologist.infrastructure.web.controller.AnalysisJobController;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * Receives webhook notifications from the Analyzer service when analysis completes.
 * Validates HMAC-SHA256 signature before processing.
 */
@RestController
@RequestMapping("/api/webhooks")
public class WebhookController {

    private static final Logger log = LoggerFactory.getLogger(WebhookController.class);

    private final WebhookConfig webhookConfig;
    private final JobQueueService jobQueueService;
    private final AnalysisJobController analysisJobController;
    private final ObjectMapper objectMapper;

    public WebhookController(
            WebhookConfig webhookConfig,
            JobQueueService jobQueueService,
            AnalysisJobController analysisJobController,
            ObjectMapper objectMapper) {
        this.webhookConfig = webhookConfig;
        this.jobQueueService = jobQueueService;
        this.analysisJobController = analysisJobController;
        this.objectMapper = objectMapper;
    }

    @PostMapping("/analysis-complete")
    public Mono<ResponseEntity<?>> analysisComplete(
            @RequestBody String rawBody,
            @RequestHeader(value = "X-Webhook-Signature", required = false) String signature) {

        // Validate HMAC signature
        if (!webhookConfig.validateSignature(rawBody, signature)) {
            log.warn("Webhook received with invalid signature");
            return Mono.just(ResponseEntity
                .status(HttpStatus.UNAUTHORIZED)
                .body(new ErrorResponse("INVALID_SIGNATURE", "Webhook signature validation failed")));
        }

        // Parse the payload
        WebhookPayload payload;
        try {
            payload = objectMapper.readValue(rawBody, WebhookPayload.class);
        } catch (JsonProcessingException e) {
            log.error("Failed to parse webhook payload", e);
            return Mono.just(ResponseEntity
                .badRequest()
                .body(new ErrorResponse("INVALID_PAYLOAD", "Could not parse webhook payload")));
        }

        log.info("Webhook received for job {} with status {}", payload.jobId(), payload.status());

        // Update job status in the in-memory store
        Map<java.util.UUID, AnalysisJob> jobStore = analysisJobController.getJobStore();
        AnalysisJob existingJob = jobStore.get(payload.jobId());

        if (existingJob == null) {
            log.warn("Webhook received for unknown job: {}", payload.jobId());
            return Mono.just(ResponseEntity.ok(Map.of("received", true)));
        }

        // Idempotency: if job is already completed or failed, skip update
        if (existingJob.status() == JobStatus.COMPLETED || existingJob.status() == JobStatus.FAILED) {
            log.info("Job {} already in terminal state {}, ignoring webhook", payload.jobId(), existingJob.status());
            return Mono.just(ResponseEntity.ok(Map.of("received", true)));
        }

        // Map webhook status to JobStatus
        JobStatus newStatus = mapWebhookStatus(payload.status());

        // Update job in store
        AnalysisJob updatedJob = new AnalysisJob(
            existingJob.id(),
            existingJob.repoUrl(),
            newStatus,
            null, // currentAgent is null when completed/failed
            existingJob.createdAt(),
            LocalDateTime.now(),
            newStatus == JobStatus.COMPLETED ? LocalDateTime.now() : null,
            newStatus == JobStatus.FAILED ? "Analysis failed" : null
        );
        jobStore.put(payload.jobId(), updatedJob);

        // Release the processing slot
        jobQueueService.release(payload.jobId());
        log.info("Job {} marked as {} and processing slot released", payload.jobId(), newStatus);

        return Mono.just(ResponseEntity.ok(Map.of("received", true)));
    }

    private JobStatus mapWebhookStatus(String status) {
        return switch (status.toLowerCase()) {
            case "completed" -> JobStatus.COMPLETED;
            case "failed" -> JobStatus.FAILED;
            case "cancelled" -> JobStatus.CANCELLED;
            default -> JobStatus.ANALYZING;
        };
    }
}
