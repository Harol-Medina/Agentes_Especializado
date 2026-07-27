# Software Archaeologist

> Comprende cualquier repositorio de software en minutos, no en semanas.

Plataforma de análisis inteligente de repositorios que utiliza agentes IA especializados, análisis estático AST y RAG para comprender automáticamente proyectos existentes, generar documentación, detectar problemas y producir planes de modernización.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USUARIO                                         │
│                                                                             │
│   Pega URL de GitHub → Ve progreso → Explora grafo → Chatea → Exporta      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                           NGINX (Reverse Proxy)                              │
│                     Port 80 · Rate limiting · SSE support                    │
└───────┬───────────────────────────────────────────────────────┬─────────────┘
        │                                                       │
┌───────▼───────────┐                               ┌──────────▼──────────┐
│    Frontend       │                               │     Backend         │
│    Next.js 14     │◄─────── REST/SSE ────────────►│   Spring Boot 3.3   │
│    React 18       │                               │     Java 21         │
│    Tailwind v4    │                               │     WebFlux         │
│    Force Graph    │                               │     Flyway          │
└───────────────────┘                               └──────────┬──────────┘
                                                               │
                                          ┌────────────────────┼──────────────┐
                                          │                    │              │
                                ┌─────────▼─────────┐  ┌──────▼──────┐      │
                                │     Analyzer      │  │  PostgreSQL │      │
                                │    FastAPI +      │  │  15 + pgvec │      │
                                │  7 Agentes IA     │  └─────────────┘      │
                                │  Tree-sitter AST  │                        │
                                │  RAG (pgvector)   │                        │
                                └─────────┬─────────┘                        │
                                          │                                  │
                              ┌───────────┼───────────┐                      │
                              │           │           │                      │
                      ┌───────▼──┐  ┌─────▼────┐  ┌──▼─────┐               │
                      │ Bedrock  │  │    S3    │  │ Webhook│               │
                      │ Claude   │  │  Repos + │  │ → Back │               │
                      │ Titan    │  │ Reports  │  └────────┘               │
                      └──────────┘  └──────────┘                            │
                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Features

| Feature | Estado | Descripción |
|---|---|---|
| Análisis de repositorios | Done | Clonar, parsear y modelar repos de GitHub |
| Detección de lenguaje/framework | Done | Java, TypeScript, JavaScript + 10 frameworks |
| Grafo de dependencias interactivo | Done | Visualización force-directed con filtros |
| Chat RAG inteligente | Done | Preguntas sobre el código con SSE streaming |
| Pipeline de 7 agentes IA | Done | Arquitectura, calidad, seguridad, docs, modernización |
| Reporte de arquitectura | Done | Patrones, capas, violaciones, métricas |
| Export Kiro Spec | Done | Plan de modernización importable en Kiro |
| Seguridad multi-capa (RAG) | Done | Rate limit + prompt guard + Bedrock Guardrail |
| Docker Compose local | Done | 5 servicios, multi-stage builds |
| Detección de código muerto | Planned | Archivos/clases/métodos sin referencias |
| Semgrep security scan | Planned | OWASP Top 10 + CVEs |
| Roadmap de modernización | Planned | Sprints priorizados |
| Comparación de versiones | Planned | Diff arquitectónico entre commits |
| Timeline Git | Planned | Evolución y hotspots |
| Diagramas C4 (Mermaid) | Planned | Context, Container, Component |
| Open in Kiro | Planned | .kiro package descargable |

---

## Tech Stack

| Capa | Tecnología | Versión |
|---|---|---|
| **Frontend** | Next.js (App Router) | 14.2 |
| | React | 18.3 |
| | Tailwind CSS | 4.x |
| | shadcn/ui + Radix | latest |
| | react-force-graph-2d | 1.25 |
| **Backend** | Java (Spring Boot + WebFlux) | 21 / 3.3.5 |
| | Flyway (migraciones) | latest |
| | PostgreSQL (driver) | latest |
| **Analyzer** | Python (FastAPI) | 3.11 / 0.111+ |
| | Tree-sitter (multi-lenguaje) | 0.23+ |
| | asyncpg + pgvector | latest |
| | boto3 (AWS SDK) | 1.34+ |
| **Base de Datos** | PostgreSQL + pgvector | 15 |
| **IA** | Claude Sonnet (Amazon Bedrock) | 4.5 |
| | Titan Embeddings V2 (Amazon Bedrock) | latest |
| **Infra** | Docker + Docker Compose | latest |
| | Nginx (reverse proxy) | alpine |
| | AWS (S3, RDS, EB, Amplify, Bedrock) | — |

---

## Quick Start

### Prerequisitos

- Docker Desktop instalado y corriendo
- Git
- Credenciales AWS con acceso a Bedrock (ver `apps/AWS/README.md`)

### Levantar el stack

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd Agentes_Especializado

# 2. Configurar credenciales AWS
# Crear el archivo .data/.env con tus credenciales:
cp .data/.env.example .data/.env
# Editar .data/.env con tus valores de AWS

# 3. Build de todos los servicios
docker compose build

# 4. Levantar el stack completo
docker compose up -d

# 5. Esperar a que el backend esté healthy (~40s)
docker compose logs -f backend
# Buscar: "Started ArchaeologistApplication"

# 6. Abrir en el navegador
open http://localhost
```

### Uso

1. Pega una URL de repositorio público de GitHub (e.g., `https://github.com/spring-projects/spring-petclinic`)
2. Espera mientras los 7 agentes analizan el repositorio (2-4 minutos)
3. Explora el grafo de dependencias interactivo
4. Haz preguntas en el chat RAG ("¿Cómo funciona la autenticación?")
5. Consulta el reporte de arquitectura
6. Exporta el Kiro Spec para modernización

### Detener

```bash
docker compose down
```

---

## Pipeline de Agentes IA

El Analyzer ejecuta 7 agentes en secuencia, cada uno especializado:

```
Repository → Architecture → Quality → Security → Documentation → Modernization → Kiro
```

| # | Agente | Función | Modelo |
|---|---|---|---|
| 1 | Repository | Clona, parsea AST, construye grafo, genera embeddings | Tree-sitter + Titan |
| 2 | Architecture | Detecta patrones, capas, violaciones circulares | Claude Sonnet |
| 3 | Quality | Métricas, code smells, complejidad | Claude Sonnet |
| 4 | Security | Vulnerabilidades, secretos, dependencias | Claude Sonnet |
| 5 | Documentation | Genera documentación técnica automática | Claude Sonnet |
| 6 | Modernization | Plan de modernización priorizado | Claude Sonnet |
| 7 | Kiro | Genera Spec compatible con Kiro IDE | Claude Sonnet |

Graceful degradation: si un agente falla (excepto Repository), el pipeline continúa.

---

## Estructura del Proyecto

```
Agentes_Especializado/
├── apps/
│   ├── frontend/          # Next.js 14 — Web UI
│   ├── backend/           # Spring Boot 3.3 — API Gateway
│   ├── analyzer/          # FastAPI — Motor de análisis IA
│   └── AWS/               # Scripts de infraestructura AWS
├── docker/
│   ├── frontend/Dockerfile
│   ├── backend/Dockerfile
│   └── analyzer/Dockerfile
├── nginx/
│   └── default.conf       # Reverse proxy config
├── docs/
│   ├── initial.md         # Documento de diseño original
│   └── e2e-test-guide.md  # Guía de testing E2E
├── .kiro/
│   ├── specs/             # 2 specs (MVP + v2)
│   ├── steering/          # 6 steering files
│   ├── agents/            # 5 custom agents
│   └── hooks/             # 4 automation hooks
├── docker-compose.yml     # Stack local completo
└── .data/.env             # Variables de entorno (no committed)
```

---

## Desarrollado con Kiro

Este proyecto fue desarrollado íntegramente con **Kiro** — un IDE con IA que va más allá del autocompletado para ofrecer un flujo de desarrollo estructurado y supervisado.

### Specs (Requirements → Design → Tasks)

El desarrollo se estructuró en dos Specs completos:

| Spec | Alcance | Tasks |
|---|---|---|
| `software-archaeologist-mvp` | MVP funcional end-to-end | 17 tasks con dependencias |
| `software-archaeologist-v2` | Full vision (deployment + docs + features) | 12 tasks en 8 waves |

Cada Spec sigue el flujo: **Requirements** (qué construir) → **Design** (cómo construirlo) → **Tasks** (en qué orden). Kiro mantiene la coherencia entre los tres documentos y ejecuta las tareas secuencialmente.

### Steering (Convenciones del Proyecto)

6 archivos de steering que guían toda interacción con Kiro:

| Steering File | Propósito |
|---|---|
| `project-structure.md` | Estructura del monorepo y convenciones de archivos |
| `stack-context.md` | Tech stack detallado con versiones y patrones |
| `design-system.md` | Paleta, tipografía, componentes UI (dark-first) |
| `agent-rules.md` | Reglas para los agentes custom |
| `continuity.md` | Contexto persistente entre sesiones |
| `lessons-learned.md` | Soluciones a problemas encontrados durante desarrollo |

### Agents (Sub-agentes Especializados)

5 agentes custom configurados en `.kiro/agents/engineering/`:

| Agente | Responsabilidad |
|---|---|
| `backend-architect` | Decisiones de arquitectura Java/Spring |
| `frontend-developer` | Implementación React/Next.js con design system |
| `analyzer-developer` | Pipeline Python + integración Bedrock |
| `code-reviewer` | Revisión de código previo a commit |
| `analyzer-developer1` | Especialista en Tree-sitter + RAG |

### Hooks (Automatizaciones)

4 hooks que automatizan el flujo de desarrollo:

| Hook | Trigger | Acción |
|---|---|---|
| `auto-commit-on-task` | PostTaskExec | Commit automático al completar un task |
| `auto-commit-post-task` | PostTaskExec | Backup de progreso |
| `code-review-post-task` | PostTaskExec | Review automático del código generado |
| `lessons-learned-on-fix` | PostToolUse | Registra soluciones en steering |

### Impacto de Kiro en el Desarrollo

- **Tiempo de diseño**: Las Specs permitieron iterar en el diseño antes de escribir código, detectando inconsistencias y edge cases temprano.
- **Consistencia**: Los Steering files aseguran que todo código generado sigue las mismas convenciones (design system, estructura hexagonal, manejo de errores).
- **Calidad**: El hook de code-review verifica cada task completado antes de avanzar al siguiente.
- **Conocimiento**: `lessons-learned.md` acumula soluciones a problemas encontrados, evitando repetir errores.

---

## Documentación

| Documento | Descripción |
|---|---|
| [apps/backend/README.md](apps/backend/README.md) | API Gateway — endpoints, config, desarrollo local |
| [apps/frontend/README.md](apps/frontend/README.md) | Web UI — componentes, design system, rutas |
| [apps/analyzer/README.md](apps/analyzer/README.md) | Motor IA — agentes, RAG, seguridad |
| [apps/AWS/README.md](apps/AWS/README.md) | Guía de reproducción AWS desde cero |
| [docs/initial.md](docs/initial.md) | Documento de diseño original |
| [docs/e2e-test-guide.md](docs/e2e-test-guide.md) | Guía de testing E2E |

---

## Despliegue

Para despliegue en AWS, seguir la guía paso a paso en [`apps/AWS/README.md`](apps/AWS/README.md).

Resumen del stack de producción:
- **Frontend**: AWS Amplify (auto-deploy desde Git)
- **Backend**: Elastic Beanstalk (Docker, t3.small)
- **Analyzer**: Elastic Beanstalk (Docker, t3.medium)
- **Database**: Amazon RDS PostgreSQL 15 + pgvector
- **Storage**: S3 (repos temporales + reportes persistentes)
- **IA**: Amazon Bedrock (Claude Sonnet + Titan Embeddings)

---

## Servicios AWS Utilizados

| Servicio | Uso |
|---|---|
| Amazon Bedrock | Claude Sonnet (razonamiento) + Titan (embeddings) |
| Amazon RDS | PostgreSQL 15 + pgvector para datos y vectores |
| Amazon S3 | Repos clonados (24h lifecycle) + reportes |
| Elastic Beanstalk | Docker hosting para Backend y Analyzer |
| AWS Amplify | Hosting Next.js con auto-deploy |
| CloudWatch Logs | Logging centralizado |
| IAM | Mínimo privilegio para el service user |

---

## Contributing

1. Fork el repositorio
2. Crear branch de feature (`git checkout -b feature/mi-feature`)
3. Seguir las convenciones del design system (`.kiro/steering/design-system.md`)
4. Asegurar que `docker compose build` funciona sin errores
5. Crear Pull Request

---

## Licencia

MIT

---

## English Summary

**Software Archaeologist** is an AI-powered platform that analyzes public GitHub repositories using 7 specialized agents (powered by Amazon Bedrock Claude Sonnet). It generates interactive dependency graphs, architecture reports, security assessments, and modernization plans — all in under 5 minutes.

Key capabilities:
- AST parsing via Tree-sitter (Java, TypeScript, JavaScript)
- RAG-based code chat with pgvector + Claude Sonnet
- 7-agent sequential pipeline with graceful degradation
- Export of Kiro-compatible specs for immediate modernization work
- Full Docker Compose local development + AWS production deployment

Built entirely with **Kiro IDE** using Specs, Steering, Agents, and Hooks for structured AI-assisted development.
