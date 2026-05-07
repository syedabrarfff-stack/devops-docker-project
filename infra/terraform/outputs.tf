output "vpc_id" {
  value = aws_vpc.main.id
}

output "alb_dns_name" {
  description = "ALB public DNS — use this if no custom domain is configured"
  value       = aws_lb.main.dns_name
}

output "api_url" {
  description = "JARVIS API URL"
  value       = var.domain_name != "" ? "https://${var.api_subdomain}.${var.domain_name}" : "http://${aws_lb.main.dns_name}"
}

output "ecr_backend_url" {
  description = "ECR repository URL for backend Docker images"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  description = "ECR repository URL for frontend Docker images"
  value       = aws_ecr_repository.frontend.repository_url
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (private — accessible from ECS only)"
  value       = aws_db_instance.postgres.address
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint (private)"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
  sensitive   = true
}

output "s3_bucket" {
  description = "S3 data lake bucket name"
  value       = aws_s3_bucket.data.bucket
}

output "secrets_manager_arn" {
  description = "ARN of the JARVIS Secrets Manager secret"
  value       = aws_secretsmanager_secret.jarvis.arn
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.backend.name
}

output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.backend.name
}
