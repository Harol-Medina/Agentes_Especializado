# Implementation Plan: Software Archaeologist v3 (Production Hardening)

## Overview

Implementación de las mejoras V3 centradas en tres ejes: **RAG chat inteligente**, **resiliencia del pipeline**, y **UX de producción**. Todas las features son incrementales sobre V1 (MVP) y V2. Se organizan en vertical slices para feedback end-to-end rápido.

## Tasks

- [x] 1. RAG Chat con Embedding Indexing
  - [x] 1.1 Implementar CodeChunker para segmentar archivos fuente
    - Crear `src/parsing/chunker.py` con lógica de chunking (~500 tokens, overlap 50)
    - Split por boundaries lógicos (funciones, clases) cuando sea posible
    - Fallback a line-based splitting para archivos no parseables
    - Cada chunk incluye: content, file_path, start_line, end_line
    - _Requirements: V3-1.2_

  - [x] 1.2 Crear tabla `code_embeddings` con pgvector
    - Schema: id, project_id (FK → projects), file_path, chunk_content, start_line, end_line, embedding vector(1024), created_at
    - Índice IVFFlat para búsqueda de similitud coseno
    - Migración Flyway o script SQL
    - _Requirements: V3-1.4_

  - [x] 1.3 Implementar embedding generation con Titan Embed V2
    - Integrar `amazon.titan-embed-text-v2:0` en Bedrock adapter
    - Batch embedding para eficiencia (múltiples chunks por request)
    - Timeout de 30s por batch
    - _Requirements: V3-1.3_

  - [x] 1.4 Hook post-pipeline para trigger automático de indexing
    - Después de pipeline exitoso, invocar embedding indexer
    - Indexar todos los archivos fuente del repo clonado
    - Reportar progreso vía job status
    - _Requirements: V3-1.1_

  - [x] 1.5 Implementar endpoint de chat con RAG
    - `POST /api/v1/projects/{id}/chat` con body `{ question: string }`
    - Generar embedding de la pregunta
    - Similarity search (top_k=5, threshold=0.05)
    - Construir context con chunks + enviar a Claude
    - Retornar respuesta con file_path citations
    - _Requirements: V3-1.5, V3-1.6_

  - [x] 1.6 Frontend: componente de chat con markdown rendering
    - Input de texto + botón enviar
    - Display de mensajes usuario/asistente
    - Renderizado markdown con react-markdown + syntax highlighting
    - Auto-scroll al último mensaje
    - _Requirements: V3-1.7, V3-9.1, V3-9.2, V3-9.3, V3-9.4, V3-9.5_

- [x] 2. Job Cancellation
  - [x] 2.1 API endpoint de cancelación
    - `POST /api/v1/jobs/{job_id}/cancel`
    - Validar que el job esté en status RUNNING
    - Actualizar status a CANCELLING
    - _Requirements: V3-2.3_

  - [x] 2.2 Pipeline: check de cancelación entre agentes
    - Consultar status del job antes de ejecutar cada agente
    - Si status == CANCELLING, detener y preservar resultados parciales
    - Actualizar status a CANCELLED
    - _Requirements: V3-2.3, V3-2.4_

  - [x] 2.3 Frontend: botón Cancel en progress view
    - Mostrar solo cuando job.status === RUNNING
    - POST al endpoint de cancelación
    - Actualizar UI a CANCELLED con resultados parciales visibles
    - _Requirements: V3-2.1, V3-2.5_

- [x] 3. Re-Analyze Button
  - [x] 3.1 API endpoint de retry
    - `POST /api/v1/jobs/{job_id}/retry`
    - Crear nuevo job para el mismo project_id (sin re-clonar)
    - Lanzar pipeline en background
    - Retornar new_job_id
    - _Requirements: V3-3.3_

  - [x] 3.2 Frontend: botón Re-analyze
    - Mostrar cuando job.status === COMPLETED y algún agente tiene status FAILED
    - POST al endpoint de retry
    - Navegar a la progress view del nuevo job
    - _Requirements: V3-3.1, V3-3.2, V3-3.4_

- [x] 4. Progressive Status Tracking
  - [x] 4.1 Implementar on_agent_start callback en pipeline
    - Actualizar job record con current_agent y agent_started_at
    - Emitir evento SSE `agent_started` con nombre del agente
    - Emitir evento SSE `agent_completed` o `agent_failed` al terminar
    - _Requirements: V3-4.1, V3-4.2, V3-4.3_

  - [x] 4.2 Frontend: display de agente actual con timer
    - Mostrar nombre del agente en ejecución ("Running: Security Agent...")
    - Timer de elapsed time por agente
    - Actualizar en tiempo real vía SSE
    - _Requirements: V3-4.4, V3-4.5_

- [x] 5. Bedrock Timeouts y Fail-Fast
  - [x] 5.1 Configurar timeouts en Bedrock adapter
    - Per-request timeout: 60 segundos
    - Retry con exponential backoff: 2 intentos (2s, 4s)
    - Pipeline timeout total: 10 minutos
    - _Requirements: V3-5.1, V3-5.2, V3-5.5_

  - [x] 5.2 Graceful degradation en pipeline
    - Wrap cada agente en try/except
    - Registrar agente fallido con error details
    - Continuar al siguiente agente sin bloquear
    - _Requirements: V3-5.3, V3-5.4_

- [x] 6. Security Modules
  - [x] 6.1 Implementar Rate Limiter
    - Middleware con slowapi o equivalente
    - 10 req/min para analysis, 30 req/min para chat
    - HTTP 429 con Retry-After header
    - _Requirements: V3-6.1, V3-6.2_

  - [x] 6.2 Implementar Prompt Guard
    - Regex patterns para detectar prompt injection
    - HTTP 400 con mensaje genérico (no revelar lógica de detección)
    - Logging de requests bloqueados
    - _Requirements: V3-6.3, V3-6.4_

  - [x] 6.3 Implementar Content Guardrail
    - Validar longitud de input (max 2000 chars)
    - Integrar prompt guard como capa interna
    - Log de todo lo bloqueado
    - _Requirements: V3-6.5, V3-6.6_

- [x] 7. Report Tabs Enriquecidos
  - [x] 7.1 Estructurar report en 7 tabs (Backend)
    - Cada agente produce una sección dedicada del reporte
    - Agregar campo `tab_id` al schema de resultados
    - Overview agrega métricas transversales
    - _Requirements: V3-7.1, V3-7.2_

  - [x] 7.2 Frontend: componente ReportTabs con 7 tabs
    - Overview, Architecture, Quality, Security, Modernization, Dead Code, Documentation
    - Cada tab renderiza data real del agente correspondiente
    - Formatting: tablas, code blocks, badges de severidad
    - _Requirements: V3-7.3, V3-7.4, V3-7.5, V3-7.6, V3-7.7, V3-7.8_

- [x] 8. Graph UX Improvements
  - [x] 8.1 Node labels y tooltips
    - Labels truncados a 20 chars
    - Tooltip on hover: full path, LOC, dependencies count, language
    - _Requirements: V3-8.1, V3-8.2_

  - [x] 8.2 Fullscreen mode
    - Botón toggle fullscreen
    - Render en portal con fixed positioning (viewport completo)
    - Preservar zoom/pan state entre toggles
    - Botón close/minimize en fullscreen
    - _Requirements: V3-8.3, V3-8.4, V3-8.5_

- [x] 9. Chat Markdown Rendering
  - [x] 9.1 Integrar react-markdown + remark-gfm
    - Instalar react-markdown, remark-gfm, react-syntax-highlighter
    - Componente ChatMessage con markdown rendering
    - Soporte: headers, bold, lists, inline code, fenced code blocks
    - Syntax highlighting con vscDarkPlus theme
    - _Requirements: V3-9.1, V3-9.2, V3-9.3, V3-9.4, V3-9.5_

- [x] 10. Reindex Script
  - [x] 10.1 Crear script de re-indexing standalone
    - `python -m src.scripts.reindex --project-id <UUID>`
    - DELETE existing embeddings for project
    - Walk source files del repo clonado
    - Chunk + embed + INSERT
    - Progress reporting (files processed / total)
    - _Requirements: V3-10.1, V3-10.2, V3-10.3, V3-10.4, V3-10.5_

- [x] 11. SSE Parsing Fix
  - [x] 11.1 Fix parser SSE en frontend
    - Manejar `event:value` y `event: value` (espacio opcional per spec)
    - Manejar `data:value` y `data: value`
    - Aplicar a todos los puntos de consumo SSE
    - Verificar que progress view no se quede stuck
    - _Requirements: V3-11.1, V3-11.2, V3-11.3, V3-11.4_

- [x] 12. FK Fix para code_embeddings
  - [x] 12.1 INSERT INTO projects antes de indexar embeddings
    - INSERT con ON CONFLICT DO NOTHING (idempotente)
    - Ejecutar antes de cualquier INSERT en code_embeddings
    - Verificar FK constraint satisfecho
    - _Requirements: V3-12.1, V3-12.2, V3-12.3, V3-12.4_

- [x] 13. Similarity Threshold Adjustment
  - [x] 13.1 Reducir threshold de 0.3 a 0.05
    - Modificar constante SIMILARITY_THRESHOLD en postgres_adapter
    - Verificar que preguntas generales retornan chunks
    - Mantener top_k=5 como limitador de contexto
    - _Requirements: V3-13.1, V3-13.2, V3-13.3, V3-13.4_

## Notes

- Todas las tasks están marcadas como completadas [x] porque esta spec documenta trabajo ya implementado en la iteración V3.
- El orden de implementación real fue: Bedrock timeouts (5) → Progressive status (4) → Cancellation (2) → RAG chat (1) → Security (6) → Report tabs (7) → Graph UX (8) → Fixes (11, 12, 13) → Reindex (10) → Re-analyze (3) → Markdown (9).
- La prioridad real fue dictada por los problemas encontrados en producción (timeouts primero, luego UX).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["5.1", "5.2"], "description": "Bedrock resilience (foundation)" },
    { "id": 1, "tasks": ["4.1", "4.2", "2.1", "2.2"], "description": "Pipeline control (status + cancel)" },
    { "id": 2, "tasks": ["1.1", "1.2", "1.3", "12.1"], "description": "RAG infrastructure (chunks + DB + FK)" },
    { "id": 3, "tasks": ["1.4", "1.5", "13.1"], "description": "RAG integration (indexing + search + threshold)" },
    { "id": 4, "tasks": ["6.1", "6.2", "6.3"], "description": "Security modules" },
    { "id": 5, "tasks": ["7.1", "7.2", "8.1", "8.2"], "description": "Report + Graph UX" },
    { "id": 6, "tasks": ["1.6", "9.1", "11.1"], "description": "Frontend: chat + markdown + SSE fix" },
    { "id": 7, "tasks": ["2.3", "3.1", "3.2", "10.1"], "description": "Frontend controls + dev tooling" }
  ]
}
```
