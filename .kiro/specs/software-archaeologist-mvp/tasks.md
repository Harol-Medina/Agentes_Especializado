# Implementation Plan: Software Archaeologist MVP

## Overview

Implementación del MVP completo de Software Archaeologist siguiendo vertical slices. Se inicia con la infraestructura Docker y base de datos, luego el esqueleto de cada servicio (Backend, Analyzer, Frontend), después las features en orden de dependencia: submission → pipeline → graph → chat → report → export. Cada servicio usa su lenguaje específico: Java 21/Spring Boot (Backend), Python 3.11/FastAPI (Analyzer), TypeScript/Next.js 14 (Frontend).

## Tasks

- [x] 1. Infrastructure and Database Setup
  - [x] 1.1 Create project directory structure and Docker Compose configuration
    - Create `docker-compose.yml` at project root with 5 services: nginx, frontend, backend, analyzer, db (pgvector/pgvector:pg15)
    - Create `docker/backend/Dockerfile` (Java 21 + Gradle)
    - Create `docker/frontend/Dockerfile` (Node 20 + Next.js)
    - Create `docker/analyzer/Dockerfile` (Python 3.11 + FastAPI)
    - Create `nginx/default.conf` with path-based routing (/api/* → backend, /* → frontend)
    - Create `.data/.env` with all environment variables (PostgreSQL, Spring, FastAPI, AWS, Next.js)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 1.2 Create PostgreSQL schema and migrations
    - Create Flyway migration `V1__initial_schema.sql` in `apps/backend/src/main/resources/db/migration/`
    - Include tables: `analysis_jobs`, `projects`, `graph_nodes`, `graph_edges`, `agent_results`, `code_embeddings`, `architecture_reports`, `kiro_specs`
    - Enable `pgvector` extension and create IVFFlat index on embeddings
    - Create all indexes as defined in the design
    - _Requirements: 3.5, 11.4_

- [x] 2. Backend Service Skeleton (Java 21 / Spring Boot 3.x)
  - [x] 2.1 Initialize Spring Boot project with domain models and configuration
    - Create `apps/backend/` with Gradle build (Spring Boot 3.x, Java 21, WebFlux, JPA, Flyway, PostgreSQL driver)
    - Implement domain models: `AnalysisJob`, `Project`, `JobStatus` enum, `AgentResult`
    - Implement JPA entities and repository interfaces
    - Configure `application.yml` with datasource, Flyway, server port
    - _Requirements: 11.1, 12.1_

  - [x] 2.2 Implement URL validation and job submission endpoint
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

  - [x] 2.5 Implement job status polling and webhook receiver
    - Create `GET /api/v1/jobs/{jobId}` endpoint returning progress with agent statuses
    - Create `WebhookController` with `POST /api/webhooks/analysis-complete`
    - Implement `PollingScheduler` with @Scheduled task polling Analyzer every 5s
    - On webhook receipt: update job status, release processing slot, persist results
    - _Requirements: 9.1, 9.2, 9.3, 12.2, 12.3, 10.3_

  - [x] 2.6 Implement Analyzer HTTP client
    - Create `AnalyzerClient` using WebClient to call `POST /analyze`, `GET /jobs/{id}`, `GET /graph/{projectId}`, `POST /query`
    - Handle 202 responses, timeout configuration, error mapping
    - _Requirements: 12.1, 12.2, 12.4, 12.5_

- [x] 3. Checkpoint - Backend foundation verified
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Analyzer Service Skeleton (Python 3.11+ / FastAPI)
  - [x] 4.1 Initialize FastAPI project with domain models and configuration
    - Create `apps/analyzer/` with `pyproject.toml`, `requirements.txt`
    - Create `src/main.py` FastAPI app entrypoint
    - Implement domain models: `ProjectModel`, `GraphNode`, `GraphEdge`, `AnalysisJob`, `AgentResult`, enums (`NodeType`, `EdgeType`, `JobStatus`, `AgentStatus`)
    - Create `src/config.py` with pydantic-settings for all env vars
    - Create `src/api/schemas.py` with Pydantic request/response models
    - _Requirements: 6.1, 11.1_

  - [x] 4.2 Implement base agent interface and pipeline orchestrator
    - Create `src/agents/base.py` with `BaseAgent` abstract class (name, execution_order, execute, can_execute)
    - Create `PipelineContext` dataclass with accumulated context fields
    - Create `AgentOutput` dataclass
    - Create `src/agents/pipeline.py` with `AgentPipeline` class implementing sequential execution with graceful degradation
    - Critical path: Repository_Agent failure terminates pipeline; other agents skip on failure
    - _Requirements: 6.1, 6.2, 6.3, 13.1, 13.2_

  - [ ]* 4.3 Write property test for pipeline sequential data flow
    - **Property 9: Pipeline Sequential Data Flow with Graceful Degradation**
    - **Validates: Requirements 6.1, 6.2, 6.3**

  - [x] 4.4 Implement Repository Agent (critical path)
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

  - [x] 4.8 Implement analysis API endpoints
    - Create `src/api/routes/analyze.py` with `POST /analyze` (202 Accepted, async execution)
    - Create `src/api/routes/jobs.py` with `GET /jobs/{job_id}` for status polling
    - Create `src/adapters/webhook_adapter.py` for notifying Backend on completion
    - Wire pipeline execution as background task on POST /analyze
    - _Requirements: 12.1, 12.3, 6.5_

- [x] 5. Checkpoint - Analyzer foundation verified
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Remaining Agents Implementation
  - [x] 6.1 Implement Architecture, Quality, Security, Documentation agents
    - Create `src/agents/architecture_agent.py` — pattern detection, layer analysis using Claude Sonnet
    - Create `src/agents/quality_agent.py` — complexity metrics, code smell detection via Bedrock
    - Create `src/agents/security_agent.py` — vulnerability scanning via Bedrock
    - Create `src/agents/documentation_agent.py` — documentation generation via Bedrock
    - Create `src/adapters/bedrock_adapter.py` for AWS Bedrock client (Claude Sonnet + retry with exponential backoff)
    - _Requirements: 6.1, 6.4, 7.1_

  - [x] 6.2 Implement Modernization and Kiro agents
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

- [x] 7. RAG System (Embeddings + Chat)
  - [x] 7.1 Implement embedding generation and pgvector indexing
    - Create `src/rag/embeddings.py` with Titan Embeddings V2 client via Bedrock
    - Create `src/parsing/chunker.py` with AST-aware chunking (function/method boundaries, context headers)
    - Create `src/rag/indexer.py` for pgvector bulk insert of embeddings
    - Create `src/adapters/postgres_adapter.py` with asyncpg + pgvector support
    - Integrate embedding generation into Repository_Agent post-graph-construction
    - _Requirements: 5.1, 5.2_

  - [ ]* 7.2 Write property test for AST-aware chunking
    - **Property 7: AST-Aware Chunking Preserves Function Boundaries**
    - **Validates: Requirements 5.2**

  - [x] 7.3 Implement RAG retriever and query endpoint
    - Create `src/rag/retriever.py` with semantic search (pgvector cosine similarity), architectural re-ranking, relevance threshold (0.65)
    - Create `src/rag/generator.py` for Claude Sonnet response generation with retrieved context
    - Create `src/api/routes/query.py` with `POST /query` (SSE streaming response)
    - Handle "no relevant context" case when all scores below threshold
    - _Requirements: 5.3, 5.4, 5.5, 5.6_

  - [ ]* 7.4 Write property test for RAG no-context threshold
    - **Property 8: RAG No-Context Threshold**
    - **Validates: Requirements 5.6**

- [x] 8. Checkpoint - Analyzer pipeline complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Backend API Completion
  - [x] 9.1 Implement Chat SSE relay endpoint
    - Create `ChatController` with `POST /api/v1/chat` that forwards to Analyzer and relays SSE stream to Frontend
    - Use Spring WebFlux for non-blocking SSE relay
    - _Requirements: 5.5, 12.4_

  - [x] 9.2 Implement Graph, Report, and Export endpoints
    - Create `GraphController` with `GET /api/v1/projects/{id}/graph` (query params: module, edgeType, depth)
    - Create `ReportController` with `GET /api/v1/projects/{id}/report` returning structured JSON
    - Create `ExportController` with `GET /api/v1/projects/{id}/kiro-spec` returning markdown file download
    - Create `src/api/routes/graph.py` in Analyzer with `GET /graph/{project_id}` and filter support
    - _Requirements: 4.1, 4.4, 7.1, 7.2, 8.1, 8.2, 12.5_

  - [ ]* 9.3 Write property test for graph filtering correctness
    - **Property 6: Graph Filtering Correctness**
    - **Validates: Requirements 4.4**

- [x] 10. Frontend — Submission and Progress
  - [x] 10.1 Initialize Next.js project with layout and design system
    - Create `apps/frontend/` with Next.js 14+ App Router, TypeScript, Tailwind CSS
    - Configure `tailwind.config.ts` with design system tokens (colors, fonts, spacing per design-system steering)
    - Create root `layout.tsx` with dark theme, Google Fonts (Roboto Slab, Inter, JetBrains Mono)
    - Create `globals.css` with CSS custom properties from design system
    - Install shadcn/ui for primitive components
    - _Requirements: 11.1_

  - [x] 10.2 Implement repository submission page
    - Create landing `page.tsx` with hero layout (1fr 420px grid)
    - Create `SubmissionForm` component with URL input, validation, submit action
    - Implement client-side validation for GitHub URL format
    - Handle API responses: success (redirect to analysis page), 400 (show error), 409 (show busy message)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 10.2_

  - [x] 10.3 Implement analysis progress page
    - Create `analysis/[jobId]/page.tsx` as analysis dashboard layout with tabs
    - Create `PipelineProgress` component showing 7 agent stages with status dots (glow animation for active)
    - Create `useAnalysisStatus` hook polling `GET /api/v1/jobs/{jobId}` every 5s
    - Display current agent, completed count, and handle failure indicators
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 13.3_

- [x] 11. Frontend — Dependency Graph
  - [x] 11.1 Implement interactive dependency graph view
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

- [x] 12. Frontend — Chat Interface
  - [x] 12.1 Implement RAG chat interface
    - Create `components/chat/ChatInterface.tsx` with message list and input
    - Create `components/chat/ChatMessage.tsx` for user and assistant messages
    - Create `useSSEChat` hook connecting to `POST /api/v1/chat` with SSE streaming
    - Display streaming tokens in real-time, show sources list on completion
    - Handle "no relevant information" response gracefully
    - Create BFF route in `app/api/` for SSE proxy if needed
    - _Requirements: 5.3, 5.5, 5.6_

- [x] 13. Frontend — Report and Export
  - [x] 13.1 Implement architecture report view
    - Create `components/report/ArchitectureReport.tsx` with formatted sections
    - Display: language/framework info, module structure, dependencies (internal/external), components with responsibilities, metrics
    - Show "Analysis incomplete" indicators for failed sections with explanation
    - Fetch report from `GET /api/v1/projects/{id}/report`
    - _Requirements: 7.1, 7.2, 7.3, 13.3, 13.4_

  - [x] 13.2 Implement Kiro spec export
    - Create `components/export/KiroExport.tsx` with download button
    - Trigger download from `GET /api/v1/projects/{id}/kiro-spec` as markdown file
    - Show partial spec indicator when Modernization_Agent failed
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 14. Integration and Wiring
  - [x] 14.1 Wire all services end-to-end and verify Docker Compose
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

- [x] 15. Final Checkpoint - All services integrated
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. AWS IAM Setup and Infrastructure
  - [x] 16.1 Create IAM user and minimal policy
    - Create `apps/AWS/iam/policy-minimal.json` with the documented IAM policy (Bedrock, S3, Lambda, CloudWatch scoped)
    - Create `apps/AWS/iam/setup.sh` script with all AWS CLI commands documented (create-user, create-policy, attach-user-policy, create-access-key)
    - Each command includes inline comments explaining purpose and justification
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7_

  - [x] 16.2 Create S3 buckets with lifecycle policies
    - Create `apps/AWS/s3/create-buckets.sh` with commands to create `archaeologist-repos-prod` and `archaeologist-reports-prod`
    - Configure lifecycle policy on repos bucket: delete objects after 24 hours
    - Document why each bucket exists and its retention policy
    - _Requirements: 14.3, 14.8_

  - [x] 16.3 Create verification script
    - Create `apps/AWS/iam/verify-permissions.sh` that runs `aws iam simulate-principal-policy` against destructive actions
    - Verify user CANNOT: `s3:DeleteBucket`, `iam:CreateUser`, `ec2:RunInstances`, `rds:DeleteDBInstance`
    - Verify user CAN: `bedrock:InvokeModel`, `s3:PutObject` on allowed buckets, `logs:PutLogEvents`
    - Output clear PASS/FAIL table for each permission check
    - _Requirements: 14.6, 14.9_

  - [x] 16.4 Document Bedrock model access verification
    - Create `apps/AWS/bedrock/verify-models.sh` with command to check model availability
    - Include instructions for enabling models via console if not accessible
    - List exact model IDs required: `anthropic.claude-3-sonnet-20240229-v1:0`, `amazon.titan-embed-text-v2:0`
    - _Requirements: 14.2_

- [x] 17. Production Deployment (First Deploy)
  - [x] 17.1 Deploy database to Amazon RDS
    - Create RDS PostgreSQL 15 instance (db.t3.medium, single-AZ for MVP)
    - Enable pgvector extension via custom parameter group
    - Configure security group: inbound port 5432 from EB instances only
    - Run Flyway migrations against production DB (from Backend container)
    - Update `.data/.env.prod` with RDS endpoint, username, password
    - _Requirements: 11.4_

  - [x] 17.2 Deploy Backend to Elastic Beanstalk
    - Create EB application `archaeologist-backend`
    - Create environment with Docker platform, single instance (t3.small)
    - Upload `docker/backend/Dockerfile` + `apps/backend/` as source bundle
    - Configure all environment variables from `.data/.env.prod`
    - Verify: `GET /actuator/health` returns 200
    - _Requirements: 11.1_

  - [x] 17.3 Deploy Analyzer to Elastic Beanstalk
    - Create EB application `archaeologist-analyzer`
    - Create environment with Docker platform, single instance (t3.medium — needs RAM for tree-sitter)
    - Upload `docker/analyzer/Dockerfile` + `apps/analyzer/` as source bundle
    - Configure environment variables (RDS URL, Bedrock credentials, S3 buckets, webhook URL pointing to Backend EB)
    - Verify: `GET /health` returns 200
    - _Requirements: 11.1_

  - [x] 17.4 Deploy Frontend to AWS Amplify
    - Connect Git repository (GitHub or GitLab) to Amplify
    - Configure build settings: `cd apps/frontend && npm ci && npm run build`
    - Set environment variable `NEXT_PUBLIC_API_URL` to Backend EB URL (e.g., `https://archaeologist-backend.us-east-1.elasticbeanstalk.com`)
    - Verify: pages render, submission form calls Backend correctly
    - _Requirements: 11.1_

  - [x] 17.5 End-to-end production smoke test
    - Submit a small public GitHub repo URL through the deployed Frontend
    - Verify full flow: submission → progress updates → graph renders → chat responds → report displays → Kiro spec downloads
    - Verify S3: repos bucket receives cloned data, reports bucket receives generated artifacts
    - Verify Bedrock: agent pipeline invokes models successfully
    - Document any production-specific issues found
    - _Requirements: 11.5, 12.1, 12.2, 12.3, 12.4_

- [ ] 18. Documentation
  - [ ] 18.1 Create apps/backend/README.md
    - Purpose: API gateway, job orchestration, sequential queue, DB reads for Frontend
    - Tech stack: Java 21, Spring Boot 3.x, Gradle, WebFlux, JPA, Flyway
    - Project structure: Clean Architecture (domain → application → infrastructure)
    - Endpoints: list all REST endpoints with method, path, description
    - Environment variables: table of all env vars consumed with description
    - Local development: `./gradlew bootRun` (or rely on Docker)
    - Testing: `./gradlew test` — JUnit 5
    - Troubleshooting: Flyway migration conflicts, WebClient timeouts, healthcheck failures

  - [ ] 18.2 Create apps/frontend/README.md
    - Purpose: Web UI for repo submission, progress, graph, chat, report, export
    - Tech stack: Next.js 14+ (App Router), React 18, TypeScript, Tailwind CSS, shadcn/ui, React Flow
    - Project structure: feature-based App Router layout
    - Key components: SubmissionForm, DependencyGraph, ChatInterface, ArchitectureReport, KiroExport, PipelineProgress
    - Design system: reference to `.kiro/steering/design-system.md` tokens
    - Environment variables: `NEXT_PUBLIC_API_URL`
    - Local development: `npm run dev` (or rely on Docker)
    - Troubleshooting: SSE connection drops through proxy, React Flow performance with large graphs

  - [ ] 18.3 Create apps/analyzer/README.md
    - Purpose: AI analysis engine — cloning, parsing, graph construction, embeddings, agent pipeline, RAG
    - Tech stack: Python 3.11+, FastAPI, Tree-sitter, asyncpg, pgvector, boto3 (Bedrock)
    - Project structure: Hexagonal (ports & adapters) with modular agents
    - Agent pipeline: diagram showing 7 agents in sequence with data flow
    - Endpoints: POST /analyze, GET /jobs/{id}, POST /query (SSE), GET /graph/{id}
    - Environment variables: table of all env vars
    - Local development: `uvicorn src.main:app --reload` (or rely on Docker)
    - Troubleshooting: Bedrock throttling (429 + backoff), Tree-sitter grammar not found, large repo timeout

  - [ ] 18.4 Create apps/AWS/README.md — Full reproduction guide
    - Title: "AWS Setup — Step by Step Reproduction Guide"
    - Prerequisites: AWS account, AWS CLI installed + configured, Docker
    - Step 1: IAM user creation (commands from `iam/setup.sh` with explanation)
    - Step 2: S3 buckets + lifecycle (commands from `s3/create-buckets.sh`)
    - Step 3: Bedrock model access (console steps + verification command)
    - Step 4: RDS PostgreSQL creation (CLI commands + pgvector setup)
    - Step 5: Elastic Beanstalk environments (Backend + Analyzer)
    - Step 6: Amplify Frontend connection
    - Step 7: Environment variable mapping (`.data/.env.prod` field by field)
    - Step 8: Verification checklist (each service responds, pipeline completes)
    - Troubleshooting: common IAM permission errors, RDS connectivity, Bedrock "model not enabled"

  - [ ] 18.5 Update root README.md
    - Project name + tagline: "Software Archaeologist — Understand any codebase in minutes"
    - Architecture diagram (ASCII from design.md)
    - Feature list: repo analysis, dependency graph, RAG chat, architecture report, Kiro spec export
    - Tech stack table (Frontend / Backend / Analyzer / DB / AI)
    - Quick start: 3 lines — `git clone`, `docker compose build`, `docker compose up` → open http://localhost
    - "Developed with Kiro" section:
      - Specs: structured dev from requirements → design → tasks (2 specs: MVP + v2)
      - Steering: project structure, design system, coding standards as auto-included rules
      - Agents: specialized sub-agents for code review, architecture, frontend
      - Hooks: verification loops, lint on save
      - MCP: AWS documentation + API MCPs for infrastructure automation
      - Iterative design review: caught 17 contradictions/edge cases before writing code
    - Link to deployed app
    - Link to demo video
    - Screenshots (placeholder paths for now)
    - License: MIT

  - [ ] 18.6 Create docs/deployment-runbook.md
    - Current state: manual deployment steps (what was done for first deploy)
    - Future CI/CD design: push to main → build images → push ECR → deploy EB + Amplify
    - Rollback: EB environment swap or version revert
    - Environment differences: table comparing `.env.dev` vs `.env.prod` (which values change)
    - Cost estimate: monthly AWS costs for MVP single-instance setup

- [ ] 19. MVP Final Delivery Checkpoint
  - App deployed and accessible at production URL
  - All 4 app READMEs complete and accurate
  - Root README renders correctly on GitHub/GitLab with architecture diagram
  - AWS guide is reproducible (could clone + follow steps on a new account)
  - Deployment runbook documents current + future process

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
    { "id": 1, "tasks": ["1.2", "10.1", "16.1"] },
    { "id": 2, "tasks": ["2.1", "4.1", "16.2", "16.3", "16.4"] },
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
    { "id": 13, "tasks": ["14.2"] },
    { "id": 14, "tasks": ["17.1"] },
    { "id": 15, "tasks": ["17.2", "17.3", "17.4"] },
    { "id": 16, "tasks": ["17.5", "18.1", "18.2", "18.3", "18.4"] },
    { "id": 17, "tasks": ["18.5", "18.6"] },
    { "id": 18, "tasks": ["19"] }
  ]
}
```
