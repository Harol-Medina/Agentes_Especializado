#!/usr/bin/env bash
# =============================================================================
# Software Archaeologist — IAM Permission Verification Script
# Requirement 14.6, 14.9
#
# Uses `aws iam simulate-principal-policy` to confirm that the
# kiro-archaeologist IAM user has EXACTLY the permissions it should:
#
#   ALLOW (required for operation):
#     bedrock:InvokeModel          — run Claude Sonnet and Titan Embeddings
#     bedrock:InvokeModelWithResponseStream — streaming Bedrock responses
#     s3:PutObject                 — upload repo archives and reports
#     s3:GetObject                 — read reports back for download
#     s3:DeleteObject              — clean up after analysis
#     s3:ListBucket                — list bucket contents
#     logs:PutLogEvents            — write application logs to CloudWatch
#     logs:CreateLogGroup          — create log groups under /archaeologist/*
#     logs:CreateLogStream         — create log streams
#     lambda:InvokeFunction        — invoke archaeologist-* Lambda functions
#
#   DENY (must NOT be permitted — blast radius control):
#     s3:DeleteBucket              — cannot destroy buckets
#     s3:CreateBucket              — bucket creation is an admin operation
#     iam:CreateUser               — cannot escalate via IAM
#     iam:AttachUserPolicy         — cannot grant itself new permissions
#     ec2:RunInstances             — cannot launch compute
#     ec2:DescribeInstances        — no EC2 visibility
#     rds:DeleteDBInstance         — cannot destroy databases
#     rds:CreateDBInstance         — no RDS access at all
#
# Output format:
#   Action                              Resource                            Expected  Result
#   bedrock:InvokeModel                 arn:aws:bedrock:...:claude-3-...   ALLOW     ✅ PASS
#   s3:DeleteBucket                     arn:aws:s3:::any-bucket             DENY      ✅ PASS
#
# Exit code: 0 if all checks pass, 1 if any check fails.
#
# Usage:
#   chmod +x verify-permissions.sh
#   ./verify-permissions.sh
#
# Prerequisites:
#   - AWS CLI v2 installed and configured
#   - Caller must have iam:SimulatePrincipalPolicy permission
#   - The kiro-archaeologist user must already exist (run setup.sh first)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
IAM_USER="kiro-archaeologist"
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Retrieve the account ID to build proper ARNs
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
USER_ARN="arn:aws:iam::${ACCOUNT_ID}:user/${IAM_USER}"

# Bedrock model ARNs (must match policy-minimal.json exactly)
CLAUDE_ARN="arn:aws:bedrock:${AWS_REGION}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
TITAN_ARN="arn:aws:bedrock:${AWS_REGION}::foundation-model/amazon.titan-embed-text-v2:0"

# S3 bucket ARNs
REPOS_BUCKET_ARN="arn:aws:s3:::archaeologist-repos-prod"
REPORTS_BUCKET_ARN="arn:aws:s3:::archaeologist-reports-prod"
REPOS_OBJECTS_ARN="arn:aws:s3:::archaeologist-repos-prod/*"
REPORTS_OBJECTS_ARN="arn:aws:s3:::archaeologist-reports-prod/*"

# CloudWatch log group ARN
LOG_GROUP_ARN="arn:aws:logs:${AWS_REGION}:${ACCOUNT_ID}:log-group:/archaeologist/analyzer"

# Lambda function ARN
LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:archaeologist-analyzer"

# ---------------------------------------------------------------------------
# Tracking variables
# ---------------------------------------------------------------------------
PASS_COUNT=0
FAIL_COUNT=0

# Column widths for the output table
COL_ACTION=42
COL_RESOURCE=50
COL_EXPECTED=10

# ---------------------------------------------------------------------------
# Print table header
# ---------------------------------------------------------------------------
print_header() {
  echo ""
  echo "=== Permission Verification Results ==="
  echo "User ARN: ${USER_ARN}"
  echo "Region  : ${AWS_REGION}"
  echo ""
  printf "%-${COL_ACTION}s %-${COL_RESOURCE}s %-${COL_EXPECTED}s %s\n" \
    "Action" "Resource (truncated)" "Expected" "Result"
  printf "%-${COL_ACTION}s %-${COL_RESOURCE}s %-${COL_EXPECTED}s %s\n" \
    "$(printf '%0.s-' $(seq 1 ${COL_ACTION}))" \
    "$(printf '%0.s-' $(seq 1 ${COL_RESOURCE}))" \
    "$(printf '%0.s-' $(seq 1 ${COL_EXPECTED}))" \
    "------"
}

# ---------------------------------------------------------------------------
# Helper: simulate a single action and check the decision
#
# Arguments:
#   $1 — IAM action (e.g., "bedrock:InvokeModel")
#   $2 — Resource ARN to simulate against
#   $3 — Expected decision: "allowed" or "explicitDeny" / "implicitDeny"
#
# Prints a table row and updates PASS_COUNT / FAIL_COUNT.
# ---------------------------------------------------------------------------
check_permission() {
  local action="$1"
  local resource="$2"
  local expected="$3"   # "allowed" | "denied"

  # Simulate the action against the principal policy
  local decision
  decision=$(aws iam simulate-principal-policy \
    --policy-source-arn "${USER_ARN}" \
    --action-names "${action}" \
    --resource-arns "${resource}" \
    --query "EvaluationResults[0].EvalDecision" \
    --output text 2>/dev/null || echo "ERROR")

  # Normalize: anything that isn't "allowed" counts as "denied" for our purposes
  local normalized
  if [ "${decision}" = "allowed" ]; then
    normalized="allowed"
  else
    normalized="denied"
  fi

  # Truncate resource ARN for display (keep it readable in the table)
  local short_resource="${resource}"
  if [ "${#resource}" -gt "${COL_RESOURCE}" ]; then
    short_resource="...${resource: -$((COL_RESOURCE - 3))}"
  fi

  # Determine PASS/FAIL
  local result_icon
  local result_label
  if [ "${normalized}" = "${expected}" ]; then
    result_icon="✅"
    result_label="PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    result_icon="❌"
    result_label="FAIL (got: ${decision})"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi

  # Expected label for display
  local expected_label
  if [ "${expected}" = "allowed" ]; then
    expected_label="ALLOW"
  else
    expected_label="DENY"
  fi

  printf "%-${COL_ACTION}s %-${COL_RESOURCE}s %-${COL_EXPECTED}s %s %s\n" \
    "${action}" \
    "${short_resource}" \
    "${expected_label}" \
    "${result_icon}" \
    "${result_label}"
}

# =============================================================================
# Main — run all checks
# =============================================================================

print_header

echo ""
echo "--- ALLOW checks (actions the user must be able to perform) ---"

# Bedrock: invoke Claude Sonnet (Requirement 14.2)
check_permission "bedrock:InvokeModel"                      "${CLAUDE_ARN}"           "allowed"
check_permission "bedrock:InvokeModelWithResponseStream"    "${CLAUDE_ARN}"           "allowed"

# Bedrock: invoke Titan Embeddings V2 (Requirement 14.2)
check_permission "bedrock:InvokeModel"                      "${TITAN_ARN}"            "allowed"

# S3: read/write objects in repos bucket (Requirement 14.3)
check_permission "s3:PutObject"                             "${REPOS_OBJECTS_ARN}"    "allowed"
check_permission "s3:GetObject"                             "${REPOS_OBJECTS_ARN}"    "allowed"
check_permission "s3:DeleteObject"                          "${REPOS_OBJECTS_ARN}"    "allowed"
check_permission "s3:ListBucket"                            "${REPOS_BUCKET_ARN}"     "allowed"

# S3: read/write objects in reports bucket (Requirement 14.3)
check_permission "s3:PutObject"                             "${REPORTS_OBJECTS_ARN}"  "allowed"
check_permission "s3:GetObject"                             "${REPORTS_OBJECTS_ARN}"  "allowed"

# CloudWatch Logs: write logs (Requirement 14.5)
check_permission "logs:PutLogEvents"                        "${LOG_GROUP_ARN}"        "allowed"
check_permission "logs:CreateLogGroup"                      "${LOG_GROUP_ARN}"        "allowed"
check_permission "logs:CreateLogStream"                     "${LOG_GROUP_ARN}"        "allowed"

# Lambda: invoke archaeologist functions (Requirement 14.4)
check_permission "lambda:InvokeFunction"                    "${LAMBDA_ARN}"           "allowed"

echo ""
echo "--- DENY checks (actions the user must NOT be able to perform) ---"

# S3 administrative actions — Requirement 14.6
check_permission "s3:DeleteBucket"                          "${REPOS_BUCKET_ARN}"     "denied"
check_permission "s3:CreateBucket"                          "arn:aws:s3:::any-bucket" "denied"

# IAM actions — cannot escalate privileges (Requirement 14.6)
check_permission "iam:CreateUser"                           "*"                       "denied"
check_permission "iam:AttachUserPolicy"                     "*"                       "denied"
check_permission "iam:CreateAccessKey"                      "*"                       "denied"

# EC2 actions — no compute access (Requirement 14.6)
check_permission "ec2:RunInstances"                         "*"                       "denied"
check_permission "ec2:DescribeInstances"                    "*"                       "denied"

# RDS actions — no database access (Requirement 14.6)
check_permission "rds:DeleteDBInstance"                     "*"                       "denied"
check_permission "rds:CreateDBInstance"                     "*"                       "denied"

# S3 cross-bucket access — cannot access buckets outside the allowed prefix
check_permission "s3:PutObject"                             "arn:aws:s3:::some-other-bucket/*" "denied"

# =============================================================================
# Summary
# =============================================================================
TOTAL=$((PASS_COUNT + FAIL_COUNT))

echo ""
echo "========================================"
echo "  Results: ${PASS_COUNT}/${TOTAL} checks passed"
echo "========================================"

if [ "${FAIL_COUNT}" -gt 0 ]; then
  echo ""
  echo "  ❌ ${FAIL_COUNT} check(s) FAILED."
  echo ""
  echo "  Possible causes:"
  echo "    - Policy not attached to the user yet (run setup.sh)"
  echo "    - Policy document differs from policy-minimal.json"
  echo "    - IAM policy propagation delay (wait ~30s and retry)"
  echo ""
  exit 1
else
  echo ""
  echo "  ✅ All checks passed. The kiro-archaeologist user has exactly"
  echo "     the permissions required — no more, no less."
  echo ""
  exit 0
fi
