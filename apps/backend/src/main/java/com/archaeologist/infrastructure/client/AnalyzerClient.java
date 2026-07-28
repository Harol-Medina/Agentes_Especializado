package com.archaeologist.infrastructure.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.Map;
import java.util.UUID;

/**
 * HTTP client for the Analyzer service (Python/FastAPI on port 8000).
 *
 * <p>Provides reactive, non-blocking access to:
 * <ul>
 *   <li>POST /analyze — start an analysis job (expects 202)</li>
 *   <li>GET /jobs/{jobId} — poll job status</li>
 *   <li>GET /graph/{projectId} — retrieve graph data</li>
 *   <li>POST /query — RAG chat with SSE streaming</li>
 * </ul>
 *
 * <p>Timeouts: 10s for REST calls, 120s for SSE streams.
 * Error mapping: 4xx→custom exceptions, 5xx→ServiceUnavailableException.
 */
@Service
public class AnalyzerClient {

    private final WebClient webClient;
    private final Duration restTimeout;
    private final Duration streamTimeout;

    public AnalyzerClient(
            @Value("${analyzer.base-url:http://analyzer:8000}") String baseUrl,
            @Value("${analyzer.timeout.rest-seconds:10}") int restTimeoutSeconds,
            @Value("${analyzer.timeout.stream-seconds:120}") int streamTimeoutSeconds) {
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .build();
        this.restTimeout = Duration.ofSeconds(restTimeoutSeconds);
        this.streamTimeout = Duration.ofSeconds(streamTimeoutSeconds);
    }

    /**
     * Triggers an analysis job in the Analyzer service.
     * Sends POST /analyze and expects a 202 Accepted response.
     *
     * @param jobId      the job UUID assigned by the Backend
     * @param repoUrl    the GitHub repository URL to analyze
     * @param webhookUrl the webhook URL for completion notification
     * @return Mono<Void> that completes when the 202 is received
     * @throws AnalyzerClientException on communication or HTTP errors
     */
    public Mono<Void> triggerAnalysis(UUID jobId, String repoUrl, String webhookUrl) {
        Map<String, Object> body = Map.of(
                "repo_url", repoUrl,
                "job_id", jobId.toString(),
                "webhook_url", webhookUrl
        );

        return webClient.post()
                .uri("/analyze")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(body)
                .retrieve()
                .onStatus(HttpStatusCode::isError, response -> mapError(response.statusCode()))
                .toBodilessEntity()
                .timeout(restTimeout)
                .onErrorMap(this::wrapError)
                .then();
    }

    /**
     * Polls the status of an analysis job.
     *
     * @param jobId the job UUID to query
     * @return Mono with strongly-typed job status
     * @throws AnalyzerClientException on communication or HTTP errors
     */
    public Mono<AnalyzerJobStatus> getJobStatus(UUID jobId) {
        return webClient.get()
                .uri("/jobs/{jobId}", jobId.toString())
                .retrieve()
                .onStatus(HttpStatusCode::isError, response -> mapError(response.statusCode()))
                .bodyToMono(AnalyzerJobStatus.class)
                .timeout(restTimeout)
                .onErrorMap(this::wrapError);
    }

    /**
     * Retrieves graph data for a project from the Analyzer.
     *
     * @param projectId the project UUID
     * @param module    optional module filter (nullable)
     * @param edgeType  optional edge type filter (nullable)
     * @param depth     optional depth filter (nullable)
     * @return Mono with strongly-typed graph data
     * @throws AnalyzerClientException on communication or HTTP errors
     */
    public Mono<GraphData> getGraph(UUID projectId, String module, String edgeType, Integer depth) {
        return webClient.get()
                .uri(uriBuilder -> {
                    uriBuilder.path("/graph/{projectId}");
                    if (module != null && !module.isBlank()) {
                        uriBuilder.queryParam("module", module);
                    }
                    if (edgeType != null && !edgeType.isBlank()) {
                        uriBuilder.queryParam("edgeType", edgeType);
                    }
                    if (depth != null) {
                        uriBuilder.queryParam("depth", depth);
                    }
                    return uriBuilder.build(projectId.toString());
                })
                .retrieve()
                .onStatus(HttpStatusCode::isError, response -> mapError(response.statusCode()))
                .bodyToMono(GraphData.class)
                .timeout(restTimeout)
                .onErrorMap(this::wrapError);
    }

    /**
     * Sends a RAG query and returns an SSE stream of responses.
     *
     * @param projectId the project UUID to query against
     * @param question  the user's question
     * @param maxChunks maximum number of context chunks to retrieve
     * @return Flux of ServerSentEvents with streaming response tokens
     * @throws AnalyzerClientException on communication or HTTP errors
     */
    public Flux<ServerSentEvent<String>> queryChat(UUID projectId, String question, int maxChunks) {
        Map<String, Object> body = Map.of(
                "projectId", projectId.toString(),
                "question", question,
                "maxChunks", maxChunks
        );

        return webClient.post()
                .uri("/query")
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .bodyValue(body)
                .retrieve()
                .onStatus(HttpStatusCode::isError, response -> mapError(response.statusCode()))
                .bodyToFlux(sseType())
                .timeout(streamTimeout)
                .onErrorMap(this::wrapError);
    }

    /**
     * Retrieves the consolidated analysis report for a project.
     *
     * @param projectId the project/job UUID
     * @return Mono with the report as a generic Map
     * @throws AnalyzerClientException on communication or HTTP errors
     */
    public Mono<Map> getReport(UUID projectId) {
        return webClient.get()
                .uri("/report/{projectId}", projectId.toString())
                .retrieve()
                .onStatus(HttpStatusCode::isError, response -> mapError(response.statusCode()))
                .bodyToMono(Map.class)
                .timeout(restTimeout)
                .onErrorMap(this::wrapError);
    }

    /**
     * Retrieves the Kiro specification for a project as JSON.
     *
     * @param projectId the project/job UUID
     * @return Mono with the kiro-spec response as a generic Map
     * @throws AnalyzerClientException on communication or HTTP errors
     */
    public Mono<Map> getKiroSpec(UUID projectId) {
        return webClient.get()
                .uri("/kiro-spec/{projectId}", projectId.toString())
                .retrieve()
                .onStatus(HttpStatusCode::isError, response -> mapError(response.statusCode()))
                .bodyToMono(Map.class)
                .timeout(restTimeout)
                .onErrorMap(this::wrapError);
    }

    /**
     * Retrieves the Kiro specification as raw markdown text.
     *
     * @param projectId the project/job UUID
     * @return Mono with the kiro-spec as plain markdown string
     * @throws AnalyzerClientException on communication or HTTP errors
     */
    public Mono<String> getKiroSpecMarkdown(UUID projectId) {
        return webClient.get()
                .uri("/kiro-spec/{projectId}", projectId.toString())
                .accept(MediaType.valueOf("text/markdown"))
                .retrieve()
                .onStatus(HttpStatusCode::isError, response -> mapError(response.statusCode()))
                .bodyToMono(String.class)
                .timeout(restTimeout)
                .onErrorMap(this::wrapError);
    }

    /**
     * Requests cancellation of a running analysis job.
     *
     * @param jobId the job UUID to cancel
     * @return Mono with the cancellation response
     * @throws AnalyzerClientException on communication or HTTP errors
     */
    public Mono<Map> cancelJob(UUID jobId) {
        return webClient.post()
                .uri("/jobs/{jobId}/cancel", jobId.toString())
                .retrieve()
                .onStatus(HttpStatusCode::isError, response -> mapError(response.statusCode()))
                .bodyToMono(Map.class)
                .timeout(restTimeout)
                .onErrorMap(this::wrapError);
    }

    /**
     * Triggers a retry of failed agents for an existing analysis job.
     * Sends POST /analyze/retry and expects a 202 Accepted response.
     *
     * @param jobId        the job UUID of the original analysis
     * @param failedAgents list of agent names to retry
     * @param webhookUrl   the webhook URL for completion notification
     * @return Mono<Void> that completes when the 202 is received
     * @throws AnalyzerClientException on communication or HTTP errors
     */
    public Mono<Void> triggerRetry(UUID jobId, java.util.List<String> failedAgents, String webhookUrl) {
        Map<String, Object> body = Map.of(
                "job_id", jobId.toString(),
                "failed_agents", failedAgents,
                "webhook_url", webhookUrl
        );

        return webClient.post()
                .uri("/analyze/retry")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(body)
                .retrieve()
                .onStatus(HttpStatusCode::isError, response -> mapError(response.statusCode()))
                .toBodilessEntity()
                .timeout(restTimeout)
                .onErrorMap(this::wrapError)
                .then();
    }

    private Mono<Throwable> mapError(HttpStatusCode statusCode) {
        int code = statusCode.value();
        if (code == 400) {
            return Mono.error(new AnalyzerClientException("Bad request to Analyzer service", ErrorType.BAD_REQUEST));
        } else if (code == 404) {
            return Mono.error(new AnalyzerClientException("Resource not found in Analyzer service", ErrorType.NOT_FOUND));
        } else if (code == 409) {
            return Mono.error(new AnalyzerClientException("Conflict in Analyzer service", ErrorType.CONFLICT));
        } else if (code >= 500) {
            return Mono.error(new AnalyzerClientException("Analyzer service unavailable (HTTP " + code + ")", ErrorType.SERVICE_UNAVAILABLE));
        }
        return Mono.error(new AnalyzerClientException("Unexpected Analyzer error (HTTP " + code + ")", ErrorType.UNKNOWN));
    }

    private Throwable wrapError(Throwable ex) {
        if (ex instanceof AnalyzerClientException) {
            return ex;
        }
        if (ex instanceof WebClientResponseException wcre) {
            int code = wcre.getStatusCode().value();
            if (code == 400) return new AnalyzerClientException("Bad request: " + wcre.getMessage(), ErrorType.BAD_REQUEST);
            if (code == 404) return new AnalyzerClientException("Not found: " + wcre.getMessage(), ErrorType.NOT_FOUND);
            if (code == 409) return new AnalyzerClientException("Conflict: " + wcre.getMessage(), ErrorType.CONFLICT);
            if (code >= 500) return new AnalyzerClientException("Service unavailable: " + wcre.getMessage(), ErrorType.SERVICE_UNAVAILABLE);
        }
        if (ex instanceof java.util.concurrent.TimeoutException) {
            return new AnalyzerClientException("Analyzer service request timed out", ErrorType.TIMEOUT);
        }
        return new AnalyzerClientException("Communication error with Analyzer: " + ex.getMessage(), ErrorType.CONNECTION_ERROR, ex);
    }

    // --- Type reference for SSE deserialization ---

    private static org.springframework.core.ParameterizedTypeReference<ServerSentEvent<String>> sseType() {
        return new org.springframework.core.ParameterizedTypeReference<>() {};
    }

    // --- Nested Exception and Error Types ---

    /**
     * Error categories for Analyzer client failures.
     */
    public enum ErrorType {
        BAD_REQUEST,
        NOT_FOUND,
        CONFLICT,
        SERVICE_UNAVAILABLE,
        TIMEOUT,
        CONNECTION_ERROR,
        UNKNOWN
    }

    /**
     * Exception thrown when communication with the Analyzer service fails.
     */
    public static class AnalyzerClientException extends RuntimeException {

        private final ErrorType errorType;

        public AnalyzerClientException(String message, ErrorType errorType) {
            super(message);
            this.errorType = errorType;
        }

        public AnalyzerClientException(String message, ErrorType errorType, Throwable cause) {
            super(message, cause);
            this.errorType = errorType;
        }

        public ErrorType getErrorType() {
            return errorType;
        }
    }
}
