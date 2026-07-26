output "kms_key_arn" { value = aws_kms_key.main.arn }
output "kms_key_id" { value = aws_kms_key.main.key_id }

output "app_secrets_arn" { value = aws_secretsmanager_secret.app_secrets.arn }
output "db_credentials_arn" { value = aws_secretsmanager_secret.db_credentials.arn }
output "db_password" {
  value     = random_password.db_password.result
  sensitive = true
}

output "ecs_task_execution_role_arn" { value = aws_iam_role.ecs_task_execution.arn }
output "ecs_task_role_arn" { value = aws_iam_role.ecs_task.arn }
