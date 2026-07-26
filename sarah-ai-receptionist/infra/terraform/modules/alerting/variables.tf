variable "project_name" { type = string }
variable "environment" { type = string }

variable "alarm_email" {
  description = "Email address subscribed to the alarm SNS topic"
  type        = string
}

variable "alb_arn_suffix" { type = string }
variable "voice_tg_arn_suffix" { type = string }
variable "api_tg_arn_suffix" { type = string }

variable "ecs_cluster_name" { type = string }
variable "ecs_voice_service_name" { type = string }
variable "ecs_api_service_name" { type = string }
variable "ecs_worker_service_name" { type = string }

variable "rds_instance_id" { type = string }
