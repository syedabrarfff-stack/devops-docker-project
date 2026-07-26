# Single React SPA (clinic dashboard + admin console, split by client-side
# routing at /admin) served from one S3 bucket via one CloudFront
# distribution, reachable on both app.<domain> and admin.<domain>.

# ── Access logs — CloudFront had none previously, no forensic visibility ───
resource "aws_s3_bucket" "cdn_logs" {
  bucket = "${var.project_name}-${var.environment}-cdn-logs"
}

resource "aws_s3_bucket_ownership_controls" "cdn_logs" {
  bucket = aws_s3_bucket.cdn_logs.id
  rule {
    # CloudFront's legacy log delivery writes via a canonical-user ACL grant,
    # which requires ACLs to still be honored on this bucket specifically.
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "cdn_logs" {
  depends_on = [aws_s3_bucket_ownership_controls.cdn_logs]
  bucket     = aws_s3_bucket.cdn_logs.id
  acl        = "log-delivery-write"
}

resource "aws_s3_bucket_public_access_block" "cdn_logs" {
  bucket                  = aws_s3_bucket.cdn_logs.id
  block_public_acls       = false # log-delivery-write ACL above requires this
  block_public_policy     = true
  ignore_public_acls      = false
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "cdn_logs" {
  bucket = aws_s3_bucket.cdn_logs.id
  rule {
    id     = "expire-old-logs"
    status = "Enabled"
    filter {}
    expiration {
      days = 180
    }
  }
}

# WAFv2 web ACLs for CloudFront must be created in us-east-1 regardless of
# the distribution's own scope — previously there was no WAF here at all.
resource "aws_wafv2_web_acl" "cdn" {
  provider    = aws.us_east_1
  name        = "${var.project_name}-${var.environment}-cdn-waf"
  description = "Rate limiting and managed protections for the dashboard/admin CloudFront distribution"
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  rule {
    name     = "rate-limit"
    priority = 1
    action {
      block {}
    }
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-${var.environment}-cdn-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "aws-managed-common"
    priority = 2
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-${var.environment}-cdn-common-rules"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-${var.environment}-cdn-waf"
    sampled_requests_enabled   = true
  }
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${var.project_name}-${var.environment}-frontend-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  default_root_object = "index.html"
  aliases             = [var.app_domain, var.admin_domain]
  price_class         = "PriceClass_100"
  web_acl_id          = aws_wafv2_web_acl.cdn.arn

  logging_config {
    bucket          = aws_s3_bucket.cdn_logs.bucket_domain_name
    prefix          = "cloudfront/"
    include_cookies = false
  }

  origin {
    domain_name              = var.frontend_bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-frontend"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6" # AWS managed "CachingOptimized"
  }

  # SPA fallback — React Router client-side routing
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    acm_certificate_arn      = var.cdn_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

resource "aws_s3_bucket_policy" "frontend_cloudfront" {
  bucket = var.frontend_bucket_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontOAC"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${var.frontend_bucket_arn}/*"
        Condition = {
          StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn }
        }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [var.frontend_bucket_arn, "${var.frontend_bucket_arn}/*"]
        Condition = {
          Bool = { "aws:SecureTransport" = "false" }
        }
      }
    ]
  })
}

resource "aws_route53_record" "app_alias" {
  zone_id = var.app_zone_id
  name    = ""
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "admin_alias" {
  zone_id = var.admin_zone_id
  name    = ""
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}
