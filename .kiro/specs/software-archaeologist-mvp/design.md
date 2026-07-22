# Design Document — Software Archaeologist MVP

## Introduction

Este documento describe la arquitectura, componentes, interfaces, modelos de datos y manejo de errores del MVP de Software Archaeologist. El sistema analiza repositorios públicos de GitHub mediante un pipeline de agentes IA especializados y produce documentación, grafos interactivos, chat RAG y artefactos Kiro exportables.

---

## High-Level Architecture

### System Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              NGINX (reverse proxy)                         │
│                              Port 80 / 443                                │
└────────┬──────────────────────────────┬───────────────────────────────────┘
         │ /api/*                       │ /*
         ▼                              ▼
┌─────────────────┐           ┌─────────────────────┐
│    Backend      │           │     Frontend        │
│  Java 21        │           │   Next.js 14+       │
│  Spring Boot 3  │           │   React 18 + TW     │
│  Port 8080      │           │   Port 3000         │
└────────┬────────┘           └─────────────────────┘
         │
         │ REST + Webhooks + SSE
         ▼
┌─────────────────┐           ┌─────────────────────┐
│    Analyzer     │──────────►│   Amazon Bedrock    │
│  Python 3.11+   │           │  Claude Sonnet      │
│  FastAPI         │           │  Titan Embeddings   │
│  Port 8000      │           └─────────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   15+ pgvector  │
│   Port 5432     │
└─────────────────┘
```

### Communication Patterns

| Pattern | Source → Target | Protocol | Use Case |
|---------|----------------|----------|----------|
| Sync REST | Frontend → Backend | HTTP JSON | All user-initiated actions |
| Async Initiation | Backend → Analyzer | POST /analyze → 202 | Start analysis job |
| Polling | Backend → Analyzer | GET /jobs/{id} (5s) | Monitor job progress |
| Webhook | Analyzer → Backend | POST /api/webhooks/* | Notify completion |
| SSE Streaming | Backend → Frontend | text/event-stream | Chat responses, progress |
| Sync Data | Backend → Analyzer | GET /graph/{id} | Retrieve graph data |

### Service Responsibilities

| Service | Responsibility |
|---------|---------------|
| **Frontend** | UI rendering, interactive graph (React Flow), chat interface, report display, Kiro export download |
| **Backend** | API gateway, job orchestration, sequential queue enforcement, data persistence, webhook receiver, SSE relay |
| **Analyzer** | Repository cloning, AST parsing, graph construction, embedding generation, agent pipeline execution, RAG queries |
| **PostgreSQL** | Project model storage, embedding vectors (pgvector), job state, analysis results |
| **Nginx** | Reverse proxy, path-based routing, static asset serving |

---

## Component Architecture

### Backend (Java 21 / Spring Boot 3.x)

**Architecture**: Clean Architecture (domain → application → infrastructure)

```
apps/backend/
├── src/main/java/com/archaeologist/
│   ├── domain/
│   │   ├── model/          # AnalysisJob, Project, AgentResult
│   │   ├── repository/     # Port interfaces
│   │   └── service/        # Domain services
│   ├── application/
│   │   ├── usecase/        # SubmitAnalysis, GetJobStatus, QueryChat
│   │   ├── dto/            # Request/Response DTOs
│   │   └── port/           # Input/Output port interfaces
│   └── infrastructure/
│       ├── web/
│       │   ├── controller/ # REST controllers
│       │   └── webhook/    # Webhook receivers
│       ├── persistence/
│       │   ├── entity/     # JPA entities
│       │   └── repository/ # JPA repository implementations
│       ├── client/         # Analyzer HTTP client (WebClient)
│       └── config/         # Spring configuration
└── src/main/resources/
    ├── application.yml
    └── db/migration/       # Flyway migrations
```

**Key Components:**

| Component | Purpose |
|-----------|---------|
| `AnalysisJobController` | POST /api/v1/jobs, GET /api/v1/jobs/{id} |
| `ChatController` | POST /api/v1/chat (SSE response) |
| `GraphController` | GET /api/v1/projects/{id}/graph |
| `ReportController` | GET /api/v1/projects/{id}/report |
| `ExportController` | GET /api/v1/projects/{id}/kiro-spec |
| `WebhookController` | POST /api/webhooks/analysis-complete |
| `AnalyzerClient` | HTTP client to Analyzer service |
| `JobQueueService` | Single-slot sequential queue enforcement |
| `PollingScheduler` | @Scheduled task polling Analyzer every 5s |

### Frontend (Next.js 14+ / App Router)

**Architecture**: Feature-based with shared components

```
apps/frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout with dark theme
│   │   ├── page.tsx            # Landing / submission page
│   │   ├── analysis/
│   │   │   └── [jobId]/
│   │   │       ├── page.tsx    # Analysis dashboard
│   │   │       ├── graph/      # Dependency graph view
│   │   │       ├── chat/       # RAG chat interface
│   │   │       ├── report/     # Architecture report view
│   │   │       └── export/     # Kiro spec export
│   │   └── api/                # BFF routes (SSE proxy)
│   ├── components/
│   │   ├── ui/                 # shadcn/ui primitives
│   │   ├── graph/              # React Flow graph components
│   │   ├── chat/               # Chat message components
│   │   ├── report/             # Report section renderers
│   │   └── shared/             # Header, Progress, StatusBadge
│   ├── hooks/                  # useAnalysisStatus, useSSE, useGraph
│   ├── lib/                    # API client, utils, constants
│   └── styles/
│       └── globals.css         # Tailwind + CSS custom properties
├── tailwind.config.ts
├── next.config.ts
└── package.json
```

**Key Components:**

| Component | Purpose |
|-----------|---------|
| `SubmissionForm` | URL input + validation + submit action |
| `AnalysisDashboard` | Main layout with tabs (Graph, Chat, Report, Export) |
| `DependencyGraph` | React Flow wrapper with filter controls |
| `GraphFilters` | Module/relationship/depth filter panel |
| `ChatInterface` | Message list + input + SSE streaming display |
| `ArchitectureReport` | Formatted report with incomplete section indicators |
| `KiroExport` | Download button for Kiro spec markdown |
| `PipelineProgress` | Agent progress indicator with stage status |
| `StatusBadge` | Reusable status dot + label (active/complete/failed) |

### Analyzer (Python 3.11+ / FastAPI)

**Architecture**: Hexagonal (ports & adapters) with modular agents

```
apps/analyzer/
├── src/
│   ├── main.py                     # FastAPI app entrypoint
│   ├── api/
│   │   ├── routes/
│   │   │   ├── analyze.py          # POST /analyze
│   │   │   ├── jobs.py             # GET /jobs/{job_id}
│   │   │   ├── query.py            # POST /query (SSE)
│   │   │   └── graph.py            # GET /graph/{project_id}
│   │   ├── schemas.py              # Pydantic request/response models
│   │   └── dependencies.py         # DI container
│   ├── domain/
│   │   ├── models/
│   │   │   ├── project_model.py    # Graph nodes, edges, metadata
│   │   │   ├── analysis_job.py     # Job state machine
│   │   │   └── agent_result.py     # Agent output models
│   │   └── ports/
│   │       ├── repository_port.py  # Abstract repo access
│   │       ├── llm_port.py         # Abstract LLM invocation
│   │       ├── embedding_port.py   # Abstract embedding generation
│   │       └── storage_port.py     # Abstract persistence
│   ├── agents/
│   │   ├── base.py                 # BaseAgent abstract class
│   │   ├── pipeline.py             # AgentPipeline orchestrator
│   │   ├── repository_agent.py     # Clone + parse + graph
│   │   ├── architecture_agent.py   # Pattern detection
│   │   ├── quality_agent.py        # Metrics + smells
│   │   ├── security_agent.py       # Vulnerability scan
│   │   ├── documentation_agent.py  # Doc generation
│   │   ├── modernization_agent.py  # Refactoring plan
│   │   └── kiro_agent.py           # Kiro spec generation
│   ├── parsing/
│   │   ├── tree_sitter_parser.py   # TS/JS/Java AST parsing
│   │   ├── java_parser.py          # JavaParser integration
│   │   ├── chunker.py              # AST-aware code chunking
│   │   └── language_detector.py    # Language/framework detection
│   ├── graph/
│   │   ├── builder.py              # Graph construction from AST
│   │   ├── models.py               # Node/Edge dataclasses
│   │   └── serializer.py           # Graph → JSON/DB format
│   ├── rag/
│   │   ├── embeddings.py           # Titan Embeddings V2 client
│   │   ├── indexer.py              # pgvector indexing
│   │   ├── retriever.py            # Semantic search + re-ranking
│   │   └── generator.py            # Claude Sonnet response gen
│   ├── adapters/
│   │   ├── bedrock_adapter.py      # AWS Bedrock client
│   │   ├── postgres_adapter.py     # asyncpg + pgvector
│   │   ├── git_adapter.py          # Git clone operations
│   │   └── webhook_adapter.py      # HTTP webhook sender
│   └── config.py                   # Settings (pydantic-settings)
├── tests/
├── requirements.txt
└── pyproject.toml
```

---

## Data Models

### PostgreSQL Schema

```sql
-- Analysis Jobs
CREATE TABLE analysis_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_url        VARCHAR(500) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- pending | cloning | analyzing | completed | failed
    current_agent   VARCHAR(50),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at    TIMESTAMP WITH TIME ZONE,
    error_message   TEXT,
    CONSTRAINT valid_status CHECK (
        status IN ('pending', 'cloning', 'analyzing', 'completed', 'failed')
    )
);

-- Projects (one per successful analysis)
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES analysis_jobs(id),
    repo_url        VARCHAR(500) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    language        VARCHAR(50),     -- java | typescript | javascript | unknown
    framework       VARCHAR(50),     -- spring-boot | react | next | etc | unknown
    total_files     INTEGER DEFAULT 0,
    total_loc       INTEGER DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Graph Nodes
CREATE TABLE graph_nodes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    node_type       VARCHAR(20) NOT NULL,
        -- file | class | function | module | package
    name            VARCHAR(500) NOT NULL,
    qualified_name  VARCHAR(1000),
    file_path       VARCHAR(1000),
    loc             INTEGER DEFAULT 0,
    complexity      INTEGER DEFAULT 1,
    last_modified   TIMESTAMP WITH TIME ZONE,
    metadata        JSONB DEFAULT '{}',
    CONSTRAINT valid_node_type CHECK (
        node_type IN ('file', 'class', 'function', 'module', 'package')
    )
);

CREATE INDEX idx_nodes_project ON graph_nodes(project_id);
CREATE INDEX idx_nodes_type ON graph_nodes(project_id, node_type);

-- Graph Edges
CREATE TABLE graph_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_node_id  UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id  UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    edge_type       VARCHAR(20) NOT NULL,
        -- import | inheritance | usage | composition
    metadata        JSONB DEFAULT '{}',
    CONSTRAINT valid_edge_type CHECK (
        edge_type IN ('import', 'inheritance', 'usage', 'composition')
    )
);

CREATE INDEX idx_edges_project ON graph_edges(project_id);
CREATE INDEX idx_edges_source ON graph_edges(source_node_id);
CREATE INDEX idx_edges_target ON graph_edges(target_node_id);

-- Agent Results
CREATE TABLE agent_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    agent_name      VARCHAR(50) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- pending | running | completed | failed | skipped
    output          JSONB,
    error_message   TEXT,
    started_at      TIMESTAMP WITH TIME ZONE,
    completed_at    TIMESTAMP WITH TIME ZONE,
    execution_order INTEGER NOT NULL
);

CREATE INDEX idx_agent_results_job ON agent_results(job_id);

-- Embeddings (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE code_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    chunk_text      TEXT NOT NULL,
    chunk_type      VARCHAR(20) NOT NULL,  -- function | method | class | file
    file_path       VARCHAR(1000),
    module_name     VARCHAR(200),
    function_name   VARCHAR(200),
    embedding       vector(1024),  -- Titan Embeddings V2 dimension
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_embeddings_project ON code_embeddings(project_id);
CREATE INDEX idx_embeddings_vector ON code_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Architecture Reports
CREATE TABLE architecture_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    content         JSONB NOT NULL,  -- Structured report sections
    agents_status   JSONB NOT NULL,  -- {agent_name: "completed"|"failed"|"skipped"}
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Kiro Specs
CREATE TABLE kiro_specs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    markdown_content TEXT NOT NULL,
    is_partial      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Domain Models (Python - Analyzer)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime


class NodeType(str, Enum):
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    MODULE = "module"
    PACKAGE = "package"


class EdgeType(str, Enum):
    IMPORT = "import"
    INHERITANCE = "inheritance"
    USAGE = "usage"
    COMPOSITION = "composition"


class JobStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class GraphNode:
    id: UUID = field(default_factory=uuid4)
    node_type: NodeType = NodeType.FILE
    name: str = ""
    qualified_name: Optional[str] = None
    file_path: Optional[str] = None
    loc: int = 0
    complexity: int = 1
    last_modified: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    id: UUID = field(default_factory=uuid4)
    source_node_id: UUID = field(default_factory=uuid4)
    target_node_id: UUID = field(default_factory=uuid4)
    edge_type: EdgeType = EdgeType.IMPORT
    metadata: dict = field(default_factory=dict)


@dataclass
class ProjectModel:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    repo_url: str = ""
    language: Optional[str] = None
    framework: Optional[str] = None
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    total_files: int = 0
    total_loc: int = 0


@dataclass
class AgentResult:
    agent_name: str = ""
    status: AgentStatus = AgentStatus.PENDING
    output: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_order: int = 0


@dataclass
class AnalysisJob:
    id: UUID = field(default_factory=uuid4)
    repo_url: str = ""
    status: JobStatus = JobStatus.PENDING
    current_agent: Optional[str] = None
    agent_results: list[AgentResult] = field(default_factory=list)
    project: Optional[ProjectModel] = None
    created_at: datetime = field(default_factory=datetime.now)
```

### Domain Models (Java - Backend)

```java
// AnalysisJob.java
public record AnalysisJob(
    UUID id,
    String repoUrl,
    JobStatus status,
    String currentAgent,
    LocalDateTime createdAt,
    LocalDateTime updatedAt,
    LocalDateTime completedAt,
    String errorMessage
) {}

public enum JobStatus {
    PENDING, CLONING, ANALYZING, COMPLETED, FAILED
}

// Project.java
public record Project(
    UUID id,
    UUID jobId,
    String repoUrl,
    String name,
    String language,
    String framework,
    int totalFiles,
    int totalLoc,
    LocalDateTime createdAt
) {}
```

---

## Low-Level Design: API Contracts

### Backend REST API (Port 8080)

#### Analysis Jobs

```
POST /api/v1/jobs
Content-Type: application/json

Request:
{
  "repoUrl": "https://github.com/owner/repo"
}

Response 202 Accepted:
{
  "jobId": "uuid",
  "status": "pending",
  "message": "Analysis queued"
}

Response 409 Conflict (system busy):
{
  "error": "SYSTEM_BUSY",
  "message": "An analysis is currently in progress. Please try again later."
}

Response 400 Bad Request:
{
  "error": "INVALID_URL",
  "message": "The provided URL is not a valid public GitHub repository."
}
```

```
GET /api/v1/jobs/{jobId}

Response 200:
{
  "jobId": "uuid",
  "status": "analyzing",
  "currentAgent": "architecture_agent",
  "progress": {
    "totalAgents": 7,
    "completedAgents": 2,
    "agents": [
      {"name": "repository_agent", "status": "completed"},
      {"name": "architecture_agent", "status": "running"},
      {"name": "quality_agent", "status": "pending"},
      {"name": "security_agent", "status": "pending"},
      {"name": "documentation_agent", "status": "pending"},
      {"name": "modernization_agent", "status": "pending"},
      {"name": "kiro_agent", "status": "pending"}
    ]
  },
  "createdAt": "2024-01-15T10:30:00Z"
}
```

#### Chat (SSE)

```
POST /api/v1/chat
Content-Type: application/json
Accept: text/event-stream

Request:
{
  "projectId": "uuid",
  "question": "How does authentication work?"
}

Response (SSE stream):
event: token
data: {"content": "The authentication"}

event: token
data: {"content": " module uses JWT"}

event: sources
data: {"files": ["src/auth/JwtFilter.java", "src/auth/AuthService.java"]}

event: done
data: {}
```

#### Graph

```
GET /api/v1/projects/{projectId}/graph?module=auth&depth=2&edgeType=import

Response 200:
{
  "nodes": [
    {
      "id": "uuid",
      "type": "module",
      "name": "auth",
      "qualifiedName": "com.example.auth",
      "loc": 1250,
      "complexity": 15,
      "isExternal": false,
      "metadata": {}
    }
  ],
  "edges": [
    {
      "id": "uuid",
      "source": "uuid-source",
      "target": "uuid-target",
      "type": "import",
      "metadata": {}
    }
  ]
}
```

#### Architecture Report

```
GET /api/v1/projects/{projectId}/report

Response 200:
{
  "projectName": "example-app",
  "language": {"name": "java", "version": "17"},
  "framework": {"name": "spring-boot", "version": "3.2.0"},
  "modules": [
    {"name": "auth", "responsibility": "Authentication and authorization", "loc": 1250}
  ],
  "dependencies": {
    "internal": [{"from": "auth", "to": "user", "type": "import"}],
    "external": [{"name": "spring-security", "version": "6.2.0"}]
  },
  "components": [
    {"name": "AuthService", "module": "auth", "responsibility": "JWT token management"}
  ],
  "metrics": {
    "totalLoc": 15000,
    "moduleCount": 12,
    "maxDependencyDepth": 4
  },
  "agentsStatus": {
    "repository_agent": "completed",
    "architecture_agent": "completed",
    "quality_agent": "completed",
    "security_agent": "failed",
    "documentation_agent": "completed",
    "modernization_agent": "skipped",
    "kiro_agent": "skipped"
  },
  "incompleteSections": ["security"]
}
```

#### Kiro Spec Export

```
GET /api/v1/projects/{projectId}/kiro-spec

Response 200:
Content-Type: text/markdown
Content-Disposition: attachment; filename="modernization-spec.md"

(Markdown content of the Kiro Spec)
```

#### Webhook Receiver

```
POST /api/webhooks/analysis-complete
Content-Type: application/json

Request (from Analyzer):
{
  "jobId": "uuid",
  "status": "completed",
  "projectId": "uuid",
  "agentsStatus": {
    "repository_agent": "completed",
    "architecture_agent": "completed",
    "quality_agent": "failed",
    "security_agent": "skipped",
    "documentation_agent": "completed",
    "modernization_agent": "completed",
    "kiro_agent": "completed"
  }
}

Response 200:
{"received": true}
```

### Analyzer API (Port 8000)

#### Start Analysis

```
POST /analyze
Content-Type: application/json

Request:
{
  "repoUrl": "https://github.com/owner/repo",
  "jobId": "uuid",
  "webhookUrl": "http://backend:8080/api/webhooks/analysis-complete"
}

Response 202 Accepted:
{
  "jobId": "uuid",
  "status": "pending",
  "estimatedDuration": "5-15 minutes"
}

Response 400 Bad Request:
{
  "error": "REPO_TOO_LARGE",
  "message": "Repository exceeds 500 MB limit.",
  "details": {"sizeBytes": 600000000, "maxBytes": 524288000}
}
```

#### Job Status

```
GET /jobs/{jobId}

Response 200:
{
  "jobId": "uuid",
  "status": "analyzing",
  "currentAgent": "quality_agent",
  "progress": {
    "completedAgents": ["repository_agent", "architecture_agent"],
    "currentAgent": "quality_agent",
    "pendingAgents": ["security_agent", "documentation_agent", "modernization_agent", "kiro_agent"],
    "failedAgents": []
  }
}
```

#### RAG Query (SSE)

```
POST /query
Content-Type: application/json
Accept: text/event-stream

Request:
{
  "projectId": "uuid",
  "question": "How does the payment flow work?",
  "maxChunks": 10
}

Response (SSE stream):
event: context
data: {"chunks": [{"file": "src/payment/PaymentService.java", "score": 0.92}]}

event: token
data: {"content": "The payment flow"}

event: token
data: {"content": " starts in PaymentController"}

event: done
data: {"totalTokens": 450}

-- When no relevant context found:
event: no_context
data: {"message": "No relevant information found for this question."}
```

#### Graph Data

```
GET /graph/{projectId}?module=auth&edgeType=import&depth=2

Response 200:
{
  "projectId": "uuid",
  "nodes": [...],
  "edges": [...],
  "stats": {
    "totalNodes": 45,
    "totalEdges": 78,
    "filteredNodes": 12,
    "filteredEdges": 15
  }
}
```

---

## Low-Level Design: Key Interfaces

### Agent Pipeline (Python)

```python
from abc import ABC, abstractmethod
from typing import Optional


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique agent identifier."""
        ...

    @property
    @abstractmethod
    def execution_order(self) -> int:
        """Position in pipeline (1-7)."""
        ...

    @abstractmethod
    async def execute(self, context: PipelineContext) -> AgentOutput:
        """
        Execute the agent's analysis task.

        Args:
            context: Accumulated context from previous agents.

        Returns:
            AgentOutput with structured results.

        Raises:
            AgentExecutionError: If agent fails non-recoverably.
        """
        ...

    def can_execute(self, context: PipelineContext) -> bool:
        """Check if minimum required context exists to run."""
        return context.project_model is not None


@dataclass
class PipelineContext:
    """Accumulated context passed through the agent chain."""
    job_id: UUID
    repo_url: str
    repo_path: Optional[str] = None
    project_model: Optional[ProjectModel] = None
    architecture_report: Optional[dict] = None
    quality_report: Optional[dict] = None
    security_report: Optional[dict] = None
    documentation_bundle: Optional[dict] = None
    modernization_plan: Optional[dict] = None
    kiro_spec: Optional[str] = None
    agent_results: list[AgentResult] = field(default_factory=list)


@dataclass
class AgentOutput:
    """Structured output from an agent execution."""
    agent_name: str
    status: AgentStatus
    data: dict
    context_updates: dict  # Keys to update in PipelineContext
    error: Optional[str] = None
```

### Pipeline Orchestrator

```python
class AgentPipeline:
    """Orchestrates sequential execution of agents with graceful degradation."""

    def __init__(self, agents: list[BaseAgent], webhook_adapter: WebhookAdapter):
        self._agents = sorted(agents, key=lambda a: a.execution_order)
        self._webhook = webhook_adapter

    async def execute(self, job_id: UUID, repo_url: str) -> PipelineContext:
        """
        Execute the full agent pipeline.

        - Agents run sequentially in order.
        - Each agent receives accumulated context from all previous agents.
        - If Repository_Agent fails, the entire pipeline terminates.
        - If any subsequent agent fails, it is skipped and pipeline continues.
        - On completion (full or partial), sends webhook notification.
        """
        context = PipelineContext(job_id=job_id, repo_url=repo_url)

        for agent in self._agents:
            try:
                if not agent.can_execute(context):
                    self._mark_skipped(context, agent)
                    continue

                output = await agent.execute(context)
                self._apply_output(context, output)

            except AgentExecutionError as e:
                if agent.name == "repository_agent":
                    # Critical failure — terminate pipeline
                    raise PipelineTerminatedError(
                        f"Repository agent failed: {e.message}"
                    )
                # Non-critical — skip and continue
                self._mark_failed(context, agent, str(e))

        await self._webhook.notify_completion(context)
        return context
```

### Language Detection

```python
class LanguageDetector:
    """Detects primary language and framework from repository file structure."""

    LANGUAGE_MARKERS: dict[str, list[str]] = {
        "java": ["pom.xml", "build.gradle", "build.gradle.kts", "*.java"],
        "typescript": ["tsconfig.json", "*.ts", "*.tsx"],
        "javascript": ["*.js", "*.jsx", "*.mjs"],
    }

    FRAMEWORK_MARKERS: dict[str, dict[str, list[str]]] = {
        "java": {
            "spring-boot": ["spring-boot-starter"],
            "quarkus": ["quarkus-"],
            "jakarta-ee": ["jakarta."],
        },
        "typescript": {
            "next": ["next"],
            "react": ["react", "react-dom"],
            "angular": ["@angular/core"],
            "vue": ["vue"],
            "nestjs": ["@nestjs/core"],
        },
        "javascript": {
            "express": ["express"],
            "react": ["react", "react-dom"],
            "next": ["next"],
            "angular": ["@angular/core"],
            "vue": ["vue"],
            "nestjs": ["@nestjs/core"],
        },
    }

    def detect(self, repo_path: str) -> tuple[str, str]:
        """
        Returns (language, framework) tuple.
        Returns ("unknown", "unknown") if detection fails.
        """
        ...
```

### AST-Aware Chunker

```python
@dataclass
class CodeChunk:
    """A chunk of code with context for embedding."""
    text: str
    chunk_type: str          # function | method | class | file
    file_path: str
    module_name: str
    function_name: Optional[str] = None
    start_line: int = 0
    end_line: int = 0


class ASTChunker:
    """Splits source code into semantic chunks using AST boundaries."""

    MAX_CHUNK_SIZE: int = 2000  # characters

    def chunk_file(self, file_path: str, ast_tree) -> list[CodeChunk]:
        """
        Split a file into chunks at function/method boundaries.

        Each chunk includes:
        - The function/method body
        - File path context header
        - Module/class context

        If a function exceeds MAX_CHUNK_SIZE, it is split at logical
        boundaries (blocks, statements) preserving context headers.
        """
        ...
```

### Sequential Job Queue (Java)

```java
@Service
public class JobQueueService {

    private final AtomicReference<UUID> activeJobId = new AtomicReference<>(null);
    private final AnalysisJobRepository jobRepository;
    private final AnalyzerClient analyzerClient;

    /**
     * Attempts to acquire the processing slot for a new job.
     *
     * @return true if slot was acquired, false if system is busy
     */
    public boolean tryAcquire(UUID jobId) {
        return activeJobId.compareAndSet(null, jobId);
    }

    /**
     * Releases the processing slot after job completion or failure.
     */
    public void release(UUID jobId) {
        activeJobId.compareAndSet(jobId, null);
    }

    /**
     * Checks if the system is currently processing a job.
     */
    public boolean isBusy() {
        return activeJobId.get() != null;
    }

    /**
     * Returns the ID of the currently active job, if any.
     */
    public Optional<UUID> getActiveJobId() {
        return Optional.ofNullable(activeJobId.get());
    }
}
```

### URL Validation

```java
@Component
public class GitHubUrlValidator {

    private static final Pattern GITHUB_URL_PATTERN =
        Pattern.compile("^https://github\\.com/[\\w.-]+/[\\w.-]+/?$");

    /**
     * Validates that the URL is a valid public GitHub repository.
     *
     * Checks:
     * 1. URL matches GitHub repository pattern
     * 2. Repository exists and is publicly accessible (HEAD request)
     * 3. Repository does not exceed size limits
     *
     * @throws InvalidRepositoryException with descriptive error
     */
    public ValidationResult validate(String repoUrl) { ... }
}

public record ValidationResult(
    boolean valid,
    String error,    // null if valid
    long repoSizeBytes,
    int fileCount
) {}
```

### Graph Builder

```python
class GraphBuilder:
    """Constructs a ProjectModel graph from parsed AST data."""

    def build(
        self,
        repo_path: str,
        parsed_files: list[ParsedFile],
    ) -> ProjectModel:
        """
        Build the complete project graph.

        1. Create file nodes for all source files
        2. Extract class/function/module nodes from AST
        3. Detect package/module groupings from directory structure
        4. Identify edges from import statements, class hierarchies,
           function calls, and composition patterns
        5. Compute metadata (LOC, complexity) per node
        """
        ...

    def _detect_imports(self, ast_tree, file_path: str) -> list[GraphEdge]:
        """Extract import relationships from AST."""
        ...

    def _detect_inheritance(self, ast_tree) -> list[GraphEdge]:
        """Extract class hierarchy relationships."""
        ...

    def _compute_complexity(self, ast_node) -> int:
        """Calculate cyclomatic complexity for a function/method node."""
        ...
```

### RAG Retriever

```python
class RAGRetriever:
    """Semantic search with architectural re-ranking."""

    RELEVANCE_THRESHOLD: float = 0.65
    MAX_CHUNKS: int = 10

    async def retrieve(
        self,
        project_id: UUID,
        question: str,
        max_chunks: int = MAX_CHUNKS,
    ) -> RetrievalResult:
        """
        1. Generate embedding for question via Titan Embeddings V2
        2. Query pgvector for top-K similar chunks (K = max_chunks * 2)
        3. Re-rank by architectural relevance (module importance, centrality)
        4. Filter by RELEVANCE_THRESHOLD
        5. Return top max_chunks results

        Returns RetrievalResult with is_empty=True if all scores
        are below threshold (triggers "no relevant info" response).
        """
        ...


@dataclass
class RetrievalResult:
    chunks: list[ScoredChunk]
    is_empty: bool  # True when no chunks pass threshold
    query_embedding: list[float]


@dataclass
class ScoredChunk:
    chunk: CodeChunk
    similarity_score: float
    relevance_score: float  # After re-ranking
```

---

## Error Handling Strategy

### Pipeline Error Classification

| Error Type | Scope | Behavior |
|-----------|-------|----------|
| `RepositoryCloneError` | Repository_Agent | Terminates entire pipeline |
| `RepositoryTooLargeError` | Pre-pipeline validation | Rejects job immediately |
| `AgentExecutionError` | Any agent (post-Repository) | Skip agent, continue pipeline |
| `BedrockThrottleError` | Any agent using LLM | Retry 3x with exponential backoff, then fail agent |
| `ParseError` | Repository_Agent | Log warning, skip unparseable file |
| `WebhookDeliveryError` | Pipeline completion | Retry 3x, log failure (job still completes) |

### Backend Error Responses

```java
// Standard error response format
public record ErrorResponse(
    String error,       // Machine-readable error code
    String message,     // Human-readable description
    Map<String, Object> details  // Optional additional context
) {}

// Error codes
public enum ErrorCode {
    INVALID_URL("INVALID_URL", "The provided URL is not a valid GitHub repository"),
    REPO_NOT_ACCESSIBLE("REPO_NOT_ACCESSIBLE", "Repository is private or does not exist"),
    REPO_TOO_LARGE("REPO_TOO_LARGE", "Repository exceeds size limits"),
    SYSTEM_BUSY("SYSTEM_BUSY", "System is processing another analysis"),
    JOB_NOT_FOUND("JOB_NOT_FOUND", "Analysis job not found"),
    PROJECT_NOT_FOUND("PROJECT_NOT_FOUND", "Project not found"),
    ANALYSIS_FAILED("ANALYSIS_FAILED", "Analysis pipeline terminated due to critical error"),
    INTERNAL_ERROR("INTERNAL_ERROR", "An unexpected error occurred");
}
```

---

## Infrastructure

### Docker Compose Services

```yaml
# docker-compose.yml (at project root)
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - backend
      - frontend

  frontend:
    build:
      context: .
      dockerfile: docker/frontend/Dockerfile
    env_file: ${COMPOSE_ENV_FILE:-.data/.env}
    expose:
      - "3000"

  backend:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
    env_file: ${COMPOSE_ENV_FILE:-.data/.env}
    expose:
      - "8080"
    depends_on:
      db:
        condition: service_healthy

  analyzer:
    build:
      context: .
      dockerfile: docker/analyzer/Dockerfile
    env_file: ${COMPOSE_ENV_FILE:-.data/.env}
    expose:
      - "8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - analyzer_repos:/tmp/repos  # Cloned repos (ephemeral)

  db:
    image: pgvector/pgvector:pg15
    env_file: ${COMPOSE_ENV_FILE:-.data/.env}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
  analyzer_repos:
```

### Nginx Configuration

```nginx
# nginx/default.conf
upstream backend {
    server backend:8080;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;

    # API routes → Backend
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;          # Required for SSE
        proxy_read_timeout 300s;      # Long analysis polling
    }

    # Everything else → Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Environment Variables

```env
# .data/.env (template)

# PostgreSQL
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=archaeologist
POSTGRES_USER=archaeologist
POSTGRES_PASSWORD=dev_password_change_me

# Backend (Spring Boot)
SPRING_DATASOURCE_URL=jdbc:postgresql://db:5432/archaeologist
SPRING_DATASOURCE_USERNAME=archaeologist
SPRING_DATASOURCE_PASSWORD=dev_password_change_me
ANALYZER_BASE_URL=http://analyzer:8000
SERVER_PORT=8080

# Analyzer (FastAPI)
DATABASE_URL=postgresql+asyncpg://archaeologist:dev_password_change_me@db:5432/archaeologist
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
WEBHOOK_SECRET=shared_webhook_secret
CLONE_TEMP_DIR=/tmp/repos
MAX_REPO_SIZE_MB=500
MAX_FILE_COUNT=50000

# Frontend (Next.js)
NEXT_PUBLIC_API_URL=/api
```

---

## AWS Deployment Architecture (Production)

| Component | AWS Service | Configuration |
|-----------|------------|---------------|
| Frontend | AWS Amplify | Next.js SSR, auto-deploy from Git |
| Backend | Elastic Beanstalk | Docker platform, single instance (MVP) |
| Analyzer | Elastic Beanstalk | Docker platform, single instance (MVP) |
| Database | Amazon RDS | PostgreSQL 15 + pgvector, db.t3.medium |
| Repo Storage | Amazon S3 | Temporary cloned repos (lifecycle: 24h deletion) |
| Reports | Amazon S3 | Generated reports and specs |
| AI Models | Amazon Bedrock | Claude Sonnet + Titan Embeddings V2 |
| Post-processing | AWS Lambda | PDF generation, notifications |

---

## Sequence Diagrams

### Analysis Flow

```
Frontend          Backend              Analyzer              Bedrock
   │                 │                     │                    │
   │ POST /api/v1/jobs                     │                    │
   │─────────────────►                     │                    │
   │                 │ validate URL         │                    │
   │                 │ tryAcquire slot      │                    │
   │                 │                     │                    │
   │  202 {jobId}    │                     │                    │
   │◄─────────────────                     │                    │
   │                 │                     │                    │
   │                 │ POST /analyze        │                    │
   │                 │─────────────────────►                    │
   │                 │     202 Accepted     │                    │
   │                 │◄─────────────────────                    │
   │                 │                     │                    │
   │                 │                     │── clone repo ──────│
   │                 │                     │── parse AST ───────│
   │                 │                     │── build graph ─────│
   │                 │                     │                    │
   │                 │                     │ generate embeddings │
   │                 │                     │───────────────────►│
   │                 │                     │◄───────────────────│
   │                 │                     │                    │
   │ GET /api/v1/jobs/{id} (polling)       │                    │
   │─────────────────►                     │                    │
   │                 │ GET /jobs/{id}       │                    │
   │                 │─────────────────────►                    │
   │                 │◄─────────────────────                    │
   │ 200 {progress}  │                     │                    │
   │◄─────────────────                     │                    │
   │                 │                     │                    │
   │                 │                     │── Agent Pipeline ──│
   │                 │                     │   (sequential)     │
   │                 │                     │──────────────────► │
   │                 │                     │◄──────────────────│
   │                 │                     │                    │
   │                 │ POST /api/webhooks/  │                    │
   │                 │  analysis-complete   │                    │
   │                 │◄─────────────────────                    │
   │                 │ release slot         │                    │
   │                 │ persist results      │                    │
   │                 │                     │                    │
   │ GET /api/v1/jobs/{id} → completed     │                    │
   │◄─────────────────►                    │                    │
```

### Chat Flow (RAG)

```
Frontend          Backend              Analyzer              Bedrock
   │                 │                     │                    │
   │ POST /api/v1/chat (SSE)              │                    │
   │─────────────────►                     │                    │
   │                 │ POST /query (SSE)   │                    │
   │                 │─────────────────────►                    │
   │                 │                     │ embed question     │
   │                 │                     │───────────────────►│
   │                 │                     │◄───────────────────│
   │                 │                     │                    │
   │                 │                     │ pgvector search    │
   │                 │                     │ re-rank chunks     │
   │                 │                     │                    │
   │                 │                     │ generate response  │
   │                 │                     │───────────────────►│
   │                 │                     │                    │
   │  SSE: token     │  SSE: token         │◄─ stream tokens ──│
   │◄─────────────────◄─────────────────────                    │
   │  SSE: token     │  SSE: token         │                    │
   │◄─────────────────◄─────────────────────                    │
   │  SSE: sources   │  SSE: sources       │                    │
   │◄─────────────────◄─────────────────────                    │
   │  SSE: done      │  SSE: done          │                    │
   │◄─────────────────◄─────────────────────                    │
```

---

## Frontend State Management

### Key Hooks

```typescript
// hooks/useAnalysisStatus.ts
interface AnalysisStatus {
  jobId: string;
  status: JobStatus;
  currentAgent: string | null;
  progress: AgentProgress[];
}

function useAnalysisStatus(jobId: string): {
  data: AnalysisStatus | null;
  isLoading: boolean;
  error: Error | null;
}

// hooks/useSSEChat.ts
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  isStreaming: boolean;
}

function useSSEChat(projectId: string): {
  messages: ChatMessage[];
  sendMessage: (question: string) => void;
  isStreaming: boolean;
}

// hooks/useGraphData.ts
interface GraphFilter {
  module?: string;
  edgeType?: EdgeType;
  depth?: number;
}

function useGraphData(projectId: string, filters: GraphFilter): {
  nodes: GraphNode[];
  edges: GraphEdge[];
  isLoading: boolean;
}
```

### React Flow Graph Configuration

```typescript
// components/graph/DependencyGraph.tsx
interface DependencyGraphProps {
  projectId: string;
}

// Node types for React Flow
const nodeTypes = {
  module: ModuleNode,      // Grouped container node
  package: PackageNode,    // Package grouping
  file: FileNode,          // Individual file
  class: ClassNode,        // Class node
  external: ExternalNode,  // External dependency (distinct style)
};

// Edge types
const edgeTypes = {
  import: ImportEdge,       // Default arrow
  inheritance: InheritanceEdge,  // Hollow arrow
  usage: UsageEdge,         // Dashed line
  composition: CompositionEdge,  // Diamond arrow
};
```

---

## Kiro Spec Output Format

```markdown
---
name: "Modernización de {project-name}"
version: 1.0
---

# Requirements

- REQ-1: {Requirement derived from analysis}
- REQ-2: {Requirement derived from analysis}

# Design

## Current Architecture
{Generated description of detected architecture}

### Language & Framework
- Language: {detected_language} {version}
- Framework: {detected_framework} {version}

### Module Structure
{Module descriptions and responsibilities}

### Dependencies
{Internal and external dependency summary}

## Proposed Architecture
{Modernization recommendations from Modernization_Agent}

### Priority Actions
{Prioritized refactoring recommendations}

# Tasks

- [ ] TASK-1: {Concrete task from modernization plan}
- [ ] TASK-2: {Concrete task from modernization plan}
- [ ] TASK-3: {Concrete task from modernization plan}
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: URL Validation Rejects Invalid Inputs

*For any* string that does not match the pattern `https://github.com/{owner}/{repo}`, or represents a private/inaccessible repository, the Backend SHALL return a descriptive error response and SHALL NOT create an Analysis_Job.

**Validates: Requirements 1.3**


### Property 2: Sequential Processing Invariant

*For any* sequence of job submission requests, at most one Analysis_Job SHALL be in active state (cloning or analyzing) at any point in time. When a job completes or fails, the processing slot SHALL be released, allowing the next submission to be accepted.

**Validates: Requirements 1.4, 10.1, 10.2, 10.3**


### Property 3: Language and Framework Detection Correctness

*For any* repository file tree containing known language markers (pom.xml/build.gradle for Java, tsconfig.json for TypeScript, package.json for JavaScript) and known framework dependency markers, the LanguageDetector SHALL return the correct (language, framework) tuple matching the dominant markers present.

**Validates: Requirements 2.1, 2.2, 2.3**


### Property 4: AST Parsing Produces Valid Output

*For any* syntactically valid source file in Java, TypeScript, or JavaScript, the Tree-sitter parser SHALL produce a non-null AST tree without parse errors for the supported language constructs.

**Validates: Requirements 3.1**


### Property 5: Project Model Node Completeness

*For any* set of parsed source files, the constructed Project_Model SHALL contain a node for each file, and each node SHALL have: a valid NodeType, LOC >= 0, cyclomatic complexity >= 1, and edges correctly typed as one of import, inheritance, usage, or composition.

**Validates: Requirements 3.2, 3.3, 3.4**


### Property 6: Graph Filtering Correctness

*For any* filter configuration (module name, relationship type, depth level) applied to a Project_Model graph, the resulting filtered set SHALL contain only nodes and edges that satisfy ALL active filter criteria simultaneously — no node outside the specified module appears, no edge of a non-matching type appears, and no node beyond the specified depth appears.

**Validates: Requirements 4.4**


### Property 7: AST-Aware Chunking Preserves Function Boundaries

*For any* source file containing N distinct functions or methods, the ASTChunker SHALL produce exactly N chunks (one per function/method), and each chunk SHALL include the complete function body plus a context header identifying the file path and containing module/class.

**Validates: Requirements 5.2**


### Property 8: RAG No-Context Threshold

*For any* user query where all retrieved chunks have similarity scores below the RELEVANCE_THRESHOLD (0.65), the RAG_System SHALL return a "no relevant information found" response instead of generating an unsupported answer.

**Validates: Requirements 5.6**


### Property 9: Pipeline Sequential Data Flow with Graceful Degradation

*For any* pipeline execution, agents SHALL execute in strict sequential order (1-7), each agent's input context SHALL contain the accumulated outputs of all previously successful agents, and if any agent after Repository_Agent fails, the pipeline SHALL continue with remaining agents using available data.

**Validates: Requirements 6.1, 6.2, 6.3**


### Property 10: Architecture Report Completeness with Degradation

*For any* completed Analysis_Job (full or partial), the Architecture_Report SHALL contain all sections whose corresponding agents completed successfully, SHALL mark sections as "Analysis incomplete" for failed agents, and SHALL include metadata listing the completion status of every agent in the pipeline.

**Validates: Requirements 7.1, 7.3, 13.4**


### Property 11: Kiro Spec Structural Completeness

*For any* valid ModernizationPlan input, the generated Kiro_Spec SHALL contain three top-level sections (Requirements, Design with current + proposed architecture, and Tasks as checkbox list) in valid markdown format conforming to Kiro's native spec structure.

**Validates: Requirements 8.1, 8.3**


### Property 12: External Dependency Visual Distinction

*For any* node in the Dependency_Graph that represents an external dependency, the rendered node SHALL have a visually distinct style (different color, border, or icon) that differentiates it from internal project nodes.

**Validates: Requirements 4.3**
