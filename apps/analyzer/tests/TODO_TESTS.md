# Analyzer Tests — TODO

Priority test areas:

1. **AgentPipeline** — sequential execution, graceful degradation, cancellation
2. **RepositoryAgent** — clone + parse + graph construction
3. **GitAdapter** — clone success/failure, file count validation
4. **ASTChunker** — chunk splitting, merging, context headers
5. **RAGRetriever** — vector search, re-ranking, threshold filtering
6. **PromptGuard** — injection detection patterns, sanitization
7. **RateLimiter** — sliding window, allow/deny decisions
8. **BedrockAdapter** — retry logic, error handling (mock boto3)
9. **API routes** — /analyze, /query, /graph, /jobs

Framework: pytest + pytest-asyncio + httpx (for TestClient)
Run: `pytest`
