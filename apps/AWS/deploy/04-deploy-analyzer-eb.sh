#!/usr/bin/env bash
# =============================================================================
# Software Archaeologist — Deploy Analyzer to Elastic Beanstalk
#
# Creates an EB application and environment for the Analyzer service using
# Docker platform on a single-instance t3.medium (tree-sitter parsing needs
# more RAM than t3.micro).
#
# Usage:
#   chmod +x 04-deploy-analyzer-eb.sh
#   ./04-deploy-analyzer-eb.sh
#
# Prerequisites:
#   - AWS CLI v2 installed and configured
#   - EB CLI installed (pip install awsebcli)
#   - The following environment variables set (or in .data/.env):
#       DATABASE_URL          — PostgreSQL asyncpg connection string
#       WEBHOOK_SECRET        — HMAC signing secret shared with Backend
#       AWS_ACCESS_KEY_ID     — IAM credentials for Bedrock/S3 access
#       AWS_SECRET_ACCESS_KEY — IAM credentials for Bedrock/S3 access
#       BACKEND_EB_URL        — Backend EB environment URL (from 03 script)
#   - S3 bucket for source bundles (created by 01-* or 02-* scripts)
#   - RDS instance accessible from EB environment
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Variables — adjust before running
# ---------------------------------------------------------------------------
APP_NAME="archaeologist-analyzer"
ENV_NAME="archaeologist-analyzer-prod"
PLATFORM="64bit Amazon Linux 2023 v4.4.4 running Docker"
INSTANCE_TYPE="t3.medium"
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
S3_BUCKET="${EB_S3_BUCKET:-archaeologist-deploy-${AWS_REGION}}"

# Source bundle configuration
BUNDLE_DIR="/tmp/eb-analyzer-bundle"
VERSION_LABEL="${APP_NAME}-$(date +%Y%m%d-%H%M%S)"
BUNDLE_FILE="${VERSION_LABEL}.zip"

# Paths relative to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ANALYZER_SRC="${PROJECT_ROOT}/apps/analyzer"
EB_DOCKERFILE="${SCRIPT_DIR}/eb/analyzer/Dockerfile"

# Environment variables for the Analyzer (read from env or prompt)
DATABASE_URL="${DATABASE_URL:-}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-}"
BACKEND_EB_URL="${BACKEND_EB_URL:-}"
APP_AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
APP_AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"

echo "=== Software Archaeologist — Analyzer EB Deployment ==="
echo "Application : ${APP_NAME}"
echo "Environment : ${ENV_NAME}"
echo "Region      : ${AWS_REGION}"
echo "Instance    : ${INSTANCE_TYPE}"
echo "Platform    : Docker (Amazon Linux 2023)"
echo ""

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
echo "[0/8] Pre-flight checks..."

if [[ -z "${DATABASE_URL}" ]]; then
  echo "ERROR: DATABASE_URL not set. Export it or add to .data/.env"
  echo "       Example: postgresql+asyncpg://user:pass@your-rds-host:5432/archaeologist"
  exit 1
fi

if [[ -z "${WEBHOOK_SECRET}" ]]; then
  echo "ERROR: WEBHOOK_SECRET not set. Must match the Backend's configured secret."
  exit 1
fi

if [[ -z "${BACKEND_EB_URL}" ]]; then
  echo "WARNING: BACKEND_EB_URL not set. The analyzer won't be able to call back to the backend."
  echo "         You can update this later with: aws elasticbeanstalk update-environment"
  BACKEND_EB_URL="http://localhost:8080"
fi

echo "      All pre-flight checks passed."
echo ""

# ---------------------------------------------------------------------------
# Step 1: Create EB Application
# ---------------------------------------------------------------------------
echo "[1/8] Creating Elastic Beanstalk application '${APP_NAME}'..."

aws elasticbeanstalk create-application \
  --application-name "${APP_NAME}" \
  --description "Software Archaeologist Analyzer — AI-powered code analysis service" \
  --tags Key=Project,Value=software-archaeologist \
         Key=Service,Value=analyzer \
         Key=ManagedBy,Value=deploy-script \
  --region "${AWS_REGION}" \
  2>/dev/null || echo "      (Application may already exist — continuing)"

echo "      Application ready."

# ---------------------------------------------------------------------------
# Step 2: Package source bundle
#
# EB with Docker expects a Dockerfile at the root of the source bundle.
# We assemble: Dockerfile + requirements.txt + src/ directory.
# ---------------------------------------------------------------------------
echo "[2/8] Packaging source bundle..."

# Clean previous bundle
rm -rf "${BUNDLE_DIR}"
mkdir -p "${BUNDLE_DIR}"

# Copy the EB-compatible Dockerfile to bundle root
cp "${EB_DOCKERFILE}" "${BUNDLE_DIR}/Dockerfile"

# Copy analyzer source and requirements
cp "${ANALYZER_SRC}/requirements.txt" "${BUNDLE_DIR}/requirements.txt"
cp -r "${ANALYZER_SRC}/src" "${BUNDLE_DIR}/src"

# Create the zip bundle
cd "${BUNDLE_DIR}"
zip -r "/tmp/${BUNDLE_FILE}" . -x "*.pyc" "__pycache__/*" ".git/*"
cd -

BUNDLE_SIZE=$(du -h "/tmp/${BUNDLE_FILE}" | cut -f1)
echo "      Bundle created: ${BUNDLE_FILE} (${BUNDLE_SIZE})"

# ---------------------------------------------------------------------------
# Step 3: Upload source bundle to S3
# ---------------------------------------------------------------------------
echo "[3/8] Uploading source bundle to S3..."

# Ensure the S3 bucket exists
aws s3 mb "s3://${S3_BUCKET}" --region "${AWS_REGION}" 2>/dev/null || true

aws s3 cp "/tmp/${BUNDLE_FILE}" "s3://${S3_BUCKET}/analyzer/${BUNDLE_FILE}" \
  --region "${AWS_REGION}"

echo "      Uploaded to s3://${S3_BUCKET}/analyzer/${BUNDLE_FILE}"

# ---------------------------------------------------------------------------
# Step 4: Create application version
# ---------------------------------------------------------------------------
echo "[4/8] Creating application version '${VERSION_LABEL}'..."

aws elasticbeanstalk create-application-version \
  --application-name "${APP_NAME}" \
  --version-label "${VERSION_LABEL}" \
  --source-bundle S3Bucket="${S3_BUCKET}",S3Key="analyzer/${BUNDLE_FILE}" \
  --description "Automated deployment $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --region "${AWS_REGION}"

echo "      Version created."

# ---------------------------------------------------------------------------
# Step 5: Create environment with Docker platform
#
# Single-instance (no load balancer) to keep costs low for MVP.
# t3.medium provides 4 GB RAM needed for tree-sitter parsing of large repos.
# ---------------------------------------------------------------------------
echo "[5/8] Creating environment '${ENV_NAME}'..."

aws elasticbeanstalk create-environment \
  --application-name "${APP_NAME}" \
  --environment-name "${ENV_NAME}" \
  --version-label "${VERSION_LABEL}" \
  --solution-stack-name "${PLATFORM}" \
  --tier Name=WebServer,Type=Standard \
  --option-settings \
    Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value="${INSTANCE_TYPE}" \
    Namespace=aws:autoscaling:launchconfiguration,OptionName=IamInstanceProfile,Value=aws-elasticbeanstalk-ec2-role \
    Namespace=aws:elasticbeanstalk:environment,OptionName=EnvironmentType,Value=SingleInstance \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=DATABASE_URL,Value="${DATABASE_URL}" \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=BACKEND_URL,Value="${BACKEND_EB_URL}" \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=WEBHOOK_SECRET,Value="${WEBHOOK_SECRET}" \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=AWS_ACCESS_KEY_ID,Value="${APP_AWS_ACCESS_KEY_ID}" \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=AWS_SECRET_ACCESS_KEY,Value="${APP_AWS_SECRET_ACCESS_KEY}" \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=AWS_REGION,Value="${AWS_REGION}" \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=BEDROCK_MODEL_ID,Value="us.anthropic.claude-sonnet-4-5-20250929-v1:0" \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=BEDROCK_EMBEDDING_MODEL_ID,Value="amazon.titan-embed-text-v2:0" \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=MAX_REPO_SIZE_BYTES,Value="524288000" \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=MAX_FILE_COUNT,Value="50000" \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=TEMP_REPO_DIR,Value="/tmp/repos" \
    Namespace=aws:elasticbeanstalk:application:environment,OptionName=LOG_LEVEL,Value="INFO" \
    Namespace=aws:elasticbeanstalk:healthreporting:system,OptionName=SystemType,Value=enhanced \
    Namespace=aws:elasticbeanstalk:cloudwatch:logs,OptionName=StreamLogs,Value=true \
    Namespace=aws:elasticbeanstalk:cloudwatch:logs,OptionName=RetentionInDays,Value=7 \
  --region "${AWS_REGION}"

echo "      Environment creation initiated."

# ---------------------------------------------------------------------------
# Step 6: Wait for environment to be ready
# ---------------------------------------------------------------------------
echo "[6/8] Waiting for environment to become ready (this may take 5-10 minutes)..."

aws elasticbeanstalk wait environment-updated \
  --application-name "${APP_NAME}" \
  --environment-names "${ENV_NAME}" \
  --region "${AWS_REGION}"

echo "      Environment is ready!"

# ---------------------------------------------------------------------------
# Step 7: Get environment URL
# ---------------------------------------------------------------------------
echo "[7/8] Retrieving environment URL..."

ENV_URL=$(aws elasticbeanstalk describe-environments \
  --application-name "${APP_NAME}" \
  --environment-names "${ENV_NAME}" \
  --query "Environments[0].CNAME" \
  --output text \
  --region "${AWS_REGION}")

echo "      Environment URL: http://${ENV_URL}"

# ---------------------------------------------------------------------------
# Step 8: Verify health endpoint
# ---------------------------------------------------------------------------
echo "[8/8] Verifying health endpoint..."

HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://${ENV_URL}/health" || echo "000")

if [[ "${HEALTH_STATUS}" == "200" ]]; then
  echo "      ✓ Health check passed (HTTP ${HEALTH_STATUS})"
else
  echo "      ⚠ Health check returned HTTP ${HEALTH_STATUS}"
  echo "      The environment may still be starting up. Retry in a few minutes:"
  echo "        curl http://${ENV_URL}/health"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Application  : ${APP_NAME}"
echo "Environment  : ${ENV_NAME}"
echo "URL          : http://${ENV_URL}"
echo "Health check : http://${ENV_URL}/health"
echo "Version      : ${VERSION_LABEL}"
echo "Instance     : ${INSTANCE_TYPE} (single instance, no LB)"
echo ""
echo "Useful commands:"
echo "  aws elasticbeanstalk describe-environment-health --environment-name ${ENV_NAME} --attribute-names All"
echo "  aws elasticbeanstalk request-environment-info --environment-name ${ENV_NAME} --info-type tail"
echo "  aws elasticbeanstalk terminate-environment --environment-name ${ENV_NAME}"
echo ""
echo "To update environment variables later:"
echo "  aws elasticbeanstalk update-environment --environment-name ${ENV_NAME} \\"
echo "    --option-settings Namespace=aws:elasticbeanstalk:application:environment,OptionName=KEY,Value=VALUE"
