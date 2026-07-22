---
inclusion: auto
---

# Continuidad del Proyecto

Contexto persistente entre sesiones. Este archivo se actualiza conforme el proyecto evoluciona para que cualquier sesión nueva tenga el panorama completo sin necesidad de re-explorar.

---

## Estado Actual del Proyecto

- **Fase**: Configuración inicial de infraestructura agéntica
- **Última actualización**: 2026-07-21

## Stack Técnico

- **Backend**: Laravel (PHP) — `apps/backend/`
- **Frontend**: React + Vite + Tailwind CSS v4 — `apps/frontend/`
- **Mobile**: Kotlin/Android — `apps/android/`
- **Infra**: Docker Compose + Nginx + PHP-FPM
- **DB**: Por definir
- **AWS**: Lambdas — `apps/AWS/`

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
- [x] Steering: design-system, continuity, lessons-learned
- [x] Agent: code-reviewer senior
- [x] Hooks: code review post-tarea, lecciones aprendidas, commit automático
- [ ] Agentes restantes (backend-architect, frontend-developer, etc.)

### Aplicación
- [ ] Backend Laravel
- [ ] Frontend React
- [ ] Mobile Android
- [ ] AWS Lambdas

---

## Notas para la Próxima Sesión

_Actualizar esta sección al final de cada sesión con lo que queda pendiente o decisiones abiertas._

- Pendiente: implementar agentes de las 6 divisiones según spec `agency-agents-spec`
- Pendiente: definir motor de DB y configurar en docker-compose
