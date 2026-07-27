#!/usr/bin/env bash
# =============================================================================
# Software Archaeologist — Deployment Script
#
# Deploys services to AWS (Elastic Beanstalk via CodeBuild).
# Supports multi-environment: production (main) and demo (any branch).
#
# Usage:
#   ./scripts/deploy.sh [service] [options]
#
# Services:
#   frontend    — Deploy frontend (Next.js)
#   backend     — Deploy backend (Spring Boot)
#   analyzer    — Deploy analyzer (FastAPI)
#   all         — Deploy all services (backend → analyzer → frontend)
#
# Options:
#   --branch <name>   Git branch to deploy (default: main = production)
#                     Any branch other than 'main' deploys to demo environment
#   --skip-build      Skip CodeBuild, deploy existing latest artifact
#   --help            Show this help
#
# Examples:
#   ./scripts/deploy.sh all                    # Deploy all to production (main)
#   ./scripts/deploy.sh frontend               # Deploy only frontend to production
#   ./scripts/deploy.sh all --branch develop   # Deploy all from 'develop' to demo env
#   ./scripts/deploy.sh backend --branch feature/auth  # Deploy backend from feature branch to demo
#
# Environment mapping:
#   Branch 'main' → Production environments (archaeologist-*-prod)
#   Any other branch → Demo environments (archaeologist-*-demo)
#
# Prerequisites:
#   - AWS CLI v2 configured (aws configure)
#   - Git repo pushed to GitHub with the target branch
#   - CodeBuild projects exist: archaeologist-{frontend,backend,analyzer}-build
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REGION="us-east-1"
ACCOUNT_ID="989735870266"
S3_BUCKET="archaeologist-eb-bundles-${ACCOUNT_ID}-${REGION}"

# CodeBuild projects
declare -A CODEBUILD_PROJECTS=(
  [frontend]="archaeologist-frontend-build"
  [backend]="archaeologist-backend-build"
  [analyzer]="archaeologist-analyzer-build"
)

# EB Applications
declare -A EB_APPS=(
  [frontend]="archaeologist-frontend"
  [backend]="archaeologist-backend"
  [analyzer]="archaeologist-analyzer"
)

# S3 artifact keys (CodeBuild outputs here)
declare -A S3_KEYS=(
  [frontend]="frontend/v3.zip"
  [backend]="backend/v2.zip"
  [analyzer]="analyzer/v2.zip"
)

# Health check paths
declare -A HEALTH_PATHS=(
  [frontend]="/"
  [backend]="/actuator/health"
  [analyzer]="/health"
)

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
if [[ -t 1 ]] && command -v tput &>/dev/null && [[ $(tput colors 2>/dev/null || echo 0) -ge 8 ]]; then
  GREEN="\033[0;32m"; RED="\033[0;31m"; YELLOW="\033[1;33m"
  CYAN="\033[0;36m"; BOLD="\033[1m"; RESET="\033[0m"
else
  GREEN=""; RED=""; YELLOW=""; CYAN=""; BOLD=""; RESET=""
fi

log_info()  { echo -e "${GREEN}[✓]${RESET} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${RESET} $1"; }
log_error() { echo -e "${RED}[✗]${RESET} $1"; }
log_step()  { echo -e "${BOLD}${CYAN}[→]${RESET} $1"; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
SERVICE=""
BRANCH="main"
SKIP_BUILD=false

while [[ $# -gt 0 ]]; do
  case $1 in
    frontend|backend|analyzer|all)
      SERVICE="$1"; shift ;;
    --branch|-b)
      BRANCH="$2"; shift 2 ;;
    --skip-build)
      SKIP_BUILD=true; shift ;;
    --help|-h)
      head -40 "$0" | grep "^#" | sed 's/^# \?//'; exit 0 ;;
    *)
      log_error "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "$SERVICE" ]]; then
  log_error "No service specified. Usage: $0 [frontend|backend|analyzer|all] [--branch <name>]"
  exit 1
fi

# ---------------------------------------------------------------------------
# Environment resolution
# ---------------------------------------------------------------------------
if [[ "$BRANCH" == "main" ]]; then
  ENV_SUFFIX="prod"
  ENV_LABEL="PRODUCTION"
else
  ENV_SUFFIX="demo"
  ENV_LABEL="DEMO (branch: $BRANCH)"
fi

# EB Environment names
declare -A EB_ENVS=(
  [frontend]="arch-frontend-${ENV_SUFFIX}"
  [backend]="archaeologist-backend-${ENV_SUFFIX}"
  [analyzer]="archaeologist-analyzer-${ENV_SUFFIX}"
)

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  Software Archaeologist — Deploy${RESET}"
echo -e "${BOLD}═══════════════════════════════════════════════════${RESET}"
echo -e "  Environment : ${CYAN}${ENV_LABEL}${RESET}"
echo -e "  Branch      : ${CYAN}${BRANCH}${RESET}"
echo -e "  Service(s)  : ${CYAN}${SERVICE}${RESET}"
echo -e "  Region      : ${REGION}"
echo -e "${BOLD}═══════════════════════════════════════════════════${RESET}"
echo ""

# ---------------------------------------------------------------------------
# Verify AWS access
# ---------------------------------------------------------------------------
if ! aws sts get-caller-identity --region "$REGION" &>/dev/null; then
  log_error "Cannot authenticate with AWS. Run 'aws configure' first."
  exit 1
fi
log_info "AWS authentication verified"

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

wait_for_build() {
  local build_id="$1"
  local max_wait=600
  local elapsed=0

  while [[ $elapsed -lt $max_wait ]]; do
    local status
    status=$(aws codebuild batch-get-builds \
      --ids "$build_id" \
      --query 'builds[0].buildStatus' \
      --output text \
      --region "$REGION" 2>/dev/null)

    case "$status" in
      SUCCEEDED)
        log_info "Build succeeded (${elapsed}s)"
        return 0 ;;
      FAILED|FAULT|TIMED_OUT|STOPPED)
        log_error "Build failed: $status"
        echo "  View logs: aws codebuild batch-get-builds --ids $build_id --region $REGION"
        return 1 ;;
      IN_PROGRESS)
        printf "."
        sleep 15
        elapsed=$((elapsed + 15)) ;;
    esac
  done

  log_error "Build timed out after ${max_wait}s"
  return 1
}

wait_for_environment() {
  local env_name="$1"
  local max_wait=300
  local elapsed=0

  while [[ $elapsed -lt $max_wait ]]; do
    local status
    status=$(aws elasticbeanstalk describe-environments \
      --environment-names "$env_name" \
      --query 'Environments[0].Status' \
      --output text \
      --region "$REGION" 2>/dev/null)

    if [[ "$status" == "Ready" ]]; then
      local health
      health=$(aws elasticbeanstalk describe-environments \
        --environment-names "$env_name" \
        --query 'Environments[0].Health' \
        --output text \
        --region "$REGION" 2>/dev/null)
      log_info "Environment ready (Health: $health)"
      return 0
    fi

    printf "."
    sleep 15
    elapsed=$((elapsed + 15))
  done

  log_warn "Timed out waiting (may still be updating)"
  return 0
}

ensure_demo_environment() {
  local service="$1"
  local env_name="${EB_ENVS[$service]}"
  local app_name="${EB_APPS[$service]}"

  # Check if demo environment exists
  local env_status
  env_status=$(aws elasticbeanstalk describe-environments \
    --application-name "$app_name" \
    --environment-names "$env_name" \
    --query "Environments[?Status!='Terminated'] | [0].Status" \
    --output text \
    --region "$REGION" 2>/dev/null || echo "None")

  if [[ "$env_status" == "None" || "$env_status" == "null" ]]; then
    log_step "Creating demo environment '$env_name'..."

    # Get the prod environment's configuration as reference
    local prod_env="$(echo "$env_name" | sed 's/-demo$/-prod/')"
    local solution_stack
    solution_stack=$(aws elasticbeanstalk describe-environments \
      --environment-names "$prod_env" \
      --query 'Environments[0].SolutionStackName' \
      --output text \
      --region "$REGION" 2>/dev/null || echo "64bit Amazon Linux 2023 v4.13.4 running Docker")

    # Create the demo environment cloning prod's config
    aws elasticbeanstalk create-environment \
      --application-name "$app_name" \
      --environment-name "$env_name" \
      --solution-stack-name "$solution_stack" \
      --option-settings \
        "Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.small" \
        "Namespace=aws:autoscaling:launchconfiguration,OptionName=IamInstanceProfile,Value=aws-elasticbeanstalk-ec2-role" \
        "Namespace=aws:elasticbeanstalk:environment,OptionName=EnvironmentType,Value=SingleInstance" \
        "Namespace=aws:elasticbeanstalk:environment,OptionName=ServiceRole,Value=aws-elasticbeanstalk-service-role" \
      --tags Key=Project,Value=software-archaeologist Key=Environment,Value=demo Key=Branch,Value="$BRANCH" \
      --region "$REGION" \
      --no-cli-pager

    log_info "Demo environment created. Waiting for it to be ready..."
    wait_for_environment "$env_name"
  else
    log_info "Demo environment '$env_name' exists (Status: $env_status)"
  fi
}

deploy_service() {
  local service="$1"
  local env_name="${EB_ENVS[$service]}"
  local app_name="${EB_APPS[$service]}"
  local codebuild_project="${CODEBUILD_PROJECTS[$service]}"
  local s3_key="${S3_KEYS[$service]}"
  local timestamp
  timestamp=$(date +%Y%m%d-%H%M%S)
  local version_label="${service}-${ENV_SUFFIX}-${timestamp}"

  echo ""
  log_step "Deploying ${BOLD}${service}${RESET} → ${CYAN}${env_name}${RESET}"
  echo ""

  # If demo, ensure environment exists
  if [[ "$ENV_SUFFIX" == "demo" ]]; then
    ensure_demo_environment "$service"
  fi

  # Step 1: Build (unless --skip-build)
  if [[ "$SKIP_BUILD" == false ]]; then
    log_step "Starting CodeBuild (project: $codebuild_project, branch: $BRANCH)..."

    local build_id
    build_id=$(aws codebuild start-build \
      --project-name "$codebuild_project" \
      --source-version "$BRANCH" \
      --query 'build.id' \
      --output text \
      --region "$REGION")

    echo "  Build ID: $build_id"
    printf "  Waiting"

    if ! wait_for_build "$build_id"; then
      log_error "Build failed for $service. Aborting."
      return 1
    fi
  else
    log_warn "Skipping build (--skip-build). Using existing artifact."
  fi

  # Step 2: Create application version
  log_step "Creating EB version: $version_label"

  aws elasticbeanstalk create-application-version \
    --application-name "$app_name" \
    --version-label "$version_label" \
    --source-bundle "S3Bucket=$S3_BUCKET,S3Key=$s3_key" \
    --description "Deploy from branch '$BRANCH' at $timestamp" \
    --region "$REGION" \
    --no-cli-pager >/dev/null

  # Step 3: Deploy to environment
  log_step "Updating environment: $env_name → $version_label"

  aws elasticbeanstalk update-environment \
    --environment-name "$env_name" \
    --version-label "$version_label" \
    --region "$REGION" \
    --no-cli-pager >/dev/null

  # Step 4: Wait for ready
  printf "  Waiting"
  wait_for_environment "$env_name"

  # Step 5: Get URL and verify
  local cname
  cname=$(aws elasticbeanstalk describe-environments \
    --environment-names "$env_name" \
    --query 'Environments[0].CNAME' \
    --output text \
    --region "$REGION" 2>/dev/null)

  local health_path="${HEALTH_PATHS[$service]}"
  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://${cname}${health_path}" 2>/dev/null || echo "000")

  if [[ "$http_code" == "200" ]]; then
    log_info "${service} deployed successfully"
    echo -e "  URL: ${CYAN}http://${cname}${RESET}"
    echo -e "  Health: ${GREEN}HTTP 200${RESET}"
  else
    log_warn "${service} deployed but health returned HTTP $http_code (may still be starting)"
    echo -e "  URL: ${CYAN}http://${cname}${RESET}"
  fi
}

# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

if [[ "$SERVICE" == "all" ]]; then
  SERVICES=(backend analyzer frontend)
else
  SERVICES=("$SERVICE")
fi

FAILED=()

for svc in "${SERVICES[@]}"; do
  if ! deploy_service "$svc"; then
    FAILED+=("$svc")
  fi
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  Deploy Summary${RESET}"
echo -e "${BOLD}═══════════════════════════════════════════════════${RESET}"
echo -e "  Environment: ${ENV_LABEL}"
echo -e "  Branch:      ${BRANCH}"
echo ""

for svc in "${SERVICES[@]}"; do
  local env_name="${EB_ENVS[$svc]}"
  local cname
  cname=$(aws elasticbeanstalk describe-environments \
    --environment-names "$env_name" \
    --query 'Environments[0].CNAME' \
    --output text \
    --region "$REGION" 2>/dev/null || echo "pending")

  if [[ " ${FAILED[*]} " =~ " $svc " ]]; then
    echo -e "  ${RED}✗${RESET} ${svc}: FAILED"
  else
    echo -e "  ${GREEN}✓${RESET} ${svc}: ${CYAN}http://${cname}${RESET}"
  fi
done

echo ""

if [[ ${#FAILED[@]} -gt 0 ]]; then
  log_error "Deploy completed with failures: ${FAILED[*]}"
  exit 1
else
  log_info "Deploy completed successfully!"
fi

# ---------------------------------------------------------------------------
# Rollback instructions
# ---------------------------------------------------------------------------
echo ""
echo "To rollback, use:"
echo "  aws elasticbeanstalk update-environment --environment-name <env> --version-label <previous-version>"
echo ""
echo "To list versions:"
echo "  aws elasticbeanstalk describe-application-versions --application-name <app> --query 'ApplicationVersions[*].VersionLabel'"
echo ""

# ---------------------------------------------------------------------------
# Cleanup demo (optional)
# ---------------------------------------------------------------------------
if [[ "$ENV_SUFFIX" == "demo" ]]; then
  echo "To tear down the demo environment when done:"
  for svc in "${SERVICES[@]}"; do
    echo "  aws elasticbeanstalk terminate-environment --environment-name ${EB_ENVS[$svc]} --region $REGION"
  done
  echo ""
fi
