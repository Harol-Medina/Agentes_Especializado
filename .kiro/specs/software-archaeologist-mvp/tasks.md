# Implementation Plan: Software Archaeologist MVP

## Overview

Implementación del MVP completo de Software Archaeologist siguiendo vertical slices. Se inicia con la infraestructura Docker y base de datos, luego el esqueleto de cada servicio (Backend, Analyzer, Frontend), después las features en orden de dependencia: submission → pipeline → graph → chat → report → export. Cada servicio usa su lenguaje específico: Java 21/Spring Boot (Backend), Python 3.11/FastAPI (Analyzer), TypeScript/Next.js 14 (Frontend).

## Tasks

- [ ] 1. Infrastructure and Database Setup
  - [ ] 1.1 Create project directory structure and Docker Compose configuration
    - Create `docker-compose.yml` at project root with 5 services: nginx, frontend, backend, analyzer, db (pgvector/pgvector:pg15)
    - Create `docker/backend/Dockerfile` (Java 21 + Gradle)
    - Create `docker/frontend/Dockerfile` (Node 20 + Next.js)
    - Create `docker/analyzer/Dockerfile` (Python 3.11 + FastAPI)
    - Create `nginx/default.conf` with path-based routing (/api/* → backend, /* → frontend)
    - Create `.data/.env` with all environment variables (PostgreSQL, Spring, FastAPI, AWS, Next.js)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [ ] 1.2 Create PostgreSQL schema and migrations
    - Create Flyway migration `V1__initial_schema.sql` in `apps/backend/src/main/resources/db/migration/`
    - Include tables: `analysis_jobs`, `projects`, `graph_nodes`, `graph_edges`, `agent_results`, `code_embeddings`, `architecture_reports`, `kiro_specs`
    - Enable `pgvector` extension and create IVFFlat index on embeddings
    - Create all indexes as defined in the design
    - _Requirements: 3.5, 11.4_

- [ ] 2. Backend Service Skeleton (Java 21 / Spring Boot 3.x)
  - [ ] 2.1 Initialize Spring Boot project with domain models and configuration
    - Create `apps/backend/` with Gradle build (Spring Boot 3.x, Java 21, WebFlux, JPA, Flyway, PostgreSQL driver)
    - Implement domain models: `AnalysisJob`, `Project`, `JobStatus` enum, `AgentResult`
    - Implement JPA entities and repository interfaces
    - Configure `application.yml` with datasource, Flyway, server port
    - _Requirements: 11.1, 12.1_

  - [ ] 2.2 Implement URL validation and job submission endpoint
    - Create `GitHubUrlValidator` with regex pattern matching and HEAD request validation
    - Create `JobQueueService` with `AtomicReference<UUID>` for single-slot processing
    - Create `AnalysisJobController` with `POST /api/v1/jobs` endpoint
    - Return 202 Accepted on success, 400 on invalid URL, 409 on system busy
    - Validate repo size < 500MB and file count < 50,000
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 10.1, 10.2_

  - [ ]* 2.3 Write property test for URL validation
    - **Property 1: URL Validation Rejects Invalid Inputs**
    - **Validates: Requirements 1.3**

  - [ ]* 2.4 Write property test for sequential processing invariant
    - **Property 2: Sequential Processing Invariant**
    - **Validates: Requirements 1.4, 10.1, 10.2, 10.3**

  - [ ] 2.5 Implement job status polling and webhook receiver
    - Create `GET /api/v1/jobs/{jobId}` endpoint returning progress with agent statuses
    - Create `WebhookController` with `POST /api/webhooks/analysis-complete`
    - Implement `PollingScheduler` with @Scheduled task polling Analyzer every 5s
    - On webhook receipt: update job status, release processing slot, persist results
    - _Requirements: 9.1, 9.2, 9.3, 12.2, 12.3, 10.3_

  - [ ] 2.6 Implement Analyzer HTTP client
    - Create `AnalyzerClient` using WebClient to call `POST /analyze`, `GET /jobs/{id}`, `GET /graph/{projectId}`, `POST /query`
    - Handle 202 responses, timeout configuration, error mapping
    - _Requirements: 12.1, 12.2, 12.4, 12.5_

- [ ] 3. Checkpoint - Backend foundation verified
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Analyzer Service Skeleton (Python 3.11+ / FastAPI)
  - [ ] 4.1 Initialize FastAPI project with domain models and configuration
    - Create `apps/analyzer/` with `pyproject.toml`, `requirements.txt`
    - Create `src/main.py` FastAPI app entrypoint
    - Implement domain models: `ProjectModel`, `GraphNode`, `GraphEdge`, `AnalysisJob`, `AgentResult`, enums (`NodeType`, `EdgeType`, `JobStatus`, `AgentStatus`)
    - Create `src/config.py` with pydantic-settings for all env vars
    - Create `src/api/schemas.py` with Pydantic request/response models
    - _Requirements: 6.1, 11.1_

  - [ ] 4.2 Implement base agent interface and pipeline orchestrator
    - Create `src/agents/base.py` with `BaseAgent` abstract class (name, execution_order, execute, can_execute)
    - Create `PipelineContext` dataclass with accumulated context fields
    - Create `AgentOutput` dataclass
    - Create `src/agents/pipeline.py` with `AgentPipeline` class implementing sequential execution with graceful degradation
    - Critical path: Repository_Agent failure terminates pipeline; other agents skip on failure
    - _Requirements: 6.1, 6.2, 6.3, 13.1, 13.2_

  - [ ]* 4.3 Write property test for pipeline sequential data flow
    - **Property 9: Pipeline Sequential Data Flow with Graceful Degradation**
    - **Validates: Requirements 6.1, 6.2, 6.3**

  - [ ] 4.4 Implement Repository Agent (critical path)
    - Create `src/agents/repository_agent.py` with git clone, language detection, AST parsing, graph construction
    - Create `src/adapters/git_adapter.py` for cloning operations with size validation
    - Create `src/parsing/language_detector.py` with marker-based detection (Java, TypeScript, JavaScript frameworks)
    - Create `src/parsing/tree_sitter_parser.py` for TS/JS/Java AST parsing
    - Create `src/graph/builder.py` for constructing ProjectModel from parsed files
    - Create `src/graph/models.py` with Node/Edge dataclasses
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 4.5 Write property test for language and framework detection
    - **Property 3: Language and Framework Detection Correctness**
    - **Validates: Requirements 2.1, 2.2, 2.3**

  - [ ]* 4.6 Write property test for AST parsing output validity
    - **Property 4: AST Parsing Produces Valid Output**
    - **Validates: Requirements 3.1**

  - [ ]* 4.7 Write property test for project model node completeness
    - **Property 5: Project Model Node Completeness**
    - **Validates: Requirements 3.2, 3.3, 3.4**

  - [ ] 4.8 Implement analysis API endpoints
    - Create `src/api/routes/analyze.py` with `POST /analyze` (202 Accepted, async execution)
    - Create `src/api/routes/jobs.py` with `GET /jobs/{job_id}` for status polling
    - Create `src/adapters/webhook_adapter.py` for notifying Backend on completion
    - Wire pipeline execution as background task on POST /analyze
    - _Requirements: 12.1, 12.3, 6.5_

- [ ] 5. Checkpoint - Analyzer foundation verified
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Remaining Agents Implementation
  - [ ] 6.1 Implement Architecture, Quality, Security, Documentation agents
    - Create `src/agents/architecture_agent.py` — pattern detection, layer analysis using Claude Sonnet
    - Create `src/agents/quality_agent.py` — complexity metrics, code smell detection via Bedrock
    - Create `src/agents/security_agent.py` — vulnerability scanning via Bedrock
    - Create `src/agents/documentation_agent.py` — documentation generation via Bedrock
    - Create `src/adapters/bedrock_adapter.py` for AWS Bedrock client (Claude Sonnet + retry with exponential backoff)
    - _Requirements: 6.1, 6.4, 7.1_

  - [ ] 6.2 Implement Modernization and Kiro agents
    - Create `src/agents/modernization_agent.py` — refactoring plan generation via Bedrock
    - Create `src/agents/kiro_agent.py` — transforms modernization plan into Kiro Spec markdown format
    - Handle partial generation when Modernization_Agent fails (use Architecture_Report data)
    - _Requirements: 8.1, 8.3, 8.4_

  - [ ]* 6.3 Write property test for architecture report completeness
    - **Property 10: Architecture Report Completeness with Degradation**
    - **Validates: Requirements 7.1, 7.3, 13.4**

  - [ ]* 6.4 Write property test for Kiro spec structural completeness
    - **Property 11: Kiro Spec Structural Completeness**
    - **Validates: Requirements 8.1, 8.3**

- [ ] 7. RAG System (Embeddings + Chat)
  - [ ] 7.1 Implement embedding generation and pgvector indexing
    - Create `src/rag/embeddings.py` with Titan Embeddings V2 client via Bedrock
    - Create `src/parsing/chunker.py` with AST-aware chunking (function/method boundaries, context headers)
    - Create `src/rag/indexer.py` for pgvector bulk insert of embeddings
    - Create `src/adapters/postgres_adapter.py` with asyncpg + pgvector support
    - Integrate embedding generation into Repository_Agent post-graph-construction
    - _Requirements: 5.1, 5.2_

  - [ ]* 7.2 Write property test for AST-aware chunking
    - **Property 7: AST-Aware Chunking Preserves Function Boundaries**
    - **Validates: Requirements 5.2**

  - [ ] 7.3 Implement RAG retriever and query endpoint
    - Create `src/rag/retriever.py` with semantic search (pgvector cosine similarity), architectural re-ranking, relevance threshold (0.65)
    - Create `src/rag/generator.py` for Claude Sonnet response generation with retrieved context
    - Create `src/api/routes/query.py` with `POST /query` (SSE streaming response)
    - Handle "no relevant context" case when all scores below threshold
    - _Requirements: 5.3, 5.4, 5.5, 5.6_

  - [ ]* 7.4 Write property test for RAG no-context threshold
    - **Property 8: RAG No-Context Threshold**
    - **Validates: Requirements 5.6**

- [ ] 8. Checkpoint - Analyzer pipeline complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Backend API Completion
  - [ ] 9.1 Implement Chat SSE relay endpoint
    - Create `ChatController` with `POST /api/v1/chat` that forwards to Analyzer and relays SSE stream to Frontend
    - Use Spring WebFlux for non-blocking SSE relay
    - _Requirements: 5.5, 12.4_

  - [ ] 9.2 Implement Graph, Report, and Export endpoints
    - Create `GraphController` with `GET /api/v1/projects/{id}/graph` (query params: module, edgeType, depth)
    - Create `ReportController` with `GET /api/v1/projects/{id}/report` returning structured JSON
    - Create `ExportController` with `GET /api/v1/projects/{id}/kiro-spec` returning markdown file download
    - Create `src/api/routes/graph.py` in Analyzer with `GET /graph/{project_id}` and filter support
    - _Requirements: 4.1, 4.4, 7.1, 7.2, 8.1, 8.2, 12.5_

  - [ ]* 9.3 Write property test for graph filtering correctness
    - **Property 6: Graph Filtering Correctness**
    - **Validates: Requirements 4.4**

- [ ] 10. Frontend — Submission and Progress
  - [ ] 10.1 Initialize Next.js project with layout and design system
    - Create `apps/frontend/` with Next.js 14+ App Router, TypeScript, Tailwind CSS
    - Configure `tailwind.config.ts` with design system tokens (colors, fonts, spacing per design-system steering)
    - Create root `layout.tsx` with dark theme, Google Fonts (Roboto Slab, Inter, JetBrains Mono)
    - Create `globals.css` with CSS custom properties from design system
    - Install shadcn/ui for primitive components
    - _Requirements: 11.1_

  - [ ] 10.2 Implement repository submission page
    - Create landing `page.tsx` with hero layout (1fr 420px grid)
    - Create `SubmissionForm` component with URL input, validation, submit action
    - Implement client-side validation for GitHub URL format
    - Handle API responses: success (redirect to analysis page), 400 (show error), 409 (show busy message)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 10.2_

  - [ ] 10.3 Implement analysis progress page
    - Create `analysis/[jobId]/page.tsx` as analysis dashboard layout with tabs
    - Create `PipelineProgress` component showing 7 agent stages with status dots (glow animation for active)
    - Create `useAnalysisStatus` hook polling `GET /api/v1/jobs/{jobId}` every 5s
    - Display current agent, completed count, and handle failure indicators
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 13.3_

- [ ] 11. Frontend — Dependency Graph
  - [ ] 11.1 Implement interactive dependency graph view
    - Install React Flow library
    - Create `components/graph/DependencyGraph.tsx` with React Flow wrapper
    - Create custom node types: `ModuleNode`, `PackageNode`, `FileNode`, `ClassNode`, `ExternalNode` (distinct visual style)
    - Create custom edge types: `ImportEdge`, `InheritanceEdge`, `UsageEdge`, `CompositionEdge`
    - Create `GraphFilters` component with module, relationship type, and depth selectors
    - Create `useGraphData` hook calling `GET /api/v1/projects/{id}/graph` with filter params
    - Implement zoom, pan, and node click navigation
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 11.2 Write property test for external dependency visual distinction
    - **Property 12: External Dependency Visual Distinction**
    - **Validates: Requirements 4.3**

- [ ] 12. Frontend — Chat Interface
  - [ ] 12.1 Implement RAG chat interface
    - Create `components/chat/ChatInterface.tsx` with message list and input
    - Create `components/chat/ChatMessage.tsx` for user and assistant messages
    - Create `useSSEChat` hook connecting to `POST /api/v1/chat` with SSE streaming
    - Display streaming tokens in real-time, show sources list on completion
    - Handle "no relevant information" response gracefully
    - Create BFF route in `app/api/` for SSE proxy if needed
    - _Requirements: 5.3, 5.5, 5.6_

- [ ] 13. Frontend — Report and Export
  - [ ] 13.1 Implement architecture report view
    - Create `components/report/ArchitectureReport.tsx` with formatted sections
    - Display: language/framework info, module structure, dependencies (internal/external), components with responsibilities, metrics
    - Show "Analysis incomplete" indicators for failed sections with explanation
    - Fetch report from `GET /api/v1/projects/{id}/report`
    - _Requirements: 7.1, 7.2, 7.3, 13.3, 13.4_

  - [ ] 13.2 Implement Kiro spec export
    - Create `components/export/KiroExport.tsx` with download button
    - Trigger download from `GET /api/v1/projects/{id}/kiro-spec` as markdown file
    - Show partial spec indicator when Modernization_Agent failed
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 14. Integration and Wiring
  - [ ] 14.1 Wire all services end-to-end and verify Docker Compose
    - Ensure all services start correctly with `docker compose up`
    - Verify nginx routing: /api/* → backend:8080, /* → frontend:3000
    - Verify Backend ↔ Analyzer communication (POST /analyze, polling, webhook)
    - Verify Frontend ↔ Backend communication (submission, status, graph, chat, report, export)
    - Test SSE streaming through nginx (proxy_buffering off)
    - _Requirements: 11.5, 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 14.2 Write integration tests for end-to-end flows
    - Test complete flow: submit URL → poll progress → view graph → chat → report → export
    - Test graceful degradation: agent failure → partial results displayed correctly
    - Test system busy: concurrent submissions rejected with 409
    - _Requirements: 1.2, 1.4, 6.3, 10.1, 13.1, 13.2, 13.3_

- [ ] 15. Final Checkpoint - All services integrated
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The pipeline is the critical path: Repository_Agent must work for anything else to function
- Backend uses Java 21 / Spring Boot 3.x / Gradle
- Frontend uses TypeScript / Next.js 14 / React 18 / Tailwind CSS / React Flow
- Analyzer uses Python 3.11+ / FastAPI / asyncpg / tree-sitter
- All services communicate via REST, webhooks, and SSE as defined in the design
- Infrastructure files (docker-compose, Dockerfiles, nginx) live at root per project-structure rules
- Application code lives in `apps/backend/`, `apps/frontend/`, `apps/analyzer/`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "10.1"] },
    { "id": 2, "tasks": ["2.1", "4.1"] },
    { "id": 3, "tasks": ["2.2", "4.2", "10.2"] },
    { "id": 4, "tasks": ["2.3", "2.4", "4.3", "4.4"] },
    { "id": 5, "tasks": ["2.5", "2.6", "4.5", "4.6", "4.7", "4.8"] },
    { "id": 6, "tasks": ["6.1", "7.1"] },
    { "id": 7, "tasks": ["6.2", "6.3", "6.4", "7.2", "7.3"] },
    { "id": 8, "tasks": ["7.4", "9.1", "9.2"] },
    { "id": 9, "tasks": ["9.3", "10.3"] },
    { "id": 10, "tasks": ["11.1", "12.1"] },
    { "id": 11, "tasks": ["11.2", "13.1", "13.2"] },
    { "id": 12, "tasks": ["14.1"] },
    { "id": 13, "tasks": ["14.2"] }
  ]
}
```
