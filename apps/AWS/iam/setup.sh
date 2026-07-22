#!/usr/bin/env bash
# =============================================================================
# Software Archaeologist — IAM Setup Script
# Requirement 14: Principio de Mínimo Privilegio
#
# Creates a dedicated IAM user `kiro-archaeologist` with only the permissions
# required to operate the platform. No console login is granted — programmatic
# access only, minimizing the blast radius of a credential leak.
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# Prerequisites:
#   - AWS CLI v2 installed and configured (aws configure)
#   - Caller must have iam:CreateUser, iam:CreatePolicy, iam:AttachUserPolicy,
#     and iam:CreateAccessKey permissions
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Variables — adjust ACCOUNT_ID before running
# ---------------------------------------------------------------------------
IAM_USER="kiro-archaeologist"
POLICY_NAME="KiroArchaeologistMinimalPolicy"
POLICY_FILE="$(dirname "$0")/policy-minimal.json"

# Retrieve the AWS account ID dynamically so the ARN is always correct.
# This avoids hardcoding account numbers in version-controlled files.
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

echo "=== Software Archaeologist — IAM Setup ==="
echo "Account : ${ACCOUNT_ID}"
echo "Region  : ${AWS_REGION}"
echo "User    : ${IAM_USER}"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Create the IAM user with no console login
#
# --no-create-home-dir equivalent for IAM: by default, CreateUser does NOT
# attach a login profile (console password). Programmatic access is granted
# only via access keys, satisfying Requirement 14.1.
# ---------------------------------------------------------------------------
echo "[1/4] Creating IAM user '${IAM_USER}' (programmatic access only)..."

aws iam create-user \
  --user-name "${IAM_USER}" \
  --tags Key=Project,Value=software-archaeologist \
         Key=ManagedBy,Value=setup-sh \
         Key=Purpose,Value=programmatic-access-only

echo "      User created. No login profile added — console access is blocked by default."

# ---------------------------------------------------------------------------
# Step 2: Create the managed IAM policy from the JSON document
#
# Using a managed (customer-managed) policy instead of an inline policy so it:
#   - Can be versioned and audited independently
#   - Can be detached and re-attached without recreating the user
#   - Shows up clearly in IAM policy listings for compliance reviews
#
# The policy document grants ONLY:
#   - bedrock:InvokeModel + InvokeModelWithResponseStream for the two specific
#     foundation models (Claude Sonnet + Titan Embed V2) — Requirement 14.2
#   - s3:PutObject/GetObject/DeleteObject/ListBucket scoped to buckets whose
#     name starts with archaeologist-repos-* or archaeologist-reports-* — Req 14.3
#   - lambda:InvokeFunction scoped to functions prefixed archaeologist-* — Req 14.4
#   - logs:Create*/PutLogEvents/DescribeLogStreams scoped to /archaeologist/* — Req 14.5
#
# Notably absent (satisfying Requirement 14.6):
#   - iam:* — cannot manage IAM resources
#   - ec2:* — cannot provision compute
#   - rds:* — cannot touch databases
#   - s3:CreateBucket / s3:DeleteBucket — cannot create or destroy buckets
#   - Any administrative or account-wide actions
# ---------------------------------------------------------------------------
echo "[2/4] Creating customer-managed policy '${POLICY_NAME}'..."

POLICY_ARN=$(aws iam create-policy \
  --policy-name "${POLICY_NAME}" \
  --policy-document "file://${POLICY_FILE}" \
  --description "Minimal policy for Software Archaeologist: Bedrock (2 models), S3 (archaeologist-* buckets), Lambda (archaeologist-* functions), CloudWatch Logs (/archaeologist/*)" \
  --tags Key=Project,Value=software-archaeologist \
         Key=ManagedBy,Value=setup-sh \
  --query "Policy.Arn" \
  --output text)

echo "      Policy ARN: ${POLICY_ARN}"

# ---------------------------------------------------------------------------
# Step 3: Attach the policy to the user
#
# Attaching as a managed policy (vs. putting it inline) keeps the user record
# clean and allows the policy to be updated or rotated independently of the
# user lifecycle — important for security operations (Requirement 14.7).
# ---------------------------------------------------------------------------
echo "[3/4] Attaching policy to user '${IAM_USER}'..."

aws iam attach-user-policy \
  --user-name "${IAM_USER}" \
  --policy-arn "${POLICY_ARN}"

echo "      Policy attached."

# ---------------------------------------------------------------------------
# Step 4: Create access keys for programmatic access
#
# Only ONE access key is created here. AWS allows a maximum of 2 per user.
# The key pair (AccessKeyId + SecretAccessKey) is printed once — the
# SecretAccessKey cannot be retrieved again after this point.
#
# IMPORTANT: Store the output in your secrets manager (e.g., AWS Secrets
# Manager, 1Password) immediately. Do NOT commit these values to git.
# ---------------------------------------------------------------------------
echo "[4/4] Creating access key (store SecretAccessKey immediately — shown once)..."

aws iam create-access-key \
  --user-name "${IAM_USER}" \
  --output table

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Copy AccessKeyId and SecretAccessKey to your secrets manager NOW."
echo "  2. Add the keys to .data/.env under AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY."
echo "  3. Run apps/AWS/iam/verify-permissions.sh to confirm the policy works as intended."
echo "  4. Run apps/AWS/bedrock/verify-models.sh to confirm model access is enabled."
echo ""
echo "User ARN : arn:aws:iam::${ACCOUNT_ID}:user/${IAM_USER}"
echo "Policy   : ${POLICY_ARN}"
