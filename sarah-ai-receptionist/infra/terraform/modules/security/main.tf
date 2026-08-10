resource "aws_kms_key" "main" {
  description             = "${var.project_name}-${var.environment} encryption key — RDS, S3, Secrets Manager"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.project_name}-${var.environment}"
  target_key_id = aws_kms_key.main.key_id
}

# ── Secrets Manager: all third-party API keys and DB credentials ───────────
resource "aws_secretsmanager_secret" "app_secrets" {
  name       = "${var.project_name}-${var.environment}/app-secrets"
  kms_key_id = aws_kms_key.main.arn
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  # Populated out-of-band via `aws secretsmanager put-secret-value` or the AWS console —
  # never store real key values in Terraform state or version control.
  secret_string = jsonencode({
    openrouter_api_key    = "REPLACE_ME"
    twilio_account_sid    = "REPLACE_ME"
    twilio_auth_token     = "REPLACE_ME"
    twilio_phone_number   = "REPLACE_ME"
    deepgram_api_key      = "REPLACE_ME"
    elevenlabs_api_key    = "REPLACE_ME"
    elevenlabs_voice_id   = "REPLACE_ME"
    jwt_secret_key        = "REPLACE_ME"
    stripe_secret_key     = "REPLACE_ME"
    stripe_webhook_secret = "REPLACE_ME"
    # The Stripe Price ID a new clinic's subscription attaches to
    # (billing_service.py). Without it, billing_service creates a Stripe
    # Customer only -- nothing ever charges, and clinics onboard as free
    # forever with no error. Must be a Price object created in the Stripe
    # Dashboard in the currency/amount the deployment actually bills in
    # (SAR for the Saudi go-to-market -- see DEFAULT_CURRENCY in
    # billing_service.py) before this stops being REPLACE_ME.
    stripe_price_id = "REPLACE_ME"
    # Browser "Call Sarah" widget (Twilio Voice SDK). Separate API Key/Secret
    # pair + TwiML App SID -- not the main twilio_auth_token above -- so a
    # leaked widget token can't touch the rest of the Twilio account. Leave
    # as REPLACE_ME (the widget's /token endpoint returns 503) until these
    # are created in the Twilio console.
    twilio_voice_api_key_sid    = "REPLACE_ME"
    twilio_voice_api_key_secret = "REPLACE_ME"
    twilio_voice_twiml_app_sid  = "REPLACE_ME"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name       = "${var.project_name}-${var.environment}/db-credentials"
  kms_key_id = aws_kms_key.main.arn
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
  })
}

# ── IAM: ECS task execution role (pulls images, reads secrets) ─────────────
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-${var.environment}-ecs-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

resource "aws_iam_role_policy" "ecs_secrets_access" {
  name = "${var.project_name}-${var.environment}-secrets-access"
  role = aws_iam_role.ecs_task_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        # Prefix-matched rather than enumerated: the database-url secret is
        # created at the root module (it needs the DB module's address output,
        # which would otherwise cycle back through this module's kms_key_arn).
        # Every secret under this project/environment shares the same name
        # prefix, so a wildcard here covers app-secrets, db-credentials, and
        # database-url without that dependency.
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}-${var.environment}/*"
        ]
      },
      {
        # secretsmanager:GetSecretValue alone isn't enough for secrets encrypted
        # with a customer-managed KMS key — Secrets Manager still calls
        # kms:Decrypt on the caller's behalf, and that's checked separately.
        # Confirmed by a real ECS task failing with
        # "AccessDeniedException: Access to KMS is not allowed" without this.
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.main.arn]
      }
    ]
  })
}

# ── IAM: ECS task role (application runtime permissions — S3 recordings) ───
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-${var.environment}-ecs-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${var.project_name}-${var.environment}-s3-recordings"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject"]
      Resource = ["${var.recordings_bucket_arn}/*"]
    }]
  })
}
