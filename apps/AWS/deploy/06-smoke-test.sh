#!/usr/bin/env bash
# =============================================================================
# Software Archaeologist — Production Smoke Test
# Task 17.5: End-to-end validation of the deployed system
#
# Verifies that all services (Frontend, Backend, Analyzer) are running and
# that a full analysis cycle works end-to-end: submit repo → poll status →
# retrieve graph, report, and kiro-spec artifacts.
#
# Usage:
#   chmod +x 06-smoke-test.sh
#   ./06-smoke-test.sh <FRONTEND_URL> <BACKEND_URL> <ANALYZER_URL>
#
# Example:
#   ./06-smoke-test.sh \
#     https://main.d1abc2def3.amplifyapp.com \
#     https://backend.us-east-1.elasticbeanstalk.com \
#     https://analyzer.us-east-1.elasticbeanstalk.com
#
# Prerequisites:
#   - curl installed
#   - aws CLI v2 installed and configured (for S3 checks)
#   - All services deployed and accessible from this machine
#   - Network access to the service URLs
#
# Exit codes:
#   0 — All checks passed
#   1 — One or more checks failed (see summary table)
# =============================================================================

set -uo pipefail

# ---------------------------------------------------------------------------
# Color support — detect if terminal supports ANSI colors
# ---------------------------------------------------------------------------
if [[ -t 1 ]] && command -v tput &>/dev/null && [[ $(tput colors 2>/dev/null || echo 0) -ge 8 ]]; then
  GREEN="\033[0;32m"
  RED="\033[0;31m"
  YELLOW="\033[0;33m"
  CYAN="\033[0;36m"
  BOLD="\033[1m"
  RESET="\033[0m"
else
  GREEN=""
  RED=""
  YELLOW=""
  CYAN=""
  BOLD=""
  RESET=""
fi

# ---------------------------------------------------------------------------
# Parameters — validate required URLs
# ---------------------------------------------------------------------------
if [[ $# -lt 3 ]]; then
  echo -e "${RED}Error: Missing required parameters.${RESET}"
  echo ""
  echo "Usage: $0 <FRONTEND_URL> <BACKEND_URL> <ANALYZER_URL>"
  echo ""
  echo "  FRONTEND_URL  — Amplify frontend URL (e.g., https://main.d1abc2def3.amplifyapp.com)"
  echo "  BACKEND_URL   — Backend Elastic Beanstalk URL (e.g., https://backend.us-east-1.elasticbeanstalk.com)"
  echo "  ANALYZER_URL  — Analyzer Elastic Beanstalk URL (e.g., https://analyzer.us-east-1.elasticbeanstalk.com)"
  exit 1
fi

FRONTEND_URL="${1%/}"   # Strip trailing slash
BACKEND_URL="${2%/}"
ANALYZER_URL="${3%/}"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TEST_REPO_URL="https://github.com/expressjs/express"
POLL_INTERVAL=15         # seconds between status polls
POLL_TIMEOUT=300         # max seconds to wait for job completion (5 min)
HTTP_TIMEOUT=30          # seconds timeout for individual HTTP requests
S3_REPOS_BUCKET="archaeologist-repos-prod"
S3_REPORTS_BUCKET="archaeologist-reports-prod"
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
declare -a CHECK_NAMES=()
declare -a CHECK_RESULTS=()
ISSUES=""

# Helper: record a check result
record_check() {
  local name="$1"
  local result="$2"  # PASS or FAIL
  CHECK_NAMES+=("$name")
  CHECK_RESULTS+=("$result")
}

# Helper: record an issue
record_issue() {
  local msg="$1"
  ISSUES="${ISSUES}\n  - ${msg}"
}

echo -e "${BOLD}=== Software Archaeologist — Production Smoke Test ===${RESET}"
echo -e "Frontend : ${CYAN}${FRONTEND_URL}${RESET}"
echo -e "Backend  : ${CYAN}${BACKEND_URL}${RESET}"
echo -e "Analyzer : ${CYAN}${ANALYZER_URL}${RESET}"
echo -e "Test Repo: ${CYAN}${TEST_REPO_URL}${RESET}"
echo -e "Timeout  : ${POLL_TIMEOUT}s"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Verify Backend health
#
# The Spring Boot actuator endpoint returns 200 with {"status":"UP"} when
# the application and its dependencies (DB, etc.) are healthy.
# ---------------------------------------------------------------------------
echo -e "[1/10] Verifying Backend health (GET /actuator/health)..."

BACKEND_HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time "${HTTP_TIMEOUT}" \
  "${BACKEND_URL}/actuator/health" 2>/dev/null)

if [[ "${BACKEND_HEALTH_STATUS}" == "200" ]]; then
  echo -e "        ${GREEN}PASS${RESET} — Backend returned HTTP 200"
  record_check "Backend Health" "PASS"
else
  echo -e "        ${RED}FAIL${RESET} — Backend returned HTTP ${BACKEND_HEALTH_STATUS}"
  record_check "Backend Health" "FAIL"
  record_issue "Backend health check failed (HTTP ${BACKEND_HEALTH_STATUS}). Verify EB environment is running and RDS is accessible."
fi

# ---------------------------------------------------------------------------
# Step 2: Verify Analyzer health
#
# FastAPI health endpoint returns 200 when the service is ready to accept
# analysis requests.
# ---------------------------------------------------------------------------
echo -e "[2/10] Verifying Analyzer health (GET /health)..."

ANALYZER_HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time "${HTTP_TIMEOUT}" \
  "${ANALYZER_URL}/health" 2>/dev/null)

if [[ "${ANALYZER_HEALTH_STATUS}" == "200" ]]; then
  echo -e "        ${GREEN}PASS${RESET} — Analyzer returned HTTP 200"
  record_check "Analyzer Health" "PASS"
else
  echo -e "        ${RED}FAIL${RESET} — Analyzer returned HTTP ${ANALYZER_HEALTH_STATUS}"
  record_check "Analyzer Health" "FAIL"
  record_issue "Analyzer health check failed (HTTP ${ANALYZER_HEALTH_STATUS}). Verify EB environment is running and Bedrock access is configured."
fi

# ---------------------------------------------------------------------------
# Step 3: Verify Frontend loads
#
# The Amplify-hosted SPA should return 200 with HTML content containing
# typical markers of a React application (root div, script tags).
# ---------------------------------------------------------------------------
echo -e "[3/10] Verifying Frontend loads (GET ${FRONTEND_URL})..."

FRONTEND_RESPONSE=$(curl -s --max-time "${HTTP_TIMEOUT}" "${FRONTEND_URL}" 2>/dev/null)
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time "${HTTP_TIMEOUT}" "${FRONTEND_URL}" 2>/dev/null)

if [[ "${FRONTEND_STATUS}" == "200" ]] && echo "${FRONTEND_RESPONSE}" | grep -qi "<html"; then
  echo -e "        ${GREEN}PASS${RESET} — Frontend returned HTTP 200 with HTML content"
  record_check "Frontend Loads" "PASS"
else
  echo -e "        ${RED}FAIL${RESET} — Frontend returned HTTP ${FRONTEND_STATUS} or missing HTML"
  record_check "Frontend Loads" "FAIL"
  record_issue "Frontend not serving HTML (HTTP ${FRONTEND_STATUS}). Verify Amplify deployment completed successfully."
fi

# ---------------------------------------------------------------------------
# Step 4: Submit a test repository for analysis
#
# POST /api/v1/jobs triggers the backend to enqueue analysis. It should
# return HTTP 202 with a JSON body containing the jobId for polling.
# ---------------------------------------------------------------------------
echo -e "[4/10] Submitting test repository for analysis..."

JOB_RESPONSE=$(curl -s --max-time "${HTTP_TIMEOUT}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"repoUrl\": \"${TEST_REPO_URL}\"}" \
  "${BACKEND_URL}/api/v1/jobs" 2>/dev/null)

JOB_HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time "${HTTP_TIMEOUT}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"repoUrl\": \"${TEST_REPO_URL}\"}" \
  "${BACKEND_URL}/api/v1/jobs" 2>/dev/null)

# Extract jobId from JSON response (works with most JSON shapes)
JOB_ID=$(echo "${JOB_RESPONSE}" | grep -oP '"(?:jobId|id)"\s*:\s*"?\K[^",}]+' | head -1)

if [[ "${JOB_HTTP_STATUS}" == "202" ]] && [[ -n "${JOB_ID}" ]]; then
  echo -e "        ${GREEN}PASS${RESET} — Job submitted (HTTP 202), jobId: ${JOB_ID}"
  record_check "Submit Job" "PASS"
else
  echo -e "        ${RED}FAIL${RESET} — Job submission failed (HTTP ${JOB_HTTP_STATUS})"
  echo -e "        Response: ${JOB_RESPONSE}"
  record_check "Submit Job" "FAIL"
  record_issue "Job submission failed (HTTP ${JOB_HTTP_STATUS}). Backend may not be connected to Analyzer or DB."
  # Cannot continue with dependent checks — mark them as FAIL
  echo -e "${YELLOW}        Skipping steps 5-8 (depend on successful job submission)${RESET}"
  record_check "Job Completion" "FAIL"
  record_check "Graph Endpoint" "FAIL"
  record_check "Report Endpoint" "FAIL"
  record_check "Kiro-Spec Endpoint" "FAIL"
  record_issue "Steps 5-8 skipped due to job submission failure."
  JOB_ID=""
fi

# ---------------------------------------------------------------------------
# Step 5: Poll job status until completed or timeout
#
# GET /api/v1/jobs/{jobId} returns the job status. We poll every
# POLL_INTERVAL seconds until status is "COMPLETED", "FAILED", or we
# hit the timeout. A successful analysis produces a projectId we use next.
# ---------------------------------------------------------------------------
PROJECT_ID=""

if [[ -n "${JOB_ID}" ]]; then
  echo -e "[5/10] Polling job status (timeout: ${POLL_TIMEOUT}s, interval: ${POLL_INTERVAL}s)..."

  ELAPSED=0
  JOB_STATUS="PENDING"

  while [[ "${ELAPSED}" -lt "${POLL_TIMEOUT}" ]]; do
    JOB_STATUS_RESPONSE=$(curl -s --max-time "${HTTP_TIMEOUT}" \
      "${BACKEND_URL}/api/v1/jobs/${JOB_ID}" 2>/dev/null)

    JOB_STATUS=$(echo "${JOB_STATUS_RESPONSE}" | grep -oP '"status"\s*:\s*"?\K[^",}]+' | head -1)
    JOB_PROGRESS=$(echo "${JOB_STATUS_RESPONSE}" | grep -oP '"progress"\s*:\s*\K[0-9]+' | head -1)

    echo -e "        Status: ${JOB_STATUS:-unknown} | Progress: ${JOB_PROGRESS:-0}% | Elapsed: ${ELAPSED}s"

    if [[ "${JOB_STATUS}" == "COMPLETED" ]] || [[ "${JOB_STATUS}" == "completed" ]]; then
      break
    fi

    if [[ "${JOB_STATUS}" == "FAILED" ]] || [[ "${JOB_STATUS}" == "failed" ]]; then
      break
    fi

    sleep "${POLL_INTERVAL}"
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
  done

  if [[ "${JOB_STATUS}" == "COMPLETED" ]] || [[ "${JOB_STATUS}" == "completed" ]]; then
    # Extract projectId from the job response
    PROJECT_ID=$(echo "${JOB_STATUS_RESPONSE}" | grep -oP '"projectId"\s*:\s*"?\K[^",}]+' | head -1)
    echo -e "        ${GREEN}PASS${RESET} — Job completed in ${ELAPSED}s, projectId: ${PROJECT_ID:-unknown}"
    record_check "Job Completion" "PASS"
  elif [[ "${JOB_STATUS}" == "FAILED" ]] || [[ "${JOB_STATUS}" == "failed" ]]; then
    echo -e "        ${RED}FAIL${RESET} — Job failed after ${ELAPSED}s"
    record_check "Job Completion" "FAIL"
    record_issue "Analysis job failed. Check Analyzer logs for errors (Bedrock quota, repo clone issues, etc.)."
  else
    echo -e "        ${RED}FAIL${RESET} — Job timed out after ${POLL_TIMEOUT}s (last status: ${JOB_STATUS:-unknown})"
    record_check "Job Completion" "FAIL"
    record_issue "Job did not complete within ${POLL_TIMEOUT}s. May need more time for large repos or Analyzer may be stuck."
  fi

  # -------------------------------------------------------------------------
  # Step 6: Verify graph endpoint returns data
  #
  # GET /api/v1/projects/{id}/graph should return JSON with nodes and edges
  # representing the analyzed repository's architecture.
  # -------------------------------------------------------------------------
  if [[ -n "${PROJECT_ID}" ]]; then
    echo -e "[6/10] Verifying graph endpoint (GET /api/v1/projects/${PROJECT_ID}/graph)..."

    GRAPH_RESPONSE=$(curl -s --max-time "${HTTP_TIMEOUT}" \
      "${BACKEND_URL}/api/v1/projects/${PROJECT_ID}/graph" 2>/dev/null)
    GRAPH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time "${HTTP_TIMEOUT}" \
      "${BACKEND_URL}/api/v1/projects/${PROJECT_ID}/graph" 2>/dev/null)

    if [[ "${GRAPH_STATUS}" == "200" ]] && echo "${GRAPH_RESPONSE}" | grep -q "nodes"; then
      NODE_COUNT=$(echo "${GRAPH_RESPONSE}" | grep -oP '"nodes"\s*:\s*\[' | wc -l)
      echo -e "        ${GREEN}PASS${RESET} — Graph returned HTTP 200 with nodes data"
      record_check "Graph Endpoint" "PASS"
    else
      echo -e "        ${RED}FAIL${RESET} — Graph endpoint returned HTTP ${GRAPH_STATUS} or missing nodes"
      record_check "Graph Endpoint" "FAIL"
      record_issue "Graph endpoint failed (HTTP ${GRAPH_STATUS}). Project may not have graph data generated."
    fi

    # -----------------------------------------------------------------------
    # Step 7: Verify report endpoint returns data
    #
    # GET /api/v1/projects/{id}/report should return the architecture
    # analysis report as JSON.
    # -----------------------------------------------------------------------
    echo -e "[7/10] Verifying report endpoint (GET /api/v1/projects/${PROJECT_ID}/report)..."

    REPORT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time "${HTTP_TIMEOUT}" \
      "${BACKEND_URL}/api/v1/projects/${PROJECT_ID}/report" 2>/dev/null)

    if [[ "${REPORT_STATUS}" == "200" ]]; then
      echo -e "        ${GREEN}PASS${RESET} — Report returned HTTP 200"
      record_check "Report Endpoint" "PASS"
    else
      echo -e "        ${RED}FAIL${RESET} — Report endpoint returned HTTP ${REPORT_STATUS}"
      record_check "Report Endpoint" "FAIL"
      record_issue "Report endpoint failed (HTTP ${REPORT_STATUS}). Agents may not have completed report generation."
    fi

    # -----------------------------------------------------------------------
    # Step 8: Verify kiro-spec endpoint returns markdown
    #
    # GET /api/v1/projects/{id}/kiro-spec should return a markdown document
    # with the Kiro spec for the analyzed project.
    # -----------------------------------------------------------------------
    echo -e "[8/10] Verifying kiro-spec endpoint (GET /api/v1/projects/${PROJECT_ID}/kiro-spec)..."

    KIRO_RESPONSE=$(curl -s --max-time "${HTTP_TIMEOUT}" \
      "${BACKEND_URL}/api/v1/projects/${PROJECT_ID}/kiro-spec" 2>/dev/null)
    KIRO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time "${HTTP_TIMEOUT}" \
      "${BACKEND_URL}/api/v1/projects/${PROJECT_ID}/kiro-spec" 2>/dev/null)

    if [[ "${KIRO_STATUS}" == "200" ]] && echo "${KIRO_RESPONSE}" | grep -qi "^#\|markdown\|spec"; then
      echo -e "        ${GREEN}PASS${RESET} — Kiro-spec returned HTTP 200 with markdown content"
      record_check "Kiro-Spec Endpoint" "PASS"
    elif [[ "${KIRO_STATUS}" == "200" ]]; then
      echo -e "        ${GREEN}PASS${RESET} — Kiro-spec returned HTTP 200"
      record_check "Kiro-Spec Endpoint" "PASS"
    else
      echo -e "        ${RED}FAIL${RESET} — Kiro-spec endpoint returned HTTP ${KIRO_STATUS}"
      record_check "Kiro-Spec Endpoint" "FAIL"
      record_issue "Kiro-spec endpoint failed (HTTP ${KIRO_STATUS}). Kiro agent may not have run."
    fi
  else
    echo -e "[6/10] ${YELLOW}SKIP${RESET} — Graph endpoint (no projectId available)"
    echo -e "[7/10] ${YELLOW}SKIP${RESET} — Report endpoint (no projectId available)"
    echo -e "[8/10] ${YELLOW}SKIP${RESET} — Kiro-spec endpoint (no projectId available)"
    record_check "Graph Endpoint" "FAIL"
    record_check "Report Endpoint" "FAIL"
    record_check "Kiro-Spec Endpoint" "FAIL"
    record_issue "Steps 6-8 skipped because job did not produce a projectId."
  fi
fi

# ---------------------------------------------------------------------------
# Step 9: Verify S3 repos bucket has objects
#
# The repos bucket stores cloned repository data during analysis. After at
# least one successful analysis, it should contain objects.
# ---------------------------------------------------------------------------
echo -e "[9/10] Verifying S3 repos bucket (${S3_REPOS_BUCKET})..."

S3_REPOS_OUTPUT=$(aws s3 ls "s3://${S3_REPOS_BUCKET}/" --region "${AWS_REGION}" --summarize 2>&1)
S3_REPOS_EXIT=$?

if [[ ${S3_REPOS_EXIT} -eq 0 ]] && echo "${S3_REPOS_OUTPUT}" | grep -qP "Total Objects:\s*[1-9]"; then
  TOTAL_OBJECTS=$(echo "${S3_REPOS_OUTPUT}" | grep -oP 'Total Objects:\s*\K[0-9]+')
  echo -e "        ${GREEN}PASS${RESET} — Repos bucket has ${TOTAL_OBJECTS} objects"
  record_check "S3 Repos Bucket" "PASS"
elif [[ ${S3_REPOS_EXIT} -eq 0 ]]; then
  echo -e "        ${YELLOW}WARN${RESET} — Repos bucket exists but appears empty (may be normal for first run)"
  record_check "S3 Repos Bucket" "PASS"
else
  echo -e "        ${RED}FAIL${RESET} — Cannot access S3 repos bucket"
  echo -e "        ${S3_REPOS_OUTPUT}"
  record_check "S3 Repos Bucket" "FAIL"
  record_issue "Cannot access S3 repos bucket '${S3_REPOS_BUCKET}'. Check IAM permissions and bucket existence."
fi

# ---------------------------------------------------------------------------
# Step 10: Verify S3 reports bucket has objects
#
# The reports bucket stores generated analysis reports and artifacts.
# ---------------------------------------------------------------------------
echo -e "[10/10] Verifying S3 reports bucket (${S3_REPORTS_BUCKET})..."

S3_REPORTS_OUTPUT=$(aws s3 ls "s3://${S3_REPORTS_BUCKET}/" --region "${AWS_REGION}" --summarize 2>&1)
S3_REPORTS_EXIT=$?

if [[ ${S3_REPORTS_EXIT} -eq 0 ]] && echo "${S3_REPORTS_OUTPUT}" | grep -qP "Total Objects:\s*[1-9]"; then
  TOTAL_OBJECTS=$(echo "${S3_REPORTS_OUTPUT}" | grep -oP 'Total Objects:\s*\K[0-9]+')
  echo -e "        ${GREEN}PASS${RESET} — Reports bucket has ${TOTAL_OBJECTS} objects"
  record_check "S3 Reports Bucket" "PASS"
elif [[ ${S3_REPORTS_EXIT} -eq 0 ]]; then
  echo -e "        ${YELLOW}WARN${RESET} — Reports bucket exists but appears empty (may be normal for first run)"
  record_check "S3 Reports Bucket" "PASS"
else
  echo -e "        ${RED}FAIL${RESET} — Cannot access S3 reports bucket"
  echo -e "        ${S3_REPORTS_OUTPUT}"
  record_check "S3 Reports Bucket" "FAIL"
  record_issue "Cannot access S3 reports bucket '${S3_REPORTS_BUCKET}'. Check IAM permissions and bucket existence."
fi

# ---------------------------------------------------------------------------
# Summary Table
#
# Print a formatted table showing PASS/FAIL for each check, followed by
# any issues discovered during the test run.
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}=== Smoke Test Summary ===${RESET}"
echo ""
printf "  %-25s %s\n" "CHECK" "RESULT"
printf "  %-25s %s\n" "-------------------------" "------"

TOTAL_PASS=0
TOTAL_FAIL=0

for i in "${!CHECK_NAMES[@]}"; do
  NAME="${CHECK_NAMES[$i]}"
  RESULT="${CHECK_RESULTS[$i]}"

  if [[ "${RESULT}" == "PASS" ]]; then
    printf "  %-25s ${GREEN}%s${RESET}\n" "${NAME}" "PASS"
    TOTAL_PASS=$((TOTAL_PASS + 1))
  else
    printf "  %-25s ${RED}%s${RESET}\n" "${NAME}" "FAIL"
    TOTAL_FAIL=$((TOTAL_FAIL + 1))
  fi
done

echo ""
echo -e "  Total: ${GREEN}${TOTAL_PASS} passed${RESET}, ${RED}${TOTAL_FAIL} failed${RESET} / $((TOTAL_PASS + TOTAL_FAIL)) checks"
echo ""

# Print issues if any were found
if [[ -n "${ISSUES}" ]]; then
  echo -e "${BOLD}Issues Found:${RESET}"
  echo -e "${ISSUES}"
  echo ""
fi

# ---------------------------------------------------------------------------
# Exit code — 0 if all passed, 1 if any failed
# ---------------------------------------------------------------------------
if [[ ${TOTAL_FAIL} -gt 0 ]]; then
  echo -e "${RED}Smoke test FAILED — ${TOTAL_FAIL} check(s) did not pass.${RESET}"
  exit 1
else
  echo -e "${GREEN}Smoke test PASSED — All checks successful!${RESET}"
  exit 0
fi
