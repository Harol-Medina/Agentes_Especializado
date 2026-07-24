---
inclusion: auto
---

# Agent Rules

Cross-cutting rules that every agent (manual or automatic) must follow. These override any agent-specific behavior when in conflict.

---

## Structure Rules

1. **Application code goes in `apps/<service>/`**. Never create source files outside this boundary.
2. **Dockerfiles go in `docker/<service>/Dockerfile`**. Never modify Dockerfiles from within app code.
3. **Environment variables go in `.data/.env`**. Never create `.env` files inside app directories.
4. **Documentation goes in `docs/`**. Specs in `.kiro/specs/`.
5. **Never generate bind mounts** in docker-compose. The Dockerfile copies code internally.
6. **Never create files at the repo root** unless they are infra-related (docker-compose, nginx, README).

## Communication Protocol

- Code: English (variable names, comments, commit messages, PR descriptions).
- Documentation: Spanish (specs, steering, agent outputs, user-facing docs).
- Agent feedback: Spanish (reviews, suggestions, analysis results).

## Code Generation Rules

1. **Read before write**. Always read the existing file before proposing changes.
2. **Match existing patterns**. Don't introduce new libraries, conventions, or architectures unless explicitly requested.
3. **Respect the design system**. Frontend code must use the CSS tokens defined in `design-system.md`.
4. **No placeholder code**. Every function must have a real implementation or throw `NotImplementedError`.
5. **No console.log / print statements** in production code. Use proper logging.
6. **No TODO comments without a tracking reference**. Either fix it now or create an issue.

## Security Rules

1. **Never hardcode secrets**. Use `System.getenv()`, `os.environ`, or `process.env`.
2. **Validate all user input** at the boundary (controller/route level).
3. **Parameterized queries only**. No string concatenation for SQL.
4. **HMAC-validate webhook payloads** between Analyzer and Backend.
5. **Sanitize before rendering** any user-generated content in the frontend.

## Testing Rules

1. **New features require tests**. No PR without at least one test for the happy path.
2. **Bug fixes require a regression test**. Write the failing test first.
3. **Don't mock what you don't own**. Use testcontainers / httpx for integration boundaries.
4. **Test behavior, not implementation**. Tests should survive refactors.

## Performance Rules

1. **Paginate all list endpoints**. Default 20, max 100.
2. **No N+1 queries**. Use eager loading or batch queries.
3. **Async for I/O**. HTTP calls, DB queries, file operations must not block.
4. **Cache expensive operations**. Embeddings, parsed ASTs, LLM responses where idempotent.

## Agent Delegation Rules

1. **One agent, one concern**. Don't ask the security agent to also do performance review.
2. **Provide context, not instructions**. Tell the agent what to review, not how to do it.
3. **Accept agent output as authoritative** unless it contradicts project steering.
4. **Escalate to user** when agents disagree on approach or when the change is high-risk.

## Docker Rules

1. **Multi-stage builds always**. Stage 1: build dependencies + compile. Stage 2: minimal runtime.
2. **`COPY apps/<service>/ .`** inside Dockerfile. The build is self-contained.
3. **`env_file: .data/.env`** in docker-compose for every service.
4. **Three commands are enough**: `docker compose build`, `docker compose up`, `docker compose down`.
5. **No flags, no scripts, no custom entrypoints** unless solving a specific documented problem.

## Verification Gate

Before any code is considered "done", it must pass:

1. **Build**: `./gradlew build` / `npm run build` / `pip install -e .`
2. **Tests**: `./gradlew test` / `npm test` / `pytest`
3. **Lint**: `./gradlew spotlessCheck` / `npm run lint` / `ruff check .`
4. **Type-check**: TypeScript strict / mypy (Python) / Java compiler
5. **Security**: No new vulnerabilities in dependency scan

If any step fails, the code is not ready for review.
