output "trail_arn" { value = aws_cloudtrail.main.arn }
output "trail_bucket_name" { value = aws_s3_bucket.trail.id }
