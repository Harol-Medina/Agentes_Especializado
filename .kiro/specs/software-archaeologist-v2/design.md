# Design Document — Software Archaeologist v2 (Full Vision)

## Introduction

Este documento extiende el design del MVP para cubrir las funcionalidades post-MVP: deployment a producción, documentación completa, features deseables (código muerto, Semgrep, roadmap) y features WOW (comparación de versiones, timeline Git, C4, Open in Kiro). Se asume que el MVP (spec-v1) está implementado y funcional.

---

## Gap Analysis: MVP → 100%

### Estado actual (MVP completado)

| Capability | Status | Notes |
|---|---|---|
| Repository submission + validation | Done | GitHub URLs, size/count validation |
| Language/framework detection | Done | Java, TS, JS + frameworks |
| AST parsing + graph construction | Done | Tree-sitter + JavaParser |
| Agent pipeline (7 agents) | Done | Sequential with graceful degradation |
| Interactive dependency graph | Done | React Flow |
| RAG chat | Done | pgvector + Claude Sonnet |
| Architecture report | Done | Structured JSON |
| Kiro spec export | Done | Markdown download |
| Progress feedback | Done | Polling |
| Docker Compose local | Done | 5 services, multi-stage builds |
| AWS IAM setup | Done | Documented scripts |

### Pendiente para 100%

| Capability | Priority | Effort |
|---|---|---|
| Production deployment (Amplify + EB + RDS) | Alta | 2-3 días |
| Per-app documentation (4 READMEs) | Alta | 1 día |
| AWS step-by-step guide | Alta | 0.5 días |
| Root README profesional + Kiro narrative | Alta | 0.5 días |
| Deployment runbook | Media | 0.5 días |
| Dead code detection | Media | 1-2 días |
| Semgrep integration | Media | 1-2 días |
| Modernization roadmap (sprint table) | Media | 1 día |
| Version comparison | Baja | 2-3 días |
| Git timeline | Baja | 2 días |
| C4 diagrams (Mermaid) | Baja | 1-2 días |
| Open in Kiro (.kiro package) | Baja | 1 día |

---

## Production Deployment Architecture

### Target Architecture

```
                    ┌──────────────┐
                    │  CloudFront  │ (optional, CDN)
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │ Amplify  │  │    EB    │  │    EB    │
      │ Frontend │  │ Backend  │  │ Analyzer │
      │ (Next.js)│  │ (Docker) │  │ (Docker) │
      └──────────┘  └────┬─────┘  └────┬─────┘
                         │              │
                    ┌────┴──────────────┴────┐
                    │     Amazon RDS         │
                    │  PostgreSQL + pgvector  │
                    └───────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      ┌──────────┐    ┌──────────┐    ┌──────────┐
      │ S3 Repos │    │S3 Reports│    │ Bedrock  │
      │(lifecycle)│    │          │    │          │
      └──────────┘    └──────────┘    └──────────┘
```

### Deployment Steps (Manual v1)

1. **RDS**: Crear instancia PostgreSQL 15, habilitar pgvector, configurar security group
2. **S3**: Crear buckets (ya documentado en spec-v1)
3. **EB Backend**: Crear environment Docker, subir Dockerfile, configurar env vars
4. **EB Analyzer**: Crear environment Docker, subir Dockerfile, configurar env vars
5. **Amplify**: Conectar repo Git, configurar build settings para Next.js
6. **DNS**: (opcional) Configurar custom domain

### Future CI/CD Pipeline

```
Push to main
    │
    ├─► GitHub Actions / CodePipeline
    │       │
    │       ├─► Build Backend Docker image → Push to ECR
    │       ├─► Build Analyzer Docker image → Push to ECR
    │       └─► Trigger Amplify build (auto via Git)
    │
    ├─► EB Deployment (Backend)
    │       └─► Rolling update from ECR image
    │
    └─► EB Deployment (Analyzer)
            └─► Rolling update from ECR image
```

---

## Dead Code Detection Design

### Integration Point

El `Quality_Agent` se extiende con un módulo de dead code detection que se ejecuta después del análisis de métricas.

### Detection Algorithm

```python
class DeadCodeDetector:
    """Detects unreferenced code using the Project_Model graph."""

    def detect(self, project_model: ProjectModel) -> DeadCodeReport:
        """
        1. Find file nodes with zero incoming import edges
        2. Find class nodes with zero incoming inheritance/usage edges
        3. Find function nodes with zero incoming usage edges
        4. Find exported symbols never imported by other files
        5. Assign confidence: high (zero refs), medium (only test refs), low (dynamic usage possible)
        """
        ...

@dataclass
class DeadCodeCandidate:
    node_id: UUID
    node_type: NodeType
    name: str
    file_path: str
    confidence: str  # high | medium | low
    reason: str      # "no incoming import edges", "only referenced in tests", etc.
```

### Limitations

- Dynamic imports (`import()`, reflection) cause false positives
- Framework-wired classes (Spring `@Component`, Angular `@Injectable`) may appear dead but are auto-discovered

---

## Semgrep Integration Design

### Execution

```python
class SemgrepScanner:
    """Runs Semgrep with OWASP rulesets on cloned repository."""

    RULESETS = {
        "java": ["p/owasp-java", "p/java"],
        "typescript": ["p/owasp-javascript", "p/typescript"],
        "javascript": ["p/owasp-javascript", "p/javascript"],
    }

    async def scan(self, repo_path: str, language: str) -> SecurityReport:
        """
        1. Determine ruleset from detected language
        2. Run: semgrep --config={ruleset} --json {repo_path}
        3. Parse JSON output into SecurityFinding objects
        4. Categorize by severity
        5. Add remediation suggestions from Bedrock
        """
        ...
```

### Docker Consideration

Semgrep se instala en el Dockerfile del Analyzer:
```dockerfile
RUN pip install semgrep
```

---

## C4 Diagram Generation Design

### Mermaid Output

```python
class C4Generator:
    """Generates C4 diagrams from Architecture_Report and Project_Model."""

    def generate_context(self, report: dict) -> str:
        """System context: the app + external systems it talks to."""
        ...

    def generate_container(self, report: dict) -> str:
        """Containers: frontend, backend, DB, external services."""
        ...

    def generate_component(self, report: dict, container: str) -> str:
        """Components within a specific container (modules)."""
        ...
```

Output is Mermaid syntax rendered in the Frontend via `mermaid` library.

---

## Open in Kiro Package Design

### Exported Structure

```
kiro-spec-{project-name}.zip
├── specs/
│   └── modernization/
│       ├── requirements.md
│       ├── design.md
│       └── tasks.md
└── hooks/
    └── post-modernization.json
```

### Hook Template

```json
{
  "version": "v1",
  "hooks": [
    {
      "name": "Lint Modernized Code",
      "trigger": "PostFileSave",
      "matcher": "\\.(java|ts|tsx|js)$",
      "action": { "type": "command", "command": "npm run lint -- --fix ${file}" }
    }
  ]
}
```

---

## Documentation Structure

### Per-app READMEs

```
apps/backend/README.md      — Spring Boot API docs
apps/frontend/README.md     — Next.js app docs
apps/analyzer/README.md     — FastAPI + agents docs
apps/AWS/README.md          — AWS setup reproduction guide
```

### Root README sections

1. Project description + architecture diagram
2. Quick start (docker compose build + up)
3. Features (with screenshots)
4. Tech stack table
5. "Developed with Kiro" section
6. API documentation links
7. Deploy guide link
8. Contributing
9. License

### AWS Reproduction Guide (`apps/AWS/README.md`)

1. Prerequisites (AWS account, CLI installed)
2. IAM user creation (copy-paste commands)
3. S3 buckets creation + lifecycle
4. RDS instance creation + pgvector
5. Bedrock model access enablement
6. Elastic Beanstalk environments
7. Amplify connection
8. Environment variables mapping (dev → prod)
9. Verification checklist
10. Troubleshooting

---

## "Developed with Kiro" Narrative

Key points to cover in README:

| Kiro Feature | How It Was Used |
|---|---|
| **Specs** | Structured the entire project from requirements → design → tasks. Two specs: MVP (v1) and Full Vision (v2) |
| **Steering** | Global conventions (project structure, Docker, coding standards) + workspace-specific (design system, stack context) |
| **Agents** | Specialized sub-agents for code review, architecture decisions, frontend development |
| **Hooks** | Verification loops (build + test on save), lint enforcement |
| **MCP** | AWS documentation MCP for IAM policies, AWS API MCP for infrastructure commands |
| **Iterative Design** | Design review sessions that caught contradictions and edge cases before implementation |
