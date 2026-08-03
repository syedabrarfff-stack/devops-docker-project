# ECR repos previously didn't exist anywhere in Terraform — deploy.yml
# assumed them, but nothing created them, so the very first apply/deploy
# would have had nowhere to push to.
resource "aws_ecr_repository" "voice" {
  name                 = "${var.project_name}-voice"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "api" {
  name                 = "${var.project_name}-api"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "voice" {
  repository = aws_ecr_repository.voice.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 20 images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 20 }
      action       = { type = "expire" }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 20 images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 20 }
      action       = { type = "expire" }
    }]
  })
}

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

locals {
  # CI/CD injects a real tagged image on every deploy; before the first image
  # is ever pushed, fall back to the ECR repo itself at :latest so task
  # definitions can register (an empty string is rejected by ECS outright).
  image_voice = var.container_image_voice != "" ? var.container_image_voice : "${aws_ecr_repository.voice.repository_url}:latest"
  image_api   = var.container_image_api != "" ? var.container_image_api : "${aws_ecr_repository.api.repository_url}:latest"

  common_env = [
    { name = "APP_ENV", value = var.environment },
    { name = "S3_BUCKET_RECORDINGS", value = var.recordings_bucket_name },
    { name = "AWS_REGION", value = var.aws_region },
    { name = "APP_BASE_URL", value = "https://${var.api_domain}" },
    # Refresh cookie must be scoped to the parent domain so app./admin./sarah.
    # subdomains can all send it -- without this the cookie is host-only to
    # sarah. and never reaches from app. on /auth/refresh, breaking silent
    # refresh and forcing a re-login every 15 minutes.
    { name = "REFRESH_COOKIE_DOMAIN", value = ".${var.root_domain}" },
  ]

  common_secrets = [
    # DATABASE_URL/REDIS_URL are whole-string secrets (not JSON), so valueFrom
    # is the bare secret ARN with no `:key::` JSON-key suffix.
    { name = "DATABASE_URL", valueFrom = var.database_url_secret_arn },
    { name = "REDIS_URL", valueFrom = var.redis_url_secret_arn },
    { name = "OPENROUTER_API_KEY", valueFrom = "${var.app_secrets_arn}:openrouter_api_key::" },
    { name = "TWILIO_ACCOUNT_SID", valueFrom = "${var.app_secrets_arn}:twilio_account_sid::" },
    { name = "TWILIO_AUTH_TOKEN", valueFrom = "${var.app_secrets_arn}:twilio_auth_token::" },
    { name = "TWILIO_PHONE_NUMBER", valueFrom = "${var.app_secrets_arn}:twilio_phone_number::" },
    { name = "DEEPGRAM_API_KEY", valueFrom = "${var.app_secrets_arn}:deepgram_api_key::" },
    { name = "ELEVENLABS_API_KEY", valueFrom = "${var.app_secrets_arn}:elevenlabs_api_key::" },
    { name = "ELEVENLABS_VOICE_ID", valueFrom = "${var.app_secrets_arn}:elevenlabs_voice_id::" },
    { name = "JWT_SECRET_KEY", valueFrom = "${var.app_secrets_arn}:jwt_secret_key::" },
    { name = "STRIPE_SECRET_KEY", valueFrom = "${var.app_secrets_arn}:stripe_secret_key::" },
    { name = "STRIPE_WEBHOOK_SECRET", valueFrom = "${var.app_secrets_arn}:stripe_webhook_secret::" },
  ]
}

resource "aws_cloudwatch_log_group" "voice" {
  name              = "/ecs/${var.project_name}-${var.environment}/voice-service"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.project_name}-${var.environment}/api-service"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.project_name}-${var.environment}/worker-service"
  retention_in_days = 30
}

# ── Voice service — handles the Twilio media stream, highest priority ──────
resource "aws_ecs_task_definition" "voice" {
  family                   = "${var.project_name}-${var.environment}-voice"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_voice_cpu
  memory                   = var.ecs_voice_memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name         = "voice-service"
    image        = local.image_voice
    essential    = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment  = local.common_env
    secrets      = local.common_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.voice.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "voice"
      }
    }
  }])
}

resource "aws_ecs_service" "voice" {
  name            = "${var.project_name}-${var.environment}-voice"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.voice.arn
  desired_count   = var.ecs_voice_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.ecs_security_group_id]
  }

  load_balancer {
    target_group_arn = var.voice_target_group_arn
    container_name   = "voice-service"
    container_port   = 8000
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}

# ── API service — dashboard/admin REST API, non-realtime traffic ───────────
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-${var.environment}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_api_cpu
  memory                   = var.ecs_api_memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name         = "api-service"
    image        = local.image_api
    essential    = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment  = local.common_env
    secrets      = local.common_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-${var.environment}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.ecs_api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.ecs_security_group_id]
  }

  load_balancer {
    target_group_arn = var.api_target_group_arn
    container_name   = "api-service"
    container_port   = 8000
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}

# ── Worker service — Arq background jobs (SMS, summaries, reminders) ───────
resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.project_name}-${var.environment}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name        = "worker-service"
    image       = local.image_api
    essential   = true
    command     = ["arq", "app.workers.worker.WorkerSettings"]
    environment = local.common_env
    secrets     = local.common_secrets
    # arq has no HTTP surface, so liveness is "the process that imported the
    # worker settings and can still touch Python" — cheap, catches a crashed
    # interpreter/import error without needing a real endpoint.
    # startPeriod/timeout were originally 10s/5s and too tight for a cold
    # interpreter importing SQLAlchemy+boto3+arq under 256 CPU units — the
    # container got killed as "unhealthy" before it ever finished starting,
    # in an infinite replace loop. Confirmed via CloudWatch logs showing the
    # worker connecting to Redis fine each time, then SIGTERM ~90s later
    # with 0 jobs processed — an ECS health-check kill, not an app crash.
    healthCheck = {
      command     = ["CMD-SHELL", "python -c 'import app.workers.worker' || exit 1"]
      interval    = 30
      timeout     = 10
      retries     = 3
      startPeriod = 45
    }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.worker.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])
}

resource "aws_ecs_service" "worker" {
  name            = "${var.project_name}-${var.environment}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.ecs_worker_desired_count # >1 for redundancy — a hung worker previously had no backup
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.ecs_security_group_id]
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}

# ── Autoscaling — voice service scales on ALB request count ────────────────
resource "aws_appautoscaling_target" "voice" {
  max_capacity       = 10
  min_capacity       = var.ecs_voice_desired_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.voice.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "voice_cpu" {
  name               = "${var.project_name}-${var.environment}-voice-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.voice.resource_id
  scalable_dimension = aws_appautoscaling_target.voice.scalable_dimension
  service_namespace  = aws_appautoscaling_target.voice.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 65
    scale_in_cooldown  = 120
    scale_out_cooldown = 60
  }
}

# ── Autoscaling — api-service was previously fixed capacity ────────────────
resource "aws_appautoscaling_target" "api" {
  max_capacity       = 6
  min_capacity       = var.ecs_api_desired_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${var.project_name}-${var.environment}-api-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 65
    scale_in_cooldown  = 120
    scale_out_cooldown = 60
  }
}
