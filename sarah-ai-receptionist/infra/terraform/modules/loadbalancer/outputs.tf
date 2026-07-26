output "alb_dns_name" { value = aws_lb.main.dns_name }
output "alb_security_group_id" { value = aws_security_group.alb.id }
output "ecs_security_group_id" { value = aws_security_group.ecs_tasks.id }
output "voice_target_group_arn" { value = aws_lb_target_group.voice.arn }
output "api_target_group_arn" { value = aws_lb_target_group.api.arn }
output "https_listener_arn" { value = aws_lb_listener.https.arn }
