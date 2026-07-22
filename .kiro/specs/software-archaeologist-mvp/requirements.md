# Requirements Document

## Introduction

Software Archaeologist es una plataforma de análisis inteligente de repositorios de software que utiliza análisis estático, IA Generativa y agentes especializados para comprender automáticamente proyectos existentes. El MVP demuestra el pipeline completo (repo → graph → chat → report → Kiro spec) con análisis superficial pero funcional de extremo a extremo, sin autenticación, con procesamiento secuencial y degradación elegante ante fallos de agentes.

## Glossary

- **Platform**: La aplicación web Software Archaeologist compuesta por Frontend (Next.js), Backend (Spring Boot) y Analyzer (FastAPI)
- **Frontend**: Aplicación web Next.js 14+ con React 18+, TailwindCSS y React Flow que sirve la interfaz de usuario
- **Backend**: Servicio Java 21 / Spring Boot 3.x que actúa como API REST y orquestador entre Frontend y Analyzer
- **Analyzer**: Servicio Python 3.11+ / FastAPI que ejecuta el análisis estático y el pipeline de agentes IA
- **Repository_Agent**: Agente que clona el repositorio, detecta lenguaje/framework, parsea AST y construye el grafo de dependencias
- **Architecture_Agent**: Agente que analiza patrones arquitectónicos, capas y violaciones de dependencias
- **Quality_Agent**: Agente que calcula métricas de complejidad y detecta code smells
- **Security_Agent**: Agente que detecta vulnerabilidades y problemas de seguridad
- **Documentation_Agent**: Agente que genera documentación técnica automática del proyecto analizado
- **Modernization_Agent**: Agente que propone un plan priorizado de refactoring y modernización
- **Kiro_Agent**: Agente que transforma el plan de modernización en formato Spec compatible con Kiro
- **Agent_Pipeline**: Secuencia ordenada de agentes ejecutados en cadena: Repository → Architecture → Quality → Security → Documentation → Modernization → Kiro
- **Project_Model**: Grafo dirigido almacenado en PostgreSQL que representa el sistema analizado (nodos: archivos, clases, funciones, módulos, paquetes; aristas: imports, herencia, uso, composición)
- **Dependency_Graph**: Representación visual interactiva del Project_Model usando React Flow
- **RAG_System**: Sistema de Retrieval-Augmented Generation compuesto por pgvector, Titan Embeddings V2 y Claude Sonnet para responder preguntas sobre el código
- **Architecture_Report**: Documento generado que describe lenguaje, framework, módulos, dependencias y métricas del proyecto analizado
- **Kiro_Spec**: Artefacto exportable en formato nativo de Kiro que contiene requisitos, diseño y tasks para modernización
- **Visitor**: Cualquier persona que accede a la Platform sin necesidad de autenticación
- **Analysis_Job**: Unidad de trabajo que representa el análisis completo de un repositorio, procesada secuencialmente

---

## Requirements

### Requirement 1: Repository Submission

**User Story:** As a Visitor, I want to submit a public GitHub repository URL for analysis, so that I can understand the architecture and dependencies of an existing project.

#### Acceptance Criteria

1. THE Platform SHALL provide an input field that accepts a GitHub repository URL in the format `https://github.com/{owner}/{repo}`
2. WHEN a Visitor submits a valid public GitHub repository URL, THE Backend SHALL create an Analysis_Job and return a job identifier to the Frontend within 3 seconds
3. WHEN a Visitor submits an invalid URL or a private repository URL, THE Backend SHALL return an error message indicating the URL is invalid or the repository is not accessible
4. WHILE an Analysis_Job is in progress, THE Platform SHALL reject new analysis submissions and inform the Visitor that the system is processing another request
5. THE Backend SHALL validate that the repository size does not exceed 500 MB and the file count does not exceed 50,000 files before initiating analysis

### Requirement 2: Language and Framework Detection

**User Story:** As a Visitor, I want the system to automatically detect the language and framework of a repository, so that I can quickly understand the technology stack without manual inspection.

#### Acceptance Criteria

1. WHEN the Repository_Agent processes a repository, THE Analyzer SHALL detect the primary programming language as one of: Java, TypeScript, or JavaScript
2. WHEN the primary language is Java, THE Analyzer SHALL detect the framework as one of: Spring Boot, Quarkus, or Jakarta EE
3. WHEN the primary language is TypeScript or JavaScript, THE Analyzer SHALL detect the framework as one of: React, Next.js, Angular, Vue, Express, or NestJS
4. IF the Analyzer cannot determine the language or framework, THEN THE Analyzer SHALL mark the detection as "unknown" and continue the pipeline with available data

### Requirement 3: Project Model Construction

**User Story:** As a Visitor, I want the system to build a structured model of the repository, so that I can explore the project's internal architecture programmatically.

#### Acceptance Criteria

1. WHEN the Repository_Agent completes cloning, THE Analyzer SHALL parse all source files using Tree-sitter for TypeScript and JavaScript, and Tree-sitter combined with JavaParser for Java
2. THE Analyzer SHALL construct a Project_Model as a directed graph with nodes representing files, classes, functions, modules, and packages
3. THE Analyzer SHALL identify edges between nodes representing imports, inheritance, usage, and composition relationships
4. THE Analyzer SHALL store metadata per node including lines of code, cyclomatic complexity, and last modification date
5. WHEN the Project_Model is constructed, THE Analyzer SHALL persist the graph in PostgreSQL

### Requirement 4: Interactive Dependency Graph

**User Story:** As a Visitor, I want to explore an interactive visual graph of the project's dependencies, so that I can understand how modules relate to each other.

#### Acceptance Criteria

1. WHEN an Analysis_Job completes successfully, THE Frontend SHALL render the Project_Model as an interactive Dependency_Graph using React Flow
2. THE Dependency_Graph SHALL display modules and packages as grouped nodes with dependency relationships as directed edges
3. THE Dependency_Graph SHALL highlight external dependencies with a distinct visual style
4. THE Frontend SHALL allow the Visitor to filter the Dependency_Graph by module, relationship type, and depth level
5. THE Frontend SHALL allow the Visitor to zoom, pan, and click on nodes to navigate to detail views

### Requirement 5: RAG-Based Chat

**User Story:** As a Visitor, I want to ask natural language questions about the analyzed code, so that I can quickly find answers about architecture, flows, and dependencies without reading the entire codebase.

#### Acceptance Criteria

1. WHEN an Analysis_Job completes, THE Analyzer SHALL generate embeddings using Amazon Bedrock Titan Embeddings V2 and index them in pgvector
2. THE Analyzer SHALL use AST-aware chunking strategy, splitting code by function or method, with each chunk including file and module context
3. WHEN a Visitor submits a question through the chat interface, THE RAG_System SHALL perform semantic search with re-ranking by architectural relevance
4. THE RAG_System SHALL generate responses using Claude Sonnet via Amazon Bedrock with the retrieved context
5. THE Frontend SHALL stream responses to the Visitor in real time using Server-Sent Events
6. IF the RAG_System cannot find relevant context for a question, THEN THE RAG_System SHALL inform the Visitor that no relevant information was found rather than generating an unsupported answer

### Requirement 6: Agent Pipeline Execution

**User Story:** As a Visitor, I want the system to run a complete analysis pipeline with specialized agents, so that I receive a comprehensive understanding of the project's architecture, quality, security, and modernization path.

#### Acceptance Criteria

1. WHEN an Analysis_Job starts, THE Analyzer SHALL execute the Agent_Pipeline in sequential order: Repository_Agent, Architecture_Agent, Quality_Agent, Security_Agent, Documentation_Agent, Modernization_Agent, Kiro_Agent
2. THE Analyzer SHALL pass the output of each agent as input context to the next agent in the pipeline
3. IF an agent in the pipeline fails, THEN THE Analyzer SHALL skip the failed agent, mark its section as incomplete, and continue execution with the remaining agents using available data
4. THE Analyzer SHALL invoke each agent using Claude Sonnet via Amazon Bedrock for reasoning and generation tasks
5. WHEN the Agent_Pipeline completes, THE Analyzer SHALL notify the Backend via webhook with the complete or partial results

### Requirement 7: Architecture Report Generation

**User Story:** As a Visitor, I want to receive an automatically generated architecture report, so that I can understand the project's technical structure without manual analysis.

#### Acceptance Criteria

1. WHEN the Documentation_Agent completes, THE Platform SHALL generate an Architecture_Report containing: detected language and version, detected framework and version, module structure, internal and external dependencies, principal components with responsibilities, and metrics (LOC, module count, dependency depth)
2. THE Frontend SHALL display the Architecture_Report in a readable formatted view
3. IF any section of the Architecture_Report could not be generated due to a pipeline failure, THEN THE Platform SHALL mark that section as "Analysis incomplete" with an explanation

### Requirement 8: Kiro Spec Export

**User Story:** As a Visitor, I want to export a Kiro-compatible Spec describing a modernization plan, so that I can import it directly into a Kiro workspace and begin modernization work.

#### Acceptance Criteria

1. WHEN the Kiro_Agent completes, THE Platform SHALL generate a Kiro_Spec in markdown format containing: requirements derived from analysis, description of current architecture, proposed modernization recommendations, and concrete tasks
2. THE Frontend SHALL provide a download action that exports the Kiro_Spec as a markdown file
3. THE Kiro_Spec SHALL follow the native Kiro spec format with sections for Requirements, Design (current architecture + proposed architecture), and Tasks (checkbox list)
4. IF the Modernization_Agent failed, THEN THE Kiro_Agent SHALL generate a partial Kiro_Spec based on available Architecture_Report data

### Requirement 9: Analysis Progress Feedback

**User Story:** As a Visitor, I want to see the progress of the analysis in real time, so that I know what the system is doing and how long it might take.

#### Acceptance Criteria

1. WHILE an Analysis_Job is in progress, THE Frontend SHALL display the current pipeline stage and which agent is executing
2. WHILE an Analysis_Job is in progress, THE Backend SHALL poll the Analyzer for status every 5 seconds and relay updates to the Frontend

3. WHEN an agent in the pipeline completes, THE Frontend SHALL update the progress indicator to reflect the completed stage
4. IF an agent fails, THEN THE Frontend SHALL display a warning indicator for that stage while continuing to show progress of subsequent agents

### Requirement 10: Sequential Processing

**User Story:** As a platform operator, I want the system to process one analysis at a time, so that resource usage remains predictable and the MVP operates within infrastructure limits.

#### Acceptance Criteria

1. THE Backend SHALL maintain a single-slot processing queue that accepts one Analysis_Job at a time
2. WHILE an Analysis_Job is active, THE Backend SHALL respond to new submission requests with a message indicating the system is busy and the Visitor should retry later
3. WHEN an Analysis_Job completes or fails, THE Backend SHALL release the processing slot and accept new submissions

### Requirement 11: Infrastructure and Deployment

**User Story:** As a developer, I want the system to run locally via Docker Compose and be deployable to AWS, so that development and production environments are consistent and reproducible.

#### Acceptance Criteria

1. THE Platform SHALL provide a docker-compose.yml at the project root that orchestrates five services: frontend (Next.js), backend (Spring Boot), analyzer (FastAPI), db (PostgreSQL with pgvector), and nginx (reverse proxy)
2. THE Platform SHALL store all environment variables in `.data/` directory with `.env`, `.env.dev`, and `.env.prod` files
3. THE Platform SHALL configure the nginx service to route requests to the appropriate backend or frontend service
4. THE Platform SHALL configure the db service with the pgvector extension enabled by default
5. WHEN `docker compose up` is executed at the project root, THE Platform SHALL start all services and be accessible via the nginx reverse proxy

### Requirement 12: Communication Between Services

**User Story:** As a developer, I want clearly defined communication protocols between Backend and Analyzer, so that the services interact reliably and long-running analyses do not block the Backend.

#### Acceptance Criteria

1. WHEN the Backend initiates an analysis, THE Backend SHALL send a POST request to the Analyzer at `/analyze` and receive a `202 Accepted` response with a `job_id`
2. THE Backend SHALL poll the Analyzer at `GET /jobs/{job_id}` every 5 seconds to retrieve the current status of the Analysis_Job
3. WHEN the Analyzer completes an Analysis_Job, THE Analyzer SHALL send a webhook POST request to the Backend at `/api/webhooks/analysis-complete` with the results
4. WHEN a Visitor sends a chat question, THE Backend SHALL forward it to the Analyzer at `POST /query` and stream the response back using Server-Sent Events
5. WHEN the Frontend requests graph data, THE Backend SHALL retrieve it from the Analyzer at `GET /graph/{project_id}` synchronously and return it as JSON

### Requirement 13: Graceful Degradation

**User Story:** As a Visitor, I want to receive partial results when parts of the analysis fail, so that a single agent failure does not invalidate the entire analysis.

#### Acceptance Criteria

1. IF the Repository_Agent fails to clone or parse the repository, THEN THE Analyzer SHALL terminate the Analysis_Job and return an error explaining the failure
2. IF any agent after Repository_Agent fails, THEN THE Analyzer SHALL continue the pipeline with available data from previously successful agents
3. WHEN the Analysis_Job completes with partial results, THE Frontend SHALL display available sections and mark failed sections with a clear "incomplete" indicator
4. THE Architecture_Report and Kiro_Spec SHALL include metadata indicating which agents completed successfully and which were skipped
