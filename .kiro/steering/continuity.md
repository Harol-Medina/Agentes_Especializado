---
inclusion: auto
---

# Continuidad del Proyecto

Contexto persistente entre sesiones. Este archivo se actualiza conforme el proyecto evoluciona para que cualquier sesión nueva tenga el panorama completo sin necesidad de re-explorar.

---

## Estado Actual del Proyecto

- **Fase**: Configuración inicial de infraestructura agéntica
- **Última actualización**: 2026-07-23

## Stack Técnico

- **Backend**: Java 21 / Spring Boot 3.x — `apps/backend/`
- **Frontend**: Next.js 14+ / React 18 / TypeScript / Tailwind CSS v4 — `apps/frontend/`
- **Analyzer**: Python 3.11+ / FastAPI — `apps/analyzer/`
- **Mobile**: Kotlin / Jetpack Compose — `apps/android/`
- **Infra**: Docker Compose + Nginx + AWS (Amplify, EB, RDS, Bedrock)
- **DB**: PostgreSQL 15 + pgvector
- **AWS**: Lambdas + Bedrock + S3 — `apps/AWS/`

## Arquitectura de Agentes

- Steering globales en `.kiro/steering/` (auto-incluidos)
- Agentes manuales en `.kiro/agents/<division>/`
- Hooks en `.kiro/hooks/`

## Decisiones Tomadas

| Fecha | Decisión | Razón |
|-------|----------|-------|
| 2026-07-21 | Dark-first design system basado en Figma Make | Consistencia visual con prototipo |
| 2026-07-21 | Variables de entorno centralizadas en `.data/` | Un solo punto de configuración para Docker |
| 2026-07-21 | Código de app siempre en `apps/`, infra en raíz | Separación clara de responsabilidades |
| 2026-07-21 | Commits en Ingles | Preferencia del equipo |
| 2026-07-21 | Code review automático post-tarea via hooks | Calidad continua sin fricción |

## Convenciones Establecidas

- Commits: mensaje simple en Ingles, descriptivo del cambio
- Branches: una por feature, nunca push directo a main
- PRs: pequeños y enfocados
- Lecciones aprendidas se registran en `.kiro/steering/lessons-learned.md`
- Code review automático al completar tareas del spec

## Progreso por Área

### Infraestructura Agéntica

#### Global (`~/.kiro/`) — aplica a todos los proyectos
- [x] Steering: coding-standards, verification-loop, token-optimization, continuous-learning, security-baseline
- [x] Steering: project-structure, agentic-engineering, agency-agents-spec
- [x] Agent: engineering/code-reviewer, backend-architect, frontend-developer, devops-automator
- [x] Agent: security/appsec-engineer
- [x] Agent: testing/test-automation

#### Workspace (`.kiro/`) — específico de Software Archaeologist
- [x] Steering: design-system, continuity, lessons-learned, project-structure, stack-context, agent-rules
- [x] Agent: engineering/backend-architect (Java/Spring Boot 3.x específico)
- [x] Agent: engineering/frontend-developer (Next.js 14 + shadcn específico)
- [x] Agent: engineering/analyzer-developer (Python/FastAPI + RAG específico)
- [x] Hooks: code review post-tarea, lecciones aprendidas, commit automático
- [ ] Agentes pendientes: design/ (UI, UX), product/, project-management/

### Aplicación
- [ ] Backend Spring Boot
- [ ] Frontend Next.js
- [ ] Analyzer FastAPI (parcialmente implementado en apps/analyzer/)
- [ ] Mobile Kotlin/Android
- [ ] AWS Lambdas

---

## Notas para la Próxima Sesión

_Actualizar esta sección al final de cada sesión con lo que queda pendiente o decisiones abiertas._

- Completado: Adaptación de ECC repo (rules, skills, patterns) a steering y agents de Kiro
- Pendiente: agentes de design, product y project-management
- Pendiente: configurar docker-compose.yml con todos los servicios
- Pendiente: scaffolding del Backend (Spring Boot) y Frontend (Next.js)
