#!/usr/bin/env bash
set -euo pipefail

# JARVIS ECS deployment wrapper.
# Run after Terraform has been applied from infra/terraform.
# Required tools: aws, docker, curl. Terraform is optional but recommended for output discovery.

AWS_REGION="${AWS_REGION:-ap-south-2}"
PROJECT="${PROJECT:-jarvis}"
ENVIRONMENT="${ENVIRONMENT:-production}"
TERRAFORM_DIR="${TERRAFORM_DIR:-infra/terraform}"
BACKEND_CONTEXT="${BACKEND_CONTEXT:-backend}"
CONTAINER_NAME="${CONTAINER_NAME:-backend}"
BACKEND_CPU="${BACKEND_CPU:-512}"
BACKEND_MEMORY="${BACKEND_MEMORY:-1024}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"

log() {
  printf '[JARVIS ECS] %s\n' "$*"
}

fail() {
  printf '[JARVIS ECS] ERROR: %s\n' "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required but not installed"
}

tf_output() {
  local key="$1"
  if command -v terraform >/dev/null 2>&1 && [ -d "$TERRAFORM_DIR" ]; then
    terraform -chdir="$TERRAFORM_DIR" output -raw "$key" 2>/dev/null || true
  fi
}

require_value() {
  local name="$1"
  local value="$2"
  local hint="$3"
  if [ -z "$value" ] || [ "$value" = "None" ]; then
    fail "$name is required. $hint"
  fi
}

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

need_cmd aws
need_cmd docker
need_cmd curl
need_cmd python3

if [ ! -d "$BACKEND_CONTEXT" ]; then
  fail "Backend build context not found: $BACKEND_CONTEXT"
fi

log "Checking AWS caller identity in $AWS_REGION"
aws sts get-caller-identity --output text >/dev/null

ECR_BACKEND_URI="${ECR_BACKEND_URI:-$(tf_output ecr_backend_url)}"
CLUSTER_NAME="${ECS_CLUSTER_NAME:-$(tf_output ecs_cluster_name)}"
SERVICE_NAME="${ECS_SERVICE_NAME:-$(tf_output ecs_service_name)}"
SECRET_ARN="${JARVIS_SECRET_ARN:-$(tf_output secrets_manager_arn)}"
LOG_GROUP="${CLOUDWATCH_LOG_GROUP:-$(tf_output cloudwatch_log_group)}"
S3_BUCKET="${AWS_S3_BUCKET:-$(tf_output s3_bucket)}"
API_URL="${API_URL:-$(tf_output api_url)}"

CLUSTER_NAME="${CLUSTER_NAME:-${PROJECT}-${ENVIRONMENT}-cluster}"
SERVICE_NAME="${SERVICE_NAME:-${PROJECT}-${ENVIRONMENT}-backend}"
LOG_GROUP="${LOG_GROUP:-/jarvis/${ENVIRONMENT}/backend}"
API_URL="${API_URL:-https://api.aliyarsolutions.com}"

require_value "ECR_BACKEND_URI" "$ECR_BACKEND_URI" "Run terraform apply first, or export ECR_BACKEND_URI."
require_value "JARVIS_SECRET_ARN" "$SECRET_ARN" "Run terraform apply first, or export JARVIS_SECRET_ARN."

ECR_REGISTRY="${ECR_BACKEND_URI%/*}"
IMAGE_URI="${ECR_BACKEND_URI}:${IMAGE_TAG}"
LATEST_URI="${ECR_BACKEND_URI}:latest"

log "Logging in to ECR: $ECR_REGISTRY"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY" >/dev/null

log "Building backend image: $IMAGE_URI"
docker build -t "jarvis-backend:${IMAGE_TAG}" "$BACKEND_CONTEXT"
docker tag "jarvis-backend:${IMAGE_TAG}" "$IMAGE_URI"
docker tag "jarvis-backend:${IMAGE_TAG}" "$LATEST_URI"

log "Pushing backend image tags"
docker push "$IMAGE_URI"
docker push "$LATEST_URI"

log "Resolving current ECS service task definition"
CURRENT_TASK_DEF_ARN="$(
  aws ecs describe-services \
    --region "$AWS_REGION" \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --query 'services[0].taskDefinition' \
    --output text
)"

require_value "CURRENT_TASK_DEF_ARN" "$CURRENT_TASK_DEF_ARN" \
  "Terraform must create the ECS service before this wrapper can update it."

TASK_FAMILY="$(
  aws ecs describe-task-definition \
    --region "$AWS_REGION" \
    --task-definition "$CURRENT_TASK_DEF_ARN" \
    --query 'taskDefinition.family' \
    --output text
)"
EXECUTION_ROLE_ARN="$(
  aws ecs describe-task-definition \
    --region "$AWS_REGION" \
    --task-definition "$CURRENT_TASK_DEF_ARN" \
    --query 'taskDefinition.executionRoleArn' \
    --output text
)"
TASK_ROLE_ARN="$(
  aws ecs describe-task-definition \
    --region "$AWS_REGION" \
    --task-definition "$CURRENT_TASK_DEF_ARN" \
    --query 'taskDefinition.taskRoleArn' \
    --output text
)"
SERVICE_CONTAINER_NAME="$(
  aws ecs describe-services \
    --region "$AWS_REGION" \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --query 'services[0].loadBalancers[0].containerName' \
    --output text 2>/dev/null || true
)"

TASK_FAMILY="${TASK_FAMILY:-${PROJECT}-${ENVIRONMENT}-backend}"
EXECUTION_ROLE_ARN="${ECS_EXECUTION_ROLE_ARN:-$EXECUTION_ROLE_ARN}"
TASK_ROLE_ARN="${ECS_TASK_ROLE_ARN:-$TASK_ROLE_ARN}"
if [ -n "$SERVICE_CONTAINER_NAME" ] && [ "$SERVICE_CONTAINER_NAME" != "None" ]; then
  CONTAINER_NAME="$SERVICE_CONTAINER_NAME"
fi

require_value "ECS_EXECUTION_ROLE_ARN" "$EXECUTION_ROLE_ARN" "Export ECS_EXECUTION_ROLE_ARN if no existing task definition is available."
require_value "ECS_TASK_ROLE_ARN" "$TASK_ROLE_ARN" "Export ECS_TASK_ROLE_ARN if no existing task definition is available."

TASK_DEF_FILE="$(mktemp)"
trap 'rm -f "$TASK_DEF_FILE"' EXIT

log "Writing task definition for family: $TASK_FAMILY"
cat > "$TASK_DEF_FILE" <<JSON
{
  "family": $(json_escape "$TASK_FAMILY"),
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": $(json_escape "$BACKEND_CPU"),
  "memory": $(json_escape "$BACKEND_MEMORY"),
  "executionRoleArn": $(json_escape "$EXECUTION_ROLE_ARN"),
  "taskRoleArn": $(json_escape "$TASK_ROLE_ARN"),
  "containerDefinitions": [
    {
      "name": $(json_escape "$CONTAINER_NAME"),
      "image": $(json_escape "$IMAGE_URI"),
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "DEBUG", "value": "false"},
        {"name": "USE_AWS", "value": "true"},
        {"name": "AWS_REGION", "value": $(json_escape "$AWS_REGION")},
        {"name": "AWS_S3_BUCKET", "value": $(json_escape "$S3_BUCKET")},
        {"name": "APP_BASE_URL", "value": $(json_escape "$API_URL")},
        {"name": "PYTHONUNBUFFERED", "value": "1"}
      ],
      "secrets": [
        {"name": "SECRET_KEY", "valueFrom": "${SECRET_ARN}:SECRET_KEY::"},
        {"name": "DATABASE_URL", "valueFrom": "${SECRET_ARN}:DATABASE_URL::"},
        {"name": "REDIS_URL", "valueFrom": "${SECRET_ARN}:REDIS_URL::"},
        {"name": "ANTHROPIC_API_KEY", "valueFrom": "${SECRET_ARN}:ANTHROPIC_API_KEY::"},
        {"name": "GOOGLE_API_KEY", "valueFrom": "${SECRET_ARN}:GOOGLE_API_KEY::"},
        {"name": "OPENAI_API_KEY", "valueFrom": "${SECRET_ARN}:OPENAI_API_KEY::"},
        {"name": "TELEGRAM_BOT_TOKEN", "valueFrom": "${SECRET_ARN}:TELEGRAM_BOT_TOKEN::"},
        {"name": "TELEGRAM_CHAT_ID", "valueFrom": "${SECRET_ARN}:TELEGRAM_CHAT_ID::"},
        {"name": "SLACK_WEBHOOK_URL", "valueFrom": "${SECRET_ARN}:SLACK_WEBHOOK_URL::"},
        {"name": "APOLLO_API_KEY", "valueFrom": "${SECRET_ARN}:APOLLO_API_KEY::"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": $(json_escape "$LOG_GROUP"),
          "awslogs-region": $(json_escape "$AWS_REGION"),
          "awslogs-stream-prefix": "backend"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 30
      }
    }
  ]
}
JSON

python3 -m json.tool "$TASK_DEF_FILE" >/dev/null

log "Registering new ECS task definition"
NEW_TASK_DEF_ARN="$(
  aws ecs register-task-definition \
    --region "$AWS_REGION" \
    --cli-input-json "file://$TASK_DEF_FILE" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text
)"
require_value "NEW_TASK_DEF_ARN" "$NEW_TASK_DEF_ARN" "Task definition registration did not return an ARN."

log "Updating ECS service: $CLUSTER_NAME / $SERVICE_NAME"
aws ecs update-service \
  --region "$AWS_REGION" \
  --cluster "$CLUSTER_NAME" \
  --service "$SERVICE_NAME" \
  --task-definition "$NEW_TASK_DEF_ARN" \
  --force-new-deployment >/dev/null

log "Waiting for service stability"
aws ecs wait services-stable \
  --region "$AWS_REGION" \
  --cluster "$CLUSTER_NAME" \
  --services "$SERVICE_NAME"

log "Service summary"
aws ecs describe-services \
  --region "$AWS_REGION" \
  --cluster "$CLUSTER_NAME" \
  --services "$SERVICE_NAME" \
  --query 'services[0].{serviceName:serviceName,status:status,running:runningCount,desired:desiredCount,taskDefinition:taskDefinition}' \
  --output table

HEALTH_URL="${API_URL%/}/health"
log "Verifying health endpoint: $HEALTH_URL"
curl -fsS "$HEALTH_URL" >/dev/null

log "Deployment complete: $IMAGE_URI"
