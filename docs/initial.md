# Software Archaeologist
## Documento de Diseño del Proyecto

> **Hackathon:** Kiro + AWS
>
> **Categoría:** Agentes Especializados
>
> **Nombre del Proyecto:** Software Archaeologist
>
> **Versión:** MVP 1.0

---

# 1. Visión del Proyecto

Software Archaeologist es una plataforma de análisis inteligente de repositorios de software que utiliza análisis estático, IA Generativa y agentes especializados para comprender automáticamente proyectos existentes.

El objetivo es reducir el tiempo necesario para comprender un proyecto legado pasando de días o semanas a pocos minutos.

La plataforma permitirá analizar repositorios públicos de GitHub, construir un modelo interno del sistema, responder preguntas mediante RAG, generar documentación técnica y producir automáticamente artefactos compatibles con Kiro para iniciar un proceso de modernización.

---

# 2. Objetivos

## Objetivo General

Construir un agente especializado capaz de comprender automáticamente cualquier proyecto de software y generar conocimiento útil para desarrolladores.

## Objetivos específicos

- Analizar repositorios de GitHub.
- Detectar automáticamente el lenguaje y framework.
- Comprender la arquitectura del sistema.
- Construir un grafo de dependencias.
- Responder preguntas sobre el código mediante IA.
- Generar documentación automática.
- Crear un roadmap de modernización.
- Generar artefactos compatibles con Kiro.

---

# 3. Alcance del Proyecto

El proyecto será desarrollado siguiendo una estrategia incremental.

## Lenguajes soportados en MVP

El MVP soportará análisis de proyectos escritos en:

- **Java** — análisis profundo via Tree-sitter + JavaParser. Cubre Spring Boot, el framework enterprise más común en proyectos legados.
- **TypeScript / JavaScript** — análisis via Tree-sitter. Un solo parser cubre React, Next.js, Angular, Vue y Express.

Esta combinación representa el escenario más frecuente de modernización: backend Java legacy + frontend JavaScript/TypeScript.

Soporte para lenguajes adicionales (PHP, Python, Go, C#) se agregará post-MVP aprovechando la arquitectura extensible de Tree-sitter.

---

# 🟢 MVP (Obligatorio)

## Análisis de Repositorios

El sistema permitirá:

- Analizar un repositorio público de GitHub.
- Clonar automáticamente el proyecto.
- Detectar el lenguaje principal.
- Detectar el framework utilizado.

Frameworks detectables en MVP:

- **Java**: Spring Boot, Quarkus, Jakarta EE
- **TypeScript/JavaScript**: React, Next.js, Angular, Vue, Express, NestJS

Limitaciones MVP:

- Repositorios de hasta 50,000 archivos / 500 MB.
- Solo repositorios públicos.

---

## Construcción del Modelo del Proyecto

El sistema deberá:

- Recorrer todos los archivos del repositorio.
- Construir el árbol del proyecto (estructura de directorios + metadata).
- Identificar módulos y sus responsabilidades.
- Detectar dependencias internas (entre módulos) y externas (librerías).

El modelo se representará como un grafo dirigido almacenado en PostgreSQL con la siguiente estructura:

- **Nodos**: archivos, clases, funciones, módulos, paquetes.
- **Aristas**: dependencias (import, herencia, uso, composición).
- **Metadata por nodo**: LOC, complejidad ciclomática, última modificación.

No deberá depender únicamente de prompts. Se utilizará análisis estático mediante AST (Tree-sitter para multi-lenguaje, JavaParser para análisis semántico profundo de Java).

---

## Grafo de Dependencias

Generar una representación visual interactiva del sistema usando React Flow.

Debe mostrar:

- Módulos y paquetes como nodos agrupados.
- Relaciones de dependencia como aristas dirigidas.
- Dependencias externas destacadas.
- Filtrado por módulo, tipo de relación y nivel de profundidad.
- Zoom, pan y click en nodo para navegar al detalle.

---

## Chat Inteligente

Implementar un chat basado en RAG (Retrieval-Augmented Generation).

El usuario podrá preguntar por ejemplo:

- ¿Cómo funciona la autenticación?
- ¿Dónde inicia el flujo de login?
- ¿Qué controlador utiliza este servicio?
- ¿Qué módulo depende de este componente?

### Arquitectura RAG

- **Vector Store**: pgvector (extensión de PostgreSQL en Amazon RDS).
- **Embeddings**: Amazon Bedrock (Titan Embeddings V2).
- **Chunking strategy**: por función/método (AST-aware). Cada chunk incluye contexto del archivo y módulo al que pertenece.
- **Indexación**: código fuente + comentarios + nombres de archivos + estructura de directorios.
- **Retrieval**: búsqueda semántica con re-ranking por relevancia arquitectónica.

Las respuestas se generan con Claude Sonnet (Amazon Bedrock) usando el contexto recuperado.

---

## Reporte de Arquitectura

Generar automáticamente:

- Lenguaje y versión detectada.
- Framework y versión.
- Estructura de módulos.
- Dependencias principales (internas y externas).
- Componentes principales con sus responsabilidades.
- Métricas: LOC, número de módulos, profundidad de dependencias.

---

## Exportación de Spec para Kiro

Generar automáticamente un Spec compatible con Kiro que describa un plan de modernización del proyecto.

### Formato de Spec generado

El Spec seguirá el formato nativo de Kiro:

```markdown
---
name: "Modernización de [nombre-proyecto]"
version: 1.0
---

# Requisitos
- REQ-1: [Requisito derivado del análisis]
- REQ-2: ...

# Diseño
## Arquitectura actual
[Descripción generada del estado actual]

## Arquitectura propuesta
[Recomendaciones de modernización]

# Tasks
- [ ] TASK-1: [Tarea concreta derivada del análisis]
- [ ] TASK-2: ...
```

Este archivo se genera en la ruta `docs/specs/` y puede importarse directamente en un workspace de Kiro.

---

# 🟡 Funcionalidades deseables

Si el tiempo del hackathon lo permite se implementarán las siguientes funcionalidades.

---

## Detección de Código Muerto

Detectar:

- Archivos no importados por ningún otro archivo.
- Clases no instanciadas ni extendidas.
- Métodos sin referencias externas.
- Componentes exportados pero nunca importados.

---

## Reporte de Seguridad

Detectar mediante Semgrep:

- Secretos expuestos (API keys, passwords en código).
- Dependencias con CVEs conocidos.
- Problemas OWASP Top 10.
- Malas prácticas de seguridad.

---

## Roadmap de Modernización

Generar automáticamente un plan priorizado:

| Sprint | Acción | Justificación |
|--------|--------|---------------|
| 1 | Eliminar código muerto | Reducir superficie de análisis |
| 2 | Actualizar dependencias vulnerables | Seguridad |
| 3 | Separar módulos acoplados | Mantenibilidad |
| 4 | Refactorizar arquitectura | Escalabilidad |

---

## Exportación de Tasks

Generar automáticamente Tasks compatibles con Kiro (lista de tareas en formato markdown con checkboxes, vinculadas a un Spec).

---

## Exportación de Hooks

Generar automáticamente Hooks compatibles con Kiro (archivos JSON en `.kiro/hooks/` con triggers PostFileSave para linting del código modernizado).

---

# 🔵 Funcionalidades WOW

Estas funcionalidades serán desarrolladas únicamente si existe tiempo disponible.

---

## Comparación entre versiones

Permitir comparar dos commits o ramas.

Mostrar:

- Cambios arquitectónicos (módulos agregados/eliminados).
- Nuevas dependencias externas.
- Incremento de complejidad ciclomática.
- Deuda técnica agregada.

---

## Línea de Tiempo

Analizar el historial Git para generar:

- Evolución del proyecto (crecimiento de LOC por módulo).
- Crecimiento de dependencias.
- Zonas de alta rotación (hotspots).
- Frecuencia de cambios por módulo.

---

## Diagramas C4

Generar automáticamente usando Mermaid:

- Context Diagram (sistema + actores externos).
- Container Diagram (aplicaciones + stores + comunicación).
- Component Diagram (módulos internos por contenedor).

---

## Open in Kiro

Botón que genere automáticamente toda la estructura necesaria para comenzar un proceso de modernización en Kiro.

Debe generar:

- Specs (plan de modernización completo).
- Tasks (tareas ejecutables vinculadas al spec).
- Hooks (automatizaciones post-modernización).

---

# 4. Arquitectura General

El sistema estará dividido en tres servicios principales, comunicados via REST.

```
┌─────────────┐     REST      ┌─────────────┐     REST      ┌─────────────┐
│  Frontend   │ ◄──────────► │   Backend   │ ◄──────────► │  Analyzer   │
│  (Next.js)  │              │(Spring Boot)│              │  (FastAPI)  │
└─────────────┘              └──────┬──────┘              └──────┬──────┘
                                    │                            │
                              ┌─────┴─────┐              ┌──────┴──────┐
                              │ PostgreSQL │              │   Bedrock   │
                              │ + pgvector │              │   (Claude)  │
                              └───────────┘              └─────────────┘
```

## Frontend

Aplicación web desarrollada con:

- Next.js 14+ (App Router)
- React 18+
- TailwindCSS
- TypeScript
- React Flow (grafo interactivo de dependencias)
- Mermaid (diagramas C4 en reportes)
- Monaco Editor (visualización de código)

Responsabilidades:

- Dashboard principal.
- Visualización interactiva del grafo.
- Chat con RAG.
- Diagramas estáticos en reportes.
- Exportación de artefactos Kiro.

---

## Backend

Desarrollado utilizando:

- Java 21
- Spring Boot 3.x
- Spring AI (orquestación de llamadas a Bedrock desde endpoints de chat)
- Spring Data JPA + PostgreSQL
- Spring Security (autenticación JWT stateless)

Responsabilidades:

- API REST (punto de entrada único para el frontend).
- Orquestación del flujo de análisis.
- Gestión de usuarios y proyectos.
- Persistencia del modelo del proyecto.
- Delegación de tareas de análisis al Analyzer.
- Integración con servicios AWS (S3, Lambda).

---

## Analyzer (Motor de Análisis)

Desarrollado con:

- Python 3.11+
- FastAPI
- Tree-sitter (parsing multi-lenguaje)
- JavaParser (análisis semántico profundo de Java)
- NetworkX (construcción y análisis del grafo en memoria)
- Semgrep (análisis de seguridad, solo features deseables)

Responsabilidades:

- Clonado del repositorio.
- Parsing AST multi-lenguaje.
- Construcción del grafo de dependencias.
- Generación de embeddings (via Bedrock Titan).
- Indexación en pgvector.
- Ejecución de agentes IA especializados.
- Respuestas RAG.

### Comunicación Backend ↔ Analyzer

Protocolo: **REST síncrono + webhooks para tareas largas**.

| Operación | Método | Patrón |
|-----------|--------|--------|
| Iniciar análisis | `POST /analyze` | Async — Backend envía URL, Analyzer responde `202 Accepted` con `job_id` |
| Consultar estado | `GET /jobs/{job_id}` | Polling desde Backend cada 5s |
| Notificar completado | Webhook `POST /api/webhooks/analysis-complete` | Analyzer notifica al Backend al terminar |
| Chat / pregunta RAG | `POST /query` | Síncrono — respuesta en streaming (SSE) |
| Obtener grafo | `GET /graph/{project_id}` | Síncrono — retorna JSON del grafo |

---

# 5. Tecnologías

## Frontend

| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| Next.js | 14+ | Framework React con SSR/SSG |
| React | 18+ | UI library |
| TailwindCSS | 3.x | Utilidades CSS |
| shadcn/ui | latest | Componentes UI |
| React Flow | 11+ | Grafo interactivo de dependencias |
| Mermaid | 10+ | Diagramas C4 estáticos en reportes |
| Monaco Editor | latest | Visualización de código en browser |
| TypeScript | 5.x | Tipado estático |

---

## Backend

| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| Java | 21 | Runtime |
| Spring Boot | 3.x | Framework web |
| Spring AI | 1.x | Integración con Bedrock para chat |
| Spring Data JPA | 3.x | ORM / Persistencia |
| Spring Security | 6.x | Auth JWT stateless |
| PostgreSQL | 15+ | Base de datos principal |
| pgvector | 0.5+ | Extensión para vector search (RAG) |
| Docker | latest | Containerización |

---

## Analyzer (Motor IA)

| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.100+ | API REST del analyzer |
| Tree-sitter | 0.20+ | Parsing AST multi-lenguaje (Java, TS, JS) |
| JavaParser | 3.25+ | Análisis semántico profundo de Java |
| NetworkX | 3.x | Grafo de dependencias en memoria |
| Semgrep | latest | Análisis de seguridad (features deseables) |
| boto3 | latest | SDK AWS para Bedrock y S3 |

---

## IA y Embeddings

| Servicio | Modelo | Propósito |
|----------|--------|-----------|
| Amazon Bedrock | Claude Sonnet | Generación de texto, razonamiento, documentación |
| Amazon Bedrock | Titan Embeddings V2 | Generación de embeddings para RAG |
| pgvector | — | Almacenamiento y búsqueda de vectores |

---

# 6. Servicios AWS

El proyecto utilizará los siguientes servicios para cumplir con los criterios del hackathon.

## Amazon Bedrock

Motor principal de IA.

Responsabilidades:

- Generación de documentación.
- Chat y respuestas RAG (Claude Sonnet).
- Embeddings para indexación (Titan Embeddings V2).
- Razonamiento de agentes especializados.

---

## Amazon S3

Almacenar:

- Repositorios clonados (temporales).
- Reportes generados (PDF/Markdown).
- Diagramas exportados.

---

## Amazon RDS

Base de datos PostgreSQL 15+ con extensión pgvector habilitada.

Almacena:

- Modelo del proyecto (nodos, aristas, metadata).
- Embeddings para RAG.
- Usuarios y sesiones.
- Historial de análisis.

---

## AWS Lambda

Procesamiento asíncrono disparado por eventos.

- **Trigger**: SQS (cola de análisis) o invocación directa desde Backend.
- **Uso**: tareas de post-procesamiento (generación de reportes PDF, notificaciones).

---

## AWS Amplify

Publicación del Frontend (Next.js con SSR).

---

## Elastic Beanstalk

Publicación del Backend (Java/Spring Boot con Docker).

---

# 7. Arquitectura de Agentes

El sistema estará compuesto por agentes especializados orquestados desde el Analyzer. Cada agente recibe un contexto específico y produce un output estructurado.

## Orquestación

Los agentes se ejecutan **secuencialmente** en el orden listado. Cada agente recibe el output del anterior como contexto adicional. La orquestación se implementa como un pipeline en Python (patrón chain).

```
Repository Agent → Architecture Agent → Quality Agent → Security Agent
                                                              ↓
                            Kiro Agent ← Modernization Agent ← Documentation Agent
```

---

## Repository Agent

**Input**: URL del repositorio GitHub.

**Proceso**:
- Clona el repositorio.
- Detecta lenguaje principal y frameworks.
- Construye el árbol de archivos.
- Ejecuta parsing AST.
- Genera el grafo de dependencias.
- Indexa embeddings en pgvector.

**Output**: `ProjectModel` (grafo completo + metadata + embeddings indexados).

---

## Architecture Agent

**Input**: `ProjectModel` del Repository Agent.

**Proceso**:
- Analiza patrones arquitectónicos (MVC, hexagonal, microservicios).
- Identifica capas y sus responsabilidades.
- Detecta violaciones de arquitectura (dependencias circulares, capas saltadas).
- Clasifica módulos por dominio.

**Output**: `ArchitectureReport` (patrón detectado, capas, violaciones, diagrama C4 sugerido).

---

## Quality Agent

**Input**: `ProjectModel` + `ArchitectureReport`.

**Proceso**:
- Calcula métricas de complejidad por módulo.
- Detecta código muerto (imports no usados, clases huérfanas).
- Identifica code smells (métodos largos, clases god object).
- Evalúa cobertura de tests (si hay tests presentes).

**Output**: `QualityReport` (métricas, lista de code smells, código muerto, score general).

---

## Security Agent

**Input**: `ProjectModel` + dependencias externas.

**Proceso**:
- Ejecuta Semgrep con ruleset OWASP.
- Busca secretos expuestos (regex + entropy).
- Verifica CVEs en dependencias (advisory databases).
- Evalúa configuraciones inseguras.

**Output**: `SecurityReport` (vulnerabilidades, severidad, recomendaciones).

---

## Documentation Agent

**Input**: `ProjectModel` + `ArchitectureReport` + `QualityReport`.

**Proceso**:
- Genera README técnico del proyecto analizado.
- Documenta cada módulo principal.
- Genera descripción de endpoints (si es API).
- Produce resumen ejecutivo.

**Output**: `DocumentationBundle` (README.md, módulos.md, API.md, resumen).

---

## Modernization Agent

**Input**: Todos los reports anteriores.

**Proceso**:
- Prioriza deuda técnica por impacto.
- Propone plan de refactoring incremental.
- Sugiere migraciones de dependencias.
- Genera roadmap por sprints.

**Output**: `ModernizationPlan` (roadmap priorizado, justificaciones, esfuerzo estimado).

---

## Kiro Agent

**Input**: `ModernizationPlan` + `ArchitectureReport`.

**Proceso**:
- Transforma el plan en formato Spec de Kiro.
- Genera Tasks vinculadas al Spec.
- Genera Hooks para automatización post-modernización.

**Output**:
- `spec.md` — Spec completo con requisitos, diseño y tasks.
- `tasks.md` — Lista de tareas ejecutables.
- `hooks.json` — Hooks para Kiro (PostFileSave, PostTaskExec).

---

# 8. Flujo General

```
┌─────────┐
│ Usuario │
└────┬────┘
     │ Ingresa URL de repositorio
     ▼
┌─────────────┐
│  Frontend   │
│  (Next.js)  │
└────┬────────┘
     │ POST /api/projects/analyze {repoUrl}
     ▼
┌─────────────┐
│   Backend   │  Valida, crea proyecto, encola análisis
│(Spring Boot)│
└────┬────────┘
     │ POST /analyze {repoUrl, projectId}
     ▼
┌─────────────┐
│  Analyzer   │  Clona → Parsea → Grafo → Embeddings → Agentes
│  (FastAPI)  │
└────┬────────┘
     │
     ├──► Repository Agent ──► Architecture Agent ──► Quality Agent
     │                                                      │
     │    Kiro Agent ◄── Modernization Agent ◄── Documentation Agent ◄──┘
     │         │
     │         ▼
     │    Genera Specs + Tasks + Hooks
     │
     │ Webhook: POST /api/webhooks/analysis-complete
     ▼
┌─────────────┐
│   Backend   │  Persiste resultados, notifica frontend
└────┬────────┘
     │
     ▼
┌─────────────┐
│  Frontend   │  Dashboard + Grafo + Chat + Reportes + Export Kiro
└─────────────┘
```

---

# 9. Estructura del Proyecto

```
software-archaeologist/

├── .data/
│   ├── .env               # Entorno activo (Docker lo usa por defecto)
│   ├── .env.dev           # Plantilla desarrollo
│   └── .env.prod          # Plantilla producción
│
├── docker-compose.yml
│
├── docker/
│   ├── backend/Dockerfile
│   ├── frontend/Dockerfile
│   └── analyzer/Dockerfile
│
├── nginx/
│   └── default.conf
│
├── scripts/
│   ├── start.sh
│   ├── stop.sh
│   └── url.sh
│
├── apps/
│   ├── backend/           # API Java/Spring Boot
│   ├── frontend/          # Web Next.js
│   ├── analyzer/          # Motor de análisis Python/FastAPI
│   └── aws/               # Lambdas, IAM, config AWS
│
├── docs/
│   ├── initial.md         # Este documento
│   ├── architecture/
│   ├── diagrams/
│   └── specs/
│
└── README.md
```

Se respetarán las siguientes reglas:

- Nunca mezclar infraestructura con código de aplicación.
- Nunca crear archivos `.env` dentro de `apps/`. Toda la configuración vive en `.data/`.
- Los cambios de entorno se realizan copiando plantillas sobre `.data/.env` o usando `--env-file`.
- Docker es el mecanismo principal de desarrollo local.
- Dockerfiles viven en `docker/<servicio>/Dockerfile` con `context: .` (raíz).
- Cada servicio en `docker-compose.yml` usa `env_file: ${COMPOSE_ENV_FILE:-.data/.env}`.

---

# 10. Principios de Desarrollo

El proyecto seguirá las siguientes prácticas:

- Clean Architecture en Backend (capas: domain, application, infrastructure).
- Arquitectura Hexagonal (puertos y adaptadores) para el Analyzer.
- SOLID en todas las capas.
- DDD para el dominio del modelo de proyecto.
- APIs REST con versionado (`/api/v1/`).
- Modularidad: cada agente es un módulo independiente en el Analyzer.
- Código desacoplado via interfaces/protocolos.
- Testing para componentes críticos (agentes, parsing, RAG).
- Git flow: branch por feature, PR con review, nunca push a main.

---

# 11. Entregables

Al finalizar el proyecto se deberá contar con:

- Repositorio GitHub público.
- Aplicación desplegada (Frontend en Amplify, Backend en Elastic Beanstalk).
- Dashboard funcional con análisis de repositorio.
- Grafo interactivo de dependencias.
- Chat con RAG funcional.
- Reporte de arquitectura generado automáticamente.
- Exportación de Specs compatibles con Kiro.
- README profesional.
- Diagramas técnicos (C4, flujo de datos).
- Docker Compose funcional para desarrollo local.
- Documentación técnica en `/docs`.
- Video demostrativo del proyecto.

---

# 12. Criterios de Éxito

El proyecto será considerado exitoso si:

- Analiza correctamente un repositorio de GitHub (Java o TypeScript/JavaScript).
- Detecta automáticamente el lenguaje y framework.
- Genera un grafo interactivo funcional del proyecto.
- Responde preguntas sobre el código mediante RAG.
- Genera un reporte de arquitectura útil y preciso.
- Exporta correctamente un Spec compatible con Kiro.

Objetivos adicionales (deseables):

- Genera Tasks y Hooks compatibles con Kiro.
- Detecta código muerto.
- Produce reporte de seguridad.
- Genera roadmap de modernización priorizado.

---

# 13. Enfoque del Hackathon

El objetivo principal no es únicamente crear un analizador de código, sino demostrar cómo **Kiro** puede utilizarse para desarrollar un sistema basado en **IA agéntica** que, además de comprender un proyecto existente, sea capaz de generar automáticamente los artefactos necesarios para iniciar su modernización.

La demostración deberá evidenciar el uso de:

- Specs (plan de modernización generado).
- Tasks (tareas ejecutables vinculadas).
- Hooks (automatizaciones reactivas).
- Agentes especializados (pipeline de análisis).
- Amazon Bedrock (Claude Sonnet + Titan Embeddings).
- Servicios AWS (RDS, S3, Lambda, Amplify, Elastic Beanstalk).
- Automatización del flujo completo de análisis y generación de conocimiento.
