# Cross-region disaster recovery for RDS. Previously backups were 14-day,
# in-region only (RDS automated backups) — a regional AWS event had no
# documented or implemented recovery path. This adds a second, independent
# copy of every backup in a different region via AWS Backup.

resource "aws_backup_vault" "primary" {
  name        = "${var.project_name}-${var.environment}-vault"
  kms_key_arn = var.kms_key_arn
}

resource "aws_backup_vault" "dr" {
  provider = aws.dr
  name     = "${var.project_name}-${var.environment}-vault-dr"
}

resource "aws_iam_role" "backup" {
  name = "${var.project_name}-${var.environment}-backup"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "backup.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_backup_plan" "main" {
  name = "${var.project_name}-${var.environment}-plan"

  rule {
    rule_name         = "daily-with-cross-region-copy"
    target_vault_name = aws_backup_vault.primary.name
    schedule          = "cron(0 8 * * ? *)" # 08:00 UTC daily
    lifecycle {
      delete_after = 35
    }

    copy_action {
      destination_vault_arn = aws_backup_vault.dr.arn
      lifecycle {
        delete_after = 35
      }
    }
  }
}

resource "aws_backup_selection" "rds" {
  name         = "${var.project_name}-${var.environment}-rds-selection"
  iam_role_arn = aws_iam_role.backup.arn
  plan_id      = aws_backup_plan.main.id
  resources    = [var.rds_instance_arn]
}
