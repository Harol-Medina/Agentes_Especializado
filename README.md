# Software Archaeologist

Plataforma de analisis inteligente de repositorios de software que utiliza agentes de IA especializados para comprender automaticamente proyectos existentes. Dado un repositorio publico de GitHub, el sistema produce grafos de dependencias interactivos, documentacion arquitectonica, chat RAG sobre el codigo y un plan de modernizacion exportable como Kiro Spec.

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────────────┐
│                         NGINX (puerto 80)                         │
│                    Reverse Proxy + Rate Limiting                   │
└────────┬────────────────────────────────┬────────────────────────┘
         │ /api/*                          │ /*
         v                                 v
┌─────────────────┐             ┌─────────────────────┐
│    Backend      │             │     Frontend        │
│  Java 21        │             │   Next.js 14+       │
│  Spring Boot 3  │             │   React 18 + TW v4  │
│  Puerto 8080    │             │   Puerto 3000       │
└────────┬────────┘             └─────────────────────┘
         │
         │ REST + Webhooks + SSE
         v
┌─────────────────┐             ┌─────────────────────┐
│    Analyzer     │────────────>│   Amazon Bedrock    │
│  Python 3.11+   │             │  Claude Sonnet      │
│  FastAPI        │             │  Titan Embeddings   │
│  Puerto 8000    │             └─────────────────────┘
└────────┬────────┘
         │
         v
┌─────────────────┐
│   PostgreSQL    │
│   15 + pgvector │
│   Puerto 5432   │
└─────────────────┘
```

### Servicios

| Servicio | Tecnologia | Directorio | Responsabilidad |
|----------|-----------|------------|-----------------|
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS v4 | `apps/frontend/` | UI, grafo interactivo (React Flow), chat, reportes |
| **Backend** | Java 21, Spring Boot 3.x, WebFlux, JPA, Flyway | `apps/backend/` | API gateway, orquestacion de jobs, DB reads, webhooks, SSE relay |
| **Analyzer** | Python 3.11+, FastAPI, Tree-sitter, asyncpg | `apps/analyzer/` | Clonado de repos, parsing AST, pipeline de agentes IA, RAG, DB writes |
| **PostgreSQL** | PostgreSQL 15 + pgvector | via Docker | Almacenamiento de grafos, embeddings, resultados de analisis |
| **Nginx** | nginx:alpine | `nginx/` | Reverse proxy, rate limiting, ruteo por path |

---

## Pipeline de Agentes IA

El Analyzer ejecuta una cadena secuencial de 7 agentes especializados:

```
Repository Agent → Architecture Agent → Quality Agent → Security Agent → Documentation Agent → Modernization Agent → Kiro Agent
```

| Agente | Funcion |
|--------|---------|
| **Repository** | Clona el repo, detecta lenguaje/framework, parsea AST, construye el grafo de dependencias |
| **Architecture** | Analiza patrones arquitectonicos, capas y violaciones de dependencias |
| **Quality** | Calcula metricas de complejidad y detecta code smells |
| **Security** | Detecta vulnerabilidades y problemas de seguridad |
| **Documentation** | Genera documentacion tecnica automatica del proyecto |
| **Modernization** | Propone un plan priorizado de refactoring y modernizacion |
| **Kiro** | Transforma el plan de modernizacion en formato Spec nativo de Kiro |

Si un agente no-critico falla, el pipeline continua con degradacion elegante. Solo la falla del Repository Agent (primer agente) termina la ejecucion.

---

## Requisitos Previos

- Docker y Docker Compose
- Credenciales de AWS con acceso a Amazon Bedrock (Claude Sonnet + Titan Embeddings V2)

---

## Inicio Rapido

1. **Clonar el repositorio**

```bash
git clone https://github.com/tu-usuario/software-archaeologist.git
cd software-archaeologist
```

2. **Configurar variables de entorno**

```bash
cp .data/.env.dev .data/.env
```

Editar `.data/.env` con las credenciales de AWS y configuracion de base de datos.

3. **Levantar el stack completo**

```bash
docker compose build
docker compose up
```

4. **Acceder a la aplicacion**

Abrir `http://localhost` en el navegador. Pegar una URL de repositorio publico de GitHub y lanzar el analisis.

---

## Estructura del Proyecto

```
/
├── docker-compose.yml          # Orquestacion de 5 servicios
├── docker/
│   ├── backend/Dockerfile      # Multi-stage: Gradle build → JRE 21
│   ├── frontend/Dockerfile     # Multi-stage: npm build → Node runtime
│   └── analyzer/Dockerfile     # Multi-stage: pip install → Python slim
├── nginx/
│   └── default.conf            # Reverse proxy con rate limiting
├── .data/
│   ├── .env                    # Variables de entorno activas
│   └── .env.dev                # Template para desarrollo
├── apps/
│   ├── backend/                # Java 21 / Spring Boot 3.x
│   ├── frontend/               # Next.js 14+ / React 18 / TypeScript
│   ├── analyzer/               # Python 3.11+ / FastAPI
│   └── android/                # Kotlin / Jetpack Compose (mobile)
├── .kiro/                      # Configuracion de Kiro IDE
│   ├── steering/               # Reglas persistentes auto-incluidas
│   ├── agents/                 # Agentes especializados invocables
│   ├── hooks/                  # Automatizaciones reactivas
│   └── specs/                  # Especificaciones de features
└── README.md
```

---

## Variables de Entorno

Todas las variables viven centralizadas en `.data/.env`. Categorias principales:

| Categoria | Prefijo | Ejemplos |
|-----------|---------|----------|
| Base de datos | `DB_` / `POSTGRES_` | `DB_HOST`, `DB_PORT`, `POSTGRES_USER` |
| AWS | `AWS_` | `AWS_REGION`, `AWS_ACCESS_KEY_ID` |
| Bedrock | `BEDROCK_` | `BEDROCK_MODEL_ID`, `BEDROCK_EMBEDDING_MODEL` |
| Aplicacion | `APP_` | `APP_ENV`, `APP_SECRET` |
| Webhooks | `WEBHOOK_` | `WEBHOOK_SECRET` |

---

## Despliegue en Produccion (AWS)

La arquitectura de produccion utiliza:

- **AWS Amplify**: Hosting del frontend
- **Elastic Beanstalk**: Backend y Analyzer como servicios independientes
- **RDS PostgreSQL 15 + pgvector**: Base de datos gestionada
- **Amazon Bedrock**: Modelos de IA (Claude Sonnet + Titan Embeddings V2)
- **S3**: Almacenamiento de artefactos
- **CloudWatch**: Monitoreo y logging

```bash
# Frontend
aws codebuild start-build --project-name archaeologist-frontend-build
aws elasticbeanstalk update-environment --environment-name arch-frontend-prod --version-label <nueva>

# Backend
aws codebuild start-build --project-name archaeologist-backend-build
aws elasticbeanstalk update-environment --environment-name archaeologist-backend-prod --version-label <nueva>

# Analyzer
aws codebuild start-build --project-name archaeologist-analyzer-build
aws elasticbeanstalk update-environment --environment-name archaeologist-analyzer-prod --version-label <nueva>
```

---

## Como se Utilizo Kiro en este Proyecto

Este proyecto fue desarrollado integramente con **Kiro**, un IDE con IA integrada. A continuacion se detalla como cada feature de Kiro fue aprovechada:

### Specs (Especificaciones Estructuradas)

Kiro permite construir features de forma iterativa a traves de un flujo **Requirements → Design → Tasks**. Este proyecto tiene dos specs:

| Spec | Ubicacion | Descripcion |
|------|-----------|-------------|
| MVP | `.kiro/specs/software-archaeologist-mvp/` | Primer release funcional con pipeline completo |
| V2 | `.kiro/specs/software-archaeologist-v2/` | Segunda iteracion con mejoras |

Cada spec contiene:
- **`requirements.md`** — Historias de usuario con criterios de aceptacion formales (formato RFC-style con SHALL/WHEN/IF)
- **`design.md`** — Documento de arquitectura con diagramas, contratos de API, modelos de datos, secuencias de comunicacion y manejo de errores
- **`tasks.md`** — Plan de implementacion con tareas ordenadas en vertical slices, cada una vinculada a requirements especificos

Este flujo permitio que Kiro ejecutara las tareas de implementacion con contexto completo: sabia que construir, por que, y en que orden.

### Steering (Reglas Persistentes)

Los archivos en `.kiro/steering/` se incluyen automaticamente en cada sesion, dando a Kiro contexto constante sobre el proyecto:

| Archivo | Proposito |
|---------|-----------|
| `stack-context.md` | Define el stack tecnico exacto (lenguajes, frameworks, versiones, patrones) |
| `design-system.md` | Sistema de diseno completo (colores, tipografia, componentes, efectos) basado en prototipo Figma |
| `project-structure.md` | Convencion de directorios: infra en raiz, codigo en `apps/`, env en `.data/` |
| `agent-rules.md` | Reglas transversales que todo agente debe respetar |
| `continuity.md` | Estado actual del proyecto, decisiones tomadas, progreso por area |
| `lessons-learned.md` | Registro acumulativo de errores y correcciones (se actualiza automaticamente) |

Esto eliminaba la necesidad de re-explicar convenciones en cada sesion. Kiro siempre sabia donde crear archivos, que patrones seguir y que decisiones ya estaban tomadas.

### Agents (Agentes Especializados)

Se crearon 5 agentes invocables manualmente en `.kiro/agents/engineering/`:

| Agente | Rol |
|--------|-----|
| `backend-architect.md` | Especialista en Java/Spring Boot, arquitectura hexagonal |
| `frontend-developer.md` | Especialista en Next.js/React/TypeScript/Tailwind |
| `analyzer-developer.md` | Especialista en Python/FastAPI, pipeline de agentes IA |
| `code-reviewer.md` | Reviewer senior multi-stack |
| `devops-automator.md` | Docker, Nginx, CI/CD |

Cada agente tiene identidad, reglas criticas y entregables definidos. Se invocan desde el chat con `#` para tareas que requieren expertise especifico.

### Hooks (Automatizaciones Reactivas)

Se configuraron 4 hooks que se ejecutan automaticamente durante el desarrollo:

| Hook | Trigger | Funcion |
|------|---------|---------|
| `auto-commit-on-task.json` | PostTaskExec | Crea un commit automatico al completar cada tarea del spec |
| `code-review-post-task.json` | PostTaskExec | Ejecuta code review senior automatico tras cada tarea |
| `lessons-learned-on-fix.json` | PostTaskExec | Registra autocorrecciones en el archivo de lecciones aprendidas |
| `auto-commit-post-task.json` | PostTaskExec | Backup de commit post-tarea |

Este pipeline automatizado garantiza que:
1. Cada tarea completada se commitea inmediatamente
2. Un reviewer virtual revisa el codigo generado
3. Si el reviewer encuentra problemas, Kiro los corrige
4. Las correcciones se documentan como lecciones aprendidas para no repetir errores

### Flujo de Trabajo Completo con Kiro

```
        ┌─────────────────────────────────────────────────┐
        │              SPEC (Requirements → Design → Tasks)│
        └─────────┬───────────────────────────────────────┘
                  │
                  v
        ┌─────────────────────┐
        │  Kiro ejecuta tarea │ ◄── Steering (contexto constante)
        │  del spec           │ ◄── Agent especializado (si necesario)
        └─────────┬───────────┘
                  │
                  v
        ┌─────────────────────┐
        │  Hook: Code Review  │ ── Si hay errores → corregir
        └─────────┬───────────┘
                  │
                  v
        ┌─────────────────────┐
        │  Hook: Auto-commit  │
        └─────────┬───────────┘
                  │
                  v
        ┌─────────────────────┐
        │  Hook: Lessons      │ ── Si hubo autocorreccion → registrar
        └─────────┬───────────┘
                  │
                  v
        ┌─────────────────────┐
        │  Siguiente tarea    │
        └─────────────────────┘
```

### Beneficios Observados

- **Consistencia**: El steering garantiza que Kiro respete las mismas convenciones en cada sesion, independientemente del contexto acumulado
- **Calidad continua**: Los hooks de code review detectan problemas antes de acumular deuda tecnica
- **Aprendizaje incremental**: El archivo `lessons-learned.md` funciona como memoria persistente — errores previos no se repiten
- **Velocidad**: El spec con tareas ordenadas permite ejecucion autonoma sin micromanagement
- **Trazabilidad**: Cada tarea tiene su commit, cada correccion tiene su leccion documentada

---

## Tecnologias Principales

| Capa | Tecnologia | Version |
|------|-----------|---------|
| Frontend | Next.js / React / TypeScript | 14.2 / 18.3 / 5.5 |
| Styling | Tailwind CSS | v4 |
| Componentes UI | shadcn/ui + Radix UI | - |
| Visualizacion | react-force-graph-2d | 1.25 |
| Backend | Java / Spring Boot / WebFlux | 21 / 3.3 |
| ORM / Migrations | Spring Data JPA / Flyway | - |
| Analyzer | Python / FastAPI | 3.11+ / latest |
| Parsing | Tree-sitter | multi-language |
| AI/LLM | Amazon Bedrock (Claude Sonnet) | - |
| Embeddings | Amazon Bedrock (Titan V2) | - |
| Base de datos | PostgreSQL + pgvector | 15 |
| Proxy | Nginx | alpine |
| Contenedores | Docker Compose | - |
| IDE | Kiro | - |

---

## Licencia

Proyecto privado. Todos los derechos reservados.
