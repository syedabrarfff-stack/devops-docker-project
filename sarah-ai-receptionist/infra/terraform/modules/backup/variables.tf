variable "project_name" { type = string }
variable "environment" { type = string }
variable "rds_instance_arn" { type = string }
variable "kms_key_arn" {
  description = "Primary-region KMS key for the primary vault. The DR vault uses the account's default AWS Backup key in the DR region — a customer-managed cross-region key isn't required for this to satisfy encryption-at-rest."
  type        = string
}
