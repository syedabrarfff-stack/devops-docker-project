output "api_zone_id" { value = aws_route53_zone.api.zone_id }
output "api_zone_name_servers" { value = aws_route53_zone.api.name_servers }

output "app_zone_id" { value = aws_route53_zone.app.zone_id }
output "app_zone_name_servers" { value = aws_route53_zone.app.name_servers }

output "admin_zone_id" { value = aws_route53_zone.admin.zone_id }
output "admin_zone_name_servers" { value = aws_route53_zone.admin.name_servers }

output "api_certificate_arn" { value = aws_acm_certificate_validation.api.certificate_arn }
output "cdn_certificate_arn" { value = aws_acm_certificate_validation.cdn.certificate_arn }
