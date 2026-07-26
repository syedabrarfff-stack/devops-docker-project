output "recordings_bucket_name" { value = aws_s3_bucket.recordings.id }
output "recordings_bucket_arn" { value = aws_s3_bucket.recordings.arn }

output "frontend_bucket_name" { value = aws_s3_bucket.frontend.id }
output "frontend_bucket_arn" { value = aws_s3_bucket.frontend.arn }
output "frontend_bucket_regional_domain_name" { value = aws_s3_bucket.frontend.bucket_regional_domain_name }
