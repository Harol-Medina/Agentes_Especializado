# AWS — Software Archaeologist

Guía completa de reproducción de la infraestructura AWS desde cero.

---

## Propósito

Este directorio contiene todos los scripts y configuraciones necesarios para:

- Crear un usuario IAM con principio de mínimo privilegio
- Configurar buckets S3 con lifecycle policies
- Crear una instancia RDS PostgreSQL 15 con pgvector
- Habilitar modelos en Amazon Bedrock
- Desplegar Backend y Analyzer en Elastic Beanstalk (Docker)
- Desplegar Frontend en AWS Amplify
- Validar el despliegue end-to-end

---

## Estructura del Directorio

```
apps/AWS/
├── iam/
│   ├── setup.sh                    # Crea usuario IAM + policy + access keys
│   ├── policy-minimal.json         # Policy document (mínimo privilegio)
│   └── verify-permissions.sh       # Valida permisos ALLOW/DENY
├── s3/
│   └── create-buckets.sh           # Crea buckets repos + reports con lifecycle
├── bedrock/
│   └── verify-models.sh            # Verifica acceso a modelos Bedrock
└── deploy/
    ├── 01-create-rds.sh            # RDS PostgreSQL 15 + pgvector
    ├── 02-run-migrations.sh        # Flyway migrations contra RDS
    ├── 03-deploy-backend-eb.sh     # Backend → Elastic Beanstalk
    ├── 04-deploy-analyzer-eb.sh    # Analyzer → Elastic Beanstalk
    ├── 05-deploy-frontend-amplify.sh # Frontend → AWS Amplify
    ├── 06-smoke-test.sh            # Validación E2E en producción
    ├── amplify/                    # Configuración de build Amplify
    └── eb/                         # Dockerfiles específicos para EB
```

---

## Prerequisitos

Antes de empezar, necesitas:

| Recurso | Detalles |
|---|---|
| Cuenta AWS | Con billing habilitado |
| AWS CLI v2 | Instalado y configurado (`aws configure`) |
| Permisos del caller | IAM admin o permisos: `iam:*`, `s3:*`, `rds:*`, `elasticbeanstalk:*`, `amplify:*` |
| Docker | Instalado y corriendo (para builds EB) |
| psql | PostgreSQL client (para verificar conectividad a RDS) |
| Git | Instalado |
| Repositorio en GitHub/GitLab | Push del código al remoto (para Amplify) |
| GitHub PAT | Token con scope `repo` (para Amplify Git connection) |

---

## Paso a Paso: Setup Completo

### Paso 1: Crear Usuario IAM (Programmatic Access)

**Script**: `iam/setup.sh`

```bash
cd apps/AWS/iam
chmod +x setup.sh
./setup.sh
```

**Qué hace**:
1. Crea usuario `kiro-archaeologist` (sin acceso a consola)
2. Crea policy `KiroArchaeologistMinimalPolicy` desde `policy-minimal.json`
3. Adjunta la policy al usuario
4. Genera access keys (mostradas UNA sola vez)

**Output esperado**:
```
=== Software Archaeologist — IAM Setup ===
Account : 123456789012
Region  : us-east-1
User    : kiro-archaeologist

[1/4] Creating IAM user...
[2/4] Creating customer-managed policy...
      Policy ARN: arn:aws:iam::123456789012:policy/KiroArchaeologistMinimalPolicy
[3/4] Attaching policy to user...
[4/4] Creating access key...

AccessKeyId     : AKIA...
SecretAccessKey  : wJal...

=== Setup Complete ===
```

**Acción requerida**: Copiar `AccessKeyId` y `SecretAccessKey` inmediatamente a tu secrets manager. Guardar en `.data/.env`:

```env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJal...
```

**Verificación**:

```bash
chmod +x verify-permissions.sh
./verify-permissions.sh
# Debe mostrar: All checks passed (✅ ALLOW y ✅ DENY)
```

### Permisos Otorgados (Policy)

| Acción | Scope | Propósito |
|---|---|---|
| `bedrock:InvokeModel` | Claude Sonnet + Titan Embed | Razonamiento + embeddings |
| `bedrock:InvokeModelWithResponseStream` | Claude Sonnet | Streaming de respuestas |
| `s3:PutObject/GetObject/DeleteObject` | `archaeologist-repos-*/*`, `archaeologist-reports-*/*` | Repos y reportes |
| `s3:ListBucket` | `archaeologist-repos-*`, `archaeologist-reports-*` | Listar contenido |
| `lambda:InvokeFunction` | `archaeologist-*` | Post-procesamiento |
| `logs:Create*/PutLogEvents` | `/archaeologist/*` | CloudWatch Logs |

### Permisos Denegados (Blast Radius Control)

- `iam:*` — no puede escalar privilegios
- `ec2:*` — no puede crear compute
- `rds:*` — no puede tocar bases de datos
- `s3:CreateBucket/DeleteBucket` — no puede crear/destruir buckets

---

### Paso 2: Crear Buckets S3

**Script**: `s3/create-buckets.sh`

```bash
cd apps/AWS/s3
chmod +x create-buckets.sh
./create-buckets.sh
```

**Qué hace**:
1. Crea bucket `archaeologist-repos-prod` (temporales, 24h lifecycle)
2. Crea bucket `archaeologist-reports-prod` (persistentes)
3. Bloquea todo acceso público en ambos
4. Aplica lifecycle policy de 24h al bucket de repos

**Output esperado**:
```
[1/6] Creating bucket 'archaeologist-repos-prod'...
[2/6] Blocking public access...
[3/6] Applying 24-hour lifecycle deletion policy...
[4/6] Creating bucket 'archaeologist-reports-prod'...
[5/6] Blocking public access...
[6/6] Verifying bucket configuration...

=== S3 Setup Complete ===
```

**Verificación**:
```bash
aws s3 ls | grep archaeologist
# Debe mostrar ambos buckets
```

| Bucket | Lifecycle | Propósito |
|---|---|---|
| `archaeologist-repos-prod` | 24h auto-delete | Repos clonados temporales |
| `archaeologist-reports-prod` | Sin auto-delete | Reportes y Kiro Specs |

---

### Paso 3: Habilitar Modelos en Bedrock

**Script**: `bedrock/verify-models.sh`

```bash
cd apps/AWS/bedrock
chmod +x verify-models.sh
./verify-models.sh
```

**Modelos requeridos**:

| Modelo | Provider | Model ID | Uso |
|---|---|---|---|
| Claude Sonnet | Anthropic | `anthropic.claude-3-sonnet-20240229-v1:0` | Razonamiento de agentes + chat RAG |
| Titan Embeddings V2 | Amazon | `amazon.titan-embed-text-v2:0` | Generación de embeddings |

**Si los modelos NO están disponibles**:

1. Ir a **AWS Console** → **Amazon Bedrock** → **Model Access**
   - URL directa: `https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess`
2. Click **"Manage model access"**
3. Buscar y habilitar:
   - **Anthropic → Claude 3 Sonnet** (requiere aceptar términos)
   - **Amazon → Titan Text Embeddings V2** (aprobación automática)
4. Click **"Request model access"**
5. Esperar aprobación (Amazon: inmediato, Anthropic: 1-5 minutos)
6. Re-ejecutar `verify-models.sh`

**Output esperado (éxito)**:
```
  anthropic.claude-3-sonnet-20240229-v1:0                 ✅ Available
  amazon.titan-embed-text-v2:0                            ✅ Available

  Results: 2/2 models available
  ✅ All required models are available in us-east-1.
```

---

### Paso 4: Crear RDS PostgreSQL 15

**Script**: `deploy/01-create-rds.sh`

```bash
cd apps/AWS/deploy
chmod +x 01-create-rds.sh

# Opcional: definir password (si no se define, se genera uno aleatorio)
export DB_PASSWORD="tu_password_seguro_aqui"

./01-create-rds.sh
```

**Qué hace**:
1. Crea parameter group con `pg_stat_statements`
2. Crea security group (TCP 5432, inicialmente desde 0.0.0.0/0)
3. Crea instancia RDS `archaeologist-db` (db.t3.medium, 20GB gp3, single-AZ)
4. Espera a que esté disponible (5-10 minutos)
5. Habilita extensión `pgvector`
6. Imprime connection strings

**Output esperado**:
```
[4/6] Creating RDS instance 'archaeologist-db'...
      This may take 5-10 minutes...
[5/6] Waiting for instance to become available...
      Instance is now available!
      Endpoint: archaeologist-db.xxxx.us-east-1.rds.amazonaws.com:5432
[6/6] Enabling pgvector extension...
      pgvector extension enabled.

Connection strings for .data/.env.prod:
  SPRING_DATASOURCE_URL=jdbc:postgresql://archaeologist-db.xxxx.us-east-1.rds.amazonaws.com:5432/archaeologist
  DATABASE_URL=postgresql+asyncpg://archaeologist:PASSWORD@archaeologist-db.xxxx.us-east-1.rds.amazonaws.com:5432/archaeologist
```

**Acción requerida**: Guardar las connection strings en `.data/.env.prod`:

```env
SPRING_DATASOURCE_URL=jdbc:postgresql://archaeologist-db.xxxx.us-east-1.rds.amazonaws.com:5432/archaeologist
SPRING_DATASOURCE_USERNAME=archaeologist
SPRING_DATASOURCE_PASSWORD=<password_generado>
DATABASE_URL=postgresql+asyncpg://archaeologist:<password>@archaeologist-db.xxxx.us-east-1.rds.amazonaws.com:5432/archaeologist
```

**Especificaciones de la instancia**:

| Propiedad | Valor |
|---|---|
| Identifier | `archaeologist-db` |
| Engine | PostgreSQL 15 |
| Instance Class | db.t3.medium (2 vCPU, 4GB RAM) |
| Storage | 20GB gp3 (3000 IOPS) |
| Multi-AZ | No (single-AZ para MVP) |
| Backup | 7 días retención |
| Encryption | SSE habilitado (KMS default) |
| Public access | No |
| Extension | pgvector |

---

### Paso 5: Ejecutar Migraciones

**Script**: `deploy/02-run-migrations.sh`

```bash
chmod +x 02-run-migrations.sh
./02-run-migrations.sh
```

**Qué hace**:
1. Valida que `.data/.env.prod` existe y tiene las connection strings
2. Verifica conectividad a la DB via psql
3. Build del Docker image del backend
4. Ejecuta Spring Boot en modo "migrate-only" (`--spring.main.web-application-type=none`)
5. Flyway aplica `V1__initial_schema.sql`

**Tablas creadas**:
- `analysis_jobs`
- `projects`
- `graph_nodes` / `graph_edges`
- `agent_results`
- `code_embeddings` (con índice pgvector)
- `architecture_reports`
- `kiro_specs`
- `flyway_schema_history`

**Verificación**:
```bash
PGPASSWORD=... psql -h <rds-endpoint> -U archaeologist -d archaeologist -c '\dt'
```

---

### Paso 6: Deploy Backend → Elastic Beanstalk

**Script**: `deploy/03-deploy-backend-eb.sh`

```bash
chmod +x 03-deploy-backend-eb.sh
./03-deploy-backend-eb.sh
```

**Qué hace**:
1. Crea EB application `archaeologist-backend`
2. Prepara source bundle (Dockerfile + backend source)
3. Sube zip a S3
4. Crea application version
5. Crea/actualiza environment (Docker, t3.small, single instance)
6. Configura env vars desde `.data/.env.prod`
7. Espera hasta health = Green (5-10 min)
8. Verifica `/actuator/health`

**Output esperado**:
```
[9/9] Retrieving environment URL and verifying health...
      Environment URL: http://archaeologist-backend-prod.us-east-1.elasticbeanstalk.com
      Health check PASSED (HTTP 200)
      Response: {"status":"UP"}
```

**Acción requerida**: Guardar la URL del backend en `.data/.env.prod`:
```env
WEBHOOK_BASE_URL=http://archaeologist-backend-prod.us-east-1.elasticbeanstalk.com
```

---

### Paso 7: Deploy Analyzer → Elastic Beanstalk

**Script**: `deploy/04-deploy-analyzer-eb.sh`

```bash
chmod +x 04-deploy-analyzer-eb.sh
./04-deploy-analyzer-eb.sh
```

**Similar al backend** pero con:
- Instance type: `t3.medium` (Tree-sitter necesita más RAM)
- Health check: `/health`
- Env vars adicionales: `DATABASE_URL`, `BEDROCK_MODEL_ID`, `AWS_ACCESS_KEY_ID`, etc.

**Verificación**:
```bash
curl http://<analyzer-eb-url>/health
# {"status":"ok","service":"analyzer"}
```

---

### Paso 8: Deploy Frontend → AWS Amplify

**Script**: `deploy/05-deploy-frontend-amplify.sh`

```bash
# Variables requeridas
export REPO_URL="https://github.com/tu-usuario/tu-repo"
export GIT_ACCESS_TOKEN="ghp_xxxx"
export BACKEND_URL="http://archaeologist-backend-prod.us-east-1.elasticbeanstalk.com"
export BRANCH_NAME="main"

chmod +x 05-deploy-frontend-amplify.sh
./05-deploy-frontend-amplify.sh
```

**Qué hace**:
1. Crea Amplify app conectada al repo Git
2. Configura build settings para monorepo (`apps/frontend`)
3. Configura `NEXT_PUBLIC_API_URL` apuntando al Backend EB
4. Crea branch y dispara primer deploy
5. Espera a que el build complete

**Amplify auto-deploy**: Cada push a `main` dispara un nuevo build automáticamente.

**Verificación**: Acceder a la URL generada por Amplify (e.g., `https://main.d1abc2def3.amplifyapp.com`).

---

### Paso 9: Smoke Test End-to-End

**Script**: `deploy/06-smoke-test.sh`

```bash
chmod +x 06-smoke-test.sh
./06-smoke-test.sh \
  https://main.d1abc2def3.amplifyapp.com \
  http://archaeologist-backend-prod.us-east-1.elasticbeanstalk.com \
  http://archaeologist-analyzer-prod.us-east-1.elasticbeanstalk.com
```

**Qué valida**:
1. Frontend accesible (HTTP 200)
2. Backend health check (`/actuator/health`)
3. Analyzer health check (`/health`)
4. Flujo completo: submit repo → poll status → retrieve graph + report + kiro-spec
5. Verificar que S3 repos bucket recibió el clone

---

## Mapa de Variables de Entorno (Local → Producción)

| Variable | Valor Local (Docker Compose) | Valor Producción |
|---|---|---|
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://db:5432/archaeologist` | `jdbc:postgresql://<rds-endpoint>:5432/archaeologist` |
| `SPRING_DATASOURCE_USERNAME` | `archaeologist` | `archaeologist` |
| `SPRING_DATASOURCE_PASSWORD` | `archaeologist_secret` | `<generado por 01-create-rds.sh>` |
| `DATABASE_URL` | `postgresql+asyncpg://archaeologist:archaeologist_secret@db:5432/archaeologist` | `postgresql+asyncpg://archaeologist:<pass>@<rds-endpoint>:5432/archaeologist` |
| `WEBHOOK_SECRET` | `shared_webhook_secret` | `<generar secreto fuerte>` |
| `WEBHOOK_BASE_URL` | `http://backend:8080` | `http://<backend-eb-url>` |
| `ANALYZER_BASE_URL` | `http://analyzer:8000` | `http://<analyzer-eb-url>` |
| `AWS_ACCESS_KEY_ID` | *(de .data/.env)* | *(de IAM setup.sh)* |
| `AWS_SECRET_ACCESS_KEY` | *(de .data/.env)* | *(de IAM setup.sh)* |
| `AWS_REGION` | `us-east-1` | `us-east-1` |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| `BEDROCK_EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` | `amazon.titan-embed-text-v2:0` |
| `NEXT_PUBLIC_API_URL` | `/api` (nginx proxy) | `http://<backend-eb-url>/api` |

---

## Verificación Final (Checklist)

| # | Check | Comando / URL | Esperado |
|---|---|---|---|
| 1 | IAM user exists | `aws iam get-user --user-name kiro-archaeologist` | 200 OK |
| 2 | Permissions correct | `iam/verify-permissions.sh` | All checks passed |
| 3 | S3 repos bucket | `aws s3 ls s3://archaeologist-repos-prod` | Existe |
| 4 | S3 reports bucket | `aws s3 ls s3://archaeologist-reports-prod` | Existe |
| 5 | Bedrock models | `bedrock/verify-models.sh` | 2/2 available |
| 6 | RDS running | `aws rds describe-db-instances --db-instance-identifier archaeologist-db` | Status: available |
| 7 | pgvector enabled | `psql -c "SELECT extname FROM pg_extension WHERE extname='vector'"` | 1 row |
| 8 | Flyway migrations | `psql -c "SELECT * FROM flyway_schema_history"` | V1 Applied |
| 9 | Backend health | `curl http://<backend-eb>/actuator/health` | `{"status":"UP"}` |
| 10 | Analyzer health | `curl http://<analyzer-eb>/health` | `{"status":"ok"}` |
| 11 | Frontend loads | Abrir URL Amplify en browser | Página de inicio |
| 12 | E2E analysis | `deploy/06-smoke-test.sh` | All checks pass |

---

## Costos Estimados (MVP — Single Instance)

| Servicio | Spec | Costo Mensual Estimado (USD) |
|---|---|---|
| RDS PostgreSQL 15 | db.t3.medium, 20GB, single-AZ | ~$30-40 |
| Elastic Beanstalk (Backend) | t3.small, single instance | ~$15-20 |
| Elastic Beanstalk (Analyzer) | t3.medium, single instance | ~$30-35 |
| AWS Amplify | Build minutes + hosting | ~$5-10 |
| S3 | Repos (24h lifecycle) + Reports | ~$1-5 |
| Bedrock (pay-per-use) | Claude input/output tokens + Titan embeddings | Variable ($10-50 dependiendo del uso) |
| **Total estimado** | | **~$90-160/mes** |

Para reducir costos en desarrollo: detener RDS y EB environments cuando no estén en uso.

---

## Troubleshooting

### IAM: "User already exists"

```bash
# Si necesitas recrear el usuario:
aws iam delete-access-key --user-name kiro-archaeologist --access-key-id AKIA...
aws iam detach-user-policy --user-name kiro-archaeologist --policy-arn arn:aws:iam::...:policy/KiroArchaeologistMinimalPolicy
aws iam delete-user --user-name kiro-archaeologist
# Luego re-ejecutar setup.sh
```

### RDS: "Cannot connect" desde local

- **Causa**: RDS no tiene acceso público y estás fuera de la VPC.
- **Solución**: 
  1. Temporalmente habilitar public access en RDS, o
  2. Usar un bastion host EC2 con SSH tunnel, o
  3. Ejecutar scripts desde una instancia EC2 en la misma VPC

### EB: "Environment terminated unexpectedly"

- **Causa**: Docker build falla en la instancia EC2.
- **Diagnóstico**: `aws elasticbeanstalk describe-events --environment-name <env-name>`
- **Solución común**: Verificar que el Dockerfile funciona localmente antes de desplegar.

### Amplify: "Build failed"

- **Causa**: monorepo path incorrecto o dependencias que fallan en install.
- **Diagnóstico**: Ver build logs en Amplify Console.
- **Solución**: Verificar que `baseDirectory` apunta a `apps/frontend` y que `next.config.mjs` tiene `output: "standalone"`.

### Bedrock: "Model not available in region"

- **Causa**: Algunos modelos solo están en regiones específicas.
- **Solución**: Usar `us-east-1` o `us-west-2` (mayor disponibilidad de modelos).

### S3: "BucketAlreadyExists"

- **Causa**: Los nombres de bucket son globales. Alguien más tiene ese nombre.
- **Solución**: Modificar el nombre en `create-buckets.sh` (e.g., agregar suffix con account ID).

---

## Orden de Ejecución (Resumen)

```
1. iam/setup.sh                    → Crear usuario + keys
2. iam/verify-permissions.sh       → Validar permisos
3. bedrock/verify-models.sh        → Verificar modelos habilitados
4. s3/create-buckets.sh            → Crear buckets
5. deploy/01-create-rds.sh         → Crear RDS PostgreSQL
6. deploy/02-run-migrations.sh     → Aplicar Flyway migrations
7. deploy/03-deploy-backend-eb.sh  → Deploy Backend
8. deploy/04-deploy-analyzer-eb.sh → Deploy Analyzer
9. deploy/05-deploy-frontend-amplify.sh → Deploy Frontend
10. deploy/06-smoke-test.sh        → Validar todo
```

Tiempo total estimado: **30-45 minutos** (la mayor parte esperando a que RDS y EB inicien).
