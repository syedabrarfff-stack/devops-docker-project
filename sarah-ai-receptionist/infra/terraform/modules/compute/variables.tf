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

variable "db_username" { type = string }
variable "db_password" {
  type      = string
  sensitive = true
}
variable "db_address" { type = string }
variable "db_name" { type = string }
variable "redis_endpoint" { type = string }

variable "recordings_bucket_name" { type = string }
variable "app_secrets_arn" { type = string }
variable "api_domain" { type = string }
