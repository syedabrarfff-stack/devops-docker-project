output "alb_dns_name" {
  value = module.loadbalancer.alb_dns_name
}

output "api_zone_name_servers" {
  description = "Add these as NS records for 'sarah' in your GoDaddy DNS panel for aliyarsolutions.com"
  value       = module.dns.api_zone_name_servers
}

output "app_zone_name_servers" {
  description = "Add these as NS records for 'app' in your GoDaddy DNS panel for aliyarsolutions.com"
  value       = module.dns.app_zone_name_servers
}

output "admin_zone_name_servers" {
  description = "Add these as NS records for 'admin' in your GoDaddy DNS panel for aliyarsolutions.com"
  value       = module.dns.admin_zone_name_servers
}

output "cloudfront_distribution_id" {
  value = module.cdn.distribution_id
}

output "db_endpoint" {
  value = module.database.db_endpoint
}

output "recordings_bucket_name" {
  value = module.storage.recordings_bucket_name
}

output "frontend_bucket_name" {
  value = module.storage.frontend_bucket_name
}

output "ecs_cluster_name" {
  value = module.compute.cluster_name
}
