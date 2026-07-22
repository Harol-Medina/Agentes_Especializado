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

---

# 🟢 MVP (Obligatorio)

## Análisis de Repositorios

El sistema permitirá:

- Analizar un repositorio público de GitHub.
- Clonar automáticamente el proyecto.
- Detectar el lenguaje principal.
- Detectar el framework utilizado.

Ejemplos:

- Spring Boot
- Laravel
- React
- Angular
- Vue
- Next.js

---

## Construcción del Modelo del Proyecto

El sistema deberá:

- Recorrer todos los archivos.
- Construir el árbol del proyecto.
- Identificar módulos.
- Detectar dependencias.

No deberá depender únicamente de prompts.

Se utilizará análisis estático mediante AST.

---

## Grafo de Dependencias

Generar una representación visual del sistema.

Debe mostrar:

- módulos
- paquetes
- relaciones
- dependencias principales

La visualización será interactiva.

---

## Chat Inteligente

Implementar un chat basado en RAG.

El usuario podrá preguntar por ejemplo:

- ¿Cómo funciona la autenticación?
- ¿Dónde inicia el flujo de login?
- ¿Qué controlador utiliza este servicio?
- ¿Qué módulo depende de este componente?

Las respuestas deberán generarse utilizando el contexto indexado del proyecto.

---

## Reporte de Arquitectura

Generar automáticamente:

- lenguaje
- framework
- estructura
- módulos
- dependencias
- componentes principales

---

## Exportación de Spec para Kiro

Generar automáticamente un Spec que describa un plan de modernización del proyecto.

Este Spec deberá poder utilizarse directamente dentro de Kiro.

---

# 🟡 Funcionalidades deseables

Si el tiempo del hackathon lo permite se implementarán las siguientes funcionalidades.

---

## Detección de Código Muerto

Detectar:

- archivos no utilizados
- clases no utilizadas
- métodos sin referencias
- componentes obsoletos

---

## Reporte de Seguridad

Detectar:

- secretos expuestos
- dependencias vulnerables
- problemas OWASP
- malas prácticas

---

## Roadmap de Modernización

Generar automáticamente un plan dividido por prioridades.

Ejemplo:

Sprint 1

Eliminar código muerto

Sprint 2

Actualizar dependencias

Sprint 3

Separar autenticación

Sprint 4

Refactorizar arquitectura

---

## Exportación de Tasks

Generar automáticamente Tasks compatibles con Kiro.

---

## Exportación de Hooks

Generar automáticamente Hooks compatibles con Kiro.

---

# 🔵 Funcionalidades WOW

Estas funcionalidades serán desarrolladas únicamente si existe tiempo disponible.

---

## Comparación entre versiones

Permitir comparar dos commits o ramas.

Mostrar:

- cambios arquitectónicos
- nuevas dependencias
- incremento de complejidad
- deuda técnica agregada

---

## Línea de Tiempo

Analizar el historial Git para generar:

- evolución del proyecto
- crecimiento de módulos
- deuda técnica
- frecuencia de cambios

---

## Diagramas C4

Generar automáticamente:

- Context Diagram
- Container Diagram
- Component Diagram

---

## Open in Kiro

Botón que genere automáticamente toda la estructura necesaria para comenzar un proceso de modernización en Kiro.

Debe generar:

- Specs
- Tasks
- Hooks

---

# 4. Arquitectura General

El sistema estará dividido en tres aplicaciones principales.

## Frontend

Aplicación web desarrollada con:

- Next.js
- React
- TailwindCSS
- TypeScript
- React Flow
- Mermaid
- Monaco Editor

Responsabilidades:

- Dashboard
- Visualización
- Chat
- Diagramas
- Reportes

---

## Backend

Desarrollado utilizando:

- Java 21
- Spring Boot
- Spring AI
- Spring Data JPA
- Spring Security

Responsabilidades:

- API REST
- Orquestación
- Usuarios
- Persistencia
- Integración AWS
- Comunicación con Python

---

## Motor de Análisis

Desarrollado con:

- Python
- FastAPI

Responsabilidades:

- Parser
- AST
- RAG
- Construcción del Grafo
- Embeddings
- Agentes IA

---

# 5. Tecnologías

## Frontend

- Next.js
- React
- TailwindCSS
- shadcn/ui
- React Flow
- Mermaid
- Monaco Editor

---

## Backend

- Java 21
- Spring Boot
- Spring AI
- PostgreSQL
- JPA
- Docker

---

## Motor IA

- Python
- FastAPI
- Tree-sitter
- JavaParser
- NetworkX
- Semgrep

---

## IA

Amazon Bedrock

Modelo sugerido:

Claude Sonnet

---

# 6. Servicios AWS

El proyecto utilizará los siguientes servicios para cumplir con los criterios del hackathon.

## Amazon Bedrock

Motor principal de IA.

Responsabilidades:

- generación de documentación
- chat
- razonamiento
- roadmap

---

## Amazon S3

Almacenar:

- reportes
- diagramas
- documentación

---

## Amazon RDS

Base de datos PostgreSQL.

---

## AWS Lambda

Procesamiento asíncrono.

---

## AWS Amplify

Publicación del Frontend.

---

## Elastic Beanstalk

Publicación del Backend.

---

# 7. Arquitectura de Agentes

El sistema estará compuesto por múltiples agentes especializados.

## Repository Agent

Analiza el repositorio.

---

## Architecture Agent

Comprende la arquitectura.

---

## Quality Agent

Evalúa calidad.

---

## Security Agent

Evalúa seguridad.

---

## Documentation Agent

Genera documentación.

---

## Modernization Agent

Propone mejoras.

---

## Kiro Agent

Genera automáticamente:

- Specs
- Tasks
- Hooks

---

# 8. Flujo General

Usuario

↓

Repositorio GitHub

↓

Repository Agent

↓

Parser

↓

AST

↓

Modelo del Proyecto

↓

Embeddings

↓

RAG

↓

Amazon Bedrock

↓

Agentes Especializados

↓

Dashboard

↓

Chat

↓

Reportes

↓

Exportación para Kiro

---

# 9. Estructura del Proyecto

Se utilizará la siguiente organización.

```
software-archaeologist/

├── .env
├── docker-compose.yml
│
├── docker/
│
├── scripts/
│
├── apps/
│   ├── backend/
│   ├── frontend/
│   ├── analyzer/
│   ├── aws/
│   └── shared/
│
├── docs/
│   ├── architecture/
│   ├── diagrams/
│   ├── specs/
│   ├── tasks/
│   └── hooks/
│
└── README.md
```

Se respetarán las siguientes reglas:

- Nunca mezclar infraestructura con código de aplicación.
- Nunca crear archivos `.env` dentro de `apps/`.
- Toda la configuración será centralizada.
- Docker será el mecanismo principal de desarrollo local.
- Los cambios de entorno se realizarán únicamente mediante `.env` o `--env-file`.

---

# 10. Principios de Desarrollo

El proyecto seguirá las siguientes prácticas.

- Clean Architecture
- Arquitectura Hexagonal
- SOLID
- DDD cuando aplique
- APIs REST
- Modularidad
- Código desacoplado
- Alta mantenibilidad
- Testing para componentes críticos

---

# 11. Entregables

Al finalizar el proyecto se deberá contar con:

- Repositorio GitHub público.
- Aplicación desplegada.
- Dashboard funcional.
- Chat con RAG.
- Reporte de arquitectura.
- Exportación de Specs para Kiro.
- README profesional.
- Diagramas técnicos.
- Docker Compose.
- Documentación técnica.
- Video demostrativo del proyecto.

---

# 12. Criterios de Éxito

El proyecto será considerado exitoso si:

- Analiza correctamente un repositorio de GitHub.
- Detecta automáticamente el lenguaje y framework.
- Genera un grafo funcional del proyecto.
- Responde preguntas mediante RAG.
- Genera un reporte de arquitectura útil.
- Exporta correctamente un Spec compatible con Kiro.

Como objetivo adicional, se buscará implementar la generación de Tasks y Hooks, así como funcionalidades avanzadas como comparación de versiones, línea de tiempo de deuda técnica y generación automática de diagramas C4.

---

# 13. Enfoque del Hackathon

El objetivo principal no es únicamente crear un analizador de código, sino demostrar cómo **Kiro** puede utilizarse para desarrollar un sistema basado en **IA agéntica** que, además de comprender un proyecto existente, sea capaz de generar automáticamente los artefactos necesarios para iniciar su modernización.

La demostración deberá evidenciar el uso de:

- Specs
- Tasks
- Hooks
- Agentes especializados
- Amazon Bedrock
- Servicios AWS
- Automatización del flujo completo de análisis y generación de conocimiento.