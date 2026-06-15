# ── Project identity ──────────────────────────────────────────────────────────
variable "project" {
  description = "Project identifier used as a prefix for all resources"
  type        = string
  default     = "jarvis"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

# ── AWS ───────────────────────────────────────────────────────────────────────
variable "aws_region" {
  description = "Primary AWS region (Hyderabad)"
  type        = string
  default     = "ap-south-2"   # Hyderabad
}

variable "backup_region" {
  description = "Future backup region (Mumbai) — enabled in Phase 2"
  type        = string
  default     = "ap-south-1"
}

# ── Networking ────────────────────────────────────────────────────────────────
variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.10.0/24", "10.0.11.0/24"]
}

# ── Domain ────────────────────────────────────────────────────────────────────
variable "domain_name" {
  description = "Base domain for Route53 and ACM (e.g. aliyarsolutions.com)"
  type        = string
  default     = ""
}

variable "api_subdomain" {
  description = "Subdomain for the API (e.g. api)"
  type        = string
  default     = "api"
}

# ── Database ──────────────────────────────────────────────────────────────────
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.small"
}

variable "db_name" {
  type    = string
  default = "jarvis"
}

variable "db_username" {
  type    = string
  default = "jarvis"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_storage_gb" {
  type    = number
  default = 20
}

# ── ElastiCache ───────────────────────────────────────────────────────────────
variable "redis_node_type" {
  type    = string
  default = "cache.t3.micro"
}

# ── ECS ───────────────────────────────────────────────────────────────────────
variable "backend_image" {
  description = "ECR image URI for JARVIS backend (set during CI/CD)"
  type        = string
  default     = ""
}

variable "frontend_image" {
  description = "ECR image URI for JARVIS frontend"
  type        = string
  default     = ""
}

variable "backend_cpu" {
  type    = number
  default = 512
}

variable "backend_memory" {
  type    = number
  default = 1024
}

variable "backend_desired_count" {
  type    = number
  default = 1
}

# ── Secrets (passed from GitHub Actions secrets or local tfvars) ──────────────
variable "secret_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "anthropic_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "google_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "openai_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "telegram_bot_token" {
  type      = string
  sensitive = true
  default   = ""
}

variable "telegram_chat_id" {
  type      = string
  sensitive = true
  default   = ""
}

variable "slack_webhook_url" {
  type      = string
  sensitive = true
  default   = ""
}

variable "apollo_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

# ── Core auth ─────────────────────────────────────────────────────────────────
variable "captain_username" {
  type      = string
  sensitive = true
  default   = "captain"
}

variable "captain_password" {
  type      = string
  sensitive = true
  default   = ""
}

variable "jarvis_default_tenant_id" {
  type    = string
  default = ""
}

# ── NVIDIA NIM 10-key rotation ────────────────────────────────────────────────
variable "nvidia_api_key"   { type = string; sensitive = true; default = "" }
variable "nvidia_api_key_b" { type = string; sensitive = true; default = "" }
variable "nvidia_api_key_c" { type = string; sensitive = true; default = "" }
variable "nvidia_api_key_d" { type = string; sensitive = true; default = "" }
variable "nvidia_api_key_e" { type = string; sensitive = true; default = "" }
variable "nvidia_api_key_f" { type = string; sensitive = true; default = "" }
variable "nvidia_api_key_g" { type = string; sensitive = true; default = "" }
variable "nvidia_api_key_h" { type = string; sensitive = true; default = "" }
variable "nvidia_api_key_i" { type = string; sensitive = true; default = "" }
variable "nvidia_api_key_j" { type = string; sensitive = true; default = "" }

# ── Additional AI providers ───────────────────────────────────────────────────
variable "deepseek_api_key"  { type = string; sensitive = true; default = "" }
variable "groq_api_key"      { type = string; sensitive = true; default = "" }
variable "mistral_api_key"   { type = string; sensitive = true; default = "" }
variable "moonshot_api_key"  { type = string; sensitive = true; default = "" }
variable "zhipuai_api_key"   { type = string; sensitive = true; default = "" }
variable "dashscope_api_key" { type = string; sensitive = true; default = "" }
variable "minimax_api_key"   { type = string; sensitive = true; default = "" }
variable "google_maps_api_key" { type = string; sensitive = true; default = "" }

# ── Payments ──────────────────────────────────────────────────────────────────
variable "stripe_secret_key"      { type = string; sensitive = true; default = "" }
variable "stripe_publishable_key" { type = string; sensitive = true; default = "" }
variable "stripe_webhook_secret"  { type = string; sensitive = true; default = "" }

# ── Automation & Notifications ────────────────────────────────────────────────
variable "n8n_base_url"    { type = string; default = "" }
variable "n8n_webhook_url" { type = string; default = "" }

# ── WhatsApp / Evolution ──────────────────────────────────────────────────────
variable "evolution_api_key"    { type = string; sensitive = true; default = "" }
variable "evolution_api_url"    { type = string; default = "" }
variable "evolution_public_url" { type = string; default = "" }
