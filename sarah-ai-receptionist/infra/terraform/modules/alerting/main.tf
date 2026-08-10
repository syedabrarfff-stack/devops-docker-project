resource "aws_sns_topic" "alarms" {
  name = "${var.project_name}-${var.environment}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# ── ALB ──────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${var.project_name}-${var.environment}-alb-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 25
  treat_missing_data  = "notBreaching"
  alarm_description   = "Elevated 5xx rate on the ALB — voice/API pipeline likely degraded"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "voice_unhealthy_hosts" {
  alarm_name          = "${var.project_name}-${var.environment}-voice-unhealthy-hosts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_description   = "One or more voice-service targets are failing health checks"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.voice_tg_arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "api_unhealthy_hosts" {
  alarm_name          = "${var.project_name}-${var.environment}-api-unhealthy-hosts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_description   = "One or more api-service targets are failing health checks"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.api_tg_arn_suffix
  }
}

# ── ECS ──────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "voice_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-voice-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 90
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_voice_service_name
  }
}

resource "aws_cloudwatch_metric_alarm" "voice_running_count" {
  alarm_name          = "${var.project_name}-${var.environment}-voice-running-count-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_description   = "voice-service has fewer than 1 running task — calls cannot be answered"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_voice_service_name
  }
}

resource "aws_cloudwatch_metric_alarm" "api_running_count" {
  alarm_name          = "${var.project_name}-${var.environment}-api-running-count-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  treat_missing_data  = "breaching"
  # UnHealthyHostCount (api_unhealthy_hosts, above) only fires when a
  # registered target fails its health check -- it stays at 0, not
  # "breaching", when a service is scaled to zero and has no targets
  # registered at all. voice-service and worker-service both had an
  # explicit RunningTaskCount alarm to catch exactly that case; api-service
  # was missing one, so a scale-to-zero on api-service (the same failure
  # mode that caused the ALB 503s this pipeline now self-heals from) would
  # have gone completely silent.
  alarm_description = "api-service has fewer than 1 running task — dashboard/admin API and booking are unreachable"
  alarm_actions     = [aws_sns_topic.alarms.arn]
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_api_service_name
  }
}

resource "aws_cloudwatch_metric_alarm" "worker_running_count" {
  alarm_name          = "${var.project_name}-${var.environment}-worker-running-count-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_description   = "worker-service has fewer than 1 running task — reminders/summaries/SMS are not being sent"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_worker_service_name
  }
}

# ── RDS ──────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions = {
    DBInstanceIdentifier = var.rds_instance_id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_free_storage" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-storage-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 5000000000 # 5 GB
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions = {
    DBInstanceIdentifier = var.rds_instance_id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_free_memory" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-memory-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "FreeableMemory"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 268435456 # 256 MB
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions = {
    DBInstanceIdentifier = var.rds_instance_id
  }
}
