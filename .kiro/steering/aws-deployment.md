# AWS Deployment — Skill Global

Patrones de despliegue en AWS aprendidos y validados. Aplicable a cualquier proyecto que use Elastic Beanstalk, RDS, S3, Bedrock, CodeBuild, o Amplify.

---

## Arquitectura de Deploy (patrón validado)

```
GitHub (push) → CodeBuild (compilar) → S3 (artefacto .zip) → Elastic Beanstalk (runtime Docker)
```

**¿Por qué CodeBuild?** Los Docker multi-stage builds fallan en instancias t3.small/medium (2-4GB RAM). Gradle necesita ~2GB, npm+Next.js necesita ~2GB. CodeBuild provee 7GB RAM (BUILD_GENERAL1_MEDIUM) para compilar. Luego se despliega solo el bundle runtime en EB.

---

## Elastic Beanstalk — Docker Platform

### Principios
- Usar **Docker platform** (no Java/Node platform) para control total del runtime.
- Source bundle = ZIP con `Dockerfile` en la raíz + archivos necesarios.
- **Nunca** hacer multi-stage builds en la instancia EB — pre-compilar en CodeBuild.
- Single instance (`EnvironmentType=SingleInstance`) para MVP. Load balancer para producción.
- Solution Stack: `64bit Amazon Linux 2023 v4.x.x running Docker` (verificar versión actual con `aws elasticbeanstalk list-available-solution-stacks`).

### Bundle para Backend (Java/Spring Boot)
```dockerfile
# Runtime-only — el JAR ya está pre-compilado por CodeBuild
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY app.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

### Bundle para Servicio Python (FastAPI/Flask)
```dockerfile
FROM python:3.11-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt
COPY src/ ./src/

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /app/deps /usr/local/lib/python3.11/site-packages
COPY --from=build /app/src ./src/
RUN useradd --create-home appuser && mkdir -p /tmp/repos && chown appuser:appuser /tmp/repos
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Bundle para Frontend (Next.js standalone)
```dockerfile
FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```
El ZIP contiene: `.next/standalone/` + `.next/static/` + `public/` + `Dockerfile`

### Crear y desplegar un environment
```bash
# 1. Crear app (una vez)
aws elasticbeanstalk create-application --application-name mi-app --description "Descripción"

# 2. Subir bundle a S3
aws s3 cp bundle.zip s3://mi-bucket-eb-bundles/app/v1.zip

# 3. Crear versión
aws elasticbeanstalk create-application-version \
  --application-name mi-app \
  --version-label v1 \
  --source-bundle S3Bucket=mi-bucket-eb-bundles,S3Key=app/v1.zip

# 4. Crear environment
aws elasticbeanstalk create-environment \
  --application-name mi-app \
  --environment-name mi-app-prod \
  --solution-stack-name "64bit Amazon Linux 2023 v4.13.4 running Docker" \
  --option-settings \
    Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.small \
    Namespace=aws:autoscaling:launchconfiguration,OptionName=IamInstanceProfile,Value=aws-elasticbeanstalk-ec2-role \
    Namespace=aws:elasticbeanstalk:environment,OptionName=EnvironmentType,Value=SingleInstance \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=MI_VAR,Value="mi-valor"

# 5. Actualizar (re-deploy)
aws elasticbeanstalk update-environment --environment-name mi-app-prod --version-label v2

# 6. Rollback
aws elasticbeanstalk update-environment --environment-name mi-app-prod --version-label v1
```

### IAM Roles necesarios para EB
- `aws-elasticbeanstalk-ec2-role` — Instance profile con políticas: AWSElasticBeanstalkWebTier, MulticontainerDocker, WorkerTier + cualquier permiso extra (S3, Bedrock).
- `aws-elasticbeanstalk-service-role` — Service role con: AWSElasticBeanstalkEnhancedHealth, AWSElasticBeanstalkManagedUpdatesCustomerRolePolicy.

---

## CodeBuild — Pre-compilación

### Cuándo usar
- **Siempre** que el build necesite >2GB RAM (Gradle, npm con frameworks pesados, Docker builds).
- Para producir artefactos ZIP que EB despliega directamente.
- Como CI: compilar + test + producir artefacto.

### Configuración típica
```bash
aws codebuild create-project \
  --name mi-proyecto-build \
  --source type=GITHUB,location=https://github.com/user/repo.git,buildspec=buildspec.yml \
  --artifacts type=S3,location=mi-bucket,path=proyecto,packaging=ZIP \
  --environment type=LINUX_CONTAINER,computeType=BUILD_GENERAL1_MEDIUM,image=aws/codebuild/amazonlinux2-x86_64-standard:5.0 \
  --service-role codebuild-role-arn
```

### Buildspec para Java (Spring Boot)
```yaml
version: 0.2
phases:
  install:
    runtime-versions:
      java: corretto21
  build:
    commands:
      - cd apps/backend && ./gradlew bootJar --no-daemon -x test
  post_build:
    commands:
      - mkdir -p /tmp/output
      - cp apps/backend/build/libs/*.jar /tmp/output/app.jar
      - echo 'FROM eclipse-temurin:21-jre-alpine\nWORKDIR /app\nCOPY app.jar app.jar\nEXPOSE 8080\nENTRYPOINT ["java","-jar","app.jar"]' > /tmp/output/Dockerfile
artifacts:
  base-directory: /tmp/output
  files: ['**/*']
```

### Buildspec para Next.js Frontend
```yaml
version: 0.2
env:
  variables:
    NEXT_PUBLIC_API_URL: http://mi-backend-url
phases:
  install:
    runtime-versions:
      nodejs: 20
  pre_build:
    commands:
      - cd apps/frontend && npm ci
  build:
    commands:
      - cd apps/frontend && npm run build
  post_build:
    commands:
      - mkdir -p /tmp/output/.next/static /tmp/output/public
      - cp -r apps/frontend/.next/standalone/. /tmp/output/
      - cp -r apps/frontend/.next/static/. /tmp/output/.next/static/
      - cp -r apps/frontend/public/. /tmp/output/public/
      - |
        cat > /tmp/output/Dockerfile << 'EOF'
        FROM node:20-alpine
        WORKDIR /app
        ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
        COPY . .
        EXPOSE 3000
        CMD ["node", "server.js"]
        EOF
artifacts:
  base-directory: /tmp/output
  files: ['**/*']
```

### Buildspec para Python (no necesita CodeBuild normalmente)
Python no requiere compilación. El Docker build de pip install es rápido (~30s). Se puede hacer directo en EB. Usar CodeBuild solo si hay dependencias nativas pesadas.

---

## RDS PostgreSQL

### Crear instancia con pgvector
```bash
# Parameter group
aws rds create-db-parameter-group --db-parameter-group-name pg15-params \
  --db-parameter-group-family postgres15 --description "Custom params"

# Security group
SG_ID=$(aws ec2 create-security-group --group-name db-sg \
  --description "DB SG" --vpc-id <VPC_ID> --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $SG_ID \
  --protocol tcp --port 5432 --cidr 0.0.0.0/0  # Restringir después

# Instancia
aws rds create-db-instance \
  --db-instance-identifier mi-db \
  --db-instance-class db.t3.micro \
  --engine postgres --engine-version 15 \
  --master-username admin --master-user-password <SECURE_PASS> \
  --db-name midb --allocated-storage 20 --storage-type gp3 \
  --db-parameter-group-name pg15-params \
  --vpc-security-group-ids $SG_ID \
  --no-multi-az --storage-encrypted --backup-retention-period 7

# Esperar
aws rds wait db-instance-available --db-instance-identifier mi-db

# Habilitar pgvector (conectar con psql)
psql -h <endpoint> -U admin -d midb -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Strings de conexión
- **JDBC (Java):** `jdbc:postgresql://<endpoint>:5432/<dbname>`
- **asyncpg (Python):** `postgresql+asyncpg://<user>:<pass>@<endpoint>:5432/<dbname>`
- **psql:** `psql -h <endpoint> -U <user> -d <dbname>`

### Migraciones (Flyway via Spring Boot)
Las migraciones corren automáticamente al arrancar. Para correrlas manualmente sin levantar el web server:
```bash
docker run --rm -e SPRING_DATASOURCE_URL=<url> -e SPRING_DATASOURCE_USERNAME=<user> \
  -e SPRING_DATASOURCE_PASSWORD=<pass> -e SPRING_MAIN_WEB_APPLICATION_TYPE=none \
  mi-imagen:tag java -jar app.jar --spring.main.web-application-type=none
```

---

## S3 — Buckets

### Crear con buenas prácticas
```bash
aws s3api create-bucket --bucket mi-bucket --region us-east-1
aws s3api put-public-access-block --bucket mi-bucket \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

### Lifecycle para buckets temporales (auto-delete)
```bash
aws s3api put-bucket-lifecycle-configuration --bucket mi-bucket-temp \
  --lifecycle-configuration '{"Rules":[{"ID":"AutoDelete","Status":"Enabled","Filter":{"Prefix":""},"Expiration":{"Days":1}}]}'
```

---

## Bedrock — Modelos AI

### Modelos probados
| Modelo | ID | Uso |
|--------|-----|-----|
| Claude Sonnet 4 | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Razonamiento, análisis de código |
| Titan Embed V2 | `amazon.titan-embed-text-v2:0` | Embeddings para RAG |

### IAM Policy para Bedrock (mínimo privilegio)
```json
{
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
  "Resource": ["arn:aws:bedrock:*::foundation-model/<model-id>"]
}
```

### Invocación desde Python (boto3)
```python
import boto3, json
client = boto3.client("bedrock-runtime", region_name="us-east-1")
response = client.invoke_model(
    modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    body=json.dumps({"anthropic_version": "bedrock-2023-05-31", "max_tokens": 4096,
                     "messages": [{"role": "user", "content": "Hola"}]})
)
result = json.loads(response["body"].read())
```

### Prerrequisito: Habilitar acceso al modelo
En la consola de AWS → Bedrock → Model access → Request access para los modelos que se usarán.

---

## IAM — Roles y Políticas

### Principio de mínimo privilegio
- Un IAM user por aplicación/servicio.
- Solo acceso programático (sin console login).
- Políticas managed customer (no inline).
- Scoped por recurso (ARN pattern con wildcards mínimos).

### Crear IAM user para app
```bash
aws iam create-user --user-name mi-app-user
aws iam create-policy --policy-name MiAppPolicy --policy-document file://policy.json
aws iam attach-user-policy --user-name mi-app-user --policy-arn <policy-arn>
aws iam create-access-key --user-name mi-app-user
```

### Template de política mínima
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Sid": "S3Access", "Effect": "Allow",
     "Action": ["s3:PutObject","s3:GetObject","s3:DeleteObject"],
     "Resource": ["arn:aws:s3:::mi-app-*/*"]},
    {"Sid": "S3List", "Effect": "Allow",
     "Action": ["s3:ListBucket"],
     "Resource": ["arn:aws:s3:::mi-app-*"]},
    {"Sid": "Bedrock", "Effect": "Allow",
     "Action": ["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"],
     "Resource": ["arn:aws:bedrock:*::foundation-model/*"]},
    {"Sid": "Logs", "Effect": "Allow",
     "Action": ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
     "Resource": ["arn:aws:logs:*:*:log-group:/mi-app/*"]}
  ]
}
```

---

## Frontend — Next.js en EB (sin Amplify)

### Patrón de API Proxy (evita CORS)
El frontend Next.js usa `rewrites` en `next.config.mjs` para proxy `/api/*` al backend:
```javascript
const nextConfig = {
  output: "standalone",
  async rewrites() {
    const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://localhost:8080";
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};
```

**Reglas:**
- `API_BASE_URL` siempre es `/api` (relativo). Nunca URL absoluta en el client.
- `NEXT_PUBLIC_API_URL` ya NO se usa para client-side (causa CORS).
- El proxy server-side (rewrite) elimina problemas de CORS.
- `BACKEND_INTERNAL_URL` es runtime env var del servidor Next.js (NO `NEXT_PUBLIC_`).

### CORS en el Backend (safety net)
Agregar siempre como fallback:
```java
@Configuration
public class CorsConfig {
    @Bean
    public CorsFilter corsFilter() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOriginPatterns(List.of("*"));
        config.setAllowedMethods(List.of("GET","POST","PUT","DELETE","OPTIONS"));
        config.setAllowedHeaders(List.of("*"));
        config.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }
}
```

---

## Troubleshooting

### Build falla en EB (Docker)
- **Causa:** OOM durante multi-stage build.
- **Fix:** Pre-compilar en CodeBuild, desplegar solo runtime Dockerfile.

### ZIP con paths de Windows (backslashes)
- **Causa:** Crear ZIP en Windows con herramientas que usan `\` en vez de `/`.
- **Fix:** Usar CodeBuild para recrear el ZIP con paths Unix, o `zip` con flag `-l`.

### EB environment stuck en Launching
- **Causa:** ASG no puede lanzar instancia (quota, security group, IAM).
- **Fix:** Terminar y recrear. Verificar que existan roles IAM y security groups.

### CORS blocked
- **Causa:** Frontend hace fetch directo a otro dominio.
- **Fix:** Usar proxy de Next.js (rewrites). No usar URLs absolutas en client-side.

### RDS no accesible desde EB
- **Causa:** Security group restrictivo.
- **Fix:** Abrir port 5432 desde el SG del EB (o 0.0.0.0/0 temporalmente).

### Bedrock "access denied"
- **Causa:** Modelo no habilitado en la cuenta.
- **Fix:** AWS Console → Bedrock → Model access → Request access.

---

## Checklist de Deploy (nuevo proyecto)

1. [ ] Crear S3 buckets (con public access block)
2. [ ] Crear RDS PostgreSQL (con pgvector si se necesita)
3. [ ] Crear IAM user/role con política mínima
4. [ ] Habilitar acceso a modelos en Bedrock console
5. [ ] Crear CodeBuild projects (backend, frontend)
6. [ ] Crear EB applications y environments
7. [ ] Configurar variables de entorno en EB
8. [ ] Verificar health endpoints
9. [ ] Configurar API proxy en frontend (rewrites)
10. [ ] Smoke test e2e

---

## Costos Estimados (us-east-1, MVP)

| Recurso | Tipo | Costo/mes |
|---------|------|-----------|
| RDS | db.t3.micro | ~$15 |
| EB (backend) | t3.small | ~$15 |
| EB (analyzer) | t3.small | ~$15 |
| EB (frontend) | t3.small | ~$15 |
| S3 | <1GB | ~$1 |
| CodeBuild | Por minuto de build | ~$5 |
| **Total MVP** | | **~$65/mes** |

Para reducir: usar instancias spot, auto-scaling a 0 en horarios no-laborales, o usar Lambda.
