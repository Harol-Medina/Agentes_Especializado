#!/usr/bin/env bash
# =============================================================================
# Software Archaeologist — S3 Bucket Creation Script
# Requirement 14.3, 14.8
#
# Creates two S3 buckets required for platform operation, each with the
# appropriate access controls and retention policies:
#
#   archaeologist-repos-prod
#     Purpose: Temporary storage for cloned repository archives while the
#              Analyzer processes them. Objects are short-lived by nature —
#              once the pipeline completes the archive is no longer needed.
#     Retention: 24-hour lifecycle policy deletes all objects automatically.
#                This limits storage costs and reduces exposure of potentially
#                sensitive source code.
#
#   archaeologist-reports-prod
#     Purpose: Persistent storage for generated architecture reports and
#              Kiro specs. Users may return to download these after analysis.
#     Retention: No automatic deletion — objects are kept until manually
#                removed. A manual review cadence is recommended.
#
# Both buckets:
#   - Block ALL public access (no ACLs, no bucket policies, no cross-account)
#   - Versioning disabled (not needed — repos bucket uses lifecycle delete,
#     reports bucket stores final artifacts that don't need version history)
#   - Server-side encryption enabled (SSE-S3 by default in all new buckets)
#
# Usage:
#   chmod +x create-buckets.sh
#   ./create-buckets.sh
#
# Prerequisites:
#   - AWS CLI v2 installed and configured (aws configure)
#   - Caller must have s3:CreateBucket, s3:PutBucketLifecycleConfiguration,
#     s3:PutBucketVersioning, s3:PutBucketPublicAccessBlock permissions
#   - Note: the kiro-archaeologist runtime user does NOT have s3:CreateBucket —
#     run this script with your admin/bootstrap credentials, not the app user.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Bucket names must match the IAM policy prefixes in policy-minimal.json
# (archaeologist-repos-* and archaeologist-reports-*)
REPOS_BUCKET="archaeologist-repos-prod"
REPORTS_BUCKET="archaeologist-reports-prod"

echo "=== Software Archaeologist — S3 Bucket Setup ==="
echo "Region         : ${AWS_REGION}"
echo "Repos bucket   : ${REPOS_BUCKET}   (24-hour lifecycle deletion)"
echo "Reports bucket : ${REPORTS_BUCKET} (no auto-deletion)"
echo ""

# ---------------------------------------------------------------------------
# Helper: block all public access on a bucket
#
# Prevents accidental public exposure via ACLs, bucket policies, or
# cross-account grants. All source code and reports are internal assets.
# ---------------------------------------------------------------------------
block_public_access() {
  local bucket="$1"
  echo "  Blocking all public access..."
  aws s3api put-public-access-block \
    --bucket "${bucket}" \
    --public-access-block-configuration \
      "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
}

# ---------------------------------------------------------------------------
# Helper: create a bucket, handling the us-east-1 special case
#
# CreateBucket in us-east-1 must NOT include a LocationConstraint.
# Every other region requires it. AWS CLI handles this inconsistency by
# requiring the --create-bucket-configuration flag only outside us-east-1.
# ---------------------------------------------------------------------------
create_bucket() {
  local bucket="$1"
  if [ "${AWS_REGION}" = "us-east-1" ]; then
    aws s3api create-bucket \
      --bucket "${bucket}" \
      --region "${AWS_REGION}"
  else
    aws s3api create-bucket \
      --bucket "${bucket}" \
      --region "${AWS_REGION}" \
      --create-bucket-configuration LocationConstraint="${AWS_REGION}"
  fi
}

# =============================================================================
# BUCKET 1: archaeologist-repos-prod
# Purpose: Temporary cloned repository archives
# Retention: 24 hours (lifecycle policy — Requirement 14.8)
# =============================================================================
echo "[1/6] Creating bucket '${REPOS_BUCKET}'..."
create_bucket "${REPOS_BUCKET}"
echo "      Created."

echo "[2/6] Blocking public access on '${REPOS_BUCKET}'..."
block_public_access "${REPOS_BUCKET}"
echo "      Done."

echo "[3/6] Applying 24-hour lifecycle deletion policy to '${REPOS_BUCKET}'..."
# The lifecycle rule deletes ALL objects after 1 day.
# This ensures:
#   - Temporary repo archives are cleaned up automatically (cost control)
#   - Source code from analyzed repos is not retained indefinitely (privacy)
#   - No manual cleanup step is required in the pipeline (operational simplicity)
#
# NoncurrentVersionExpiration is also set to 1 day in case versioning is ever
# enabled in the future, ensuring the same 24h guarantee holds.
aws s3api put-bucket-lifecycle-configuration \
  --bucket "${REPOS_BUCKET}" \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "DeleteTempReposAfter24Hours",
        "Status": "Enabled",
        "Filter": {
          "Prefix": ""
        },
        "Expiration": {
          "Days": 1
        },
        "NoncurrentVersionExpiration": {
          "NoncurrentDays": 1
        },
        "AbortIncompleteMultipartUpload": {
          "DaysAfterInitiation": 1
        }
      }
    ]
  }'
echo "      Lifecycle policy applied: all objects deleted after 24 hours."

# =============================================================================
# BUCKET 2: archaeologist-reports-prod
# Purpose: Persistent generated reports and Kiro specs
# Retention: No automatic deletion (kept until manually removed)
# =============================================================================
echo "[4/6] Creating bucket '${REPORTS_BUCKET}'..."
create_bucket "${REPORTS_BUCKET}"
echo "      Created."

echo "[5/6] Blocking public access on '${REPORTS_BUCKET}'..."
block_public_access "${REPORTS_BUCKET}"
echo "      Done."

echo "[6/6] Verifying bucket configuration..."
echo ""
echo "--- ${REPOS_BUCKET} ---"
echo "  Public access block:"
aws s3api get-public-access-block --bucket "${REPOS_BUCKET}" \
  --query "PublicAccessBlockConfiguration" --output table
echo "  Lifecycle rules:"
aws s3api get-bucket-lifecycle-configuration --bucket "${REPOS_BUCKET}" \
  --query "Rules[*].{ID:ID,Status:Status,ExpirationDays:Expiration.Days}" --output table

echo ""
echo "--- ${REPORTS_BUCKET} ---"
echo "  Public access block:"
aws s3api get-public-access-block --bucket "${REPORTS_BUCKET}" \
  --query "PublicAccessBlockConfiguration" --output table
echo "  Lifecycle: none (reports are kept indefinitely)"

echo ""
echo "=== S3 Setup Complete ==="
echo ""
echo "Summary:"
echo "  ${REPOS_BUCKET}"
echo "    - All public access blocked"
echo "    - Objects automatically deleted after 24 hours (Requirement 14.8)"
echo "    - Use this bucket for cloned repo archives during analysis"
echo ""
echo "  ${REPORTS_BUCKET}"
echo "    - All public access blocked"
echo "    - No automatic deletion — reports are persistent"
echo "    - Use this bucket for architecture reports and Kiro spec exports"
echo ""
echo "Both bucket ARNs follow the IAM policy prefix (archaeologist-repos-* / archaeologist-reports-*)"
echo "and are accessible by the kiro-archaeologist user via policy-minimal.json."
