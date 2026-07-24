#!/usr/bin/env bash
# =============================================================================
# Software Archaeologist — Backend Deployment to Elastic Beanstalk
#
# Deploys the Spring Boot backend as a single-container Docker application
# on AWS Elastic Beanstalk. Uses the Docker platform (not Corretto/Java)
# so the build is identical to what runs locally via docker-compose.
#
# Usage:
#   chmod +x 03-deploy-backend-eb.sh
#   ./03-deploy-backend-eb.sh
#
# Prerequisites:
#   - AWS CLI v2 installed and configured
#   - Caller must have elasticbeanstalk:*, s3:PutObject, s3:GetObject,
#     s3:CreateBucket permissions (or use the kiro-archaeologist IAM user
#     with an expanded policy)
#   - .data/.env.prod exists with production environment variables
#   - apps/backend/ contains a buildable Gradle project
#
# What this script does:
#   1. Creates the EB application (if not exists)
#   2. Prepares a source bundle (Dockerfile + backend source)
#   3. Creates/uses S3 bucket for source bundles
#   4. Uploads the source bundle to S3
#   5. Creates an application version
#   6. Creates/updates the EB environment (Docker, t3.small, single instance)
#   7. Configures environment variables from .data/.env.prod
#   8. Waits for environment to be ready
#   9. Verifies health endpoint
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
APP_NAME="archaeologist-backend"
ENV_NAME="archaeologist-backend-prod"
PLATFORM="64bit Amazon Linux 2023 v4.4.4 running Docker"
INSTANCE_TYPE="t3.small"
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Paths — relative to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
BACKEND_SRC="${PROJECT_ROOT}/apps/backend"
EB_DOCKERFILE="${SCRIPT_DIR}/eb/backend/Dockerfile"
ENV_FILE="${PROJECT_ROOT}/.data/.env.prod"

# Source bundle
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
VERSION_LABEL="${APP_NAME}-${TIMESTAMP}"
BUNDLE_DIR="/tmp/${VERSION_LABEL}"
BUNDLE_ZIP="/tmp/${VERSION_LABEL}.zip"

# S3 bucket for EB source bundles
S3_BUCKET="archaeologist-eb-bundles-${ACCOUNT_ID}-${AWS_REGION}"

echo "=== Software Archaeologist — Backend EB Deployment ==="
echo "Application : ${APP_NAME}"
echo "Environment : ${ENV_NAME}"
echo "Region      : ${AWS_REGION}"
echo "Account     : ${ACCOUNT_ID}"
echo "Version     : ${VERSION_LABEL}"
echo "Backend src : ${BACKEND_SRC}"
echo ""

# ---------------------------------------------------------------------------
# Validation — Ensure required files exist before proceeding
# ---------------------------------------------------------------------------
if [ ! -d "${BACKEND_SRC}" ]; then
  echo "ERROR: Backend source not found at ${BACKEND_SRC}"
  echo "       Make sure you run this script from the project root context."
  exit 1
fi

if [ ! -f "${EB_DOCKERFILE}" ]; then
  echo "ERROR: EB Dockerfile not found at ${EB_DOCKERFILE}"
  echo "       Expected at apps/AWS/deploy/eb/backend/Dockerfile"
  exit 1
fi

if [ ! -f "${ENV_FILE}" ]; then
  echo "WARNING: .data/.env.prod not found at ${ENV_FILE}"
  echo "         Environment variables will need to be configured manually."
  echo "         Continuing without env vars..."
  ENV_FILE=""
fi

# ---------------------------------------------------------------------------
# Step 1: Create EB Application (idempotent — skips if already exists)
#
# The application is a logical container for environments, versions, and
# configurations. Creating it is free and has no running resources.
# ---------------------------------------------------------------------------
echo "[1/9] Creating Elastic Beanstalk application '${APP_NAME}'..."

if aws elasticbeanstalk describe-applications \
    --application-names "${APP_NAME}" \
    --query "Applications[0].ApplicationName" \
    --output text 2>/dev/null | grep -q "${APP_NAME}"; then
  echo "      Application already exists — skipping creation."
else
  aws elasticbeanstalk create-application \
    --application-name "${APP_NAME}" \
    --description "Software Archaeologist backend API (Spring Boot + Docker)" \
    --tags Key=Project,Value=software-archaeologist \
           Key=ManagedBy,Value=deploy-script
  echo "      Application created."
fi

# ---------------------------------------------------------------------------
# Step 2: Prepare source bundle
#
# EB Docker platform expects either:
#   a) A Dockerfile at the root of the source bundle, OR
#   b) A Dockerrun.aws.json (v1 for single container)
#
# We use option (a) with our EB-specific Dockerfile that expects the backend
# source at ./backend/ relative to itself. The bundle layout:
#
#   source-bundle.zip/
#   ├── Dockerfile
#   └── backend/
#       ├── build.gradle
#       ├── settings.gradle
#       ├── src/
#       └── ...
# ---------------------------------------------------------------------------
echo "[2/9] Preparing source bundle..."

# Clean up any previous bundle
rm -rf "${BUNDLE_DIR}" "${BUNDLE_ZIP}"
mkdir -p "${BUNDLE_DIR}"

# Copy the EB-specific Dockerfile to bundle root
cp "${EB_DOCKERFILE}" "${BUNDLE_DIR}/Dockerfile"

# Copy backend source (excluding build artifacts to keep bundle small)
rsync -a \
  --exclude='build/' \
  --exclude='.gradle/' \
  --exclude='bin/' \
  --exclude='out/' \
  "${BACKEND_SRC}/" "${BUNDLE_DIR}/backend/"

echo "      Bundle prepared at ${BUNDLE_DIR}"
echo "      Contents: Dockerfile + backend/ source"

# ---------------------------------------------------------------------------
# Step 3: Create zip archive for the source bundle
#
# EB requires the source bundle as a zip. The zip must have the Dockerfile
# at its root level (not nested in a subdirectory).
# ---------------------------------------------------------------------------
echo "[3/9] Creating zip archive..."

(cd "${BUNDLE_DIR}" && zip -r "${BUNDLE_ZIP}" . -x '*.git*')

BUNDLE_SIZE=$(du -h "${BUNDLE_ZIP}" | cut -f1)
echo "      Archive: ${BUNDLE_ZIP} (${BUNDLE_SIZE})"

# ---------------------------------------------------------------------------
# Step 4: Create S3 bucket for EB source bundles (idempotent)
#
# EB needs source bundles stored in S3. We use a dedicated bucket per
# account+region to avoid conflicts. The bucket name includes the account ID
# to ensure global uniqueness.
# ---------------------------------------------------------------------------
echo "[4/9] Ensuring S3 bucket '${S3_BUCKET}' exists..."

if aws s3api head-bucket --bucket "${S3_BUCKET}" 2>/dev/null; then
  echo "      Bucket already exists."
else
  # For us-east-1, CreateBucketConfiguration is not needed (and actually errors)
  if [ "${AWS_REGION}" = "us-east-1" ]; then
    aws s3api create-bucket \
      --bucket "${S3_BUCKET}" \
      --region "${AWS_REGION}"
  else
    aws s3api create-bucket \
      --bucket "${S3_BUCKET}" \
      --region "${AWS_REGION}" \
      --create-bucket-configuration LocationConstraint="${AWS_REGION}"
  fi
  echo "      Bucket created."
fi

# ---------------------------------------------------------------------------
# Step 5: Upload source bundle to S3
#
# The S3 key includes a timestamp so each deploy creates a unique version
# and we can roll back to any previous deployment.
# ---------------------------------------------------------------------------
echo "[5/9] Uploading source bundle to S3..."

S3_KEY="backend/${VERSION_LABEL}.zip"

aws s3 cp "${BUNDLE_ZIP}" "s3://${S3_BUCKET}/${S3_KEY}" --quiet

echo "      Uploaded: s3://${S3_BUCKET}/${S3_KEY}"

# ---------------------------------------------------------------------------
# Step 6: Create application version
#
# An application version is a labeled reference to the source bundle in S3.
# EB uses this to know what code to deploy when creating/updating environments.
# ---------------------------------------------------------------------------
echo "[6/9] Creating application version '${VERSION_LABEL}'..."

aws elasticbeanstalk create-application-version \
  --application-name "${APP_NAME}" \
  --version-label "${VERSION_LABEL}" \
  --source-bundle S3Bucket="${S3_BUCKET}",S3Key="${S3_KEY}" \
  --description "Automated deploy at ${TIMESTAMP}" \
  --no-auto-create-application

echo "      Version registered."

# ---------------------------------------------------------------------------
# Step 7: Create or update EB environment
#
# If the environment doesn't exist, create it. If it does, update it to the
# new version. The environment runs:
#   - Docker platform (builds from our Dockerfile)
#   - Single instance (no load balancer) — appropriate for MVP
#   - t3.small (2 vCPU, 2GB RAM) — sufficient for Spring Boot
#
# Environment variables are loaded from .data/.env.prod and passed as
# EB option settings. EB injects them into the Docker container at runtime.
# ---------------------------------------------------------------------------
echo "[7/9] Creating/updating environment '${ENV_NAME}'..."

# Build option-settings JSON for environment variables
OPTIONS_FILE="/tmp/${VERSION_LABEL}-options.json"
cat > "${OPTIONS_FILE}" << 'EOF'
[
  {
    "Namespace": "aws:autoscaling:launchconfiguration",
    "OptionName": "InstanceType",
    "Value": "t3.small"
  },
  {
    "Namespace": "aws:elasticbeanstalk:environment",
    "OptionName": "EnvironmentType",
    "Value": "SingleInstance"
  },
  {
    "Namespace": "aws:elasticbeanstalk:application:environment",
    "OptionName": "SERVER_PORT",
    "Value": "8080"
  },
  {
    "Namespace": "aws:elasticbeanstalk:environment:process:default",
    "OptionName": "HealthCheckPath",
    "Value": "/actuator/health"
  },
  {
    "Namespace": "aws:elasticbeanstalk:environment:process:default",
    "OptionName": "Port",
    "Value": "8080"
  }
]
EOF

# If .env.prod exists, parse it and add env vars to the options JSON
if [ -n "${ENV_FILE}" ] && [ -f "${ENV_FILE}" ]; then
  echo "      Loading environment variables from .data/.env.prod..."

  # Read env vars and append to options JSON (skip comments and empty lines)
  while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    # Remove surrounding quotes from value if present
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"

    # Only include relevant backend variables
    case "$key" in
      SPRING_DATASOURCE_URL|SPRING_DATASOURCE_USERNAME|SPRING_DATASOURCE_PASSWORD|\
      WEBHOOK_SECRET|WEBHOOK_BASE_URL|ANALYZER_BASE_URL|SERVER_PORT)
        # Append to options JSON using jq
        OPTIONS_FILE_TMP="${OPTIONS_FILE}.tmp"
        jq --arg key "$key" --arg val "$value" \
          '. += [{"Namespace": "aws:elasticbeanstalk:application:environment", "OptionName": $key, "Value": $val}]' \
          "${OPTIONS_FILE}" > "${OPTIONS_FILE_TMP}" && mv "${OPTIONS_FILE_TMP}" "${OPTIONS_FILE}"
        echo "      + ${key}=****"
        ;;
    esac
  done < "${ENV_FILE}"
fi

# Check if environment already exists
if aws elasticbeanstalk describe-environments \
    --application-name "${APP_NAME}" \
    --environment-names "${ENV_NAME}" \
    --query "Environments[?Status!='Terminated'] | [0].EnvironmentId" \
    --output text 2>/dev/null | grep -qv "None"; then

  echo "      Environment exists — updating to version '${VERSION_LABEL}'..."
  aws elasticbeanstalk update-environment \
    --application-name "${APP_NAME}" \
    --environment-name "${ENV_NAME}" \
    --version-label "${VERSION_LABEL}" \
    --option-settings "file://${OPTIONS_FILE}"
else
  echo "      Creating new environment '${ENV_NAME}'..."
  aws elasticbeanstalk create-environment \
    --application-name "${APP_NAME}" \
    --environment-name "${ENV_NAME}" \
    --solution-stack-name "${PLATFORM}" \
    --version-label "${VERSION_LABEL}" \
    --option-settings "file://${OPTIONS_FILE}" \
    --tags Key=Project,Value=software-archaeologist \
           Key=ManagedBy,Value=deploy-script
fi

echo "      Environment deployment initiated."

# ---------------------------------------------------------------------------
# Step 8: Wait for environment to be ready
#
# EB environments go through: Launching → Updating → Ready.
# This can take 5-10 minutes for Docker builds (it builds the image on the
# EC2 instance). We poll every 30 seconds up to 15 minutes.
# ---------------------------------------------------------------------------
echo "[8/9] Waiting for environment to become healthy (this may take 5-10 min)..."

MAX_WAIT=900  # 15 minutes
ELAPSED=0
INTERVAL=30

while [ ${ELAPSED} -lt ${MAX_WAIT} ]; do
  STATUS=$(aws elasticbeanstalk describe-environments \
    --application-name "${APP_NAME}" \
    --environment-names "${ENV_NAME}" \
    --query "Environments[0].Status" \
    --output text 2>/dev/null || echo "Unknown")

  HEALTH=$(aws elasticbeanstalk describe-environments \
    --application-name "${APP_NAME}" \
    --environment-names "${ENV_NAME}" \
    --query "Environments[0].Health" \
    --output text 2>/dev/null || echo "Unknown")

  echo "      Status: ${STATUS} | Health: ${HEALTH} (${ELAPSED}s elapsed)"

  if [ "${STATUS}" = "Ready" ] && [ "${HEALTH}" = "Green" ]; then
    echo "      Environment is healthy!"
    break
  fi

  if [ "${STATUS}" = "Terminated" ] || [ "${STATUS}" = "Terminating" ]; then
    echo "ERROR: Environment entered ${STATUS} state. Check EB console for details."
    exit 1
  fi

  sleep ${INTERVAL}
  ELAPSED=$((ELAPSED + INTERVAL))
done

if [ ${ELAPSED} -ge ${MAX_WAIT} ]; then
  echo "WARNING: Timed out waiting for environment. Check AWS console."
  echo "         Environment may still be launching."
fi

# ---------------------------------------------------------------------------
# Step 9: Print environment URL and verify health
#
# The EB environment URL is auto-generated (CNAME). We retrieve it and
# hit the /actuator/health endpoint to confirm the app is responding.
# ---------------------------------------------------------------------------
echo "[9/9] Retrieving environment URL and verifying health..."

ENV_URL=$(aws elasticbeanstalk describe-environments \
  --application-name "${APP_NAME}" \
  --environment-names "${ENV_NAME}" \
  --query "Environments[0].CNAME" \
  --output text)

echo ""
echo "      Environment URL: http://${ENV_URL}"
echo "      Health endpoint: http://${ENV_URL}/actuator/health"
echo ""

# Attempt health check (non-fatal if it fails — environment might still be warming up)
echo "      Checking health endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://${ENV_URL}/actuator/health" 2>/dev/null || echo "000")

if [ "${HTTP_STATUS}" = "200" ]; then
  echo "      Health check PASSED (HTTP 200)"
  HEALTH_BODY=$(curl -s "http://${ENV_URL}/actuator/health" 2>/dev/null)
  echo "      Response: ${HEALTH_BODY}"
else
  echo "      Health check returned HTTP ${HTTP_STATUS}"
  echo "      The application may still be starting up. Retry in 1-2 minutes."
fi

# ---------------------------------------------------------------------------
# Cleanup temporary files
# ---------------------------------------------------------------------------
rm -rf "${BUNDLE_DIR}" "${OPTIONS_FILE}"
echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Summary:"
echo "  Application    : ${APP_NAME}"
echo "  Environment    : ${ENV_NAME}"
echo "  Version        : ${VERSION_LABEL}"
echo "  URL            : http://${ENV_URL}"
echo "  Health check   : http://${ENV_URL}/actuator/health"
echo "  S3 bundle      : s3://${S3_BUCKET}/${S3_KEY}"
echo ""
echo "Next steps:"
echo "  1. Verify the health endpoint returns {\"status\":\"UP\"}"
echo "  2. Update WEBHOOK_BASE_URL in .data/.env.prod to http://${ENV_URL}"
echo "  3. Configure a custom domain (Route53 CNAME → ${ENV_URL})"
echo "  4. Consider enabling HTTPS with ACM certificate"
echo "  5. Monitor logs: aws elasticbeanstalk request-environment-info \\"
echo "       --environment-name ${ENV_NAME} --info-type tail"
