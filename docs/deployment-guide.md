# Guía de Despliegue — Software Archaeologist

> Guía práctica para desplegar cambios en cada servicio del proyecto.
> Región: `us-east-1` | Cuenta: `989735870266`

---

## Tabla de Contenidos

1. [Prerequisitos](#1-prerequisitos)
2. [Cambios en el Frontend](#2-cambios-en-el-frontend)
3. [Cambios en el Backend](#3-cambios-en-el-backend)
4. [Cambios en el Analyzer](#4-cambios-en-el-analyzer)
5. [Cambios en Infraestructura AWS](#5-cambios-en-infraestructura-aws)
6. [Comandos Útiles](#6-comandos-útiles)
7. [Troubleshooting](#7-troubleshooting)
8. [Script Rápido de Deploy](#8-script-rápido-de-deploy)

---

## Arquitectura de Despliegue

```
GitHub (main) → CodeBuild (compilar) → S3 (bundle) → Elastic Beanstalk (runtime)
```

**¿Por qué CodeBuild?** Los Docker multi-stage builds fallan en instancias t3.small (2GB RAM).
CodeBuild provee 7GB RAM para compilar. Luego se despliega solo el bundle runtime en EB.

### Recursos

| Servicio | EB Environment | CodeBuild Project |
|----------|---------------|-------------------|
| Frontend | `arch-frontend-prod` | `archaeologist-frontend-build` |
| Backend | `archaeologist-backend-prod` | `archaeologist-backend-build` |
| Analyzer | `archaeologist-analyzer-prod` | `archaeologist-analyzer-build` |

| Recurso | Nombre |
|---------|--------|
| RDS PostgreSQL 15 | `archaeologist-db` (con pgvector) |
| S3 Repos Temp | `archaeologist-repos-prod` |
| S3 Reports | `archaeologist-reports-prod` |

---

## 1. Prerequisitos

### Herramientas Requeridas

```bash
# AWS CLI v2
aws --version  # aws-cli/2.x.x

# Docker
docker --version  # Docker version 24+

# Node.js (para frontend)
node --version  # v20.x o superior

# Java 21 (para backend)
java --version  # openjdk 21

# Python 3.11 (para analyzer)
python --version  # Python 3.11.x
```

### Configuración AWS

```bash
# Configurar credenciales
aws configure
# AWS Access Key ID: [tu-key]
# AWS Secret Access Key: [tu-secret]
# Default region name: us-east-1
# Default output format: json

# Verificar acceso
aws sts get-caller-identity
```

### Permisos IAM Necesarios

El usuario/rol debe tener acceso a:
- `codebuild:StartBuild`, `codebuild:BatchGetBuilds`
- `elasticbeanstalk:*`
- `s3:GetObject`, `s3:PutObject` (buckets del proyecto)
- `logs:GetLogEvents`, `logs:FilterLogEvents`

---

## 2. Cambios en el Frontend

**Directorio:** `apps/frontend/`  
**Stack:** Next.js + TypeScript + Tailwind CSS  
**EB Environment:** `arch-frontend-prod`  
**CodeBuild Project:** `archaeologist-frontend-build`

### Cómo Funciona

1. CodeBuild descarga el código de GitHub (branch `main`)
2. Ejecuta `npm ci && npm run build` (Next.js standalone output)
3. Empaqueta el bundle runtime (`.next/standalone` + `.next/static` + `public/`)
4. Sube el ZIP a S3
5. Elastic Beanstalk descarga el ZIP y lo ejecuta con Docker (imagen Node.js runtime)

### Variable Importante

`NEXT_PUBLIC_API_URL` se **bake en build time**. Si cambia la URL del backend,
hay que re-buildear el frontend.

### Pasos para Desplegar

```bash
# 1. Hacer cambios en apps/frontend/ y push a main
git add apps/frontend/
git commit -m "feat: cambios en frontend"
git push origin main

# 2. Iniciar build en CodeBuild
BUILD_ID=$(aws codebuild start-build \
  --project-name archaeologist-frontend-build \
  --query 'build.id' \
  --output text)

echo "Build iniciado: $BUILD_ID"

# 3. Esperar que termine (polling cada 30s)
aws codebuild batch-get-builds \
  --ids "$BUILD_ID" \
  --query 'builds[0].buildStatus' \
  --output text

# Esperar hasta que retorne SUCCEEDED

# 4. Crear nueva versión en EB
VERSION="frontend-$(date +%Y%m%d-%H%M%S)"

aws elasticbeanstalk create-application-version \
  --application-name archaeologist-frontend \
  --version-label "$VERSION" \
  --source-bundle S3Bucket="archaeologist-deploy-artifacts",S3Key="frontend/latest.zip"

# 5. Desplegar la nueva versión
aws elasticbeanstalk update-environment \
  --environment-name arch-frontend-prod \
  --version-label "$VERSION"

# 6. Verificar salud
aws elasticbeanstalk describe-environments \
  --environment-names arch-frontend-prod \
  --query 'Environments[0].{Status:Status,Health:Health,URL:CNAME}'
```

### Rollback

```bash
# Listar versiones anteriores
aws elasticbeanstalk describe-application-versions \
  --application-name archaeologist-frontend \
  --query 'ApplicationVersions[*].VersionLabel' \
  --output table

# Volver a una versión anterior
aws elasticbeanstalk update-environment \
  --environment-name arch-frontend-prod \
  --version-label "<version-anterior>"
```

---

## 3. Cambios en el Backend

**Directorio:** `apps/backend/`  
**Stack:** Spring Boot 3 + Java 21 + Gradle  
**EB Environment:** `archaeologist-backend-prod`  
**CodeBuild Project:** `archaeologist-backend-build`

### Cómo Funciona

1. CodeBuild descarga código de GitHub
2. Ejecuta `./gradlew bootJar` (compila JAR fat con todas las dependencias)
3. Empaqueta JAR + Dockerfile runtime + Dockerrun.aws.json
4. Sube ZIP a S3
5. EB construye imagen Docker ligera (solo JRE 21 + JAR) y la despliega

### Migraciones de Base de Datos

Las migraciones corren **automáticamente al arrancar** via Flyway.
- Los scripts viven en `apps/backend/src/main/resources/db/migration/`
- Formato: `V{version}__{descripcion}.sql`
- Flyway aplica solo las migraciones pendientes

Si necesitas correr migraciones manualmente, ver [sección de infraestructura](#rds-migraciones-manuales).

### Variables de Entorno (configuradas en EB)

| Variable | Descripción |
|----------|-------------|
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://<host>:5432/archaeologist` |
| `SPRING_DATASOURCE_USERNAME` | Usuario DB |
| `SPRING_DATASOURCE_PASSWORD` | Password DB |
| `AWS_REGION` | `us-east-1` |
| `S3_BUCKET_REPOS` | `archaeologist-repos-prod` |
| `S3_BUCKET_REPORTS` | `archaeologist-reports-prod` |
| `ANALYZER_URL` | URL interna del analyzer |

### Health Check

```
GET /actuator/health
```

EB verifica este endpoint cada 30s. Si falla 3 veces consecutivas, reinicia la instancia.

### Pasos para Desplegar

```bash
# 1. Push cambios a main
git add apps/backend/
git commit -m "feat: cambios en backend"
git push origin main

# 2. Iniciar build
BUILD_ID=$(aws codebuild start-build \
  --project-name archaeologist-backend-build \
  --query 'build.id' \
  --output text)

echo "Build iniciado: $BUILD_ID"

# 3. Monitorear build
watch -n 10 "aws codebuild batch-get-builds --ids $BUILD_ID \
  --query 'builds[0].{Status:buildStatus,Phase:currentPhase}' --output table"

# 4. Crear versión en EB
VERSION="backend-$(date +%Y%m%d-%H%M%S)"

aws elasticbeanstalk create-application-version \
  --application-name archaeologist-backend \
  --version-label "$VERSION" \
  --source-bundle S3Bucket="archaeologist-deploy-artifacts",S3Key="backend/latest.zip"

# 5. Desplegar
aws elasticbeanstalk update-environment \
  --environment-name archaeologist-backend-prod \
  --version-label "$VERSION"

# 6. Verificar
aws elasticbeanstalk describe-environments \
  --environment-names archaeologist-backend-prod \
  --query 'Environments[0].{Status:Status,Health:Health,URL:CNAME}'
```

### Rollback

```bash
# Volver a versión anterior
aws elasticbeanstalk update-environment \
  --environment-name archaeologist-backend-prod \
  --version-label "<version-anterior>"
```

> **Nota sobre migraciones:** Si la nueva versión incluyó migraciones de DB,
> el rollback del código no revierte la migración. Crear una migración nueva
> que deshaga los cambios si es necesario.

---

## 4. Cambios en el Analyzer

**Directorio:** `apps/analyzer/`  
**Stack:** Python 3.11 + FastAPI + LangChain  
**EB Environment:** `archaeologist-analyzer-prod`  
**CodeBuild Project:** `archaeologist-analyzer-build`

### Cómo Funciona

1. CodeBuild descarga código de GitHub
2. Empaqueta el source Python + requirements.txt + Dockerfile
3. Sube ZIP a S3
4. EB construye la imagen Docker (Python no necesita pre-compilar, `pip install` es rápido)
5. La imagen runtime ejecuta `uvicorn src.main:app`

### Variables de Entorno (configuradas en EB)

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | `postgresql://<user>:<pass>@<host>:5432/archaeologist` |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `BEDROCK_EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` |
| `AWS_DEFAULT_REGION` | `us-east-1` |
| `S3_BUCKET_REPOS` | `archaeologist-repos-prod` |
| `S3_BUCKET_REPORTS` | `archaeologist-reports-prod` |
| `WEBHOOK_URL` | URL del backend para notificaciones |
| `LOG_LEVEL` | `INFO` |

### Health Check

```
GET /health
```

### Pasos para Desplegar

```bash
# 1. Push cambios a main
git add apps/analyzer/
git commit -m "feat: cambios en analyzer"
git push origin main

# 2. Iniciar build
BUILD_ID=$(aws codebuild start-build \
  --project-name archaeologist-analyzer-build \
  --query 'build.id' \
  --output text)

echo "Build iniciado: $BUILD_ID"

# 3. Monitorear
aws codebuild batch-get-builds \
  --ids "$BUILD_ID" \
  --query 'builds[0].buildStatus' \
  --output text

# 4. Crear versión
VERSION="analyzer-$(date +%Y%m%d-%H%M%S)"

aws elasticbeanstalk create-application-version \
  --application-name archaeologist-analyzer \
  --version-label "$VERSION" \
  --source-bundle S3Bucket="archaeologist-deploy-artifacts",S3Key="analyzer/latest.zip"

# 5. Desplegar
aws elasticbeanstalk update-environment \
  --environment-name archaeologist-analyzer-prod \
  --version-label "$VERSION"

# 6. Verificar salud
curl -s https://$(aws elasticbeanstalk describe-environments \
  --environment-names archaeologist-analyzer-prod \
  --query 'Environments[0].CNAME' --output text)/health
```

### Rollback

```bash
aws elasticbeanstalk update-environment \
  --environment-name archaeologist-analyzer-prod \
  --version-label "<version-anterior>"
```

### Consideraciones Especiales

- **Bedrock Access:** El analyzer necesita acceso al modelo Claude en Bedrock.
  Verificar que el model access esté habilitado en la consola de Bedrock.
- **Memoria:** Los análisis de repos grandes consumen bastante RAM.
  La instancia debe tener al menos 4GB disponibles.
- **Timeouts:** Los análisis pueden tomar varios minutos.
  El timeout de la instancia EB está configurado a 600s.

---

## 5. Cambios en Infraestructura AWS

### RDS PostgreSQL

**Instancia:** `archaeologist-db`  
**Engine:** PostgreSQL 15 con extensión pgvector  
**Endpoint:** Disponible en la consola RDS o via CLI

#### Conectarse a la DB

```bash
# Obtener endpoint
aws rds describe-db-instances \
  --db-instance-identifier archaeologist-db \
  --query 'DBInstances[0].Endpoint.{Address:Address,Port:Port}' \
  --output table

# Conectar via psql (requiere estar en la VPC o usar port forwarding)
psql -h <endpoint> -U <usuario> -d archaeologist
```

#### RDS: Migraciones Manuales

```bash
# Si necesitas correr Flyway manualmente (desde una instancia con acceso a la VPC)
flyway -url=jdbc:postgresql://<endpoint>:5432/archaeologist \
       -user=<usuario> \
       -password=<password> \
       -locations=filesystem:apps/backend/src/main/resources/db/migration \
       migrate

# O directamente con psql
psql -h <endpoint> -U <usuario> -d archaeologist -f script.sql
```

#### Verificar extensión pgvector

```sql
-- Conectado a la DB
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Si no existe
CREATE EXTENSION IF NOT EXISTS vector;
```

### S3 Buckets

```bash
# Verificar buckets
aws s3 ls s3://archaeologist-repos-prod/
aws s3 ls s3://archaeologist-reports-prod/

# Ver tamaño total
aws s3 ls s3://archaeologist-repos-prod --recursive --summarize \
  | tail -2

# Lifecycle: los repos temporales se eliminan después de 24h
aws s3api get-bucket-lifecycle-configuration \
  --bucket archaeologist-repos-prod
```

### Elastic Beanstalk

#### Ver logs de un servicio

```bash
# Solicitar logs
aws elasticbeanstalk request-environment-info \
  --environment-name archaeologist-backend-prod \
  --info-type tail

# Esperar 5-10 segundos, luego recuperar
aws elasticbeanstalk retrieve-environment-info \
  --environment-name archaeologist-backend-prod \
  --info-type tail \
  --query 'EnvironmentInfo[0].Message' \
  --output text
```

#### Cambiar tipo de instancia

```bash
# Ver configuración actual
aws elasticbeanstalk describe-configuration-settings \
  --application-name archaeologist-backend \
  --environment-name archaeologist-backend-prod \
  --query "ConfigurationSettings[0].OptionSettings[?OptionName=='InstanceType']"

# Cambiar a t3.medium (requiere restart)
aws elasticbeanstalk update-environment \
  --environment-name archaeologist-backend-prod \
  --option-settings Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.medium
```

#### Escalar instancias

```bash
# Configurar auto-scaling (min 1, max 3)
aws elasticbeanstalk update-environment \
  --environment-name archaeologist-backend-prod \
  --option-settings \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=1 \
    Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=3
```

### Seguridad

#### Rotar credenciales de DB

```bash
# 1. Generar nueva password
NEW_PASS=$(openssl rand -base64 24)

# 2. Actualizar en RDS
aws rds modify-db-instance \
  --db-instance-identifier archaeologist-db \
  --master-user-password "$NEW_PASS" \
  --apply-immediately

# 3. Actualizar en cada environment de EB
for ENV in archaeologist-backend-prod archaeologist-analyzer-prod; do
  aws elasticbeanstalk update-environment \
    --environment-name "$ENV" \
    --option-settings Namespace=aws:elasticbeanstalk:application:environment,OptionName=DB_PASSWORD,Value="$NEW_PASS"
done
```

#### Actualizar variables de entorno

```bash
# Actualizar una variable en un environment
aws elasticbeanstalk update-environment \
  --environment-name archaeologist-backend-prod \
  --option-settings \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=MI_VARIABLE,Value="nuevo-valor"

# Ver todas las variables actuales
aws elasticbeanstalk describe-configuration-settings \
  --application-name archaeologist-backend \
  --environment-name archaeologist-backend-prod \
  --query "ConfigurationSettings[0].OptionSettings[?Namespace=='aws:elasticbeanstalk:application:environment'].[OptionName,Value]" \
  --output table
```

---

## 6. Comandos Útiles

### Ver Logs

```bash
# Logs del backend (últimos 100 líneas)
aws logs filter-log-events \
  --log-group-name /aws/elasticbeanstalk/archaeologist-backend-prod/var/log/eb-docker/containers/eb-current-app/stdouterr.log \
  --limit 100 \
  --query 'events[*].message' \
  --output text

# Logs del analyzer
aws logs filter-log-events \
  --log-group-name /aws/elasticbeanstalk/archaeologist-analyzer-prod/var/log/eb-docker/containers/eb-current-app/stdouterr.log \
  --limit 100 \
  --query 'events[*].message' \
  --output text

# Logs del frontend
aws logs filter-log-events \
  --log-group-name /aws/elasticbeanstalk/arch-frontend-prod/var/log/eb-docker/containers/eb-current-app/stdouterr.log \
  --limit 100 \
  --query 'events[*].message' \
  --output text
```

### Verificar Salud

```bash
# Estado de todos los environments
aws elasticbeanstalk describe-environments \
  --environment-names archaeologist-backend-prod archaeologist-analyzer-prod arch-frontend-prod \
  --query 'Environments[*].{Name:EnvironmentName,Status:Status,Health:Health,HealthStatus:HealthStatus}' \
  --output table

# Health check directo
curl -s https://$(aws elasticbeanstalk describe-environments \
  --environment-names archaeologist-backend-prod \
  --query 'Environments[0].CNAME' --output text)/actuator/health | jq .

curl -s https://$(aws elasticbeanstalk describe-environments \
  --environment-names archaeologist-analyzer-prod \
  --query 'Environments[0].CNAME' --output text)/health | jq .
```

### Escalar Instancias

```bash
# Escalar backend a 2 instancias mínimo
aws elasticbeanstalk update-environment \
  --environment-name archaeologist-backend-prod \
  --option-settings \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=2

# Volver a 1 instancia
aws elasticbeanstalk update-environment \
  --environment-name archaeologist-backend-prod \
  --option-settings \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=1
```

### Terminar y Recrear Environments

```bash
# ⚠️ DESTRUCTIVO - Terminar environment
aws elasticbeanstalk terminate-environment \
  --environment-name archaeologist-backend-prod

# Recrear con la última versión
aws elasticbeanstalk create-environment \
  --application-name archaeologist-backend \
  --environment-name archaeologist-backend-prod \
  --solution-stack-name "64bit Amazon Linux 2023 v4.3.0 running Docker" \
  --version-label "<última-versión>"
```

### Ver Costos (aproximado)

```bash
# Costo del último mes por servicio
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '-30 days' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[0].Groups[*].{Service:Keys[0],Cost:Metrics.BlendedCost.Amount}' \
  --output table
```

---

## 7. Troubleshooting

### Build Falla en CodeBuild

**Síntoma:** Build termina con status `FAILED`

```bash
# Ver logs del build fallido
aws codebuild batch-get-builds \
  --ids "<build-id>" \
  --query 'builds[0].phases[*].{Phase:phaseType,Status:phaseStatus,Context:contexts}' \
  --output table

# Ver logs detallados en CloudWatch
aws logs get-log-events \
  --log-group-name /aws/codebuild/archaeologist-backend-build \
  --log-stream-name "<build-id>" \
  --limit 50
```

**Causas comunes:**
- **Out of memory:** Si por alguna razón se intenta build local en t3.small, usar CodeBuild.
- **Dependencias no resuelven:** Verificar que `requirements.txt` o `build.gradle` no tengan versiones conflictivas.
- **Tests fallan:** CodeBuild puede ejecutar tests como parte del build. Verificar logs.

### Health Check Falla

**Síntoma:** Environment en estado `Degraded` o `Severe`

```bash
# Ver eventos recientes
aws elasticbeanstalk describe-events \
  --environment-name archaeologist-backend-prod \
  --max-items 20 \
  --query 'Events[*].{Date:EventDate,Severity:Severity,Message:Message}' \
  --output table
```

**Causas comunes:**
- **Variables de entorno faltantes:** Verificar que todas las env vars estén configuradas.
- **DB no accesible:** Verificar Security Groups y que la instancia RDS esté running.
- **Puerto incorrecto:** Verificar que el Dockerfile expone el puerto correcto (8080 backend, 8000 analyzer, 3000 frontend).

```bash
# Verificar conectividad DB desde EB (ver en logs)
aws elasticbeanstalk request-environment-info \
  --environment-name archaeologist-backend-prod \
  --info-type tail
```

### Analyzer No Procesa Repositorios

**Síntoma:** Jobs quedan en estado `PENDING` o `FAILED`

**Verificar:**

1. **Acceso a Bedrock:**
```bash
# Verificar que el modelo está habilitado
aws bedrock list-foundation-models \
  --query "modelSummaries[?modelId=='anthropic.claude-3-5-sonnet-20241022-v2:0'].{Id:modelId,Status:modelLifecycle.status}" \
  --output table
```

2. **Permisos IAM del instance profile de EB:**
   - Debe tener `bedrock:InvokeModel`
   - Debe tener acceso a S3 (`archaeologist-repos-prod`)

3. **Espacio en disco:**
   - Repos grandes pueden llenar el disco de la instancia
   - Verificar que el lifecycle policy de S3 limpia repos temporales

### Frontend No Muestra Datos

**Síntoma:** UI carga pero las llamadas API fallan

**Verificar:**

1. **`NEXT_PUBLIC_API_URL` correcto:**
```bash
# Ver qué URL tiene el frontend bakeada
# Esta variable se define en build time, no en runtime
aws codebuild batch-get-builds \
  --ids "<último-frontend-build-id>" \
  --query 'builds[0].environment.environmentVariables[?name==`NEXT_PUBLIC_API_URL`].value' \
  --output text
```

2. **CORS en el backend:**
   - El backend debe permitir requests desde el dominio del frontend
   - Verificar headers `Access-Control-Allow-Origin`

3. **Backend accesible:**
```bash
curl -s https://$(aws elasticbeanstalk describe-environments \
  --environment-names archaeologist-backend-prod \
  --query 'Environments[0].CNAME' --output text)/actuator/health
```

### Instancia EB No Arranca

**Síntoma:** Environment cycling, instancias se reinician constantemente

```bash
# Ver log de Docker
aws elasticbeanstalk request-environment-info \
  --environment-name archaeologist-backend-prod \
  --info-type bundle

# Verificar que la imagen Docker se construye correctamente
# (esperar 30s y luego retrieve)
aws elasticbeanstalk retrieve-environment-info \
  --environment-name archaeologist-backend-prod \
  --info-type bundle
```

**Causas comunes:**
- OOM (Out of Memory): El JAR necesita al menos 512MB de heap. Configurar `-Xmx` en Dockerfile.
- Disco lleno: Imágenes Docker viejas ocupan espacio. Recrear el environment limpia esto.
- Security Group: La instancia no puede alcanzar RDS o internet.

---

## 8. Script Rápido de Deploy

Guarda este script como `scripts/deploy.sh` en la raíz del proyecto:

```bash
#!/bin/bash
set -euo pipefail

# ============================================================
# deploy.sh — Script de despliegue para Software Archaeologist
# Uso: ./scripts/deploy.sh [frontend|backend|analyzer|all]
# ============================================================

REGION="us-east-1"
ACCOUNT="989735870266"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuración por servicio
declare -A CODEBUILD_PROJECTS=(
  [frontend]="archaeologist-frontend-build"
  [backend]="archaeologist-backend-build"
  [analyzer]="archaeologist-analyzer-build"
)

declare -A EB_APPS=(
  [frontend]="archaeologist-frontend"
  [backend]="archaeologist-backend"
  [analyzer]="archaeologist-analyzer"
)

declare -A EB_ENVS=(
  [frontend]="arch-frontend-prod"
  [backend]="archaeologist-backend-prod"
  [analyzer]="archaeologist-analyzer-prod"
)

declare -A HEALTH_PATHS=(
  [frontend]="/"
  [backend]="/actuator/health"
  [analyzer]="/health"
)

# ============================================================
# Funciones
# ============================================================

wait_for_build() {
  local build_id=$1
  local max_wait=600  # 10 minutos
  local elapsed=0

  log_info "Esperando build: $build_id"

  while [ $elapsed -lt $max_wait ]; do
    STATUS=$(aws codebuild batch-get-builds \
      --ids "$build_id" \
      --query 'builds[0].buildStatus' \
      --output text \
      --region "$REGION")

    case $STATUS in
      SUCCEEDED)
        log_info "Build completado exitosamente"
        return 0
        ;;
      FAILED|FAULT|TIMED_OUT|STOPPED)
        log_error "Build falló con status: $STATUS"
        return 1
        ;;
      IN_PROGRESS)
        echo -n "."
        sleep 15
        elapsed=$((elapsed + 15))
        ;;
    esac
  done

  log_error "Timeout esperando build"
  return 1
}

wait_for_environment() {
  local env_name=$1
  local max_wait=300  # 5 minutos
  local elapsed=0

  log_info "Esperando environment: $env_name"

  while [ $elapsed -lt $max_wait ]; do
    STATUS=$(aws elasticbeanstalk describe-environments \
      --environment-names "$env_name" \
      --query 'Environments[0].Status' \
      --output text \
      --region "$REGION")

    if [ "$STATUS" = "Ready" ]; then
      HEALTH=$(aws elasticbeanstalk describe-environments \
        --environment-names "$env_name" \
        --query 'Environments[0].Health' \
        --output text \
        --region "$REGION")
      log_info "Environment listo. Health: $HEALTH"
      return 0
    fi

    echo -n "."
    sleep 15
    elapsed=$((elapsed + 15))
  done

  log_warn "Timeout esperando environment (puede seguir actualizando)"
  return 0
}

deploy_service() {
  local service=$1
  local timestamp=$(date +%Y%m%d-%H%M%S)
  local version="${service}-${timestamp}"

  log_info "=========================================="
  log_info "Desplegando: $service"
  log_info "=========================================="

  # 1. Iniciar build
  log_info "Iniciando CodeBuild..."
  BUILD_ID=$(aws codebuild start-build \
    --project-name "${CODEBUILD_PROJECTS[$service]}" \
    --query 'build.id' \
    --output text \
    --region "$REGION")

  # 2. Esperar build
  if ! wait_for_build "$BUILD_ID"; then
    log_error "Build falló para $service. Abortando."
    return 1
  fi

  # 3. Crear versión
  log_info "Creando versión: $version"
  aws elasticbeanstalk create-application-version \
    --application-name "${EB_APPS[$service]}" \
    --version-label "$version" \
    --source-bundle S3Bucket="archaeologist-deploy-artifacts",S3Key="${service}/latest.zip" \
    --region "$REGION" \
    --no-cli-pager

  # 4. Desplegar
  log_info "Actualizando environment..."
  aws elasticbeanstalk update-environment \
    --environment-name "${EB_ENVS[$service]}" \
    --version-label "$version" \
    --region "$REGION" \
    --no-cli-pager

  # 5. Esperar
  wait_for_environment "${EB_ENVS[$service]}"

  # 6. Verificar health
  local cname=$(aws elasticbeanstalk describe-environments \
    --environment-names "${EB_ENVS[$service]}" \
    --query 'Environments[0].CNAME' \
    --output text \
    --region "$REGION")

  log_info "URL: https://$cname"
  log_info "Health check: https://$cname${HEALTH_PATHS[$service]}"

  local http_code=$(curl -s -o /dev/null -w "%{http_code}" "https://$cname${HEALTH_PATHS[$service]}" || echo "000")

  if [ "$http_code" = "200" ]; then
    log_info "✓ $service desplegado correctamente (HTTP $http_code)"
  else
    log_warn "Health check retornó HTTP $http_code (puede estar aún iniciando)"
  fi

  echo ""
}

# ============================================================
# Main
# ============================================================

SERVICE=${1:-}

if [ -z "$SERVICE" ]; then
  echo "Uso: $0 [frontend|backend|analyzer|all]"
  echo ""
  echo "Ejemplos:"
  echo "  $0 frontend    # Despliega solo el frontend"
  echo "  $0 backend     # Despliega solo el backend"
  echo "  $0 analyzer    # Despliega solo el analyzer"
  echo "  $0 all         # Despliega todos los servicios"
  exit 1
fi

# Verificar AWS CLI
if ! aws sts get-caller-identity &>/dev/null; then
  log_error "No se puede autenticar con AWS. Ejecuta 'aws configure' primero."
  exit 1
fi

log_info "Cuenta AWS: $(aws sts get-caller-identity --query 'Account' --output text)"
log_info "Región: $REGION"
echo ""

if [ "$SERVICE" = "all" ]; then
  for svc in backend analyzer frontend; do
    deploy_service "$svc"
  done
else
  if [[ ! " frontend backend analyzer " =~ " $SERVICE " ]]; then
    log_error "Servicio desconocido: $SERVICE"
    exit 1
  fi
  deploy_service "$SERVICE"
fi

log_info "=========================================="
log_info "Deploy completado"
log_info "=========================================="
```

### Uso del Script

```bash
# Hacer el script ejecutable
chmod +x scripts/deploy.sh

# Desplegar un servicio específico
./scripts/deploy.sh frontend
./scripts/deploy.sh backend
./scripts/deploy.sh analyzer

# Desplegar todo (backend → analyzer → frontend)
./scripts/deploy.sh all
```

---

## Notas Finales

- **Orden de despliegue:** Si hay cambios en múltiples servicios, desplegar en orden: Backend → Analyzer → Frontend.
  El backend debe estar listo antes que el analyzer (que le notifica vía webhook),
  y el frontend debe buildearse con la URL correcta del backend.
- **Costos:** Con t3.small × 3 environments + RDS + CodeBuild por uso, el costo mensual
  estimado es ~$80-120 USD dependiendo del uso.
- **Backups:** RDS tiene backups automáticos con retención de 7 días.
  Para restore: `aws rds restore-db-instance-to-point-in-time`.
