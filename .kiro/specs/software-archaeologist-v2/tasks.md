# Implementation Plan: Software Archaeologist v2 (Full Vision)

## Overview

Implementación de las funcionalidades post-MVP para llevar el proyecto del estado actual (MVP funcional end-to-end) al 100% de la visión. Se prioriza: deployment → documentación → features deseables → features WOW. Cada fase es independiente y entregable.

## Tasks

- [ ] 1. Production Deployment
  - [ ] 1.1 Deploy database to Amazon RDS
    - Create RDS PostgreSQL 15 instance (db.t3.medium) with pgvector
    - Configure security group: allow inbound from EB instances only
    - Run Flyway migrations against production DB
    - Update `.data/.env.prod` with RDS endpoint and credentials
    - _Requirements: V2-1.3_

  - [ ] 1.2 Deploy Backend to Elastic Beanstalk
    - Create EB environment with Docker platform (single instance)
    - Build and upload Backend Docker image
    - Configure environment variables from `.data/.env.prod`
    - Verify health check endpoint responds
    - _Requirements: V2-1.2_

  - [ ] 1.3 Deploy Analyzer to Elastic Beanstalk
    - Create EB environment with Docker platform (single instance)
    - Build and upload Analyzer Docker image
    - Configure environment variables (RDS, Bedrock, S3)
    - Verify `/health` endpoint responds
    - _Requirements: V2-1.2_

  - [ ] 1.4 Deploy Frontend to AWS Amplify
    - Connect Git repository to Amplify
    - Configure build settings for Next.js 14+ (App Router)
    - Set `NEXT_PUBLIC_API_URL` to point to Backend EB URL
    - Verify SSR pages render correctly
    - _Requirements: V2-1.1_

  - [ ] 1.5 End-to-end production verification
    - Submit a test repository URL through the deployed Frontend
    - Verify the complete flow: submission → progress → graph → chat → report → export
    - Verify S3 repos bucket receives cloned repos and lifecycle deletes after 24h
    - _Requirements: V2-1.4, V2-1.5_

- [ ] 2. Documentation
  - [ ] 2.1 Create apps/backend/README.md
    - Document: purpose (API gateway + orchestrator), tech stack (Java 21, Spring Boot 3.x), project structure, endpoints list, environment variables consumed, how to run locally (Gradle), testing (JUnit + Mockito)
    - Include troubleshooting: common Flyway issues, WebClient timeouts
    - _Requirements: V2-2.1, V2-2.4_

  - [ ] 2.2 Create apps/frontend/README.md
    - Document: purpose (web UI), tech stack (Next.js 14, React 18, Tailwind, React Flow, shadcn/ui), project structure (App Router), design system reference, environment variables, how to run locally (npm run dev), component catalogue
    - Include troubleshooting: SSE connection drops, React Flow rendering
    - _Requirements: V2-2.1, V2-2.4_

  - [ ] 2.3 Create apps/analyzer/README.md
    - Document: purpose (AI analysis engine), tech stack (Python 3.11, FastAPI, Tree-sitter, asyncpg), project structure (hexagonal), agent pipeline overview, endpoints, environment variables, how to run locally (uvicorn), testing (pytest)
    - Include troubleshooting: Bedrock throttling, Tree-sitter grammar installation, large repo handling
    - _Requirements: V2-2.1, V2-2.4_

  - [ ] 2.4 Create apps/AWS/README.md — Full reproduction guide
    - Step-by-step from zero: prerequisites, IAM user, S3, RDS, Bedrock, EB, Amplify
    - Each step with: command, what it does, expected output, verification
    - Include screenshots placeholders for console steps (Bedrock model access)
    - Environment variable mapping table (local name → what to put in prod)
    - Verification checklist at the end
    - _Requirements: V2-2.2, V2-2.3_

  - [ ] 2.5 Create root README.md (professional)
    - Project description (what it does, why it matters)
    - Architecture diagram (ASCII from design.md)
    - Feature list with status badges (Done/In Progress/Planned)
    - Tech stack table
    - Quick start: `docker compose build` + `docker compose up` + open localhost
    - "Developed with Kiro" section (specs, steering, agents, hooks, MCP usage)
    - Screenshots / demo video link
    - Link to deployed app
    - Contributing guide
    - License
    - _Requirements: V2-3.1, V2-3.2, V2-3.3, V2-3.4_

  - [ ] 2.6 Create docs/deployment-runbook.md
    - Manual deployment steps (current state)
    - Future CI/CD pipeline design (diagram + description)
    - Rollback procedure
    - Environment differences table (dev vs prod)
    - _Requirements: V2-11.1, V2-11.2, V2-11.3, V2-11.4_

- [ ] 3. Checkpoint — Deployed + Documented
  - Verify app is accessible at production URL
  - Verify all 4 app READMEs are complete and accurate
  - Verify root README renders correctly on GitHub/GitLab

- [ ] 4. Desirable Features — Dead Code Detection
  - [ ] 4.1 Implement DeadCodeDetector in Quality_Agent
    - Create `src/agents/dead_code_detector.py` with graph-based detection
    - Detect: unimported files, un-instantiated classes, unreferenced functions, unused exports
    - Assign confidence levels (high/medium/low) based on reference patterns
    - Handle framework special cases (Spring `@Component`, Angular `@Injectable`)
    - Integrate into Quality_Agent output as `dead_code` section
    - _Requirements: V2-4.1, V2-4.2_

  - [ ] 4.2 Display dead code results in Frontend
    - Add "Dead Code" tab/section to Architecture Report view
    - Display candidates with: file path, type, confidence badge, reason
    - Filter by confidence level
    - _Requirements: V2-4.3_

- [ ] 5. Desirable Features — Semgrep Security
  - [ ] 5.1 Integrate Semgrep into Security_Agent
    - Add `semgrep` to Analyzer Dockerfile
    - Create `src/agents/semgrep_scanner.py` with OWASP ruleset selection by language
    - Parse JSON output into structured findings
    - Add remediation suggestions via Bedrock
    - _Requirements: V2-5.1, V2-5.2_

  - [ ] 5.2 Display security findings in Frontend
    - Add "Security" section to Architecture Report with severity badges
    - Display: finding description, file location, severity, remediation
    - Sort by severity (Critical → Low)
    - _Requirements: V2-5.3_

- [ ] 6. Desirable Features — Modernization Roadmap
  - [ ] 6.1 Generate sprint-organized roadmap in Modernization_Agent
    - Produce table: Sprint, Action, Justification, Estimated Effort
    - Priority order: dead code → security → deps → decoupling → refactor
    - Include effort estimates (hours/story points)
    - _Requirements: V2-6.1, V2-6.2_

  - [ ] 6.2 Display roadmap in Frontend + export in Kiro Spec
    - Add "Roadmap" tab with interactive sprint-grouped table
    - Include roadmap as Tasks in Kiro Spec export (grouped by sprint)
    - _Requirements: V2-6.3, V2-6.4_

- [ ] 7. Checkpoint — Desirable Features Complete
  - Verify dead code detection works on test repo
  - Verify Semgrep runs and produces findings
  - Verify roadmap generates coherent sprint plan

- [ ] 8. WOW Features — Version Comparison
  - [ ] 8.1 Implement version comparison endpoint
    - Add `POST /api/v1/compare` accepting two git refs
    - Analyzer clones both refs, builds Project_Model for each, computes diff
    - Diff includes: module additions/removals, dependency changes, complexity delta
    - _Requirements: V2-7.1, V2-7.2_

  - [ ] 8.2 Display comparison in Frontend
    - Create comparison view with before/after metrics
    - Highlight: added modules (green), removed (red), changed (amber)
    - Show dependency diff as edge additions/removals on graph
    - _Requirements: V2-7.3_

- [ ] 9. WOW Features — Git Timeline
  - [ ] 9.1 Implement Git history analysis
    - Parse Git log for: commit dates, files changed, LOC per commit
    - Compute: LOC growth per module over time, change frequency per file
    - Identify hotspots (top 10 most-changed files = potential instability)
    - _Requirements: V2-8.1_

  - [ ] 9.2 Display timeline chart in Frontend
    - Line chart showing LOC growth by module over time
    - Heatmap of change frequency (hotspots)
    - Interactive: hover for commit details
    - _Requirements: V2-8.2, V2-8.3_

- [ ] 10. WOW Features — C4 Diagrams
  - [ ] 10.1 Generate C4 Mermaid code in Documentation_Agent
    - Context diagram: system + external actors
    - Container diagram: frontend, backend, analyzer, DB, Bedrock
    - Component diagram: modules within each container
    - Output as Mermaid syntax stored in Architecture_Report
    - _Requirements: V2-9.1_

  - [ ] 10.2 Render Mermaid diagrams in Frontend
    - Install mermaid library
    - Render diagrams inline in Architecture Report
    - Add export buttons (PNG, SVG)
    - _Requirements: V2-9.2, V2-9.3_

- [ ] 11. WOW Features — Open in Kiro
  - [ ] 11.1 Generate full .kiro package in Kiro_Agent
    - Generate: `specs/modernization/requirements.md`, `design.md`, `tasks.md`
    - Generate suggested hooks JSON for post-modernization automation
    - Package as downloadable zip
    - _Requirements: V2-10.1, V2-10.2_

  - [ ] 11.2 Add "Download .kiro Package" button in Frontend
    - Button triggers zip download from `GET /api/v1/projects/{id}/kiro-package`
    - Zip contains complete `.kiro/` structure importable into a Kiro workspace
    - _Requirements: V2-10.3, V2-10.4_

- [ ] 12. Final Checkpoint — 100% Vision Complete
  - Full end-to-end verification of all features
  - Demo video recording
  - Final README update with all screenshots and links

## Notes

- This spec assumes the MVP (spec-v1) is fully implemented
- Phases are independent: each can be delivered separately
- Priority order: 1 (Deploy) → 2 (Docs) → 3 (Checkpoint) → 4-6 (Desirable) → 8-11 (WOW)
- Deploy + Docs should be completed first to have a demonstrable product
- WOW features are stretch goals — implement based on available time
- All code follows the same Docker conventions: `docker compose build` + `up` must work with new features included

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4"] },
    { "id": 2, "tasks": ["1.5", "2.1", "2.2", "2.3", "2.4"] },
    { "id": 3, "tasks": ["2.5", "2.6"] },
    { "id": 4, "tasks": ["4.1", "5.1", "6.1"] },
    { "id": 5, "tasks": ["4.2", "5.2", "6.2"] },
    { "id": 6, "tasks": ["8.1", "9.1", "10.1", "11.1"] },
    { "id": 7, "tasks": ["8.2", "9.2", "10.2", "11.2"] }
  ]
}
```
