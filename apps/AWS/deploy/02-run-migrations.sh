#!/usr/bin/env bash
# =============================================================================
# Software Archaeologist — Flyway Migration Runner
# Task 17.1: Run Database Migrations Against Production RDS
#
# Builds the backend Docker image and runs Flyway migrations against the
# production RDS instance using a temporary container.
#
# The backend application uses Spring Boot + Flyway. Migrations live in:
#   apps/backend/src/main/resources/db/migration/
#
# This script:
#   1. Validates that required environment variables are set
#   2. Builds the backend Docker image (multi-stage, includes migrations)
#   3. Runs the container with Flyway in "migrate" mode via Spring Boot
#   4. Reports success or failure
#
# Usage:
#   chmod +x 02-run-migrations.sh
#   ./02-run-migrations.sh
#
# Prerequisites:
#   - Docker installed and running
#   - .data/.env.prod configured with valid RDS connection details
#   - RDS instance running and reachable (01-create-rds.sh completed)
#   - psql client available (for connectivity check)
#
# Environment Variables Required (from .data/.env.prod):
#   SPRING_DATASOURCE_URL      - jdbc:postgresql://HOST:5432/archaeologist
#   SPRING_DATASOURCE_USERNAME - Database username
#   SPRING_DATASOURCE_PASSWORD - Database password
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.data/.env.prod"
DOCKER_CONTEXT="${PROJECT_ROOT}"
DOCKERFILE="${PROJECT_ROOT}/docker/backend/Dockerfile"
IMAGE_NAME="archaeologist-backend"
IMAGE_TAG="migrations-$(date +%Y%m%d-%H%M%S)"
CONTAINER_NAME="archaeologist-flyway-runner"

echo "=== Software Archaeologist — Flyway Migration Runner ==="
echo "Project Root : ${PROJECT_ROOT}"
echo "Env File     : ${ENV_FILE}"
echo "Image        : ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Validate environment
#
# Ensure the .env.prod file exists and contains the required database
# connection variables. Without these, Flyway cannot connect to RDS.
# ---------------------------------------------------------------------------
echo "[1/4] Validating environment..."

if [ ! -f "${ENV_FILE}" ]; then
  echo "ERROR: ${ENV_FILE} not found."
  echo "       Run 01-create-rds.sh first, then update .data/.env.prod with connection details."
  exit 1
fi

# Source the env file to get variables
set -a
source "${ENV_FILE}"
set +a

# Validate required variables
if [ -z "${SPRING_DATASOURCE_URL:-}" ]; then
  echo "ERROR: SPRING_DATASOURCE_URL is not set in ${ENV_FILE}"
  exit 1
fi

if [ -z "${SPRING_DATASOURCE_USERNAME:-}" ]; then
  echo "ERROR: SPRING_DATASOURCE_USERNAME is not set in ${ENV_FILE}"
  exit 1
fi

if [ -z "${SPRING_DATASOURCE_PASSWORD:-}" ]; then
  echo "ERROR: SPRING_DATASOURCE_PASSWORD is not set in ${ENV_FILE}"
  exit 1
fi

echo "      Environment variables validated."
echo "      Target: ${SPRING_DATASOURCE_URL}"

# ---------------------------------------------------------------------------
# Step 2: Test database connectivity
#
# Before building the image, verify we can reach the database.
# Extracts host/port from the JDBC URL for a quick psql ping.
# ---------------------------------------------------------------------------
echo "[2/4] Testing database connectivity..."

# Extract host and port from JDBC URL: jdbc:postgresql://HOST:PORT/DB
DB_HOST=$(echo "${SPRING_DATASOURCE_URL}" | sed -n 's|.*://\([^:]*\):.*|\1|p')
DB_PORT=$(echo "${SPRING_DATASOURCE_URL}" | sed -n 's|.*://[^:]*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo "${SPRING_DATASOURCE_URL}" | sed -n 's|.*/\([^?]*\).*|\1|p')

if command -v psql &> /dev/null; then
  PGPASSWORD="${SPRING_DATASOURCE_PASSWORD}" psql \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${SPRING_DATASOURCE_USERNAME}" \
    -d "${DB_NAME}" \
    -c "SELECT 1;" > /dev/null 2>&1 && \
    echo "      Database is reachable." || \
    { echo "WARNING: Cannot connect to database. Migrations may fail."; echo "         Ensure the RDS instance is running and accessible from this machine."; }
else
  echo "      psql not found — skipping connectivity check."
  echo "      (Install postgresql-client for pre-flight validation)"
fi

# ---------------------------------------------------------------------------
# Step 3: Build the backend Docker image
#
# Uses the existing multi-stage Dockerfile which:
#   Stage 1: Compiles the Spring Boot app (includes Flyway migrations)
#   Stage 2: Creates a minimal JRE runtime image
#
# The Flyway migrations are bundled inside the JAR at:
#   classpath:db/migration/
# ---------------------------------------------------------------------------
echo "[3/4] Building backend Docker image..."

docker build \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" \
  -f "${DOCKERFILE}" \
  "${DOCKER_CONTEXT}"

echo "      Image built: ${IMAGE_NAME}:${IMAGE_TAG}"

# ---------------------------------------------------------------------------
# Step 4: Run Flyway migrations
#
# We start the Spring Boot app with a special profile trick:
#   - SPRING_FLYWAY_ENABLED=true (already default)
#   - The app will run migrations on startup, then we stop it
#
# We use --spring.main.web-application-type=none to prevent the web server
# from starting — we only need Flyway to run and exit.
#
# Alternative: We could use the Flyway CLI directly, but since migrations
# are bundled in the JAR and the project already uses Spring Boot's Flyway
# integration, this approach is simpler and doesn't require an extra tool.
# ---------------------------------------------------------------------------
echo "[4/4] Running Flyway migrations..."

# Remove any previous container with the same name
docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true

# Run the container with migration-only mode
# --spring.main.web-application-type=none prevents web server startup
# The app will:
#   1. Start Spring context
#   2. Run Flyway migrations
#   3. Exit (since there's no web server to keep it alive)
docker run \
  --name "${CONTAINER_NAME}" \
  --rm \
  -e "SPRING_DATASOURCE_URL=${SPRING_DATASOURCE_URL}" \
  -e "SPRING_DATASOURCE_USERNAME=${SPRING_DATASOURCE_USERNAME}" \
  -e "SPRING_DATASOURCE_PASSWORD=${SPRING_DATASOURCE_PASSWORD}" \
  -e "SPRING_FLYWAY_ENABLED=true" \
  -e "SPRING_MAIN_WEB_APPLICATION_TYPE=none" \
  -e "WEBHOOK_SECRET=${WEBHOOK_SECRET:-placeholder}" \
  "${IMAGE_NAME}:${IMAGE_TAG}" \
  java -jar app.jar --spring.main.web-application-type=none

MIGRATION_EXIT_CODE=$?

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
echo ""
if [ ${MIGRATION_EXIT_CODE} -eq 0 ]; then
  echo "=== Migrations Completed Successfully ==="
  echo ""
  echo "Flyway has applied all pending migrations to:"
  echo "  Host     : ${DB_HOST}"
  echo "  Port     : ${DB_PORT}"
  echo "  Database : ${DB_NAME}"
  echo ""
  echo "Tables created by V1__initial_schema.sql:"
  echo "  - analysis_jobs"
  echo "  - projects"
  echo "  - graph_nodes / graph_edges"
  echo "  - agent_results"
  echo "  - code_embeddings (with pgvector index)"
  echo "  - architecture_reports"
  echo "  - kiro_specs"
  echo ""
  echo "Next steps:"
  echo "  1. Verify tables: psql -h ${DB_HOST} -U ${SPRING_DATASOURCE_USERNAME} -d ${DB_NAME} -c '\\dt'"
  echo "  2. Deploy the backend application to Elastic Beanstalk."
  echo "  3. Deploy the analyzer service."
else
  echo "=== Migration FAILED (exit code: ${MIGRATION_EXIT_CODE}) ==="
  echo ""
  echo "Troubleshooting:"
  echo "  1. Check that the RDS instance is running and accessible."
  echo "  2. Verify credentials in .data/.env.prod are correct."
  echo "  3. Check Docker logs: docker logs ${CONTAINER_NAME}"
  echo "  4. Ensure pgvector extension was created (01-create-rds.sh step 6)."
  echo "  5. Try connecting manually:"
  echo "     PGPASSWORD='...' psql -h ${DB_HOST} -p ${DB_PORT} -U ${SPRING_DATASOURCE_USERNAME} -d ${DB_NAME}"
  exit ${MIGRATION_EXIT_CODE}
fi
