resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnets"
  subnet_ids = var.private_subnet_ids
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-${var.environment}-rds-"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.ecs_security_group_id]
  }

  # No egress rule — a database has no legitimate reason to initiate outbound
  # connections. Previously allowed all traffic to 0.0.0.0/0.
}

resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-${var.environment}"
  engine         = "postgres"
  engine_version = "16.4"
  instance_class = var.db_instance_class

  allocated_storage     = 50
  max_allocated_storage = 200
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = var.kms_key_arn

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az                     = true
  backup_retention_period      = 14
  backup_window                = "03:00-04:00"
  maintenance_window           = "mon:04:30-mon:05:30"
  deletion_protection          = true
  skip_final_snapshot          = false
  final_snapshot_identifier    = "${var.project_name}-${var.environment}-final"
  performance_insights_enabled = true

  tags = { Name = "${var.project_name}-${var.environment}-postgres" }
}

# ── Redis (ElastiCache) — active call session state, config cache ─────────
resource "random_password" "redis_auth_token" {
  length  = 32
  special = false # ElastiCache AUTH tokens reject most special characters
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-redis-subnets"
  subnet_ids = var.private_subnet_ids
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-${var.environment}-redis-"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.ecs_security_group_id]
  }

  # No egress rule — same reasoning as the RDS security group above.
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${var.project_name}-${var.environment}-redis"
  description          = "Sarah call session cache"

  node_type                  = var.redis_node_type
  num_cache_clusters         = 2
  engine                     = "redis"
  engine_version             = "7.1"
  port                       = 6379
  automatic_failover_enabled = true

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth_token.result
  kms_key_id                 = var.kms_key_arn
}
