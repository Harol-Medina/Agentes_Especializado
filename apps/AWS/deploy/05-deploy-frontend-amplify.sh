#!/usr/bin/env bash
# =============================================================================
# Software Archaeologist — Frontend Deployment to AWS Amplify
# Task 17.4: Deploy Frontend (Next.js 14+) to AWS Amplify Hosting
#
# Creates an Amplify app connected to a Git repository, configures build
# settings for a monorepo layout (apps/frontend), sets the backend URL as
# an environment variable, creates a branch for auto-builds, and triggers
# the initial deployment.
#
# Usage:
#   chmod +x 05-deploy-frontend-amplify.sh
#   ./05-deploy-frontend-amplify.sh
#
# Prerequisites:
#   - AWS CLI v2 installed and configured
#   - Repository already pushed to GitHub or GitLab (Amplify requires remote)
#   - A GitHub personal access token (PAT) with `repo` scope, OR
#     GitLab token with `read_repository` and `read_api` permissions
#   - Backend already deployed (EB URL needed for NEXT_PUBLIC_API_URL)
#   - Caller must have amplify:* and iam:CreateServiceRole permissions
#
# Required environment variables (set before running or modify below):
#   REPO_URL          — Full HTTPS URL of the Git repository
#   GIT_ACCESS_TOKEN  — GitHub PAT or GitLab token for repo access
#   BACKEND_URL       — Backend Elastic Beanstalk URL (e.g., http://my-app.us-east-1.elasticbeanstalk.com)
#   BRANCH_NAME       — Git branch to deploy (defaults to 'main')
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Variables — adjust before running
# ---------------------------------------------------------------------------
APP_NAME="software-archaeologist-frontend"
BRANCH_NAME="${BRANCH_NAME:-main}"

# These MUST be set by the user before running the script
REPO_URL="${REPO_URL:?ERROR: Set REPO_URL to your Git repository HTTPS URL}"
GIT_ACCESS_TOKEN="${GIT_ACCESS_TOKEN:?ERROR: Set GIT_ACCESS_TOKEN to your GitHub/GitLab token}"
BACKEND_URL="${BACKEND_URL:?ERROR: Set BACKEND_URL to your Backend Elastic Beanstalk URL}"

# AWS context
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Path to the Amplify build spec (relative to this script)
BUILD_SPEC_FILE="$(dirname "$0")/amplify/amplify.yml"

echo "=== Software Archaeologist — Amplify Frontend Deployment ==="
echo "Account     : ${ACCOUNT_ID}"
echo "Region      : ${AWS_REGION}"
echo "App Name    : ${APP_NAME}"
echo "Repository  : ${REPO_URL}"
echo "Branch      : ${BRANCH_NAME}"
echo "Backend URL : ${BACKEND_URL}"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Create the Amplify App
#
# Connects Amplify to the Git repository. The access token allows Amplify to
# clone the repo and set up webhooks for auto-build on push. The platform is
# set to WEB_COMPUTE for Next.js SSR support (server-side rendering via
# Amplify's compute backend).
# ---------------------------------------------------------------------------
echo "[1/5] Creating Amplify app '${APP_NAME}' connected to repository..."

# Read the build spec file content
BUILD_SPEC=$(cat "${BUILD_SPEC_FILE}")

APP_ID=$(aws amplify create-app \
  --name "${APP_NAME}" \
  --repository "${REPO_URL}" \
  --access-token "${GIT_ACCESS_TOKEN}" \
  --platform "WEB_COMPUTE" \
  --build-spec "${BUILD_SPEC}" \
  --environment-variables "NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
  --custom-rules '[{"source":"/<*>","target":"/index.html","status":"404-200"}]' \
  --tags Key=Project,Value=software-archaeologist \
         Key=ManagedBy,Value=deploy-script \
         Key=Component,Value=frontend \
  --region "${AWS_REGION}" \
  --query "app.appId" \
  --output text)

echo "      Amplify App ID: ${APP_ID}"
echo "      Build spec loaded from: ${BUILD_SPEC_FILE}"

# ---------------------------------------------------------------------------
# Step 2: Configure environment variables
#
# NEXT_PUBLIC_API_URL is the critical env var — it tells the Next.js frontend
# where to reach the backend API. This is baked into the build at compile time
# since it uses the NEXT_PUBLIC_ prefix (client-side accessible).
# ---------------------------------------------------------------------------
echo "[2/5] Configuring environment variables..."

aws amplify update-app \
  --app-id "${APP_ID}" \
  --environment-variables \
    "NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
    "_CUSTOM_IMAGE=amplify:al2023" \
    "AMPLIFY_MONOREPO_APP_ROOT=apps/frontend" \
  --region "${AWS_REGION}" \
  > /dev/null

echo "      NEXT_PUBLIC_API_URL = ${BACKEND_URL}"
echo "      AMPLIFY_MONOREPO_APP_ROOT = apps/frontend"

# ---------------------------------------------------------------------------
# Step 3: Create branch (auto-build enabled)
#
# Creates a branch configuration in Amplify. When code is pushed to this
# branch, Amplify automatically triggers a build and deploys the new version.
# Framework is set to 'Next.js - SSR' for proper server-side rendering support.
# ---------------------------------------------------------------------------
echo "[3/5] Creating branch '${BRANCH_NAME}' with auto-build enabled..."

aws amplify create-branch \
  --app-id "${APP_ID}" \
  --branch-name "${BRANCH_NAME}" \
  --framework "Next.js - SSR" \
  --stage "PRODUCTION" \
  --enable-auto-build \
  --environment-variables "NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
  --region "${AWS_REGION}" \
  > /dev/null

echo "      Branch '${BRANCH_NAME}' configured for auto-build."
echo "      Stage: PRODUCTION"

# ---------------------------------------------------------------------------
# Step 4: Trigger initial deployment
#
# Starts the first build job for the branch. Subsequent deployments happen
# automatically when code is pushed to the branch (via webhook). You can
# monitor progress in the Amplify Console or with `aws amplify get-job`.
# ---------------------------------------------------------------------------
echo "[4/5] Triggering initial deployment..."

JOB_ID=$(aws amplify start-job \
  --app-id "${APP_ID}" \
  --branch-name "${BRANCH_NAME}" \
  --job-type "RELEASE" \
  --region "${AWS_REGION}" \
  --query "jobSummary.jobId" \
  --output text)

echo "      Build job started. Job ID: ${JOB_ID}"
echo "      Monitor at: https://${AWS_REGION}.console.aws.amazon.com/amplify/apps/${APP_ID}/overview"

# ---------------------------------------------------------------------------
# Step 5: Print deployment info and next steps
#
# The default Amplify domain follows the pattern:
#   https://<branch>.<app-id>.amplifyapp.com
# For custom domains, use the instructions below after the initial deploy
# completes successfully.
# ---------------------------------------------------------------------------
echo "[5/5] Retrieving deployment details..."

DEFAULT_DOMAIN=$(aws amplify get-app \
  --app-id "${APP_ID}" \
  --region "${AWS_REGION}" \
  --query "app.defaultDomain" \
  --output text)

echo ""
echo "=== Deployment Initiated ==="
echo ""
echo "Amplify App ID     : ${APP_ID}"
echo "Default Domain     : https://${BRANCH_NAME}.${DEFAULT_DOMAIN}"
echo "Console URL        : https://${AWS_REGION}.console.aws.amazon.com/amplify/apps/${APP_ID}/overview"
echo "Build Job ID       : ${JOB_ID}"
echo ""
echo "The build typically takes 3-5 minutes. Check progress with:"
echo "  aws amplify get-job --app-id ${APP_ID} --branch-name ${BRANCH_NAME} --job-id ${JOB_ID} --region ${AWS_REGION}"
echo ""
echo "=== Custom Domain Setup (Optional) ==="
echo ""
echo "To connect a custom domain after deployment succeeds:"
echo ""
echo "  1. Add domain association:"
echo "     aws amplify create-domain-association \\"
echo "       --app-id ${APP_ID} \\"
echo "       --domain-name yourdomain.com \\"
echo "       --sub-domain-settings prefix='',branchName=${BRANCH_NAME} \\"
echo "       --region ${AWS_REGION}"
echo ""
echo "  2. Amplify will provide CNAME records. Add them to your DNS provider."
echo ""
echo "  3. Verify domain ownership:"
echo "     aws amplify get-domain-association \\"
echo "       --app-id ${APP_ID} \\"
echo "       --domain-name yourdomain.com \\"
echo "       --region ${AWS_REGION}"
echo ""
echo "  4. Amplify automatically provisions an SSL certificate via ACM."
echo ""
echo "=== Important Notes ==="
echo ""
echo "  - The repository MUST be pushed to GitHub/GitLab BEFORE running this script."
echo "  - NEXT_PUBLIC_API_URL is embedded at build time (not runtime). If the backend"
echo "    URL changes, you must trigger a new build for the frontend."
echo "  - To update the backend URL later:"
echo "    aws amplify update-app --app-id ${APP_ID} --environment-variables NEXT_PUBLIC_API_URL=<new-url>"
echo "    aws amplify start-job --app-id ${APP_ID} --branch-name ${BRANCH_NAME} --job-type RELEASE"
echo ""
