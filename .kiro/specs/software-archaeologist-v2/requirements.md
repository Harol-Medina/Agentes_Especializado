# Requirements Document — Software Archaeologist v2 (Full Vision)

## Introduction

Este spec cubre las funcionalidades que van **más allá del MVP** para alcanzar el 100% de la visión descrita en `docs/initial.md`. Incluye: deployment a producción con S3, documentación de las 4 apps, paso a paso de AWS, features deseables (código muerto, seguridad Semgrep, roadmap), features WOW (comparación de versiones, timeline Git, diagramas C4, Open in Kiro), y README profesional con la narrativa de cómo Kiro ayudó al desarrollo.

## Glossary (extensiones al MVP)

- **Dead_Code_Detector**: Módulo que identifica archivos, clases y métodos no referenciados en el proyecto
- **Semgrep_Scanner**: Integración con Semgrep para análisis de seguridad OWASP Top 10
- **Version_Comparator**: Feature que permite comparar dos commits/ramas mostrando cambios arquitectónicos
- **Git_Timeline**: Visualización de la evolución del proyecto a lo largo del historial Git
- **C4_Generator**: Generador automático de diagramas C4 (Context, Container, Component) usando Mermaid
- **Open_In_Kiro**: Feature que genera toda la estructura (.kiro/specs, tasks, hooks) para importar en Kiro

---

## Requirements

### Requirement V2-1: Production Deployment via S3 + AWS

**User Story:** As a platform operator, I want to deploy the application to AWS using S3 for static assets and Elastic Beanstalk for services, so that the platform is accessible públicamente.

#### Acceptance Criteria

1. THE Frontend SHALL be deployed to AWS Amplify with auto-deploy from the Git repository
2. THE Backend and Analyzer SHALL be deployed to Elastic Beanstalk using Docker platform (single instance for v1)
3. THE Database SHALL be hosted on Amazon RDS PostgreSQL 15 with pgvector extension enabled
4. THE Platform SHALL use the S3 buckets (`archaeologist-repos-prod`, `archaeologist-reports-prod`) for repo storage and report persistence
5. THE deployment process SHALL be documented step-by-step in `docs/aws-deployment-guide.md`
6. A future CI/CD pipeline SHALL be defined (design only, implementation deferred) that deploys on merge to `main`

### Requirement V2-2: Application Documentation

**User Story:** As a developer joining the project, I want comprehensive documentation for each of the 4 apps (analyzer, AWS, frontend, backend), so that I can understand, run, and contribute without tribal knowledge.

#### Acceptance Criteria

1. Each app (`apps/backend/`, `apps/frontend/`, `apps/analyzer/`, `apps/AWS/`) SHALL have a `README.md` explaining: purpose, tech stack, local development, environment variables consumed, endpoints/commands, and testing
2. `apps/AWS/README.md` SHALL include a step-by-step reproduction guide of everything configured in AWS (IAM user, S3 buckets, Bedrock model access, RDS setup)
3. The documentation SHALL be sufficient for a new developer to replicate the AWS setup from scratch in a new account
4. Each README SHALL include a "Troubleshooting" section with common issues and solutions found during development

### Requirement V2-3: Project README with Kiro Development Narrative

**User Story:** As a hackathon judge or evaluator, I want a professional README that explains what the app does and how Kiro was used in the development process, so that I can evaluate the project's quality and the role of AI-assisted development.

#### Acceptance Criteria

1. THE root `README.md` SHALL contain: project description, architecture diagram (ASCII), feature list, tech stack, quick start (`docker compose build` + `up`), screenshots/demo link
2. THE README SHALL include a section "Developed with Kiro" describing: use of Specs (requirements → design → tasks), use of Steering (project structure, design system, coding standards), use of Agents (specialized sub-agents for review, architecture), use of Hooks (verification loops, linting)
3. THE README SHALL include links to the deployed application and demo video
4. THE README SHALL be bilingual (Spanish primary, English summary)

### Requirement V2-4: Dead Code Detection (Desirable)

**User Story:** As a Visitor, I want the system to detect unused code in the analyzed repository, so that I can identify candidates for safe removal.

#### Acceptance Criteria

1. THE Quality_Agent SHALL detect: files not imported by any other file, classes not instantiated or extended, methods/functions without external references, exported components never imported
2. THE Architecture_Report SHALL include a "Dead Code" section listing candidates with confidence level (high/medium/low) and file location
3. THE Frontend SHALL display dead code results with filtering by confidence level

### Requirement V2-5: Security Report with Semgrep (Desirable)

**User Story:** As a Visitor, I want a security analysis of the repository using industry-standard tools, so that I can identify vulnerabilities before modernization.

#### Acceptance Criteria

1. THE Security_Agent SHALL integrate Semgrep with OWASP Top 10 rulesets for the detected language
2. THE Security_Agent SHALL detect: exposed secrets (regex + entropy), dependencies with known CVEs, insecure configurations
3. THE Architecture_Report SHALL include a "Security" section with findings categorized by severity (Critical, High, Medium, Low)
4. THE Frontend SHALL display security findings with severity badges and remediation suggestions

### Requirement V2-6: Modernization Roadmap (Desirable)

**User Story:** As a Visitor, I want a prioritized modernization roadmap organized by sprints, so that I have a concrete plan to follow.

#### Acceptance Criteria

1. THE Modernization_Agent SHALL generate a roadmap table with columns: Sprint, Action, Justification, Estimated Effort
2. THE roadmap SHALL prioritize: dead code removal → security fixes → dependency updates → module decoupling → architecture refactoring
3. THE Frontend SHALL display the roadmap as an interactive table with sprint grouping
4. THE Kiro_Spec export SHALL include the roadmap as Tasks organized by sprint

### Requirement V2-7: Version Comparison (WOW)

**User Story:** As a Visitor, I want to compare two commits or branches of the same repository, so that I can understand architectural evolution over time.

#### Acceptance Criteria

1. THE Platform SHALL accept two git refs (commits, branches, tags) for comparison
2. THE Analyzer SHALL compute diffs in: module structure (added/removed), new external dependencies, complexity delta per module, technical debt delta
3. THE Frontend SHALL display a comparison view with before/after metrics and highlighted changes

### Requirement V2-8: Git Timeline (WOW)

**User Story:** As a Visitor, I want to see the evolution of the project over time based on Git history, so that I can identify growth patterns and hotspots.

#### Acceptance Criteria

1. THE Analyzer SHALL analyze Git log to compute: LOC growth by module over time, dependency growth, change frequency hotspots (most modified files/modules)
2. THE Frontend SHALL display a timeline chart showing evolution metrics
3. THE Frontend SHALL highlight hotspot modules (high change frequency = potential instability)

### Requirement V2-9: C4 Diagrams (WOW)

**User Story:** As a Visitor, I want automatically generated C4 architecture diagrams, so that I can visualize the system at different levels of abstraction.

#### Acceptance Criteria

1. THE Documentation_Agent SHALL generate Mermaid code for: Context Diagram (system + external actors), Container Diagram (apps + stores + communication), Component Diagram (modules within each container)
2. THE Frontend SHALL render Mermaid diagrams inline in the Architecture Report
3. THE diagrams SHALL be exportable as PNG/SVG

### Requirement V2-10: Open in Kiro (WOW)

**User Story:** As a Visitor, I want a one-click action that generates the complete .kiro/ structure for importing into a Kiro workspace, so that I can immediately start modernization work.

#### Acceptance Criteria

1. THE Kiro_Agent SHALL generate: `requirements.md`, `design.md`, `tasks.md` (full spec structure)
2. THE Kiro_Agent SHALL generate suggested Hooks: `PostFileSave` for linting modernized code, `PostTaskExec` for running tests after each task
3. THE Frontend SHALL provide a "Download .kiro Package" button that exports a zip containing the complete `.kiro/specs/` structure
4. THE exported structure SHALL be importable directly into a Kiro workspace without modification

### Requirement V2-11: Clean Deploy Pipeline (Future)

**User Story:** As a platform operator, I want a documented deployment strategy that can be automated in the future, so that deployments are reproducible and low-risk.

#### Acceptance Criteria

1. THE documentation SHALL describe the target CI/CD flow: push to main → build Docker images → push to ECR → deploy to EB
2. THE documentation SHALL include rollback procedure
3. THE documentation SHALL specify which environment variables differ between dev and prod
4. THE Platform SHALL provide a `docs/deployment-runbook.md` with manual deployment steps usable today
