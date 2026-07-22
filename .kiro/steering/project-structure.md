---
inclusion: auto
---

# Estructura del Proyecto — Software Archaeologist

Este proyecto tiene una arquitectura de tres servicios (Frontend, Backend, Analyzer) con infraestructura Docker centralizada en la raíz.

---

## Raíz — Infraestructura y Orquestación

Todo lo relacionado con Docker, proxy y configuración de entorno vive en la raíz:

```
/
├── docker-compose.yml       # Orquestación de todos los servicios
├── docker/                  # Dockerfiles centralizados
│   ├── backend/Dockerfile   # Java 21 / Spring Boot
│   ├── frontend/Dockerfile  # Next.js
│   └── analyzer/Dockerfile  # Python / FastAPI
├── nginx/
│   └── default.conf         # Reverse proxy
├── .data/
│   ├── .env                 # Entorno activo (Docker lo consume por defecto)
│   ├── .env.dev             # Plantilla desarrollo
│   └── .env.prod            # Plantilla producción
├── scripts/
│   ├── start.sh             # Levanta el stack (./start.sh | ./start.sh prod)
│   ├── stop.sh              # Apaga el stack
│   └── url.sh               # Muestra la URL pública + QR
└── README.md
```

### Reglas de infraestructura

- Nunca crear Dockerfiles, configs de nginx ni docker-compose dentro de `apps/`.
- Dockerfiles viven en `docker/<servicio>/Dockerfile` con `context: .` (raíz) para acceder a `apps/`.
- El `env_file` de cada servicio apunta a `${COMPOSE_ENV_FILE:-.data/.env}`.
- No existe PHP ni configuración PHP en este proyecto. El backend es Java/Spring Boot.

---

## /apps — Código de las Aplicaciones

Todo el código fuente vive dentro de `/apps`:

```
apps/
├── backend/     # API Java 21 / Spring Boot 3.x — servicio "api" en Docker
├── frontend/    # Web Next.js 14+ / React / TypeScript — servicio "frontend" en Docker
├── analyzer/    # Motor de análisis Python 3.11+ / FastAPI — servicio "analyzer" en Docker
└── aws/         # AWS Lambdas, scripts de deploy, IAM policies
```

### Reglas de código

- Todo código de aplicación va dentro de `apps/<servicio>/`.
- Nunca colocar código de aplicación en la raíz.
- Nunca crear carpetas `apps/android/`, `apps/shared/` u otras no listadas sin decisión explícita.
- Cada servicio es independiente y se comunica via REST.

---

## /docs — Documentación

```
docs/
├── initial.md       # Documento de diseño principal
├── architecture/    # Diagramas y decisiones de arquitectura
├── diagrams/        # Diagramas exportados (C4, flujo, grafo)
└── specs/           # Specs generados por el sistema
```

---

## Variables de Entorno

- `.data/.env` es el archivo activo que Docker Compose consume.
- `.data/.env.dev` y `.data/.env.prod` son plantillas.
- **Nunca crear archivos `.env` dentro de `apps/`**. Toda la configuración se inyecta via Docker `env_file`.
- Las credenciales AWS (access key, secret, region) van en `.data/.env`.

### Cambio de entorno

```bash
# Copiar plantilla al .env activo
cp .data/.env.dev .data/.env         # Linux/Mac
copy .data\.env.dev .data\.env       # Windows

# O pasar explícito
docker compose --env-file .data/.env.dev up -d --build

# O usar scripts
./scripts/start.sh          # usa .data/.env
./scripts/start.sh prod     # usa .data/.env.prod
```

---

## Stack Técnico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Frontend | Next.js (App Router) + React + TailwindCSS + TypeScript | 14+ / 18+ / 3.x / 5.x |
| Frontend UI | shadcn/ui + React Flow + Mermaid + Monaco Editor | latest |
| Backend | Java + Spring Boot + Spring AI + Spring Data JPA | 21 / 3.x / 1.x / 3.x |
| Backend Auth | Spring Security (JWT stateless) | 6.x |
| Analyzer | Python + FastAPI + Tree-sitter + JavaParser + NetworkX | 3.11+ / 0.100+ |
| Base de datos | PostgreSQL + pgvector | 15+ / 0.5+ |
| IA | Amazon Bedrock (Claude Sonnet + Titan Embeddings V2) | — |
| Storage | Amazon S3 | — |
| Async | AWS Lambda + SQS | — |
| Deploy Frontend | AWS Amplify | — |
| Deploy Backend | AWS Elastic Beanstalk | — |
| Deploy Analyzer | AWS Elastic Beanstalk o ECS (por definir) | — |

---

## Comunicación entre Servicios

```
Frontend ──REST──► Backend ──REST──► Analyzer
                      │                   │
                      ▼                   ▼
                  PostgreSQL          Amazon Bedrock
                  (+ pgvector)       (Claude + Titan)
```

- Frontend → Backend: REST JSON. El frontend nunca habla directo con el Analyzer.
- Backend → Analyzer: REST síncrono para queries, async (202 + webhook) para análisis largos.
- Analyzer → Backend: Webhook `POST /api/webhooks/analysis-complete` al terminar.
- Chat streaming: SSE (Server-Sent Events) desde Analyzer → Backend → Frontend.

---

## Convenciones de Naming

| Contexto | Convención | Ejemplo |
|----------|-----------|---------|
| Paquetes Java | `com.archaeologist.<modulo>` | `com.archaeologist.analysis` |
| Endpoints REST | kebab-case, versionados | `/api/v1/project-analysis` |
| Componentes React | PascalCase | `DependencyGraph.tsx` |
| Módulos Python | snake_case | `repository_agent.py` |
| Variables de entorno | UPPER_SNAKE_CASE | `AWS_BEDROCK_REGION` |
| Archivos de config | kebab-case | `docker-compose.yml` |
| Branches Git | `feature/`, `fix/`, `docs/` | `feature/rag-chat` |

---

## Servicios Docker Compose

| Servicio | Puerto | Imagen base |
|----------|--------|-------------|
| `frontend` | 3000 | node:20-alpine |
| `api` | 8080 | eclipse-temurin:21-jre |
| `analyzer` | 8000 | python:3.11-slim |
| `db` | 5432 | pgvector/pgvector:pg15 |
| `nginx` | 80/443 | nginx:alpine |

---

## Reglas Críticas (resumen)

1. Backend = Java/Spring Boot. No PHP, no Laravel, no Node backend.
2. Frontend = Next.js. No Vite, no CRA.
3. Analyzer = Python/FastAPI. Toda la lógica de IA y parsing vive aquí.
4. `.env` solo en `.data/`. Nunca en `apps/`.
5. Dockerfiles solo en `docker/`. Nunca en `apps/`.
6. Frontend nunca habla directo con Analyzer ni con Bedrock.
7. Credenciales AWS nunca hardcodeadas. Siempre en `.data/.env`.
