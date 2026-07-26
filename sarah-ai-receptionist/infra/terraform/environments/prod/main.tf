terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    # bucket, key, region, dynamodb_table supplied via -backend-config at `terraform init`
    # to keep this file environment-agnostic and avoid committing account-specific state config.
  }
}

provider "aws" {
  region = var.aws_region
}

# CloudFront + its ACM certificate must be provisioned from us-east-1 regardless of primary region
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

module "networking" {
  source       = "../../modules/networking"
  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
}

module "dns" {
  source = "../../modules/dns"
  providers = {
    aws            = aws
    aws.us_east_1  = aws.us_east_1
  }
  root_domain     = var.root_domain
  api_subdomain   = var.api_subdomain
  app_subdomain   = var.app_subdomain
  admin_subdomain = var.admin_subdomain
}

module "security" {
  source       = "../../modules/security"
  project_name = var.project_name
  environment  = var.environment
  db_username  = var.db_username
  # Bucket ARN computed deterministically (matches storage module's naming)
  # to avoid a module dependency cycle between security and storage.
  recordings_bucket_arn = "arn:aws:s3:::${var.project_name}-${var.environment}-recordings"
}

module "storage" {
  source       = "../../modules/storage"
  project_name = var.project_name
  environment  = var.environment
  kms_key_arn  = module.security.kms_key_arn
}

module "loadbalancer" {
  source              = "../../modules/loadbalancer"
  project_name        = var.project_name
  environment         = var.environment
  vpc_id              = module.networking.vpc_id
  public_subnet_ids   = module.networking.public_subnet_ids
  api_certificate_arn = module.dns.api_certificate_arn
  api_zone_id         = module.dns.api_zone_id
}

module "cdn" {
  source = "../../modules/cdn"
  providers = { aws = aws }

  project_name                         = var.project_name
  environment                          = var.environment
  app_domain                           = "${var.app_subdomain}.${var.root_domain}"
  admin_domain                         = "${var.admin_subdomain}.${var.root_domain}"
  app_zone_id                          = module.dns.app_zone_id
  admin_zone_id                        = module.dns.admin_zone_id
  cdn_certificate_arn                  = module.dns.cdn_certificate_arn
  frontend_bucket_name                 = module.storage.frontend_bucket_name
  frontend_bucket_arn                  = module.storage.frontend_bucket_arn
  frontend_bucket_regional_domain_name = module.storage.frontend_bucket_regional_domain_name
}

module "database" {
  source                 = "../../modules/database"
  project_name           = var.project_name
  environment            = var.environment
  vpc_id                 = module.networking.vpc_id
  private_subnet_ids     = module.networking.private_subnet_ids
  ecs_security_group_id  = module.loadbalancer.ecs_security_group_id
  kms_key_arn            = module.security.kms_key_arn
  db_instance_class      = var.db_instance_class
  db_name                = var.db_name
  db_username            = var.db_username
  db_password            = module.security.db_password
  redis_node_type        = var.redis_node_type
}

# The full DATABASE_URL — including the password — is a secret in its own
# right, created here (not inside a module) because it needs module.database's
# address output and module.security's password output together. Storing it
# as a Secrets Manager value and injecting it via ECS `secrets` (not
# `environment`) keeps the password out of the task definition, the console,
# and Terraform's own plan output for anyone who can read the ECS API.
resource "aws_secretsmanager_secret" "database_url" {
  name       = "${var.project_name}-${var.environment}/database-url"
  kms_key_id = module.security.kms_key_arn
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql+asyncpg://${var.db_username}:${module.security.db_password}@${module.database.db_address}:5432/${var.db_name}"
}

# Same treatment for REDIS_URL — now that Redis requires an AUTH token, the
# connection string is a credential too and gets the same Secrets Manager
# treatment as DATABASE_URL, not a plain ECS environment variable.
resource "aws_secretsmanager_secret" "redis_url" {
  name       = "${var.project_name}-${var.environment}/redis-url"
  kms_key_id = module.security.kms_key_arn
}

resource "aws_secretsmanager_secret_version" "redis_url" {
  secret_id     = aws_secretsmanager_secret.redis_url.id
  secret_string = "rediss://:${module.database.redis_auth_token}@${module.database.redis_primary_endpoint}:6379/0"
}

module "compute" {
  source = "../../modules/compute"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region

  private_subnet_ids     = module.networking.private_subnet_ids
  ecs_security_group_id  = module.loadbalancer.ecs_security_group_id
  voice_target_group_arn = module.loadbalancer.voice_target_group_arn
  api_target_group_arn   = module.loadbalancer.api_target_group_arn

  ecs_task_execution_role_arn = module.security.ecs_task_execution_role_arn
  ecs_task_role_arn           = module.security.ecs_task_role_arn

  ecs_voice_cpu            = var.ecs_voice_cpu
  ecs_voice_memory         = var.ecs_voice_memory
  ecs_voice_desired_count  = var.ecs_voice_desired_count
  ecs_api_cpu              = var.ecs_api_cpu
  ecs_api_memory           = var.ecs_api_memory
  ecs_api_desired_count    = var.ecs_api_desired_count

  container_image_voice = var.container_image_voice
  container_image_api   = var.container_image_api

  database_url_secret_arn = aws_secretsmanager_secret.database_url.arn
  redis_url_secret_arn    = aws_secretsmanager_secret.redis_url.arn

  recordings_bucket_name = module.storage.recordings_bucket_name
  app_secrets_arn         = module.security.app_secrets_arn
  api_domain              = "${var.api_subdomain}.${var.root_domain}"
}

# All CloudWatch alarms/SNS live downstream of compute/loadbalancer/database —
# alerting depends on them, never the reverse, so this can't form a cycle.
module "alerting" {
  source = "../../modules/alerting"

  project_name         = var.project_name
  environment          = var.environment
  alarm_email          = var.alarm_email
  alb_arn_suffix       = module.loadbalancer.alb_arn_suffix
  voice_tg_arn_suffix  = module.loadbalancer.voice_target_group_arn_suffix
  api_tg_arn_suffix    = module.loadbalancer.api_target_group_arn_suffix
  ecs_cluster_name     = module.compute.ecs_cluster_name
  ecs_voice_service_name  = module.compute.ecs_voice_service_name
  ecs_api_service_name    = module.compute.ecs_api_service_name
  ecs_worker_service_name = module.compute.ecs_worker_service_name
  rds_instance_id      = module.database.db_instance_id
}

module "audit" {
  source       = "../../modules/audit"
  project_name = var.project_name
  environment  = var.environment
}
