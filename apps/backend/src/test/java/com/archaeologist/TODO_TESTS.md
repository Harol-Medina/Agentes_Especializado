# Backend Tests — TODO

Priority test areas:

1. **AnalysisJobController** — submit job, get status, cancel
2. **WebhookController** — HMAC signature validation, status updates
3. **ChatController** — SSE streaming relay, input validation
4. **GraphController** — graph retrieval, error responses
5. **GitHubUrlValidator** — valid/invalid URL patterns
6. **AnalyzerClient** — WebClient integration (use WireMock)

Framework: JUnit 5 + Spring Boot Test + Reactor Test (for Mono/Flux)
Run: `./gradlew test`
