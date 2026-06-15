################################################################################
# JARVIS ECS — Fargate cluster, task definitions, services, autoscaling
################################################################################

################################################################################
# ECS Cluster
################################################################################

resource "aws_ecs_cluster" "main" {
  name = "${local.prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = { Name = "${local.prefix}-cluster" }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }
}

################################################################################
# IAM — ECS Task Execution Role
################################################################################

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = "${local.prefix}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "${local.prefix}-ecs-secrets"
  role = aws_iam_role.ecs_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue", "kms:Decrypt"]
      Resource = [aws_secretsmanager_secret.jarvis.arn]
    }]
  })
}

################################################################################
# IAM — ECS Task Role (runtime permissions)
################################################################################

resource "aws_iam_role" "ecs_task" {
  name               = "${local.prefix}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "ecs_task_permissions" {
  name = "${local.prefix}-task-permissions"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [aws_s3_bucket.data.arn, "${aws_s3_bucket.data.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath", "ssm:PutParameter"]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/jarvis/*"
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.jarvis.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = ["${aws_cloudwatch_log_group.backend.arn}:*"]
      }
    ]
  })
}

################################################################################
# ECS Task Definition — Backend + Frontend sidecar
# Both containers share an ENI (awsvpc) and communicate over localhost.
# ALB hits port 80 on the frontend nginx, which proxies /api/ to localhost:8000.
################################################################################

locals {
  secret_arn = aws_secretsmanager_secret.jarvis.arn
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.prefix}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    # ── Backend — FastAPI / Gunicorn ──────────────────────────────────────────
    {
      name      = "backend"
      image     = var.backend_image != "" ? var.backend_image : "${aws_ecr_repository.backend.repository_url}:latest"
      essential = true

      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]

      # Individual secrets from Secrets Manager — FastAPI Settings reads these as env vars.
      secrets = [
        { name = "SECRET_KEY",           valueFrom = "${local.secret_arn}:SECRET_KEY::" },
        { name = "CAPTAIN_PASSWORD",     valueFrom = "${local.secret_arn}:CAPTAIN_PASSWORD::" },
        { name = "CAPTAIN_USERNAME",     valueFrom = "${local.secret_arn}:CAPTAIN_USERNAME::" },
        { name = "DATABASE_URL",         valueFrom = "${local.secret_arn}:DATABASE_URL::" },
        { name = "REDIS_URL",            valueFrom = "${local.secret_arn}:REDIS_URL::" },
        { name = "ANTHROPIC_API_KEY",    valueFrom = "${local.secret_arn}:ANTHROPIC_API_KEY::" },
        { name = "NVIDIA_API_KEY",       valueFrom = "${local.secret_arn}:NVIDIA_API_KEY::" },
        { name = "NVIDIA_API_KEY_B",     valueFrom = "${local.secret_arn}:NVIDIA_API_KEY_B::" },
        { name = "NVIDIA_API_KEY_C",     valueFrom = "${local.secret_arn}:NVIDIA_API_KEY_C::" },
        { name = "NVIDIA_API_KEY_D",     valueFrom = "${local.secret_arn}:NVIDIA_API_KEY_D::" },
        { name = "NVIDIA_API_KEY_E",     valueFrom = "${local.secret_arn}:NVIDIA_API_KEY_E::" },
        { name = "NVIDIA_API_KEY_F",     valueFrom = "${local.secret_arn}:NVIDIA_API_KEY_F::" },
        { name = "NVIDIA_API_KEY_G",     valueFrom = "${local.secret_arn}:NVIDIA_API_KEY_G::" },
        { name = "NVIDIA_API_KEY_H",     valueFrom = "${local.secret_arn}:NVIDIA_API_KEY_H::" },
        { name = "NVIDIA_API_KEY_I",     valueFrom = "${local.secret_arn}:NVIDIA_API_KEY_I::" },
        { name = "NVIDIA_API_KEY_J",     valueFrom = "${local.secret_arn}:NVIDIA_API_KEY_J::" },
        { name = "GOOGLE_MAPS_API_KEY",  valueFrom = "${local.secret_arn}:GOOGLE_MAPS_API_KEY::" },
        { name = "OPENAI_API_KEY",       valueFrom = "${local.secret_arn}:OPENAI_API_KEY::" },
        { name = "GROQ_API_KEY",         valueFrom = "${local.secret_arn}:GROQ_API_KEY::" },
        { name = "MISTRAL_API_KEY",      valueFrom = "${local.secret_arn}:MISTRAL_API_KEY::" },
        { name = "DEEPSEEK_API_KEY",     valueFrom = "${local.secret_arn}:DEEPSEEK_API_KEY::" },
        { name = "MOONSHOT_API_KEY",     valueFrom = "${local.secret_arn}:MOONSHOT_API_KEY::" },
        { name = "ZHIPUAI_API_KEY",      valueFrom = "${local.secret_arn}:ZHIPUAI_API_KEY::" },
        { name = "DASHSCOPE_API_KEY",    valueFrom = "${local.secret_arn}:DASHSCOPE_API_KEY::" },
        { name = "MINIMAX_API_KEY",      valueFrom = "${local.secret_arn}:MINIMAX_API_KEY::" },
        { name = "STRIPE_SECRET_KEY",    valueFrom = "${local.secret_arn}:STRIPE_SECRET_KEY::" },
        { name = "STRIPE_PUBLISHABLE_KEY", valueFrom = "${local.secret_arn}:STRIPE_PUBLISHABLE_KEY::" },
        { name = "STRIPE_WEBHOOK_SECRET", valueFrom = "${local.secret_arn}:STRIPE_WEBHOOK_SECRET::" },
        { name = "SLACK_WEBHOOK_URL",    valueFrom = "${local.secret_arn}:SLACK_WEBHOOK_URL::" },
        { name = "TELEGRAM_BOT_TOKEN",   valueFrom = "${local.secret_arn}:TELEGRAM_BOT_TOKEN::" },
        { name = "TELEGRAM_CHAT_ID",     valueFrom = "${local.secret_arn}:TELEGRAM_CHAT_ID::" },
        { name = "N8N_BASE_URL",         valueFrom = "${local.secret_arn}:N8N_BASE_URL::" },
        { name = "N8N_WEBHOOK_URL",      valueFrom = "${local.secret_arn}:N8N_WEBHOOK_URL::" },
        { name = "EVOLUTION_API_KEY",    valueFrom = "${local.secret_arn}:EVOLUTION_API_KEY::" },
        { name = "EVOLUTION_API_URL",    valueFrom = "${local.secret_arn}:EVOLUTION_API_URL::" },
        { name = "EVOLUTION_PUBLIC_URL", valueFrom = "${local.secret_arn}:EVOLUTION_PUBLIC_URL::" },
        { name = "JARVIS_DEFAULT_TENANT_ID", valueFrom = "${local.secret_arn}:JARVIS_DEFAULT_TENANT_ID::" },
      ]

      environment = [
        { name = "DEBUG",             value = "false" },
        { name = "USE_AWS",           value = "true" },
        { name = "AWS_REGION",        value = var.aws_region },
        { name = "AWS_S3_BUCKET",     value = aws_s3_bucket.data.bucket },
        { name = "APP_BASE_URL",      value = var.domain_name != "" ? "https://${var.domain_name}" : "" },
        { name = "CORS_ORIGINS",      value = var.domain_name != "" ? "https://${var.domain_name},https://www.${var.domain_name}" : "" },
        { name = "WHATSAPP_ENABLED",  value = "true" },
        { name = "LOG_LEVEL",         value = "INFO" },
        { name = "GUNICORN_WORKERS",  value = "2" },
        { name = "GUNICORN_TIMEOUT",  value = "240" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 45
      }
    },

    # ── Frontend — nginx serving React SPA, proxying /api/ to localhost:8000 ─
    {
      name      = "frontend"
      image     = var.frontend_image != "" ? var.frontend_image : "${aws_ecr_repository.frontend.repository_url}:latest"
      essential = true

      portMappings = [{
        containerPort = 80
        protocol      = "tcp"
      }]

      environment = [
        # localhost because both containers share Fargate task network namespace
        { name = "BACKEND_HOST", value = "localhost" },
      ]

      dependsOn = [{
        containerName = "backend"
        condition     = "HEALTHY"
      }]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "frontend"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "wget -qO- http://localhost/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = { Name = "${local.prefix}-task" }
}

################################################################################
# ECS Service
################################################################################

resource "aws_ecs_service" "backend" {
  name            = "${local.prefix}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.backend.id]
    assign_public_ip = false
  }

  # ALB routes to the frontend container port 80
  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "frontend"
    container_port   = 80
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_controller {
    type = "ECS"
  }

  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_lb_listener.http_redirect]

  tags = { Name = "${local.prefix}-svc" }
}

################################################################################
# Auto Scaling — Backend
################################################################################

resource "aws_appautoscaling_target" "backend" {
  max_capacity       = 5
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "backend_cpu" {
  name               = "${local.prefix}-backend-cpu-scale"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "backend_memory" {
  name               = "${local.prefix}-backend-mem-scale"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 80.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

################################################################################
# CloudWatch Alarms — Captain notifications on critical events
################################################################################

resource "aws_cloudwatch_metric_alarm" "backend_cpu_critical" {
  alarm_name          = "${local.prefix}-backend-cpu-critical"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 90
  alarm_description   = "JARVIS backend CPU >90% for 2 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.backend.name
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${local.prefix}-rds-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "JARVIS RDS connections approaching limit"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres.identifier
  }
}
