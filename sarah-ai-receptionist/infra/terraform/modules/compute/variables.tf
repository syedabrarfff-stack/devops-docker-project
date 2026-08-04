variable "project_name" { type = string }
variable "environment" { type = string }
variable "aws_region" { type = string }

variable "private_subnet_ids" { type = list(string) }
variable "ecs_security_group_id" { type = string }
variable "voice_target_group_arn" { type = string }
variable "api_target_group_arn" { type = string }

variable "ecs_task_execution_role_arn" { type = string }
variable "ecs_task_role_arn" { type = string }

variable "ecs_voice_cpu" { type = number }
variable "ecs_voice_memory" { type = number }
variable "ecs_voice_desired_count" { type = number }
variable "ecs_api_cpu" { type = number }
variable "ecs_api_memory" { type = number }
variable "ecs_api_desired_count" { type = number }

variable "container_image_voice" { type = string }
variable "container_image_api" { type = string }

variable "database_url_secret_arn" {
  description = "Secrets Manager ARN of the full DATABASE_URL (includes credentials) — injected via ECS `secrets`, never a plain environment variable"
  type        = string
}
variable "redis_url_secret_arn" {
  description = "Secrets Manager ARN of the full REDIS_URL (includes the AUTH token)"
  type        = string
}

variable "ecs_worker_desired_count" {
  type    = number
  default = 2
}

variable "recordings_bucket_name" { type = string }
variable "app_secrets_arn" { type = string }
variable "api_domain" { type = string }
variable "root_domain" {
  description = "Parent domain (e.g. aliyarsolutions.com). Refresh-token cookies are scoped to .<root_domain> so app./admin./sarah. can share the session."
  type        = string
}
