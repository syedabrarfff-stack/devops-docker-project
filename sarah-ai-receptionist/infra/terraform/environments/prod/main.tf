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

  db_username    = var.db_username
  db_password    = module.security.db_password
  db_address     = module.database.db_address
  db_name        = var.db_name
  redis_endpoint = module.database.redis_primary_endpoint

  recordings_bucket_name = module.storage.recordings_bucket_name
  app_secrets_arn         = module.security.app_secrets_arn
  api_domain              = "${var.api_subdomain}.${var.root_domain}"
}
