# Backend — Software Archaeologist

API Gateway y orquestador del flujo de análisis.

---

## Propósito

El Backend es el punto de entrada REST para el Frontend. Se encarga de:

- Recibir solicitudes de análisis de repositorios
- Orquestar el flujo de trabajo entre Frontend y Analyzer
- Persistir el estado de los jobs de análisis
- Gestionar migraciones de base de datos (Flyway)
- Relay de SSE streaming para el chat RAG
- Exponer el grafo de dependencias y reportes al Frontend

---

## Tech Stack

| Tecnología | Versión | Propósito |
|---|---|---|
| Java | 21 | Runtime (Eclipse Temurin) |
| Spring Boot | 3.3.5 | Framework web |
| Spring WebFlux | 3.3.x | HTTP reactivo + SSE streaming |
| Spring Data JPA | 3.3.x | Persistencia ORM |
| Spring Actuator | 3.3.x | Health checks + monitoring |
| Flyway | latest | Migraciones de base de datos |
| PostgreSQL (driver) | latest | Conexión a DB |
| Gradle | 8.x | Build tool |
| Docker | latest | Containerización (Eclipse Temurin 21 JRE Alpine) |

---

## Estructura del Proyecto

```
apps/backend/
├── build.gradle                    # Dependencias y plugins
├── settings.gradle                 # Nombre del proyecto Gradle
├── gradle/                         # Gradle wrapper
└── src/
    └── main/
        ├── java/com/archaeologist/
        │   ├── ArchaeologistApplication.java   # Entry point Spring Boot
        │   ├── application/
        │   │   └── dto/                        # Data Transfer Objects
        │   ├── domain/
        │   │   ├── model/                      # Entidades de dominio
        │   │   │   ├── AnalysisJob.java        # Job de análisis
        │   │   │   ├── JobStatus.java          # Enum de estados
        │   │   │   ├── AgentResult.java        # Resultado por agente
        │   │   │   ├── AgentStatus.java        # Estado de cada agente
        │   │   │   └── Project.java            # Entidad proyecto
        │   │   ├── repository/                 # Interfaces de persistencia
        │   │   └── service/                    # Lógica de negocio
        │   └── infrastructure/
        │       ├── client/
        │       │   ├── AnalyzerClient.java     # WebClient → Analyzer service
        │       │   ├── AnalyzerJobStatus.java  # DTO status del Analyzer
        │       │   └── GraphData.java          # DTO grafo de dependencias
        │       ├── config/                     # Configuración Spring beans
        │       ├── persistence/                # Implementaciones JPA
        │       ├── scheduling/                 # Tareas programadas (polling)
        │       └── web/
        │           ├── controller/
        │           │   ├── AnalysisJobController.java   # POST/GET/DELETE /api/v1/jobs
        │           │   ├── ChatController.java          # POST /api/v1/chat (SSE relay)
        │           │   ├── ExportController.java        # GET /api/v1/export/kiro/{id}
        │           │   ├── GraphController.java         # GET /api/v1/graph/{id}
        │           │   ├── ProjectsController.java      # Gestión de proyectos
        │           │   └── ReportController.java        # GET /api/v1/reports/{id}
        │           └── webhook/
        │               └── WebhookController.java       # POST /api/webhooks/*
        └── resources/
            ├── application.yml                 # Configuración Spring
            └── db/migration/
                └── V1__initial_schema.sql      # Schema inicial (pgvector)
```

---

## Endpoints API

### Jobs (Análisis)

| Método | Path | Descripción |
|---|---|---|
| `POST` | `/api/v1/jobs` | Inicia análisis de un repositorio (`{ "repoUrl": "..." }`) |
| `GET` | `/api/v1/jobs/{jobId}` | Consulta estado del job (polling) |
| `DELETE` | `/api/v1/jobs/{jobId}` | Cancela/elimina un job |

### Chat RAG

| Método | Path | Descripción |
|---|---|---|
| `POST` | `/api/v1/chat` | Pregunta al chat (SSE stream relay desde Analyzer) |

### Grafo de Dependencias

| Método | Path | Parámetros | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/graph/{projectId}` | `module`, `edgeType`, `depth` | Obtiene grafo de dependencias |

### Reportes

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/api/v1/reports/{projectId}` | Reporte completo de arquitectura |

### Exportación

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/api/v1/export/kiro/{projectId}` | Descarga Kiro Spec como `.md` |

### Webhooks (internos)

| Método | Path | Descripción |
|---|---|---|
| `POST` | `/api/webhooks/analysis-complete` | Notificación del Analyzer al completar |

### Actuator

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/actuator/health` | Health check (detallado) |
| `GET` | `/actuator/info` | Info de la aplicación |

---

## Variables de Entorno

| Variable | Default | Descripción |
|---|---|---|
| `SERVER_PORT` | `8080` | Puerto del servidor |
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://localhost:5432/archaeologist` | URL de conexión JDBC |
| `SPRING_DATASOURCE_USERNAME` | `archaeologist` | Usuario de la DB |
| `SPRING_DATASOURCE_PASSWORD` | `archaeologist_secret` | Contraseña de la DB |
| `WEBHOOK_SECRET` | `shared_webhook_secret` | Secreto HMAC-SHA256 compartido con Analyzer |
| `WEBHOOK_BASE_URL` | `http://backend:8080` | URL base para webhooks (usado por Analyzer) |
| `ANALYZER_BASE_URL` | `http://analyzer:8000` | URL base del servicio Analyzer |

---

## Desarrollo Local

### Prerequisitos

- Java 21 (recomendado: SDKMAN o Eclipse Temurin)
- PostgreSQL 15 con extensión pgvector
- Gradle 8.x (o usar el wrapper `./gradlew`)

### Ejecutar

```bash
# Desde apps/backend/

# 1. Configurar variables (o usar defaults con Docker Compose DB)
export SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/archaeologist
export SPRING_DATASOURCE_USERNAME=archaeologist
export SPRING_DATASOURCE_PASSWORD=archaeologist_secret

# 2. Build
./gradlew build

# 3. Run
./gradlew bootRun

# El servidor arranca en http://localhost:8080
```

### Con Docker Compose (recomendado)

```bash
# Desde la raíz del proyecto
docker compose build backend
docker compose up db backend
```

---

## Testing

```bash
# Unit tests
./gradlew test

# Framework: JUnit 5 + Reactor Test
# Los tests usan Spring Boot Test con contexto auto-configurado
```

---

## Build Docker

El Dockerfile usa multi-stage build:

1. **Stage Build**: `gradle:8-jdk21` — compila el JAR con `gradle bootJar`
2. **Stage Runtime**: `eclipse-temurin:21-jre-alpine` — ejecuta el JAR (~150MB imagen final)

```bash
# Build manual (desde raíz del proyecto)
docker build -f docker/backend/Dockerfile -t archaeologist-backend .
```

---

## Migraciones (Flyway)

Las migraciones viven en `src/main/resources/db/migration/`:

| Archivo | Descripción |
|---|---|
| `V1__initial_schema.sql` | Schema inicial: tablas de proyectos, jobs, pgvector |

Flyway se ejecuta automáticamente al arrancar la aplicación (`spring.flyway.enabled=true`).

### Crear nueva migración

```bash
# Naming convention: V{N}__{description}.sql
# Ejemplo: V2__add_agent_results_table.sql
```

---

## Troubleshooting

### Flyway no aplica migraciones

- **Causa**: La tabla `flyway_schema_history` ya tiene un checksum diferente.
- **Solución**: Si es desarrollo local, borrar la tabla y reiniciar. En producción, usar `flyway repair`.

```sql
-- Solo en desarrollo local:
DROP TABLE IF EXISTS flyway_schema_history;
```

### WebClient timeout al llamar Analyzer

- **Causa**: El Analyzer tarda más de 10s en responder (repos grandes).
- **Config**: Ajustar `analyzer.timeout.rest-seconds` en `application.yml`.
- **Síntoma**: Log `ReadTimeoutException` o `ConnectTimeoutException`.

### Health check falla en Docker

- **Causa**: El backend necesita ~30-40s para arrancar (JVM warmup + Flyway).
- **Solución**: El `docker-compose.yml` usa `start_period: 40s`. Si persiste, aumentar a 60s.

### SSE streaming se corta

- **Causa**: Proxy intermedio (nginx) cierra la conexión.
- **Solución**: El nginx ya está configurado con `proxy_buffering off` y `proxy_read_timeout 600s`.

### Base de datos no disponible

- **Síntoma**: `Connection refused` al arrancar.
- **Solución**: Verificar que PostgreSQL está corriendo y acepta conexiones en el puerto configurado.

```bash
# Verificar conectividad
pg_isready -h localhost -p 5432
```
