# Route53 hosted zones for subdomain delegation.
# The root domain (aliyarsolutions.com) stays on GoDaddy untouched.
# We create one hosted zone per subdomain and delegate only that subdomain
# by adding NS records at GoDaddy — zero risk to the existing website/email.

resource "aws_route53_zone" "api" {
  name    = "${var.api_subdomain}.${var.root_domain}"
  comment = "Sarah voice engine / API — delegated subdomain"
}

resource "aws_route53_zone" "app" {
  name    = "${var.app_subdomain}.${var.root_domain}"
  comment = "Sarah clinic dashboard — delegated subdomain"
}

resource "aws_route53_zone" "admin" {
  name    = "${var.admin_subdomain}.${var.root_domain}"
  comment = "Sarah admin console — delegated subdomain"
}

# ── ACM certificate for the API (ALB, regional) ─────────────────────────────
resource "aws_acm_certificate" "api" {
  domain_name       = "${var.api_subdomain}.${var.root_domain}"
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
}

resource "aws_route53_record" "api_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.api.domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  }
  zone_id = aws_route53_zone.api.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn         = aws_acm_certificate.api.arn
  validation_record_fqdns = [for r in aws_route53_record.api_cert_validation : r.fqdn]
}

# ── ACM certificate for CloudFront (must be us-east-1) — covers app + admin ─
resource "aws_acm_certificate" "cdn" {
  provider                 = aws.us_east_1
  domain_name               = "${var.app_subdomain}.${var.root_domain}"
  subject_alternative_names = ["${var.admin_subdomain}.${var.root_domain}"]
  validation_method          = "DNS"
  lifecycle { create_before_destroy = true }
}

resource "aws_route53_record" "cdn_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cdn.domain_validation_options : dvo.domain_name => {
      name    = dvo.resource_record_name
      type    = dvo.resource_record_type
      value   = dvo.resource_record_value
      zone_id = dvo.domain_name == "${var.app_subdomain}.${var.root_domain}" ? aws_route53_zone.app.zone_id : aws_route53_zone.admin.zone_id
    }
  }
  zone_id = each.value.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "cdn" {
  provider                 = aws.us_east_1
  certificate_arn           = aws_acm_certificate.cdn.arn
  validation_record_fqdns   = [for r in aws_route53_record.cdn_cert_validation : r.fqdn]
}
