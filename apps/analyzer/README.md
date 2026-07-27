# Analyzer — Software Archaeologist

Motor de análisis de código con IA y agentes especializados.

---

## Propósito

El Analyzer es el cerebro del sistema. Se encarga de:

- Clonar repositorios de GitHub
- Detectar lenguaje y framework automáticamente
- Parsear código fuente via AST (Tree-sitter + JavaParser)
- Construir grafos de dependencias
- Ejecutar un pipeline de 7 agentes IA especializados
- Generar embeddings e indexar en pgvector para RAG
- Responder preguntas sobre el código (chat RAG con SSE streaming)
- Generar reportes de arquitectura, calidad, seguridad y documentación
- Producir Kiro Specs para modernización

---

## Tech Stack

| Tecnología | Versión | Propósito |
|---|---|---|
| Python | 3.11+ | Runtime |
| FastAPI | 0.111+ | Framework web async |
| Uvicorn | 0.30+ | ASGI server |
| Pydantic | 2.7+ | Validación y schemas |
| pydantic-settings | 2.3+ | Configuración por env vars |
| asyncpg | 0.29+ | Driver PostgreSQL async |
| pgvector | 0.3+ | Búsqueda vectorial |
| NumPy | 1.26+ | Operaciones numéricas (embeddings) |
| boto3 | 1.34+ | AWS SDK (Bedrock, S3) |
| GitPython | 3.1.43+ | Clonado de repositorios |
| Tree-sitter | 0.23+ | Parsing AST multi-lenguaje |
| tree-sitter-java | 0.23.1+ | Gramática Java |
| tree-sitter-typescript | 0.23+ | Gramática TypeScript |
| tree-sitter-javascript | 0.23+ | Gramática JavaScript |
| httpx | 0.27+ | HTTP client async (webhooks) |
| Docker | latest | Containerización (Python 3.11 slim) |

---

## Arquitectura (Hexagonal)

```
┌──────────────────────────────────────────────────────────────────┐
│                           API Layer                               │
│   routes/analyze  routes/query  routes/graph  routes/jobs         │
│   routes/report   routes/kiro_spec                               │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                        Domain Layer                                │
│   models/analysis_job   models/project_model   models/agent_result│
│   ports/llm_port   ports/storage_port   ports/embedding_port      │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                       Adapters Layer                               │
│   bedrock_adapter   postgres_adapter   git_adapter   webhook      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Estructura del Proyecto

```
apps/analyzer/
├── pyproject.toml                # Metadata del proyecto
├── requirements.txt              # Dependencias pip
└── src/
    ├── __init__.py
    ├── main.py                   # FastAPI app entry point
    ├── config.py                 # Settings via pydantic-settings
    │
    ├── api/                      # Capa de presentación (HTTP)
    │   ├── __init__.py
    │   ├── schemas.py            # Pydantic request/response models
    │   ├── dependencies.py       # FastAPI dependency injection
    │   ├── job_store.py          # In-memory job store (dict)
    │   └── routes/
    │       ├── __init__.py
    │       ├── analyze.py        # POST /analyze — inicia pipeline
    │       ├── jobs.py           # GET /jobs/{id} — status polling
    │       ├── query.py          # POST /query — RAG chat (SSE)
    │       ├── graph.py          # GET /graph/{id} — dependencias
    │       ├── report.py         # GET /report/{id} — reporte
    │       └── kiro_spec.py      # GET /kiro-spec/{id} — export
    │
    ├── agents/                   # Pipeline de agentes IA
    │   ├── __init__.py
    │   ├── base.py               # BaseAgent ABC + PipelineContext
    │   ├── pipeline.py           # AgentPipeline orchestrator
    │   ├── repository_agent.py   # Clonado + parsing + grafo
    │   ├── architecture_agent.py # Patrones y capas
    │   ├── quality_agent.py      # Métricas + code smells
    │   ├── security_agent.py     # Vulnerabilidades
    │   ├── documentation_agent.py# Documentación automática
    │   ├── modernization_agent.py# Plan de modernización
    │   └── kiro_agent.py         # Generación de Kiro Spec
    │
    ├── adapters/                  # Implementaciones de puertos
    │   ├── __init__.py
    │   ├── bedrock_adapter.py    # AWS Bedrock (Claude + Titan)
    │   ├── git_adapter.py        # GitPython (clone + log)
    │   ├── postgres_adapter.py   # asyncpg (pgvector queries)
    │   └── webhook_adapter.py    # httpx (notificaciones HMAC)
    │
    ├── domain/                    # Modelos y puertos (hexagonal core)
    │   ├── __init__.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── agent_result.py   # AgentResult + AgentStatus
    │   │   ├── analysis_job.py   # AnalysisJob + JobStatus
    │   │   └── project_model.py  # ProjectModel (nodos + aristas)
    │   └── ports/
    │       ├── __init__.py
    │       ├── embedding_port.py # ABC para embeddings
    │       ├── llm_port.py       # ABC para LLM
    │       ├── repository_port.py# ABC para repos
    │       └── storage_port.py   # ABC para persistencia
    │
    ├── graph/                     # Construcción del grafo
    │   ├── __init__.py
    │   ├── builder.py            # Construye grafo desde AST
    │   ├── models.py             # Node, Edge, GraphData
    │   └── serializer.py         # JSON serialization
    │
    ├── parsing/                   # Parsing de código fuente
    │   ├── __init__.py
    │   ├── chunker.py            # AST-aware chunking para RAG
    │   ├── java_parser.py        # JavaParser wrapper
    │   ├── language_detector.py  # Detección de lenguaje/framework
    │   └── tree_sitter_parser.py # Tree-sitter multi-lenguaje
    │
    ├── rag/                       # Retrieval-Augmented Generation
    │   ├── __init__.py
    │   ├── embeddings.py         # Titan Embeddings V2 client
    │   ├── generator.py          # RAG response generator (Claude)
    │   ├── indexer.py            # Indexación en pgvector
    │   └── retriever.py          # Búsqueda semántica + re-ranking
    │
    └── security/                  # Seguridad del endpoint RAG
        ├── __init__.py
        ├── audit_log.py          # Logging de eventos de seguridad
        ├── bedrock_guardrail.py  # AWS Guardrail (content + PII)
        ├── prompt_guard.py       # Detección de prompt injection
        └── rate_limiter.py       # Rate limiting por IP
```

---

## Pipeline de Agentes

Los agentes se ejecutan **secuencialmente**. Cada uno recibe el contexto acumulado de los anteriores.

```
Repository Agent → Architecture Agent → Quality Agent → Security Agent
                                                              ↓
                            Kiro Agent ← Modernization Agent ← Documentation Agent
```

| # | Agente | Entrada | Salida | Crítico |
|---|---|---|---|---|
| 1 | Repository Agent | URL del repo | ProjectModel (grafo + embeddings) | Si (falla = pipeline termina) |
| 2 | Architecture Agent | ProjectModel | ArchitectureReport (patrones, capas) | No |
| 3 | Quality Agent | ProjectModel + Architecture | QualityReport (métricas, smells) | No |
| 4 | Security Agent | ProjectModel + dependencias | SecurityReport (vulnerabilidades) | No |
| 5 | Documentation Agent | Todo lo anterior | DocumentationBundle | No |
| 6 | Modernization Agent | Todo lo anterior | ModernizationPlan | No |
| 7 | Kiro Agent | Todo lo anterior | KiroSpec (requirements + design + tasks) | No |

### Graceful Degradation

- Si **Repository Agent** falla → pipeline termina, job status = `FAILED`
- Si cualquier otro agente falla → se registra como `FAILED`, pipeline continúa
- Agentes sin prerequisitos → se marcan como `SKIPPED`
- Cancelación del usuario → agentes restantes se marcan como `SKIPPED`

---

## Endpoints API

| Método | Path | Descripción |
|---|---|---|
| `POST` | `/analyze` | Inicia análisis (202 Accepted, async background) |
| `GET` | `/jobs/{job_id}` | Estado del job + progreso por agente |
| `POST` | `/query` | Chat RAG con SSE streaming |
| `GET` | `/graph/{project_id}` | Grafo de dependencias (JSON) |
| `GET` | `/report/{project_id}` | Reporte de arquitectura completo |
| `GET` | `/kiro-spec/{project_id}` | Kiro Spec generado |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI (OpenAPI) |
| `GET` | `/redoc` | ReDoc (OpenAPI) |

### SSE Events (POST /query)

| Event | Descripción |
|---|---|
| `context` | Archivos fuente relevantes con scores |
| `token` | Token de respuesta generada |
| `no_context` | Sin contexto suficiente para responder |
| `error` | Error durante generación |
| `done` | Fin del stream |

---

## Seguridad del Chat RAG

El endpoint `/query` implementa 5 capas de seguridad:

1. **Rate limiting**: 20 req/min por IP
2. **Input validation**: Longitud máxima, sanitización de caracteres
3. **Prompt injection detection**: Regex patterns locales (PromptGuard)
4. **Bedrock Guardrail**: Filtrado de contenido + PII (AWS-side)
5. **Output validation**: Guardrail sobre la respuesta antes de enviar

---

## Variables de Entorno

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | *(requerido)* | URL asyncpg: `postgresql+asyncpg://user:pass@host:5432/db` |
| `BACKEND_URL` | `http://backend:8080` | URL del Backend (para webhooks) |
| `WEBHOOK_SECRET` | *(requerido)* | Secreto HMAC-SHA256 compartido |
| `AWS_ACCESS_KEY_ID` | `""` | Access Key de AWS |
| `AWS_SECRET_ACCESS_KEY` | `""` | Secret Key de AWS |
| `AWS_REGION` | `us-east-1` | Región de AWS |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Modelo Claude para generación |
| `BEDROCK_EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Modelo Titan para embeddings |
| `MAX_REPO_SIZE_BYTES` | `524288000` (500MB) | Tamaño máximo de repo |
| `MAX_FILE_COUNT` | `50000` | Archivos máximos en repo |
| `TEMP_REPO_DIR` | `/tmp/repos` | Directorio temporal para clones |
| `LOG_LEVEL` | `INFO` | Nivel de logging |

---

## Desarrollo Local

### Prerequisitos

- Python 3.11+
- PostgreSQL 15 con pgvector
- Git instalado
- Credenciales AWS configuradas (para Bedrock)

### Ejecutar

```bash
# Desde apps/analyzer/

# 1. Crear entorno virtual
python -m venv .venv

# Linux/Mac:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
export DATABASE_URL="postgresql+asyncpg://archaeologist:archaeologist_secret@localhost:5432/archaeologist"
export WEBHOOK_SECRET="shared_webhook_secret"
export AWS_ACCESS_KEY_ID="<tu-access-key>"
export AWS_SECRET_ACCESS_KEY="<tu-secret-key>"
export BEDROCK_MODEL_ID="us.anthropic.claude-sonnet-4-5-20250929-v1:0"
export BEDROCK_EMBEDDING_MODEL_ID="amazon.titan-embed-text-v2:0"
export AWS_REGION="us-east-1"

# 4. Iniciar servidor
uvicorn src.main:app --reload --port 8000

# Swagger UI: http://localhost:8000/docs
```

### Con Docker Compose (recomendado)

```bash
# Desde la raíz del proyecto
docker compose build analyzer
docker compose up db analyzer
```

---

## Testing

```bash
# Unit tests (pytest)
pytest

# E2E test (standalone — sin Docker)
python test_e2e_petclinic.py
# Resultados en e2e_results.json
```

Ver guía completa: `docs/e2e-test-guide.md`

---

## Build Docker

Multi-stage build:

1. **Stage Build**: `python:3.11-slim` — instala dependencias en `/app/deps`
2. **Stage Runtime**: `python:3.11-slim` + `git` — copia app + deps

```bash
# Build manual (desde raíz del proyecto)
docker build -f docker/analyzer/Dockerfile -t archaeologist-analyzer .
```

El runtime necesita `git` instalado (para clonar repositorios).

---

## Lenguajes Soportados (MVP)

| Lenguaje | Parser | Frameworks Detectados |
|---|---|---|
| Java | Tree-sitter + JavaParser | Spring Boot, Quarkus, Jakarta EE |
| TypeScript | Tree-sitter | React, Next.js, Angular, Vue, NestJS |
| JavaScript | Tree-sitter | React, Express, Vue |

Post-MVP: Python, PHP, Go, C# (extensible via Tree-sitter grammars).

---

## Modelos AWS Bedrock Utilizados

| Modelo | Model ID | Uso |
|---|---|---|
| Claude Sonnet 4.5 | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Razonamiento de agentes, chat RAG, documentación |
| Titan Embeddings V2 | `amazon.titan-embed-text-v2:0` | Generación de embeddings para indexación vectorial |

---

## Troubleshooting

### Bedrock `AccessDeniedException`

- **Causa**: El modelo no está habilitado en la consola de AWS Bedrock.
- **Solución**: Ir a Bedrock Console → Model Access → habilitar Claude Sonnet 4.5 y Titan Embed Text V2.
- **Verificación**: `aws bedrock list-foundation-models --region us-east-1 | grep "modelId"`

### Bedrock `ThrottlingException`

- **Causa**: Se superó el rate limit de Bedrock (tokens/min).
- **Solución**: El adapter implementa retry automático (3x con exponential backoff). Esperar y reintentar.

### Tree-sitter gramática no encontrada

- **Causa**: La gramática del lenguaje no se instaló correctamente.
- **Solución**: Verificar que `tree-sitter-java`, `tree-sitter-typescript`, `tree-sitter-javascript` están en `requirements.txt` y se instalaron sin error.

```bash
pip install tree-sitter-java tree-sitter-typescript tree-sitter-javascript
```

### Clone de repo falla

- **Causa**: Git no instalado en el container o problemas de red.
- **Solución**: El Dockerfile del analyzer instala `git` vía apt-get. Si ejecutas localmente, verificar con `git --version`.

### Repos grandes exceden timeout

- **Causa**: Repos con >50,000 archivos o >500MB.
- **Solución**: Los límites están en `config.py`. El clone usa `depth=1` (shallow) para reducir tamaño.

### `asyncpg.InvalidPasswordError`

- **Causa**: Credenciales incorrectas en `DATABASE_URL`.
- **Solución**: Verificar que el formato es `postgresql+asyncpg://user:password@host:port/database` y que las credenciales coinciden con `.data/.env`.

### SSE streaming se corta prematuramente

- **Causa**: Timeout del proxy o error en la generación.
- **Solución**: Verificar logs del analyzer. El stream incluye evento `error` con detalle del problema.
