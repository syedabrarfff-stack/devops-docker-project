################################################################################
# JARVIS — Aliyar Solutions
# AWS Production Infrastructure
# Primary region: ap-south-2 (Hyderabad)
# Backup region:  ap-south-1 (Mumbai) — Phase 2
################################################################################

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # Uncomment to use S3 backend for team state management:
  # backend "s3" {
  #   bucket         = "jarvis-terraform-state"
  #   key            = "production/terraform.tfstate"
  #   region         = "ap-south-2"
  #   encrypt        = true
  #   dynamodb_table = "jarvis-terraform-locks"
  # }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "Aliyar-Solutions"
    }
  }
}

locals {
  prefix = "${var.project}-${var.environment}"
  azs    = data.aws_availability_zones.available.names
}

data "aws_availability_zones" "available" {
  state = "available"
}

################################################################################
# VPC
################################################################################

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "${local.prefix}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.prefix}-igw" }
}

resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = local.azs[count.index % length(local.azs)]
  map_public_ip_on_launch = true
  tags = { Name = "${local.prefix}-public-${count.index + 1}", Tier = "Public" }
}

resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = local.azs[count.index % length(local.azs)]
  tags = { Name = "${local.prefix}-private-${count.index + 1}", Tier = "Private" }
}

resource "aws_eip" "nat" {
  count  = 1
  domain = "vpc"
  tags   = { Name = "${local.prefix}-nat-eip" }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.main]
  tags = { Name = "${local.prefix}-nat" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "${local.prefix}-rt-public" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
  tags = { Name = "${local.prefix}-rt-private" }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

################################################################################
# Security Groups
################################################################################

resource "aws_security_group" "alb" {
  name        = "${local.prefix}-sg-alb"
  description = "ALB — allow HTTP/HTTPS from anywhere"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${local.prefix}-sg-alb" }
}

resource "aws_security_group" "backend" {
  name        = "${local.prefix}-sg-backend"
  description = "JARVIS backend ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${local.prefix}-sg-backend" }
}

resource "aws_security_group" "rds" {
  name        = "${local.prefix}-sg-rds"
  description = "RDS PostgreSQL — backend only"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }
  tags = { Name = "${local.prefix}-sg-rds" }
}

resource "aws_security_group" "redis" {
  name        = "${local.prefix}-sg-redis"
  description = "ElastiCache Redis — backend only"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }
  tags = { Name = "${local.prefix}-sg-redis" }
}

################################################################################
# RDS PostgreSQL
################################################################################

resource "aws_db_subnet_group" "main" {
  name       = "${local.prefix}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
  tags = { Name = "${local.prefix}-db-subnet-group" }
}

resource "aws_db_instance" "postgres" {
  identifier             = "${local.prefix}-postgres"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_storage_gb
  max_allocated_storage  = 100
  storage_type           = "gp3"
  storage_encrypted      = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period   = 7
  backup_window             = "03:00-04:00"
  maintenance_window        = "sun:04:30-sun:05:30"
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.prefix}-postgres-final"
  copy_tags_to_snapshot     = true
  multi_az                  = false   # enable after MVP stabilisation

  performance_insights_enabled = true

  tags = { Name = "${local.prefix}-postgres" }
}

################################################################################
# ElastiCache Redis
################################################################################

resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.prefix}-redis-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${local.prefix}-redis"
  engine               = "redis"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  engine_version       = "7.1"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]
  tags = { Name = "${local.prefix}-redis" }
}

################################################################################
# ECR Repositories
################################################################################

resource "aws_ecr_repository" "backend" {
  name                 = "${local.prefix}-backend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = { Name = "${local.prefix}-backend-ecr" }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${local.prefix}-frontend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = { Name = "${local.prefix}-frontend-ecr" }
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 }
      action       = { type = "expire" }
    }]
  })
}

################################################################################
# Application Load Balancer
################################################################################

resource "aws_lb" "main" {
  name               = "${local.prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = true
  tags = { Name = "${local.prefix}-alb" }
}

resource "aws_lb_target_group" "backend" {
  name        = "${local.prefix}-tg-backend"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    interval            = 30
    timeout             = 10
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }
  tags = { Name = "${local.prefix}-tg-backend" }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# HTTPS listener — requires ACM certificate (set domain_name variable)
resource "aws_lb_listener" "https" {
  count             = var.domain_name != "" ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.main[0].certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

# HTTP-only fallback listener (no domain configured)
resource "aws_lb_listener" "http_forward" {
  count             = var.domain_name == "" ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

################################################################################
# ACM + Route53 (optional — requires domain_name variable)
################################################################################

resource "aws_acm_certificate" "main" {
  count             = var.domain_name != "" ? 1 : 0
  domain_name       = "${var.api_subdomain}.${var.domain_name}"
  validation_method = "DNS"
  subject_alternative_names = [var.domain_name]
  lifecycle { create_before_destroy = true }
}

data "aws_route53_zone" "main" {
  count        = var.domain_name != "" ? 1 : 0
  name         = var.domain_name
  private_zone = false
}

resource "aws_route53_record" "cert_validation" {
  for_each = var.domain_name != "" ? {
    for dvo in aws_acm_certificate.main[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main[0].zone_id
}

resource "aws_acm_certificate_validation" "main" {
  count                   = var.domain_name != "" ? 1 : 0
  certificate_arn         = aws_acm_certificate.main[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

resource "aws_route53_record" "api" {
  count   = var.domain_name != "" ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "${var.api_subdomain}.${var.domain_name}"
  type    = "A"
  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

################################################################################
# Secrets Manager
################################################################################

resource "aws_secretsmanager_secret" "jarvis" {
  name                    = "${local.prefix}/env"
  description             = "JARVIS production environment secrets"
  recovery_window_in_days = 7
  tags = { Name = "${local.prefix}-secrets" }
}

resource "aws_secretsmanager_secret_version" "jarvis" {
  secret_id = aws_secretsmanager_secret.jarvis.id
  secret_string = jsonencode({
    SECRET_KEY         = var.secret_key
    DATABASE_URL       = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.address}:5432/${var.db_name}"
    REDIS_URL          = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"
    ANTHROPIC_API_KEY  = var.anthropic_api_key
    GOOGLE_API_KEY     = var.google_api_key
    OPENAI_API_KEY     = var.openai_api_key
    TELEGRAM_BOT_TOKEN = var.telegram_bot_token
    TELEGRAM_CHAT_ID   = var.telegram_chat_id
    SLACK_WEBHOOK_URL  = var.slack_webhook_url
    APOLLO_API_KEY     = var.apollo_api_key
  })
}

################################################################################
# S3 — Event lake + backups
################################################################################

resource "aws_s3_bucket" "data" {
  bucket = "${local.prefix}-data-${data.aws_caller_identity.current.account_id}"
  tags = { Name = "${local.prefix}-data" }
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

################################################################################
# CloudWatch Log Groups
################################################################################

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/jarvis/${var.environment}/backend"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${local.prefix}"
  retention_in_days = 14
}
