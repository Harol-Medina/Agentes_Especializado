# Guía E2E — Análisis de spring-petclinic

## Prerequisitos

- Docker Desktop corriendo
- Git instalado
- Conexión a internet (para clonar el repo y llamar a Bedrock)

## Opción A: E2E Completo con Docker (producción)

El stack completo: PostgreSQL + Backend (Spring Boot) + Analyzer (FastAPI) + Frontend (Next.js) + Nginx.

```bash
# 1. Build de todos los servicios
docker compose build

# 2. Levantar el stack
docker compose up -d

# 3. Esperar a que el backend esté healthy (~40s)
docker compose logs -f backend

# 4. Disparar análisis via API
curl -X POST http://localhost/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"repoUrl": "https://github.com/spring-projects/spring-petclinic"}'

# 5. Copiar el jobId del response y hacer polling
curl http://localhost/api/v1/jobs/{JOB_ID}

# 6. Ver logs del pipeline en tiempo real
docker compose logs -f analyzer

# 7. Bajar el stack
docker compose down
```

## Opción B: E2E Standalone (solo Analyzer, sin Docker)

Ejecuta solo el servicio analyzer directamente con Python. No requiere PostgreSQL ni backend.

```powershell
# 1. Ir al directorio del analyzer
cd apps/analyzer

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
$env:DATABASE_URL = "postgresql+asyncpg://x:x@localhost:5432/x"
$env:WEBHOOK_SECRET = "test_secret"
$env:AWS_ACCESS_KEY_ID = "<your-access-key-id>"
$env:AWS_SECRET_ACCESS_KEY = "<your-secret-access-key>"
$env:BEDROCK_MODEL_ID = "anthropic.claude-sonnet-4-5-20250929-v1:0"
$env:BEDROCK_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
$env:AWS_REGION = "us-east-1"

# 5. Ejecutar test E2E
python test_e2e_petclinic.py

# 6. Los resultados se guardan en e2e_results.json
```

## Qué esperar

### RepositoryAgent (~30-60s)
- Clona spring-petclinic (shallow, depth=1)
- Detecta: language=java, framework=spring-boot
- Parsea ~50-80 archivos .java con tree-sitter
- Construye grafo de dependencias (200+ nodos, 100+ edges)

### ArchitectureAgent (~10-20s)
- Envía resumen del grafo a Claude Sonnet 4.5
- Recibe: patrones detectados (MVC, Layered), layers, violations

### QualityAgent (~10-20s)
- Calcula métricas (complejidad, LOC, coupling)
- Envía a Claude para análisis de code smells
- Recibe: maintainability score, tech debt indicators, hotspots

### SecurityAgent (~10-20s)
- Identifica dependencias y archivos sensibles
- Envía a Claude para vulnerability assessment
- Recibe: risk score, vulnerabilities, recommendations

### DocumentationAgent (~10-20s)
- Combina project model + architecture report
- Genera: overview, module docs, getting started, API surface

### ModernizationAgent (~10-20s)
- Combina architecture + quality + security reports
- Genera: migration steps, priority order, risk assessment, quick wins

### KiroAgent (~10-20s)
- Genera un spec completo en formato Kiro (Requirements/Design/Tasks)
- Nivel "full" si tiene modernization_plan + architecture_report

### Total estimado: 2-4 minutos

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `AccessDeniedException` en Bedrock | Verifica que el modelo esté habilitado en la consola de Bedrock (Model Access) |
| `ThrottlingException` | El adapter hace retry automático (3x con backoff). Espera y reintenta |
| Clone falla | Verifica conexión a internet y que git esté instalado |
| "No parseable source files" | El repo no tiene archivos .java/.ts/.js. Usa spring-petclinic |

## Infraestructura AWS Creada

| Recurso | Valor |
|---------|-------|
| IAM User | `archaeologist-service` |
| Access Key ID | *(stored in .data/.env, never commit)* |
| Policy | `ArchaeologistBedrockAccess` |
| Modelos habilitados | Claude Sonnet 4.5, Titan Embed Text V2 |
| Región | us-east-1 |
