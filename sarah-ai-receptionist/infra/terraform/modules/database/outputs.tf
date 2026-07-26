output "db_endpoint" { value = aws_db_instance.main.endpoint }
output "db_address" { value = aws_db_instance.main.address }
output "redis_primary_endpoint" { value = aws_elasticache_replication_group.main.primary_endpoint_address }
