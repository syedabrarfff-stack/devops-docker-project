variable "aws_region" {
  description = "Primary AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "sarah-receptionist"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "root_domain" {
  description = "Root domain already hosted on GoDaddy (e.g. aliyarsolutions.com). DNS for subdomains only is delegated to Route53."
  type        = string
  default     = "aliyarsolutions.com"
}

variable "api_subdomain" {
  description = "Subdomain for the voice engine / API (ALB direct, low latency for Twilio Media Streams)"
  type        = string
  default     = "sarah"
}

variable "app_subdomain" {
  description = "Subdomain for the clinic dashboard (CloudFront + S3)"
  type        = string
  default     = "app"
}

variable "admin_subdomain" {
  description = "Subdomain for the admin console (CloudFront + S3)"
  type        = string
  default     = "admin"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "db_name" {
  type    = string
  default = "sarah_receptionist"
}

variable "db_username" {
  type    = string
  default = "sarah_admin"
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.small"
}

variable "ecs_voice_cpu" {
  type    = number
  default = 1024
}

variable "ecs_voice_memory" {
  type    = number
  default = 2048
}

variable "ecs_voice_desired_count" {
  type    = number
  default = 2
}

variable "ecs_api_cpu" {
  type    = number
  default = 512
}

variable "ecs_api_memory" {
  type    = number
  default = 1024
}

variable "ecs_api_desired_count" {
  type    = number
  default = 2
}

variable "container_image_voice" {
  description = "ECR image URI for the voice-service, injected by CI/CD"
  type        = string
  default     = ""
}

variable "container_image_api" {
  description = "ECR image URI for the api-service, injected by CI/CD"
  type        = string
  default     = ""
}
