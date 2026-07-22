---
inclusion: auto
---

# Estructura del Proyecto — Software Archaeologist

Tres servicios (Frontend, Backend, Analyzer) con infraestructura Docker centralizada en la raíz.

---

## Estructura

```
/
├── docker-compose.yml
├── docker/
│   ├── backend/Dockerfile       # Java 21 / Spring Boot (multi-stage)
│   ├── frontend/Dockerfile      # Next.js (multi-stage)
│   └── analyzer/Dockerfile      # Python / FastAPI (multi-stage)
├── nginx/
│   └── default.conf
├── .data/
│   ├── .env                     # Entorno activo
│   ├── .env.dev
│   └── .env.prod
│
├── apps/
│   ├── backend/                 # Java 21 / Spring Boot 3.x
│   ├── frontend/                # Next.js 14+ / React / TypeScript
│   ├── analyzer/                # Python 3.11+ / FastAPI
│   └── AWS/                     # Lambdas, IAM policies, scripts de infra
│
├── docs/
│   ├── initial.md
│   ├── architecture/
│   └── specs/
│
└── README.md
```

---

## Docker — Operación

```
docker compose build
docker compose up
docker compose down
```

Sin parámetros, sin scripts, sin flags. Estos tres comandos son suficientes en cualquier equipo con Docker.

## Docker — Builds

Cada Dockerfile es multi-stage:
1. **build** — descarga dependencias + compila
2. **runtime** — imagen mínima que ejecuta

El Dockerfile copia código con `COPY apps/<servicio>/ .`. El build es autocontenido: cualquier equipo que clone el repo obtiene el mismo stack funcional.

> **Contrarresta inercia del modelo:** Se tiende a generar bind mounts (`volumes: ./apps/x:/app`) para hot-reload. Aquí el Dockerfile copia todo internamente. Los bind mounts rompen portabilidad.

---

## Variables de entorno

- `.data/.env` es lo que Docker Compose consume.
- Cada servicio: `env_file: .data/.env`
- Cambio de entorno: copiar plantilla → rebuild.

> **Contrarresta inercia del modelo:** Se tiende a crear `.env.local` dentro de cada app o usar `--env-file` como flag. Toda la config vive en `.data/` y se inyecta via Docker.

---

## Comunicación entre servicios

```
Frontend ──REST──► Backend ──REST/SSE──► Analyzer
                      │                       │
                      ▼                       ▼
                  PostgreSQL             Amazon Bedrock
                  (+ pgvector)          (Claude + Titan)
```

- Frontend → Backend: REST JSON. Frontend habla solo con Backend.
- Backend → Analyzer: async (202 + webhook) para análisis, sync para queries.
- Analyzer → Backend: webhook HMAC-signed al completar.
- Chat: SSE stream Analyzer → Backend → Frontend.
- Graph/Report/Spec: Backend lee de PostgreSQL (Analyzer escribe, Backend lee).

---

## Servicios

| Servicio | Puerto | Base |
|----------|--------|------|
| `frontend` | 3000 | node:20-alpine |
| `backend` | 8080 | eclipse-temurin:21-jre |
| `analyzer` | 8000 | python:3.11-slim |
| `db` | 5432 | pgvector/pgvector:pg15 |
| `nginx` | 80 | nginx:alpine |

---

## Naming

| Contexto | Convención | Ejemplo |
|----------|-----------|---------|
| Paquetes Java | `com.archaeologist.<modulo>` | `com.archaeologist.analysis` |
| Endpoints REST | kebab-case, versionados | `/api/v1/analysis-jobs` |
| Componentes React | PascalCase | `DependencyGraph.tsx` |
| Módulos Python | snake_case | `repository_agent.py` |
| Variables de entorno | UPPER_SNAKE_CASE | `AWS_REGION` |
| Branches Git | `feature/`, `fix/`, `docs/` | `feature/rag-chat` |

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | Next.js 14+ / React 18 / TypeScript / Tailwind / shadcn/ui / React Flow |
| Backend | Java 21 / Spring Boot 3.x / Spring Data JPA / Flyway / WebFlux |
| Analyzer | Python 3.11+ / FastAPI / Tree-sitter / asyncpg / pgvector |
| DB | PostgreSQL 15 + pgvector |
| IA | Amazon Bedrock (Claude Sonnet + Titan Embeddings V2) |
| Deploy | Amplify (frontend) / Elastic Beanstalk (backend, analyzer) / RDS |

---

## Reglas de ubicación

| Qué | Dónde |
|-----|-------|
| Dockerfiles | `docker/<servicio>/Dockerfile` |
| Código de aplicación | `apps/<servicio>/` |
| Variables de entorno | `.data/.env` |
| Nginx config | `nginx/default.conf` |
| IAM / Lambdas | `apps/AWS/` |
| Documentación | `docs/` |
| Specs Kiro | `.kiro/specs/` |
