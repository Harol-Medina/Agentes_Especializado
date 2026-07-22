package com.archaeologist.domain.service;

import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.regex.Pattern;

@Service
public class GitHubUrlValidator {

    private static final Pattern GITHUB_URL_PATTERN =
        Pattern.compile("^https://github\\.com/[\\w.-]+/[\\w.-]+/?$");

    private static final long MAX_REPO_SIZE_KB = 500L * 1024; // 500 MB in KB

    private final WebClient webClient;

    public GitHubUrlValidator(WebClient.Builder webClientBuilder) {
        this.webClient = webClientBuilder
            .baseUrl("https://api.github.com")
            .defaultHeader("Accept", "application/vnd.github.v3+json")
            .defaultHeader("User-Agent", "Software-Archaeologist")
            .build();
    }

    /**
     * Validates that the URL matches the GitHub repository pattern.
     */
    public boolean isValidFormat(String repoUrl) {
        if (repoUrl == null || repoUrl.isBlank()) {
            return false;
        }
        return GITHUB_URL_PATTERN.matcher(repoUrl.trim()).matches();
    }

    /**
     * Validates the URL format and checks that the repository is publicly accessible
     * and within size limits via the GitHub API.
     *
     * @return a Mono emitting the ValidationResult
     */
    public Mono<ValidationResult> validate(String repoUrl) {
        if (!isValidFormat(repoUrl)) {
            return Mono.just(ValidationResult.invalid("INVALID_URL",
                "The provided URL is not a valid public GitHub repository."));
        }

        String[] parts = extractOwnerRepo(repoUrl);
        if (parts == null) {
            return Mono.just(ValidationResult.invalid("INVALID_URL",
                "Could not extract owner/repo from the URL."));
        }

        String owner = parts[0];
        String repo = parts[1];

        return webClient.get()
            .uri("/repos/{owner}/{repo}", owner, repo)
            .retrieve()
            .bodyToMono(GitHubRepoResponse.class)
            .timeout(Duration.ofSeconds(10))
            .map(response -> {
                if (response.privateRepo()) {
                    return ValidationResult.invalid("REPO_NOT_ACCESSIBLE",
                        "Repository is private or does not exist.");
                }
                long sizeKb = response.size();
                if (sizeKb > MAX_REPO_SIZE_KB) {
                    long sizeMb = sizeKb / 1024;
                    return ValidationResult.invalid("REPO_TOO_LARGE",
                        "Repository exceeds 500 MB limit (current: " + sizeMb + " MB).");
                }
                return ValidationResult.valid(sizeKb * 1024); // Convert KB to bytes
            })
            .onErrorResume(ex -> Mono.just(ValidationResult.invalid("REPO_NOT_ACCESSIBLE",
                "Repository is private or does not exist.")));
    }

    private String[] extractOwnerRepo(String repoUrl) {
        String trimmed = repoUrl.trim();
        if (trimmed.endsWith("/")) {
            trimmed = trimmed.substring(0, trimmed.length() - 1);
        }
        String prefix = "https://github.com/";
        String path = trimmed.substring(prefix.length());
        String[] segments = path.split("/");
        if (segments.length == 2) {
            return segments;
        }
        return null;
    }

    /**
     * Internal record to deserialize GitHub API response (relevant fields only).
     */
    private record GitHubRepoResponse(
        long size,
        @com.fasterxml.jackson.annotation.JsonProperty("private") boolean privateRepo
    ) {}


    public record ValidationResult(
        boolean valid,
        String errorCode,
        String errorMessage,
        long repoSizeBytes
    ) {
        public static ValidationResult valid(long repoSizeBytes) {
            return new ValidationResult(true, null, null, repoSizeBytes);
        }

        public static ValidationResult invalid(String errorCode, String message) {
            return new ValidationResult(false, errorCode, message, 0);
        }
    }
}
