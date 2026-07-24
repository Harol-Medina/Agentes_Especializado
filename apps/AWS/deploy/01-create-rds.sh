#!/usr/bin/env bash
# =============================================================================
# Software Archaeologist — RDS PostgreSQL 15 Deployment Script
# Task 17.1: Database Infrastructure
#
# Creates a production PostgreSQL 15 instance on Amazon RDS with pgvector
# support for the Software Archaeologist platform.
#
# What this script does:
#   1. Creates a custom DB parameter group (pg_stat_statements enabled)
#   2. Creates a VPC security group allowing inbound on port 5432
#   3. Creates an RDS instance (db.t3.medium, 20GB gp3, single-AZ)
#   4. Waits for the instance to become available
#   5. Connects and enables the pgvector extension
#   6. Prints the endpoint for .env.prod configuration
#
# Usage:
#   chmod +x 01-create-rds.sh
#   ./01-create-rds.sh
#
# Prerequisites:
#   - AWS CLI v2 installed and configured (aws configure)
#   - psql client installed (for extension creation)
#   - Caller must have rds:*, ec2:CreateSecurityGroup, ec2:AuthorizeSecurityGroupIngress
#   - Set DB_PASSWORD environment variable before running (or it will be generated)
#
# Security Notes:
#   - The security group initially allows 0.0.0.0/0 on port 5432.
#     TODO: After Elastic Beanstalk is deployed, restrict to EB security group.
#   - DB credentials are printed once — store them in your secrets manager.
#   - The instance is NOT publicly accessible by default in production VPCs.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

DB_IDENTIFIER="archaeologist-db"
DB_NAME="archaeologist"
DB_USERNAME="archaeologist"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 32)}"
DB_INSTANCE_CLASS="db.t3.medium"
DB_STORAGE_SIZE=20
DB_STORAGE_TYPE="gp3"
DB_ENGINE="postgres"
DB_ENGINE_VERSION="15"
PARAM_GROUP_NAME="archaeologist-pg15-params"
PARAM_GROUP_FAMILY="postgres15"
SECURITY_GROUP_NAME="archaeologist-db-sg"
SECURITY_GROUP_DESC="Security group for Software Archaeologist RDS instance"

echo "=== Software Archaeologist — RDS PostgreSQL 15 Setup ==="
echo "Region          : ${AWS_REGION}"
echo "DB Identifier   : ${DB_IDENTIFIER}"
echo "DB Name         : ${DB_NAME}"
echo "Instance Class  : ${DB_INSTANCE_CLASS}"
echo "Storage         : ${DB_STORAGE_SIZE}GB ${DB_STORAGE_TYPE}"
echo "Engine          : ${DB_ENGINE} ${DB_ENGINE_VERSION}"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Create a custom DB parameter group
#
# We enable pg_stat_statements via shared_preload_libraries for query
# performance monitoring. The pgvector extension does NOT require
# shared_preload_libraries — it's loaded on-demand with CREATE EXTENSION.
# ---------------------------------------------------------------------------
echo "[1/6] Creating custom parameter group '${PARAM_GROUP_NAME}'..."

aws rds create-db-parameter-group \
  --db-parameter-group-name "${PARAM_GROUP_NAME}" \
  --db-parameter-group-family "${PARAM_GROUP_FAMILY}" \
  --description "Custom params for Software Archaeologist: pg_stat_statements enabled" \
  --region "${AWS_REGION}" \
  --tags Key=Project,Value=software-archaeologist \
         Key=ManagedBy,Value=deploy-script

# Enable pg_stat_statements for query performance monitoring
aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PARAM_GROUP_NAME}" \
  --parameters "ParameterName=shared_preload_libraries,ParameterValue=pg_stat_statements,ApplyMethod=pending-reboot" \
  --region "${AWS_REGION}"

echo "      Parameter group created with shared_preload_libraries = 'pg_stat_statements'."

# ---------------------------------------------------------------------------
# Step 2: Get the default VPC ID
#
# We need a VPC to create the security group in. Using the default VPC
# for simplicity — production deployments should use a dedicated VPC.
# ---------------------------------------------------------------------------
echo "[2/6] Retrieving default VPC ID..."

VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=is-default,Values=true" \
  --query "Vpcs[0].VpcId" \
  --output text \
  --region "${AWS_REGION}")

if [ "${VPC_ID}" = "None" ] || [ -z "${VPC_ID}" ]; then
  echo "ERROR: No default VPC found in ${AWS_REGION}. Create one or specify a VPC manually."
  exit 1
fi

echo "      VPC ID: ${VPC_ID}"

# ---------------------------------------------------------------------------
# Step 3: Create a security group for the RDS instance
#
# Initially allows inbound on port 5432 from anywhere (0.0.0.0/0).
# TODO: After Elastic Beanstalk deployment, restrict the source to the
# EB environment's security group for defense-in-depth.
# ---------------------------------------------------------------------------
echo "[3/6] Creating security group '${SECURITY_GROUP_NAME}'..."

SG_ID=$(aws ec2 create-security-group \
  --group-name "${SECURITY_GROUP_NAME}" \
  --description "${SECURITY_GROUP_DESC}" \
  --vpc-id "${VPC_ID}" \
  --region "${AWS_REGION}" \
  --query "GroupId" \
  --output text)

echo "      Security Group ID: ${SG_ID}"

# Allow inbound PostgreSQL traffic
# TODO: Replace 0.0.0.0/0 with EB security group after deployment
aws ec2 authorize-security-group-ingress \
  --group-id "${SG_ID}" \
  --protocol tcp \
  --port 5432 \
  --cidr "0.0.0.0/0" \
  --region "${AWS_REGION}"

aws ec2 create-tags \
  --resources "${SG_ID}" \
  --tags Key=Project,Value=software-archaeologist \
         Key=Name,Value="${SECURITY_GROUP_NAME}" \
  --region "${AWS_REGION}"

echo "      Inbound rule added: TCP 5432 from 0.0.0.0/0 (restrict after EB deploy)."

# ---------------------------------------------------------------------------
# Step 4: Create the RDS PostgreSQL 15 instance
#
# Configuration:
#   - db.t3.medium: 2 vCPU, 4 GiB RAM (sufficient for MVP workloads)
#   - 20GB gp3: baseline 3000 IOPS, 125 MB/s throughput (good for pgvector)
#   - Single-AZ: cost-effective for MVP (upgrade to Multi-AZ for production)
#   - No public access: only accessible within the VPC
#   - Encryption at rest enabled (AWS default KMS key)
#   - Automated backups: 7-day retention
#   - Auto minor version upgrades enabled
# ---------------------------------------------------------------------------
echo "[4/6] Creating RDS instance '${DB_IDENTIFIER}'..."
echo "      This may take 5-10 minutes..."

aws rds create-db-instance \
  --db-instance-identifier "${DB_IDENTIFIER}" \
  --db-instance-class "${DB_INSTANCE_CLASS}" \
  --engine "${DB_ENGINE}" \
  --engine-version "${DB_ENGINE_VERSION}" \
  --master-username "${DB_USERNAME}" \
  --master-user-password "${DB_PASSWORD}" \
  --db-name "${DB_NAME}" \
  --allocated-storage "${DB_STORAGE_SIZE}" \
  --storage-type "${DB_STORAGE_TYPE}" \
  --db-parameter-group-name "${PARAM_GROUP_NAME}" \
  --vpc-security-group-ids "${SG_ID}" \
  --no-multi-az \
  --no-publicly-accessible \
  --storage-encrypted \
  --backup-retention-period 7 \
  --auto-minor-version-upgrade \
  --copy-tags-to-snapshot \
  --tags Key=Project,Value=software-archaeologist \
         Key=ManagedBy,Value=deploy-script \
         Key=Environment,Value=production \
  --region "${AWS_REGION}"

echo "      Instance creation initiated."

# ---------------------------------------------------------------------------
# Step 5: Wait for the instance to become available
#
# This typically takes 5-10 minutes. The waiter polls every 30 seconds.
# ---------------------------------------------------------------------------
echo "[5/6] Waiting for instance to become available (this takes 5-10 minutes)..."

aws rds wait db-instance-available \
  --db-instance-identifier "${DB_IDENTIFIER}" \
  --region "${AWS_REGION}"

echo "      Instance is now available!"

# Retrieve the endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier "${DB_IDENTIFIER}" \
  --query "DBInstances[0].Endpoint.Address" \
  --output text \
  --region "${AWS_REGION}")

RDS_PORT=$(aws rds describe-db-instances \
  --db-instance-identifier "${DB_IDENTIFIER}" \
  --query "DBInstances[0].Endpoint.Port" \
  --output text \
  --region "${AWS_REGION}")

echo "      Endpoint: ${RDS_ENDPOINT}:${RDS_PORT}"

# ---------------------------------------------------------------------------
# Step 6: Enable the pgvector extension
#
# pgvector is available in RDS PostgreSQL 15+ as a trusted extension.
# We connect via psql and run CREATE EXTENSION. This requires the
# instance to be reachable from where this script runs — if running
# from outside the VPC, ensure a bastion host or VPN is configured.
# ---------------------------------------------------------------------------
echo "[6/6] Enabling pgvector extension..."

# NOTE: If running from outside the VPC, you may need to:
#   1. Temporarily make the instance publicly accessible, OR
#   2. Run this from an EC2 instance in the same VPC, OR
#   3. Use an SSH tunnel through a bastion host
PGPASSWORD="${DB_PASSWORD}" psql \
  -h "${RDS_ENDPOINT}" \
  -p "${RDS_PORT}" \
  -U "${DB_USERNAME}" \
  -d "${DB_NAME}" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "      pgvector extension enabled."

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== RDS Setup Complete ==="
echo ""
echo "Connection details (save these in your secrets manager NOW):"
echo "  Host     : ${RDS_ENDPOINT}"
echo "  Port     : ${RDS_PORT}"
echo "  Database : ${DB_NAME}"
echo "  Username : ${DB_USERNAME}"
echo "  Password : ${DB_PASSWORD}"
echo ""
echo "Connection strings for .data/.env.prod:"
echo "  SPRING_DATASOURCE_URL=jdbc:postgresql://${RDS_ENDPOINT}:${RDS_PORT}/${DB_NAME}"
echo "  DATABASE_URL=postgresql+asyncpg://${DB_USERNAME}:${DB_PASSWORD}@${RDS_ENDPOINT}:${RDS_PORT}/${DB_NAME}"
echo ""
echo "Next steps:"
echo "  1. Store the password in your secrets manager immediately."
echo "  2. Update .data/.env.prod with the connection strings above."
echo "  3. Run 02-run-migrations.sh to apply Flyway migrations."
echo "  4. After EB deployment, restrict the security group to EB's SG."
echo ""
echo "Resources created:"
echo "  Parameter Group : ${PARAM_GROUP_NAME}"
echo "  Security Group  : ${SG_ID} (${SECURITY_GROUP_NAME})"
echo "  RDS Instance    : ${DB_IDENTIFIER}"
