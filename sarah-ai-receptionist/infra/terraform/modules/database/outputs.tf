output "db_endpoint" { value = aws_db_instance.main.endpoint }
output "db_address" { value = aws_db_instance.main.address }
output "db_instance_id" { value = aws_db_instance.main.id }
output "redis_primary_endpoint" { value = aws_elasticache_replication_group.main.primary_endpoint_address }
output "redis_auth_token" {
  value     = random_password.redis_auth_token.result
  sensitive = true
}
