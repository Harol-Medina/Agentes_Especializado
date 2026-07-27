# Deployment Runbook — Software Archaeologist

Manual de despliegue para producción y diseño del pipeline CI/CD futuro.

---

## Estado Actual: Despliegue Manual

El despliegue actual se realiza ejecutando scripts secuenciales desde `apps/AWS/deploy/`. No hay pipeline automatizado — cada paso requiere intervención humana.

---

## 1. Pre-Deployment Checklist

Antes de cada despliegue, verificar:

| # | Check | Cómo verificar |
|---|---|---|
| 1 | Código compila localmente | `docker compose build` sin errores |
| 2 | Tests pasan | Backend: `./gradlew test`, Analyzer: `pytest` |
| 3 | `.data/.env.prod` actualizado | Revisar que las connection strings son correctas |
| 4 | RDS accesible | `psql -h <endpoint> -U archaeologist -c "SELECT 1"` |
| 5 | Bedrock models disponibles | `apps/AWS/bedrock/verify-models.sh` |
| 6 | Git limpio | `git status` — no hay cambios sin commit |
| 7 | Branch correcto | Confirmar que estás en `main` (o branch de release) |

---

## 2. Manual Deployment Steps

### 2.1 Deploy Database Changes (si hay migraciones nuevas)

```bash
cd apps/AWS/deploy
./02-run-migrations.sh
```

**Verificar**: Conectar a RDS y confirmar que la versión de Flyway es la esperada:
```sql
SELECT version, description, installed_on FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 1;
```

**Rollback si falla**: Flyway no soporta rollback automático. Si una migración falla a mitad:
1. Identificar el estado parcial con `\dt` y `flyway_schema_history`
2. Corregir manualmente en la DB
3. Ejecutar `flyway repair` para limpiar el historial
4. Corregir el script de migración y re-ejecutar

---

### 2.2 Deploy Backend

```bash
cd apps/AWS/deploy
./03-deploy-backend-eb.sh
```

**Duración**: 5-10 minutos (build Docker en EC2 + startup JVM)

**Verificar**:
```bash
curl http://<backend-eb-url>/actuator/health
# Esperado: {"status":"UP","components":{"db":{"status":"UP"},...}}
```

**Rollback**:
```bash
# Listar versiones anteriores
aws elasticbeanstalk describe-application-versions \
  --application-name archaeologist-backend \
  --query "ApplicationVersions[*].[VersionLabel,DateCreated]" \
  --output table

# Rollback a versión anterior
aws elasticbeanstalk update-environment \
  --application-name archaeologist-backend \
  --environment-name archaeologist-backend-prod \
  --version-label <VERSION_ANTERIOR>
```

---

### 2.3 Deploy Analyzer

```bash
cd apps/AWS/deploy
./04-deploy-analyzer-eb.sh
```

**Duración**: 5-10 minutos

**Verificar**:
```bash
curl http://<analyzer-eb-url>/health
# Esperado: {"status":"ok","service":"analyzer"}
```

**Rollback**: Mismo procedimiento que Backend con `archaeologist-analyzer`.

---

### 2.4 Deploy Frontend

```bash
cd apps/AWS/deploy
./05-deploy-frontend-amplify.sh
```

**O (si auto-deploy está configurado)**: Simplemente hacer push a `main`:
```bash
git push origin main
# Amplify detecta el push y dispara build automáticamente
```

**Duración**: 3-5 minutos (npm install + next build)

**Verificar**: Abrir la URL de Amplify en browser y confirmar que la página carga.

**Rollback**:
```bash
# En Amplify Console → App → Branch → Redeploy previous version
# O via CLI:
aws amplify start-job \
  --app-id <APP_ID> \
  --branch-name main \
  --job-type RELEASE \
  --job-reason "Rollback to previous version"
```

---

### 2.5 Post-Deploy Verification

```bash
cd apps/AWS/deploy
./06-smoke-test.sh <FRONTEND_URL> <BACKEND_URL> <ANALYZER_URL>
```

Verificaciones manuales adicionales:
1. Abrir frontend → enviar un repo → verificar que el análisis inicia
2. Esperar a que complete → verificar grafo, chat, reporte, export
3. Revisar logs: `docker compose logs -f` (local) o EB logs (prod)

---

## 3. Rollback Procedure (Resumen)

| Servicio | Método de Rollback | Tiempo |
|---|---|---|
| **Database** | Manual SQL fix + `flyway repair` | 10-30 min |
| **Backend (EB)** | `update-environment --version-label <prev>` | 5-10 min |
| **Analyzer (EB)** | `update-environment --version-label <prev>` | 5-10 min |
| **Frontend (Amplify)** | Redeploy previous version desde console | 3-5 min |

### Orden de Rollback

Si un deploy falla y necesitas revertir todo:

1. **Frontend primero** (menos impacto, cambios solo visuales)
2. **Analyzer** (si el pipeline de agentes falla)
3. **Backend** (si las APIs no responden)
4. **Database último** (solo si hay incompatibilidad de schema)

### Regla de Oro

> Si el backend requiere un schema nuevo (migración), despliega la DB **antes** del backend. Si necesitas rollback del backend, verifica que el schema anterior sigue siendo compatible.

---

## 4. Environment Differences (Dev vs Prod)

| Variable | Dev (Docker Compose) | Prod (AWS) |
|---|---|---|
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://db:5432/archaeologist` | `jdbc:postgresql://<rds-endpoint>:5432/archaeologist` |
| `SPRING_DATASOURCE_PASSWORD` | `archaeologist_secret` | Generado por `01-create-rds.sh` (secreto fuerte) |
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5432/archaeologist` | `postgresql+asyncpg://...@<rds-endpoint>:5432/archaeologist` |
| `WEBHOOK_SECRET` | `shared_webhook_secret` | Secreto fuerte generado |
| `WEBHOOK_BASE_URL` | `http://backend:8080` | `http://<backend-eb-url>` |
| `ANALYZER_BASE_URL` | `http://analyzer:8000` | `http://<analyzer-eb-url>` |
| `NEXT_PUBLIC_API_URL` | `/api` (nginx proxy) | `http://<backend-eb-url>/api` |
| `AWS_ACCESS_KEY_ID` | Mismo en ambos | Mismo en ambos |
| `AWS_SECRET_ACCESS_KEY` | Mismo en ambos | Mismo en ambos |
| `AWS_REGION` | `us-east-1` | `us-east-1` |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| `LOG_LEVEL` | `DEBUG` | `INFO` |
| **DB Instance** | Docker container (pgvector/pgvector:pg15) | RDS db.t3.medium |
| **Networking** | Docker network interno | VPC + Security Groups |
| **SSL/TLS** | No (localhost) | Pendiente (ACM + HTTPS) |
| **Rate Limiting** | nginx (5 req/min) | nginx (5 req/min) + Analyzer (20 req/min) |
| **Scaling** | Single instance | Single instance (EB SingleInstance mode) |

### Diferencias de Comportamiento

| Aspecto | Dev | Prod |
|---|---|---|
| Repos clonados | `/tmp/repos` (volumen Docker) | `/tmp/repos` (ephemeral EB storage) |
| Persistencia repos | Hasta `docker compose down` | 24h lifecycle (S3) |
| Logs | `docker compose logs` | CloudWatch Logs |
| Health checks | Docker healthcheck | EB enhanced health |
| Backups | Ninguno | RDS automated backup (7 días) |
| DNS | `localhost:80` | `*.elasticbeanstalk.com` / `*.amplifyapp.com` |

---

## 5. Future CI/CD Pipeline (Diseño)

### Target Flow

```
┌──────────────┐     ┌─────────────────────────────────────────────────────────┐
│  Developer   │     │                  GitHub Actions                          │
│              │     │                                                          │
│  git push    │────►│  ┌─────────┐   ┌──────────┐   ┌──────────┐            │
│  to main     │     │  │  Test   │──►│  Build   │──►│  Deploy  │            │
│              │     │  │         │   │  Images  │   │          │            │
└──────────────┘     │  └─────────┘   └──────────┘   └──────────┘            │
                     │       │              │               │                  │
                     │       ▼              ▼               ▼                  │
                     │  ┌─────────┐   ┌──────────┐   ┌──────────────────┐    │
                     │  │ Gradle  │   │   ECR    │   │ EB (Backend)     │    │
                     │  │  test   │   │  Push    │   │ EB (Analyzer)    │    │
                     │  │ pytest  │   │  Images  │   │ Amplify (auto)   │    │
                     │  │  lint   │   │          │   │                  │    │
                     │  └─────────┘   └──────────┘   └──────────────────┘    │
                     │                                                          │
                     └─────────────────────────────────────────────────────────┘
```

### Pipeline Stages

#### Stage 1: Test (2-3 min)

```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    # Backend tests
    - uses: actions/setup-java@v4
      with: { java-version: '21' }
    - run: cd apps/backend && ./gradlew test
    
    # Analyzer tests
    - uses: actions/setup-python@v5
      with: { python-version: '3.11' }
    - run: cd apps/analyzer && pip install -r requirements.txt && pytest
    
    # Frontend lint
    - uses: actions/setup-node@v4
      with: { node-version: '20' }
    - run: cd apps/frontend && npm ci && npm run lint
```

#### Stage 2: Build + Push to ECR (5-7 min)

```yaml
build:
  needs: test
  runs-on: ubuntu-latest
  steps:
    - uses: aws-actions/configure-aws-credentials@v4
    - uses: aws-actions/amazon-ecr-login@v2
    
    - name: Build and push backend
      run: |
        docker build -f docker/backend/Dockerfile -t $ECR_REPO/backend:$SHA .
        docker push $ECR_REPO/backend:$SHA
    
    - name: Build and push analyzer
      run: |
        docker build -f docker/analyzer/Dockerfile -t $ECR_REPO/analyzer:$SHA .
        docker push $ECR_REPO/analyzer:$SHA
```

#### Stage 3: Deploy (5-10 min)

```yaml
deploy:
  needs: build
  runs-on: ubuntu-latest
  steps:
    - name: Deploy Backend to EB
      run: |
        aws elasticbeanstalk update-environment \
          --environment-name archaeologist-backend-prod \
          --version-label backend-$SHA
    
    - name: Deploy Analyzer to EB
      run: |
        aws elasticbeanstalk update-environment \
          --environment-name archaeologist-analyzer-prod \
          --version-label analyzer-$SHA
    
    - name: Wait for healthy
      run: |
        aws elasticbeanstalk wait environment-updated \
          --environment-name archaeologist-backend-prod
        aws elasticbeanstalk wait environment-updated \
          --environment-name archaeologist-analyzer-prod
```

#### Stage 4: Smoke Test (2-3 min)

```yaml
smoke-test:
  needs: deploy
  runs-on: ubuntu-latest
  steps:
    - name: Verify health endpoints
      run: |
        curl -f http://$BACKEND_URL/actuator/health
        curl -f http://$ANALYZER_URL/health
    
    - name: Run E2E smoke test
      run: ./apps/AWS/deploy/06-smoke-test.sh $FRONTEND_URL $BACKEND_URL $ANALYZER_URL
```

### Frontend (Amplify Auto-Deploy)

Amplify auto-deploys on push to `main` — no GitHub Actions step needed. The Amplify webhook fires independently of the backend pipeline.

### Secrets Required in GitHub Actions

| Secret | Source |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM CI/CD user (separate from app user) |
| `AWS_SECRET_ACCESS_KEY` | IAM CI/CD user |
| `AWS_REGION` | `us-east-1` |
| `ECR_REPOSITORY` | ECR repo URI |
| `BACKEND_URL` | EB environment CNAME |
| `ANALYZER_URL` | EB environment CNAME |
| `FRONTEND_URL` | Amplify app URL |

### Migration Strategy in CI/CD

Las migraciones de DB se manejan de forma especial:

1. **Flyway en startup**: El backend aplica migraciones automáticamente al arrancar.
2. **Forward-only**: Las migraciones deben ser backward-compatible (additive changes).
3. **Breaking changes**: Requieren deploy en 2 fases:
   - Fase 1: Deploy migración que agrega nueva estructura (sin romper la anterior)
   - Fase 2: Deploy código que usa la nueva estructura
   - Fase 3: (siguiente sprint) Migración que elimina estructura antigua

---

## 6. Monitoring y Alertas (Futuro)

### CloudWatch Metrics Recomendadas

| Métrica | Threshold | Acción |
|---|---|---|
| Backend HealthStatus | != Green | Alerta + investigar |
| Analyzer HealthStatus | != Green | Alerta + investigar |
| RDS CPU Utilization | > 80% | Scale up instance class |
| RDS Free Storage | < 2GB | Extend storage |
| Bedrock ThrottlingExceptions | > 5/min | Revisar rate limits |
| EB Environment Status | Degraded/Severe | Auto-rollback |

### Log Groups

| Log Group | Fuente |
|---|---|
| `/archaeologist/backend` | Spring Boot logs |
| `/archaeologist/analyzer` | FastAPI logs |
| `/archaeologist/nginx` | Access + error logs |

---

## 7. Disaster Recovery

### Escenario: RDS corruption/failure

1. RDS tiene backup automático (7 días retención)
2. Restaurar desde snapshot: `aws rds restore-db-instance-from-db-snapshot`
3. Actualizar connection strings en EB environments
4. Re-deploy Backend y Analyzer

### Escenario: EB instance failure

EB automatically replaces unhealthy instances (single instance mode). Si el environment completo falla:
1. Terminate environment
2. Re-crear con el script de deploy
3. La versión anterior en S3 se reutiliza

### Escenario: Región no disponible

No hay multi-región configurada para MVP. Recovery manual:
1. Restaurar RDS snapshot en otra región
2. Re-crear buckets S3
3. Re-desplegar EB y Amplify en nueva región
4. Actualizar DNS

---

## 8. Contacto y Escalación

| Nivel | Quién | Cuándo |
|---|---|---|
| L1 | Developer on-call | Health check falla, errores 5xx |
| L2 | Team lead | Rollback necesario, pérdida de datos |
| L3 | AWS Support | Servicio AWS degradado, problemas de cuenta |
