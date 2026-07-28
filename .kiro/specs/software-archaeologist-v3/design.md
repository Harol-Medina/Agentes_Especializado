# Design Document — Software Archaeologist v3 (Production Hardening)

## Introduction

Este documento describe el diseño técnico de las 13 mejoras implementadas en la iteración V3. Se asume que el MVP (v1) y la visión completa (v2) están implementados. V3 se centra en tres ejes: **chat inteligente con RAG**, **resiliencia del pipeline**, y **UX interactiva de producción**.

---

## RAG Chat con Embedding Indexing Automático

### Arquitectura

```
Pipeline completa → on_pipeline_complete callback
                         │
                         ▼
              ┌─────────────────────┐
              │  Embedding Indexer   │
              │  (chunker + Titan)   │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   PostgreSQL         │
              │   code_embeddings    │
              │   (vector(1024))     │
              └──────────┬──────────┘
                         │
        Chat query ──────┤
                         ▼
              ┌─────────────────────┐
              │  Similarity Search   │
              │  cosine_distance     │
              │  threshold=0.05      │
              │  top_k=5             │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   Claude Sonnet      │
              │   (context + query)  │
              └─────────────────────┘
```

### Chunking Strategy

```python
# src/parsing/chunker.py
class CodeChunker:
    """Splits source files into overlapping chunks for embedding."""

    CHUNK_SIZE = 500       # tokens (~2000 chars)
    CHUNK_OVERLAP = 50     # tokens overlap between chunks

    def chunk_file(self, file_path: str, content: str) -> list[CodeChunk]:
        """
        1. Split by logical boundaries (functions, classes) when possible
        2. Fall back to line-based splitting for non-parseable files
        3. Each chunk includes: content, file_path, start_line, end_line
        4. Overlap ensures no context is lost at boundaries
        """
        ...
```

### Database Schema

```sql
CREATE TABLE code_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    file_path TEXT NOT NULL,
    chunk_content TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    embedding vector(1024) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_embeddings_project ON code_embeddings(project_id);
CREATE INDEX idx_embeddings_vector ON code_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Query Flow

```python
# src/api/routes/query.py
async def chat_with_project(project_id: UUID, question: str):
    # 1. Generate embedding for the question
    query_embedding = await bedrock.embed(question)

    # 2. Search similar chunks (threshold=0.05, top_k=5)
    chunks = await postgres.similarity_search(
        project_id=project_id,
        embedding=query_embedding,
        threshold=0.05,
        top_k=5
    )

    # 3. Build context from retrieved chunks
    context = format_chunks_as_context(chunks)

    # 4. Send to Claude with system prompt + context + question
    response = await bedrock.invoke_claude(
        system="You are a code analysis assistant. Answer based on the provided code context.",
        context=context,
        question=question
    )
    return response
```

---

## Job Cancellation Design

### State Machine

```
PENDING → RUNNING → COMPLETED
                  → FAILED
                  → CANCELLING → CANCELLED
```

### API Endpoint

```python
# POST /api/v1/jobs/{job_id}/cancel
async def cancel_job(job_id: UUID):
    job = await job_store.get(job_id)
    if job.status != "RUNNING":
        raise HTTPException(400, "Can only cancel running jobs")
    await job_store.update_status(job_id, "CANCELLING")
    return {"status": "CANCELLING"}
```

### Pipeline Cancellation Check

```python
# src/agents/pipeline.py
class AgentPipeline:
    async def run(self, project_id: UUID, job_id: UUID):
        for agent in self.agents:
            # Check cancellation before each agent
            job = await self.job_store.get(job_id)
            if job.status == "CANCELLING":
                await self.job_store.update_status(job_id, "CANCELLED")
                return partial_results

            await self.on_agent_start(agent.name, job_id)
            result = await agent.execute(project_model)
            results.append(result)

        return results
```

### Frontend Integration

```typescript
// Cancel button visible only during RUNNING state
const handleCancel = async () => {
  await fetch(`/api/v1/jobs/${jobId}/cancel`, { method: 'POST' });
  // SSE stream will emit status change to CANCELLED
};
```

---

## Re-Analyze Button Design

### Trigger Condition

El botón aparece cuando:
- `job.status === "COMPLETED"`
- Al menos un agente tiene `status === "FAILED"` en los resultados

### API Endpoint

```python
# POST /api/v1/jobs/{job_id}/retry
async def retry_job(job_id: UUID):
    original_job = await job_store.get(job_id)
    # Create new job for the same project (no re-clone)
    new_job = await job_store.create(project_id=original_job.project_id)
    # Trigger pipeline in background
    asyncio.create_task(pipeline.run(original_job.project_id, new_job.id))
    return {"new_job_id": new_job.id}
```

---

## Progressive Status Tracking Design

### Callback System

```python
# src/agents/pipeline.py
class AgentPipeline:
    async def on_agent_start(self, agent_name: str, job_id: UUID):
        """Called before each agent executes."""
        await self.job_store.update(job_id, {
            "current_agent": agent_name,
            "agent_started_at": datetime.utcnow()
        })
        # Emit SSE event
        await self.sse_emitter.emit(job_id, {
            "event": "agent_started",
            "data": {"agent": agent_name, "timestamp": datetime.utcnow().isoformat()}
        })
```

### SSE Event Format

```
event: agent_started
data: {"agent": "SecurityAgent", "timestamp": "2025-01-15T10:30:00Z"}

event: agent_completed
data: {"agent": "SecurityAgent", "status": "success", "duration_ms": 12500}

event: agent_failed
data: {"agent": "SecurityAgent", "error": "Bedrock timeout after 60s"}
```

### Frontend Display

```typescript
// Progress component shows current agent with elapsed timer
<div className="flex items-center gap-2">
  <PulsingDot color="amber" />
  <span className="font-mono text-xs uppercase">
    Running: {currentAgent}...
  </span>
  <span className="text-muted-foreground text-xs">
    {elapsedTime}s
  </span>
</div>
```

---

## Bedrock Timeouts y Fail-Fast Design

### Timeout Configuration

```python
# src/adapters/bedrock_adapter.py
class BedrockAdapter:
    REQUEST_TIMEOUT = 60       # seconds per request
    MAX_RETRIES = 2
    BACKOFF_BASE = 2           # seconds (2s, 4s)
    PIPELINE_TIMEOUT = 600     # 10 minutes total

    async def invoke_model(self, prompt: str, **kwargs) -> str:
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                async with asyncio.timeout(self.REQUEST_TIMEOUT):
                    response = await self._call_bedrock(prompt, **kwargs)
                    return response
            except asyncio.TimeoutError:
                if attempt == self.MAX_RETRIES:
                    raise BedrockTimeoutError(f"Timeout after {self.REQUEST_TIMEOUT}s")
                await asyncio.sleep(self.BACKOFF_BASE ** (attempt + 1))
            except ThrottlingException:
                if attempt == self.MAX_RETRIES:
                    raise
                await asyncio.sleep(self.BACKOFF_BASE ** (attempt + 1))
```

### Graceful Degradation in Pipeline

```python
# Each agent is wrapped in try/except
for agent in self.agents:
    try:
        result = await agent.execute(project_model)
        results.append(AgentResult(agent=agent.name, status="success", data=result))
    except (BedrockTimeoutError, Exception) as e:
        results.append(AgentResult(agent=agent.name, status="failed", error=str(e)))
        # Continue to next agent — don't block pipeline
```

---

## Security Modules Design

### Rate Limiter

```python
# src/api/middleware/rate_limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Applied per-route:
# Analysis endpoints: 10/minute
# Chat endpoints: 30/minute
# Health/status: unlimited
```

### Prompt Guard

```python
# src/api/middleware/prompt_guard.py
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+a",
    r"system\s*prompt",
    r"reveal\s+(your|the)\s+(system|instructions)",
    r"disregard\s+(all|any)\s+(prior|previous)",
    r"pretend\s+you\s+are",
]

class PromptGuard:
    def check(self, user_input: str) -> bool:
        """Returns True if injection detected."""
        normalized = user_input.lower().strip()
        return any(re.search(pattern, normalized) for pattern in INJECTION_PATTERNS)
```

### Guardrail

```python
# src/api/middleware/guardrail.py
class ContentGuardrail:
    MAX_INPUT_LENGTH = 2000  # characters

    def validate_input(self, text: str) -> ValidationResult:
        if len(text) > self.MAX_INPUT_LENGTH:
            return ValidationResult(valid=False, reason="Input too long")
        if self.prompt_guard.check(text):
            return ValidationResult(valid=False, reason="Invalid input")
        return ValidationResult(valid=True)
```

---

## Report Tabs Design

### Tab Structure

| # | Tab | Source Agent | Content |
|---|-----|-------------|---------|
| 1 | Overview | Pipeline aggregate | Metrics, tech stack, health score |
| 2 | Architecture | Architecture_Agent | Module structure, patterns, coupling |
| 3 | Quality | Quality_Agent | Metrics, complexity, testing gaps |
| 4 | Security | Security_Agent + Semgrep | Vulnerabilities, severity, remediation |
| 5 | Modernization | Modernization_Agent | Roadmap, priorities, effort |
| 6 | Dead Code | Dead_Code_Detector | Unused files/classes/functions |
| 7 | Documentation | Documentation_Agent + C4 | Diagrams, API docs, onboarding |

### Frontend Component Architecture

```typescript
// apps/frontend/src/components/report/ReportTabs.tsx
const TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'architecture', label: 'Architecture', icon: Network },
  { id: 'quality', label: 'Quality', icon: Gauge },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'modernization', label: 'Modernization', icon: Rocket },
  { id: 'dead-code', label: 'Dead Code', icon: Trash2 },
  { id: 'documentation', label: 'Documentation', icon: FileText },
];
```

---

## Graph UX Improvements Design

### Node Labels

```typescript
// Truncate at 20 chars, show full on hover
const getNodeLabel = (name: string) =>
  name.length > 20 ? `${name.slice(0, 17)}...` : name;
```

### Tooltips

```typescript
// Custom tooltip component for React Flow nodes
interface NodeTooltipData {
  fullPath: string;
  loc: number;
  dependencies: number;
  language: string;
}
```

### Fullscreen Mode

```typescript
// Toggle fullscreen with state preservation
const [isFullscreen, setIsFullscreen] = useState(false);
const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });

// Fullscreen renders in a portal with fixed positioning
// Viewport state is preserved across toggle
```

---

## Chat Markdown Rendering Design

### Library Choice

`react-markdown` con `remark-gfm` para GitHub Flavored Markdown y `react-syntax-highlighter` para code blocks.

### Supported Elements

| Markdown | Rendered As |
|----------|-------------|
| `# Header` | Styled h1-h6 with font-display |
| `**bold**` | `<strong>` |
| `- list items` | `<ul><li>` styled |
| `` `inline code` `` | `<code>` with mono font + background |
| ` ```language ` | Syntax-highlighted code block |
| Tables | Styled HTML tables |

### Component

```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const ChatMessage = ({ content }: { content: string }) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    components={{
      code({ className, children }) {
        const language = className?.replace('language-', '');
        return language ? (
          <SyntaxHighlighter style={vscDarkPlus} language={language}>
            {String(children)}
          </SyntaxHighlighter>
        ) : (
          <code className="bg-muted px-1 py-0.5 rounded font-mono text-sm">
            {children}
          </code>
        );
      },
    }}
  />
);
```

---

## Reindex Script Design

### Usage

```bash
python -m src.scripts.reindex --project-id <UUID>
```

### Implementation

```python
# src/scripts/reindex.py
async def reindex_project(project_id: UUID):
    """
    1. Delete existing embeddings for project_id
    2. Find cloned repo path from projects table
    3. Walk source files (filter by extension)
    4. Chunk each file
    5. Generate embeddings via Titan
    6. Batch INSERT into code_embeddings
    7. Report progress
    """
    await postgres.execute(
        "DELETE FROM code_embeddings WHERE project_id = $1", project_id
    )
    repo_path = await get_repo_path(project_id)
    files = list_source_files(repo_path)

    for i, file_path in enumerate(files):
        chunks = chunker.chunk_file(file_path, read_file(file_path))
        embeddings = await bedrock.batch_embed([c.content for c in chunks])
        await postgres.batch_insert_embeddings(project_id, chunks, embeddings)
        print(f"  [{i+1}/{len(files)}] {file_path}")
```

---

## SSE Parsing Fix Design

### Problem

El SSE spec (RFC) permite un espacio opcional después del colon en campos:
- `event: status` (con espacio) — lo envía Python/FastAPI
- `event:status` (sin espacio) — válido per spec

El parser del frontend solo manejaba una de las variantes, causando que algunos eventos no se procesaran.

### Fix

```typescript
// Before (broken):
const parseSSE = (line: string) => {
  const [field, value] = line.split(': ');  // Only handles space variant
  ...
};

// After (fixed):
const parseSSE = (line: string) => {
  const colonIdx = line.indexOf(':');
  if (colonIdx === -1) return null;
  const field = line.slice(0, colonIdx);
  // Skip optional space after colon (per SSE spec)
  const value = line.slice(colonIdx + 1).replace(/^ /, '');
  return { field, value };
};
```

---

## FK Fix para code_embeddings Design

### Problem

El pipeline indexaba embeddings inmediatamente después del análisis, pero la tabla `projects` no tenía el registro insertado si el proyecto era nuevo. El FK constraint en `code_embeddings.project_id → projects.id` fallaba.

### Solution

```python
# Before embedding indexing, ensure project exists
await postgres.execute("""
    INSERT INTO projects (id, repo_url, name, created_at)
    VALUES ($1, $2, $3, now())
    ON CONFLICT (id) DO NOTHING
""", project_id, repo_url, project_name)
```

### Order of Operations

```
1. Clone repo
2. INSERT INTO projects (ON CONFLICT DO NOTHING)  ← FIX
3. Run agent pipeline
4. Index embeddings (references projects.id)
5. Mark job complete
```

---

## Similarity Threshold Adjustment Design

### Problem

Con threshold=0.3, preguntas generales como "what does this project do?" no devolvían chunks porque ningún chunk individual tenía >0.3 de similitud con la pregunta.

### Solution

Reducir a 0.05, que permite matches mucho más amplios. El top_k=5 sigue limitando la cantidad de context enviado a Claude.

### Trade-offs

| Threshold | Pros | Cons |
|-----------|------|------|
| 0.3 (anterior) | Resultados muy relevantes | Muchas preguntas sin respuesta |
| 0.05 (nuevo) | Responde preguntas generales | Puede incluir chunks tangencialmente relevantes |

### Mitigation

Claude recibe instrucciones de ignorar contexto no relevante. El top_k=5 asegura que solo 5 chunks entran como contexto, manteniendo el prompt manejable.

```python
# src/adapters/postgres_adapter.py
SIMILARITY_THRESHOLD = 0.05  # Was 0.3

async def similarity_search(self, project_id, embedding, top_k=5):
    return await self.fetch("""
        SELECT file_path, chunk_content, start_line, end_line,
               1 - (embedding <=> $1::vector) AS similarity
        FROM code_embeddings
        WHERE project_id = $2
          AND 1 - (embedding <=> $1::vector) > $3
        ORDER BY embedding <=> $1::vector
        LIMIT $4
    """, embedding, project_id, SIMILARITY_THRESHOLD, top_k)
```
