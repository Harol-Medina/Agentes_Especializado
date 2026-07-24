---
inclusion: auto
---

# Stack Context

Technical reference for all agents and steering. This file defines the exact technologies, versions, and tooling used across the Software Archaeologist project.

---

## Services Overview

| Service | Language | Framework | Port | Directory |
|---------|----------|-----------|------|-----------|
| Backend | Java 21 | Spring Boot 3.x | 8080 | `apps/backend/` |
| Frontend | TypeScript | Next.js 14+ / React 18 | 3000 | `apps/frontend/` |
| Analyzer | Python 3.11+ | FastAPI | 8000 | `apps/analyzer/` |
| Mobile | Kotlin | Jetpack Compose | — | `apps/android/` |
| Database | — | PostgreSQL 15 + pgvector | 5432 | via Docker |
| Proxy | — | Nginx | 80 | `nginx/` |

---

## Backend — Java / Spring Boot

- **Runtime**: Java 21 (eclipse-temurin:21-jre)
- **Framework**: Spring Boot 3.x
- **Build**: Gradle (Kotlin DSL)
- **ORM**: Spring Data JPA + Hibernate
- **Migrations**: Flyway
- **Reactive**: Spring WebFlux (SSE streams)
- **Security**: Spring Security
- **Testing**: JUnit 5, Mockito, Testcontainers
- **API docs**: SpringDoc OpenAPI

### Key patterns
- Hexagonal architecture (ports & adapters)
- Package-by-feature: `com.archaeologist.<feature>`
- Records for DTOs, entities for persistence
- Constructor injection exclusively

---

## Frontend — React / Next.js

- **Runtime**: Node.js 20 (node:20-alpine)
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS v4 + custom design tokens
- **Components**: shadcn/ui
- **Visualization**: React Flow (dependency graphs)
- **State**: React Query (server), Context (UI)
- **Testing**: Vitest + Testing Library + Playwright (E2E)
- **Linting**: ESLint + Prettier

### Key patterns
- Server Components by default
- Feature-based folder structure
- Design system tokens in CSS variables (see `design-system.md`)
- Dark-first theme

---

## Analyzer — Python / FastAPI

- **Runtime**: Python 3.11+ (python:3.11-slim)
- **Framework**: FastAPI (async)
- **Parsing**: Tree-sitter (multi-language AST)
- **Database**: asyncpg + pgvector
- **AI/ML**: Amazon Bedrock (Claude Sonnet + Titan Embeddings V2)
- **RAG**: Custom pipeline (embed → index → retrieve → generate)
- **Testing**: pytest + pytest-asyncio + httpx
- **Linting**: Ruff + Black + mypy

### Key patterns
- Agent architecture: each analysis concern is an independent agent
- Pipeline composition: agents chain into analysis pipeline
- Ports & Adapters: `domain/ports/` interfaces, `adapters/` implementations
- Async-first: all I/O operations are async
- Webhook callbacks (HMAC-signed) for async results

---

## Mobile — Kotlin / Android

- **Language**: Kotlin
- **UI**: Jetpack Compose
- **Architecture**: MVVM + Clean Architecture
- **Networking**: Retrofit + OkHttp
- **DI**: Hilt
- **Persistence**: Room + DataStore
- **Testing**: JUnit 5 + MockK + Compose Testing

---

## Infrastructure

- **Orchestration**: Docker Compose (local), AWS (production)
- **Proxy**: Nginx (reverse proxy + static assets)
- **CI/CD**: GitHub Actions
- **Cloud**: AWS
  - Amplify (frontend hosting)
  - Elastic Beanstalk (backend + analyzer)
  - RDS PostgreSQL 15 + pgvector
  - Amazon Bedrock (LLM + Embeddings)
  - Lambda (scheduled tasks, webhooks)
  - S3 (artifact storage)
  - CloudWatch (monitoring)

---

## Database

- **Engine**: PostgreSQL 15
- **Extensions**: pgvector (similarity search)
- **Image**: pgvector/pgvector:pg15
- **Migrations**: Flyway (backend), Alembic-style raw SQL (analyzer)
- **Connection pools**: HikariCP (Java), asyncpg pool (Python)

---

## Environment Variables

All variables centralized in `.data/.env`. Key categories:

| Category | Prefix | Example |
|----------|--------|---------|
| Database | `DB_` | `DB_HOST`, `DB_PORT`, `DB_NAME` |
| AWS | `AWS_` | `AWS_REGION`, `AWS_ACCESS_KEY_ID` |
| Bedrock | `BEDROCK_` | `BEDROCK_MODEL_ID`, `BEDROCK_EMBEDDING_MODEL` |
| App | `APP_` | `APP_ENV`, `APP_SECRET` |
| Webhook | `WEBHOOK_` | `WEBHOOK_SECRET` |

---

## Package Managers

| Service | Manager | Lock file |
|---------|---------|-----------|
| Backend | Gradle | `gradle.lockfile` |
| Frontend | npm | `package-lock.json` |
| Analyzer | pip | `requirements.txt` |
| Mobile | Gradle | `gradle.lockfile` |
