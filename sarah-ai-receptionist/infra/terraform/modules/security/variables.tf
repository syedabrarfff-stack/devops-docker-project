variable "project_name" { type = string }
variable "environment" { type = string }
variable "db_username" { type = string }
variable "recordings_bucket_arn" {
  description = "ARN (or ARN pattern) of the S3 recordings bucket, computed from the deterministic bucket name to avoid a module dependency cycle with the storage module"
  type        = string
}
