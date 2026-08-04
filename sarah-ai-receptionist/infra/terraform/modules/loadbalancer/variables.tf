variable "project_name" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "api_certificate_arn" { type = string }
variable "api_zone_id" { type = string }
