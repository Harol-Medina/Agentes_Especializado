#!/usr/bin/env bash
# =============================================================================
# Software Archaeologist — Bedrock Model Access Verification
# Requirement 14.2
#
# Verifies that the required Amazon Bedrock foundation models are available
# and accessible in the configured AWS region. The platform requires exactly
# two models:
#
#   1. anthropic.claude-3-sonnet-20240229-v1:0
#      Used by: Architecture, Quality, Security, Documentation, Modernization,
#               and Kiro agents for reasoning and generation tasks.
#      Also used by: RAG system for generating chat responses.
#
#   2. amazon.titan-embed-text-v2:0
#      Used by: RAG system for generating text embeddings (indexed in pgvector).
#
# If models are not available, this script prints step-by-step instructions
# for enabling them via the AWS Management Console.
#
# Usage:
#   chmod +x verify-models.sh
#   ./verify-models.sh
#
# Prerequisites:
#   - AWS CLI v2 installed and configured
#   - Caller must have bedrock:ListFoundationModels permission
#   - Models must be enabled in the target region (see instructions below)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Exact model IDs required by the platform — these must match
# the IAM policy in policy-minimal.json
REQUIRED_MODELS=(
  "anthropic.claude-3-sonnet-20240229-v1:0"
  "amazon.titan-embed-text-v2:0"
)

# Human-readable descriptions for the output
declare -A MODEL_DESCRIPTIONS
MODEL_DESCRIPTIONS["anthropic.claude-3-sonnet-20240229-v1:0"]="Claude 3 Sonnet (reasoning & generation)"
MODEL_DESCRIPTIONS["amazon.titan-embed-text-v2:0"]="Titan Text Embeddings V2 (RAG embeddings)"

# Tracking
AVAILABLE_COUNT=0
MISSING_MODELS=()

echo "=== Software Archaeologist — Bedrock Model Verification ==="
echo "Region: ${AWS_REGION}"
echo ""
echo "Checking availability of required foundation models..."
echo ""

# ---------------------------------------------------------------------------
# Query available models from Bedrock
#
# list-foundation-models returns all models available in the region.
# We filter for our specific model IDs.
# ---------------------------------------------------------------------------

# Get the full list of available model IDs once
ALL_MODELS=$(aws bedrock list-foundation-models \
  --region "${AWS_REGION}" \
  --query "modelSummaries[*].modelId" \
  --output text 2>/dev/null || echo "")

if [ -z "${ALL_MODELS}" ]; then
  echo "  ❌ ERROR: Could not retrieve model list from Bedrock."
  echo ""
  echo "  Possible causes:"
  echo "    - AWS CLI not configured for region ${AWS_REGION}"
  echo "    - Caller lacks bedrock:ListFoundationModels permission"
  echo "    - Bedrock is not available in region ${AWS_REGION}"
  echo ""
  echo "  Supported Bedrock regions (as of 2024):"
  echo "    us-east-1, us-west-2, eu-west-1, ap-southeast-1, ap-northeast-1"
  echo ""
  exit 1
fi

# ---------------------------------------------------------------------------
# Check each required model
# ---------------------------------------------------------------------------
printf "  %-55s %s\n" "Model ID" "Status"
printf "  %-55s %s\n" "-------------------------------------------------------" "------"

for model_id in "${REQUIRED_MODELS[@]}"; do
  description="${MODEL_DESCRIPTIONS[${model_id}]}"

  if echo "${ALL_MODELS}" | grep -q "${model_id}"; then
    printf "  %-55s %s\n" "${model_id}" "✅ Available"
    echo "    └─ ${description}"
    AVAILABLE_COUNT=$((AVAILABLE_COUNT + 1))
  else
    printf "  %-55s %s\n" "${model_id}" "❌ NOT FOUND"
    echo "    └─ ${description}"
    MISSING_MODELS+=("${model_id}")
  fi
  echo ""
done

# ---------------------------------------------------------------------------
# Results summary
# ---------------------------------------------------------------------------
echo "========================================"
echo "  Results: ${AVAILABLE_COUNT}/${#REQUIRED_MODELS[@]} models available"
echo "========================================"

if [ ${#MISSING_MODELS[@]} -eq 0 ]; then
  echo ""
  echo "  ✅ All required models are available in ${AWS_REGION}."
  echo "  The platform is ready to use Bedrock for analysis and embeddings."
  echo ""

  # Additional check: verify the IAM user can actually invoke them
  echo "  Tip: Run apps/AWS/iam/verify-permissions.sh to confirm the"
  echo "  kiro-archaeologist user has bedrock:InvokeModel permission"
  echo "  on these specific model ARNs."
  echo ""
  exit 0
fi

# ---------------------------------------------------------------------------
# If models are missing, print console instructions
# ---------------------------------------------------------------------------
echo ""
echo "  ❌ ${#MISSING_MODELS[@]} model(s) not available. You need to enable"
echo "  model access via the AWS Management Console."
echo ""
echo "  Missing models:"
for m in "${MISSING_MODELS[@]}"; do
  echo "    - ${m}"
done
echo ""
echo "==========================================================="
echo "  HOW TO ENABLE MODEL ACCESS (AWS Console)"
echo "==========================================================="
echo ""
echo "  Step 1: Open the Bedrock Model Access page"
echo "    https://console.aws.amazon.com/bedrock/home?region=${AWS_REGION}#/modelaccess"
echo ""
echo "  Step 2: Click 'Manage model access' (top right button)"
echo ""
echo "  Step 3: Find and enable the required models:"
echo ""
echo "    For Claude 3 Sonnet:"
echo "      Provider: Anthropic"
echo "      Model: Claude 3 Sonnet"
echo "      Check the box to request access"
echo "      NOTE: Anthropic models may require acceptance of terms"
echo ""
echo "    For Titan Text Embeddings V2:"
echo "      Provider: Amazon"
echo "      Model: Titan Text Embeddings V2"
echo "      Check the box to request access"
echo "      NOTE: Amazon models are typically auto-approved"
echo ""
echo "  Step 4: Click 'Request model access' at the bottom"
echo ""
echo "  Step 5: Wait for access to be granted (usually immediate for"
echo "    Amazon models; Anthropic may take a few minutes)"
echo ""
echo "  Step 6: Re-run this script to verify:"
echo "    ./verify-models.sh"
echo ""
echo "==========================================================="
echo "  ALTERNATIVE: AWS CLI (if you have bedrock:* admin access)"
echo "==========================================================="
echo ""
echo "  There is no CLI command to enable model access — it must be"
echo "  done via the AWS Console. However, you can check pending"
echo "  invitations with:"
echo ""
echo "    aws bedrock list-model-access-requests --region ${AWS_REGION}"
echo ""
echo "==========================================================="
echo ""
echo "  Console URL (direct link):"
echo "  https://console.aws.amazon.com/bedrock/home?region=${AWS_REGION}#/modelaccess"
echo ""

exit 1
