# Requirements Document — Software Archaeologist v3 (Production Hardening)

## Introduction

Este spec documenta las funcionalidades implementadas en la iteración V3, centrada en **hardening de producción, UX interactiva, y chat inteligente**. Todas estas features son incrementales sobre el MVP (v1) y la visión completa (v2), y fueron implementadas para resolver problemas reales encontrados en uso: timeouts de Bedrock, pipelines que fallan sin feedback, chat que no entiende el contexto, y UX cruda sin interactividad real.

## Glossary (extensiones a V2)

- **RAG_Chat**: Chat conversacional que usa Retrieval Augmented Generation con embeddings del código indexado
- **Embedding_Indexing**: Proceso que genera embeddings vectoriales del código fuente y los almacena en pgvector para búsqueda semántica
- **Job_Cancellation**: Capacidad de abortar un análisis en progreso desde la UI, propagando la señal hasta el pipeline de agentes
- **Progressive_Status**: Tracking granular del estado del pipeline, reportando qué agente está ejecutándose en tiempo real
- **Rate_Limiter**: Middleware que limita requests por IP/endpoint para prevenir abuso
- **Prompt_Guard**: Módulo que detecta y bloquea intentos de prompt injection en el chat
- **Guardrail**: Capa de validación que filtra contenido inapropiado o peligroso antes de enviarlo a Bedrock
- **SSE**: Server-Sent Events, protocolo de streaming unidireccional para status updates en tiempo real
- **FK_Fix**: Corrección de foreign key constraint que impedía indexar embeddings antes de que el proyecto existiera en la tabla `projects`
- **Similarity_Threshold**: Umbral mínimo de similitud coseno para considerar un chunk relevante en RAG

---

## Requirements

### Requirement V3-1: RAG Chat con Embedding Indexing Automático Post-Pipeline

**User Story:** As a Visitor, I want to chat with the analyzed repository using natural language and get contextual answers based on the actual code, so that I can explore the codebase conversationally without reading all files manually.

#### Acceptance Criteria

1. THE Pipeline SHALL automatically trigger embedding generation after completing the agent pipeline successfully
2. THE Embedding process SHALL chunk the repository source files into segments of ~500 tokens with overlap
3. THE Embeddings SHALL be generated using Amazon Titan Embed V2 (`amazon.titan-embed-text-v2:0`)
4. THE Embeddings SHALL be stored in PostgreSQL using pgvector (`vector(1024)` column in `code_embeddings` table)
5. THE Chat endpoint SHALL retrieve top-K relevant chunks (K=5) using cosine similarity before sending context to Claude
6. THE Chat responses SHALL be grounded in actual code snippets, citing file paths when referencing specific implementations
7. THE Frontend SHALL display chat responses with markdown rendering (code blocks, headers, lists)

### Requirement V3-2: Cancelación de Jobs (UI + API + Graceful Pipeline Stop)

**User Story:** As a Visitor, I want to cancel an in-progress analysis if I submitted the wrong URL or if it's taking too long, so that I don't have to wait for completion or waste resources.

#### Acceptance Criteria

1. THE Frontend SHALL display a "Cancel" button while a job is in status `RUNNING`
2. THE API SHALL expose `POST /api/v1/jobs/{job_id}/cancel` that sets job status to `CANCELLING`
3. THE Pipeline SHALL check for cancellation signal between each agent execution
4. THE Pipeline SHALL stop gracefully when cancellation is detected, preserving partial results already computed
5. THE Frontend SHALL update the UI to show `CANCELLED` status with partial results accessible
6. THE Cancellation SHALL be near-instant (< 5 seconds from button click to pipeline stop)

### Requirement V3-3: Botón Re-Analyze Cuando Agentes Fallan

**User Story:** As a Visitor, I want to retry the analysis when one or more agents fail (e.g., due to Bedrock throttling), so that I can get complete results without re-submitting the repository URL.

#### Acceptance Criteria

1. THE Frontend SHALL display a "Re-analyze" button when the job completes with `status=COMPLETED` but one or more agents have `status=FAILED`
2. THE Re-analyze action SHALL re-trigger the full pipeline for the same repository without re-cloning
3. THE API SHALL expose `POST /api/v1/jobs/{job_id}/retry` that creates a new job linked to the same project
4. THE Frontend SHALL navigate to the new job's progress view upon retry

### Requirement V3-4: Progressive Status Tracking (on_agent_start Callback)

**User Story:** As a Visitor, I want to see which specific agent is currently running during analysis, so that I know the pipeline is progressing and can estimate completion time.

#### Acceptance Criteria

1. THE Pipeline SHALL invoke an `on_agent_start` callback before each agent begins execution
2. THE Callback SHALL update the job record with `current_agent` name and `agent_started_at` timestamp
3. THE SSE stream SHALL emit `agent_started` events with agent name to the Frontend
4. THE Frontend SHALL display the current agent name (e.g., "Running: Security Agent...") in the progress UI
5. THE Frontend SHALL show elapsed time per agent

### Requirement V3-5: Bedrock Timeouts y Fail-Fast

**User Story:** As the system, I want to fail fast when Bedrock is unresponsive rather than hanging indefinitely, so that the pipeline completes in bounded time and individual agent failures don't block the entire analysis.

#### Acceptance Criteria

1. THE Bedrock adapter SHALL enforce a per-request timeout of 60 seconds
2. THE Bedrock adapter SHALL retry up to 2 times with exponential backoff (2s, 4s) on throttling errors
3. THE Agent pipeline SHALL continue to the next agent if one agent fails (graceful degradation)
4. THE Failed agent's result SHALL be recorded with error details in the job record
5. THE Total pipeline execution SHALL be bounded to 10 minutes maximum

### Requirement V3-6: Security Modules (Rate Limiter, Prompt Guard, Guardrail)

**User Story:** As the platform operator, I want the application protected against abuse, prompt injection, and inappropriate content, so that the system remains secure and available for legitimate users.

#### Acceptance Criteria

1. THE Rate Limiter SHALL enforce: 10 requests/minute per IP for analysis endpoints, 30 requests/minute for chat endpoints
2. THE Rate Limiter SHALL return HTTP 429 with `Retry-After` header when limits are exceeded
3. THE Prompt Guard SHALL detect common prompt injection patterns (e.g., "ignore previous instructions", "you are now", system prompt extraction attempts)
4. THE Prompt Guard SHALL reject detected injections with HTTP 400 and a generic error message (not revealing detection logic)
5. THE Guardrail SHALL validate chat input length (max 2000 characters) and output for harmful content categories
6. THE Security modules SHALL log all blocked requests for monitoring

### Requirement V3-7: Report Tabs Enriquecidos (7 Tabs con Data Real de Claude)

**User Story:** As a Visitor, I want the architecture report to be organized in meaningful tabs with rich, actionable content generated by Claude, so that I can navigate specific aspects of the analysis without information overload.

#### Acceptance Criteria

1. THE Report SHALL be organized in 7 tabs: Overview, Architecture, Quality, Security, Modernization, Dead Code, Documentation
2. EACH tab SHALL contain real analysis data from Claude (not placeholder text)
3. THE Overview tab SHALL show: key metrics, tech stack summary, overall health score
4. THE Architecture tab SHALL show: module structure, dependency patterns, coupling analysis
5. THE Quality tab SHALL show: code metrics, complexity hotspots, testing gaps
6. THE Security tab SHALL show: vulnerability findings with severity, remediation steps
7. THE Modernization tab SHALL show: prioritized recommendations with effort estimates
8. THE Frontend SHALL render tab content with proper formatting (tables, code blocks, badges)

### Requirement V3-8: Graph UX (Labels, Tooltips, Fullscreen)

**User Story:** As a Visitor, I want the dependency graph to be interactive and informative with node labels, hover tooltips, and fullscreen mode, so that I can explore the architecture visually without squinting.

#### Acceptance Criteria

1. THE Graph nodes SHALL display readable labels (module/file name, truncated if > 20 chars)
2. THE Graph nodes SHALL show tooltips on hover with: full path, LOC count, number of dependencies, language
3. THE Graph SHALL support fullscreen mode via a toggle button
4. THE Graph fullscreen mode SHALL use the entire viewport with a close/minimize button
5. THE Graph SHALL maintain zoom and pan state when toggling fullscreen

### Requirement V3-9: Chat Markdown Rendering (Headers, Bold, Lists, Code Blocks)

**User Story:** As a Visitor, I want the chat responses to render markdown properly (headings, bold, lists, fenced code blocks with syntax highlighting), so that technical explanations are readable and well-formatted.

#### Acceptance Criteria

1. THE Chat component SHALL render markdown using a library (react-markdown or similar)
2. THE Renderer SHALL support: `#` headers, `**bold**`, `- lists`, `` `inline code` ``, and fenced code blocks with language
3. THE Code blocks SHALL have syntax highlighting appropriate to the detected language
4. THE Chat messages SHALL preserve whitespace and formatting from the LLM response
5. THE Chat SHALL auto-scroll to the latest message

### Requirement V3-10: Reindex Script para Desarrollo sin Re-Análisis Completo

**User Story:** As a developer, I want a script that re-generates embeddings for an existing project without re-running the full analysis pipeline, so that I can iterate on RAG quality without waiting 5+ minutes per test.

#### Acceptance Criteria

1. THE Script SHALL accept a project_id parameter and re-index only that project's source files
2. THE Script SHALL delete existing embeddings for the project before re-indexing (idempotent)
3. THE Script SHALL be executable via `python -m src.scripts.reindex --project-id <UUID>`
4. THE Script SHALL report progress (files processed / total) and completion time
5. THE Script SHALL work on repositories already cloned (no re-clone needed)

### Requirement V3-11: SSE Parsing Fix (event: con/sin Espacio)

**User Story:** As a frontend developer, I want SSE events to parse correctly regardless of whether the server sends `event:status` or `event: status` (with space after colon), so that the progress view works reliably across environments.

#### Acceptance Criteria

1. THE SSE parser SHALL handle both `event:value` and `event: value` formats (per SSE spec, space after colon is optional)
2. THE SSE parser SHALL handle both `data:value` and `data: value` formats
3. THE Frontend SHALL not show blank/stuck progress due to unparsed events
4. THE Fix SHALL be applied to all SSE consumption points in the frontend

### Requirement V3-12: FK Fix para code_embeddings (INSERT INTO projects Antes de Indexar)

**User Story:** As the system, I want the embedding indexing process to ensure the project record exists in the `projects` table before inserting embeddings that reference it, so that foreign key constraints are satisfied and indexing doesn't fail silently.

#### Acceptance Criteria

1. THE Indexing process SHALL INSERT the project into the `projects` table (if not exists) before creating embeddings
2. THE INSERT SHALL use `ON CONFLICT DO NOTHING` to be idempotent on re-runs
3. THE `code_embeddings` table SHALL have a valid FK constraint to `projects(id)`
4. THE Fix SHALL prevent `INSERT or update on table "code_embeddings" violates foreign key constraint` errors

### Requirement V3-13: Similarity Threshold Ajustado (0.3 → 0.05)

**User Story:** As a Visitor, I want the RAG chat to return relevant results even for broad or exploratory questions, so that the chat is useful for general questions about the codebase (not just exact keyword matches).

#### Acceptance Criteria

1. THE Similarity threshold SHALL be set to 0.05 (cosine distance) for chunk retrieval
2. THE Lower threshold SHALL allow broader matches while still filtering completely irrelevant content
3. THE Chat SHALL return meaningful responses for general questions like "what does this project do?" or "what frameworks are used?"
4. THE System SHALL still use top-K (K=5) to limit context size regardless of how many chunks pass the threshold
