# JARVIS Infrastructure — Docker Compose & AWS Fargate

Complete infrastructure-as-code for running JARVIS in development (Docker Compose) and production (AWS ECS Fargate). This guide covers setup, deployment, monitoring, and troubleshooting.

---

## Overview

| Environment | Platform | Config | Deployment |
|---|---|---|---|
| **Development** | Docker Compose | Local .env | `docker-compose up` |
| **Staging** | AWS ECS Fargate | AWS Secrets Manager | GitHub Actions |
| **Production** | AWS ECS Fargate (multi-region) | AWS Secrets Manager | GitHub Actions + blue/green |

---

## Docker Compose (Development)

### Quick Start

```bash
# 1. Navigate to infrastructure directory
cd infrastructure

# 2. Start all services
docker-compose up -d

# 3. Verify services are running
docker-compose ps

# 4. View logs
docker-compose logs -f backend

# 5. Stop services
docker-compose down
```

### Services

**Database & Cache (Data Layer)**

| Service | Image | Port | Purpose | Data |
|---|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | Relational database | PostgreSQL data volume |
| `redis` | redis:7-alpine | 6379 | Cache & queues | Redis data volume |

**Application (Core)**

| Service | Image | Port | Purpose |
|---|---|---|---|
| `backend` | jarvis:latest | 8000 | FastAPI application |
| `frontend` | jarvis-frontend:latest | 5173 | React SPA |

**Reverse Proxy**

| Service | Image | Port | Purpose |
|---|---|---|---|
| `nginx` | nginx:alpine | 80, 443 | HTTP/HTTPS reverse proxy |

**Monitoring Stack**

| Service | Image | Port | Purpose |
|---|---|---|---|
| `prometheus` | prom/prometheus:latest | 9090 | Metrics collection |
| `grafana` | grafana/grafana:latest | 3000 | Metrics visualization |
| `alertmanager` | prom/alertmanager:latest | 9093 | Alert routing & management |

**Logging Stack**

| Service | Image | Port | Purpose |
|---|---|---|---|
| `loki` | grafana/loki:latest | 3100 | Log aggregation |
| `promtail` | grafana/promtail:latest | 9080 | Log shipper |

**Optional**

| Service | Image | Port | Purpose |
|---|---|---|---|
| `evolution-api` | atmajs/evolution-api:latest | 8080 | WhatsApp integration (optional) |

### Environment Variables

Edit `docker-compose.yml` or `.env`:

```bash
# Backend configuration
POSTGRES_USER=jarvis
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=jarvis
DATABASE_URL=postgresql+asyncpg://jarvis:secure_password@postgres:5432/jarvis
REDIS_URL=redis://redis:6379/0

# Application
APP_VERSION=1.0.0
DEBUG=false
JARVIS_DEFAULT_TENANT_ID=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa

# API Keys (from .env file)
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-v1-...
# ... all other keys
```

### Useful Commands

```bash
# View logs
docker-compose logs -f backend         # Backend only
docker-compose logs -f postgres        # Database
docker-compose logs                    # All services

# Access services
docker-compose exec postgres psql -U jarvis -d jarvis
docker-compose exec redis redis-cli
docker-compose exec backend bash

# Rebuild images
docker-compose build --no-cache

# Scale services
docker-compose up -d --scale worker=3

# Remove everything
docker-compose down -v
```

### Networking

All services communicate via Docker network `jarvis-network`:

```
┌─────────────────────────────────────────┐
│         Docker Network (bridge)         │
├─────────────────────────────────────────┤
│                                         │
│  nginx ──> backend:8000                 │
│         └> frontend:5173                │
│                                         │
│  backend ──> postgres:5432              │
│          └> redis:6379                  │
│                                         │
│  prometheus ──> backend:8000            │
│              └> postgres                │
│              └> alertmanager            │
│                                         │
│  loki <── promtail                      │
│                                         │
└─────────────────────────────────────────┘
```

---

## AWS Infrastructure (Production)

### Architecture

**Multi-Region Setup:**

```
┌─────────────────────────────────────────────────────────┐
│                     Route 53                             │
│              (DNS, failover routing)                     │
└──────────┬───────────────────────────────┬──────────────┘
           │                               │
    ┌──────▼────────────────────┐   ┌──────▼────────────────────┐
    │   ap-south-2 (Primary)    │   │   ap-south-1 (Disaster)   │
    │     (Hyderabad)           │   │      (Mumbai)             │
    ├──────────────────────────┤   ├──────────────────────────┤
    │                          │   │                          │
    │  ALB (80, 443)           │   │  ALB (80, 443)           │
    │  ↓                       │   │  ↓                       │
    │  ECS Fargate (backend)   │   │  ECS Fargate (backend)   │
    │  ↓                       │   │  ↓                       │
    │  RDS PostgreSQL          │   │  RDS PostgreSQL (replica)│
    │  ElastiCache Redis       │   │  ElastiCache Redis       │
    │  ↓                       │   │  ↓                       │
    │  S3 (regional)           │   │  S3 (cross-region repl)  │
    │                          │   │                          │
    └──────┬───────────────────┘   └──────┬───────────────────┘
           │                              │
           └──────────────────┬───────────┘
                              │
                    ┌─────────▼────────┐
                    │  S3 (documents)  │
                    │  CloudFront CDN  │
                    └──────────────────┘
```

### Terraform Structure

```
infra/terraform/
├── main.tf              # VPC, ECS, ALB, RDS, Redis, S3, monitoring
├── variables.tf         # Input variables
├── outputs.tf          # Output values
├── secrets.tf          # AWS Secrets Manager
├── iam.tf              # IAM roles & policies
├── networking.tf       # VPC, subnets, security groups
├── rds.tf              # RDS PostgreSQL configuration
├── ecs.tf              # ECS cluster, service, task definition
├── alb.tf              # Application load balancer
├── cloudfront.tf       # CloudFront CDN for S3
├── monitoring.tf       # CloudWatch, SNS
└── backend.tf          # Terraform state backend (S3)
```

### Deployment Steps

#### 1. Prerequisites

```bash
# Install Terraform
brew install terraform           # macOS
# or download from terraform.io

# Configure AWS credentials
aws configure
# Provide: AWS Access Key ID, Secret Access Key, Default region

# Verify AWS access
aws s3 ls
```

#### 2. Initialize Terraform

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Verify configuration
terraform validate

# Plan changes
terraform plan -out=tfplan
```

#### 3. Review & Apply

```bash
# Review the plan carefully
cat tfplan

# Apply infrastructure changes
terraform apply tfplan

# Outputs will include:
# - alb_dns_name: DNS for load balancer
# - ecs_cluster_name: ECS cluster name
# - rds_endpoint: Database endpoint
# - s3_bucket_name: Document storage bucket
```

#### 4. Post-Deployment

```bash
# Verify resources
aws ec2 describe-security-groups
aws rds describe-db-instances
aws ecs describe-clusters

# Get DNS name
aws elbv2 describe-load-balancers

# Test connectivity
curl $(terraform output -raw alb_dns_name)/health
```

### Terraform Variables

Create `terraform.tfvars`:

```hcl
aws_region             = "ap-south-2"
environment            = "production"
app_name              = "jarvis"

# Networking
vpc_cidr              = "10.0.0.0/16"
availability_zones    = ["ap-south-2a", "ap-south-2b"]

# ECS
container_image       = "111111111111.dkr.ecr.ap-south-2.amazonaws.com/jarvis:latest"
container_port        = 8000
container_cpu         = 512  # 0.5 CPU
container_memory      = 1024 # 1 GB
desired_count         = 2    # Number of tasks

# RDS
db_instance_class     = "db.t4g.micro"
db_allocated_storage  = 20
db_name              = "jarvis"
db_user              = "jarvis"
# db_password should be in AWS Secrets Manager

# Redis
redis_node_type      = "cache.t4g.micro"

# Tags
tags = {
  Environment = "production"
  Team        = "Platform"
  CostCenter  = "Engineering"
}
```

---

## AWS ECR (Container Registry)

### Build & Push Docker Image

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name jarvis --region ap-south-2

# 2. Get login token
aws ecr get-login-password --region ap-south-2 | \
  docker login --username AWS --password-stdin \
  111111111111.dkr.ecr.ap-south-2.amazonaws.com

# 3. Build image
docker build -t jarvis:latest .

# 4. Tag for ECR
docker tag jarvis:latest \
  111111111111.dkr.ecr.ap-south-2.amazonaws.com/jarvis:latest

# 5. Push to ECR
docker push 111111111111.dkr.ecr.ap-south-2.amazonaws.com/jarvis:latest
```

---

## GitHub Actions Deployment

### Workflow File

`.github/workflows/deploy.yml`:

```yaml
name: Deploy JARVIS to AWS

on:
  push:
    branches: [main, develop]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Build Docker image
      - name: Build image
        run: docker build -t jarvis:latest .
      
      # Push to ECR
      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
          docker tag jarvis:latest $ECR_URI/jarvis:latest
          docker push $ECR_URI/jarvis:latest
      
      # Deploy to ECS
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster jarvis-cluster \
            --service jarvis-service \
            --force-new-deployment
        env:
          AWS_REGION: ap-south-2
          ECR_URI: 111111111111.dkr.ecr.ap-south-2.amazonaws.com
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### Deployment Process

1. **Push to GitHub** → Triggers workflow
2. **Build Docker image** in GitHub runner
3. **Push to ECR** (Elastic Container Registry)
4. **Update ECS Service** (triggers rolling update)
5. **Blue/Green Deployment** (new tasks launched, old tasks drained)
6. **Health Check** (verifies new tasks are healthy)
7. **Rollback on Failure** (automatic if health checks fail)

---

## Monitoring

### CloudWatch Dashboards

Access via AWS Console → CloudWatch → Dashboards

**Key Metrics:**

- **ECS:** CPU utilization, memory utilization, task count
- **RDS:** Database connections, CPU, replication lag
- **ElastiCache:** CPU, memory, evictions, hit rate
- **ALB:** Request count, target health, latency
- **Application:** Request rate, error rate, latency (via Prometheus)

### Alarms

Configured via Terraform:

| Alarm | Threshold | Action |
|---|---|---|
| High CPU | >70% for 5 min | SNS → Slack |
| High Memory | >80% for 5 min | SNS → Slack |
| Task Failures | >1 per min | Restart + alert |
| Database Errors | >10 per min | Escalate to team |
| RDS Replication Lag | >30s | Page on-call |

### Application Monitoring

Backend exports Prometheus metrics:

```bash
# Access from inside AWS:
curl http://backend.internal:8000/metrics

# Available in Prometheus:
request_duration_seconds
request_count
ai_provider_cost_usd
scheduler_job_duration_seconds
scheduler_job_failure_count
```

---

## Backup & Recovery

### RDS Backups

```bash
# Automated backups (daily)
# Retention: 30 days (configurable)

# Manual backup
aws rds create-db-snapshot \
  --db-instance-identifier jarvis-prod \
  --db-snapshot-identifier jarvis-prod-backup-$(date +%Y%m%d)

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier jarvis-restored \
  --db-snapshot-identifier jarvis-prod-backup-20240702
```

### S3 Backups

```bash
# Enable versioning on S3
aws s3api put-bucket-versioning \
  --bucket jarvis-documents \
  --versioning-configuration Status=Enabled

# Enable cross-region replication
# (Configured via Terraform)

# List all versions of a file
aws s3api list-object-versions \
  --bucket jarvis-documents \
  --prefix proposals/
```

---

## Troubleshooting

### ECS Task Won't Start

```bash
# Check task logs
aws logs tail /ecs/jarvis-backend --follow

# Inspect task definition
aws ecs describe-task-definition --task-definition jarvis-backend

# Check container health
aws ecs describe-tasks --cluster jarvis-cluster --tasks <task-arn>
```

### Database Connection Issues

```bash
# Test RDS connectivity
# From ECS task or EC2:
psql -h jarvis-rds.123456789.ap-south-2.rds.amazonaws.com \
     -U jarvis \
     -d jarvis

# Check security group rules
aws ec2 describe-security-groups --group-ids sg-xxxxx

# Verify RDS endpoint in task definition
aws ecs describe-task-definition --task-definition jarvis-backend
```

### Deployment Won't Complete

```bash
# Check service events
aws ecs describe-services \
  --cluster jarvis-cluster \
  --services jarvis-service

# View detailed status
aws ecs list-tasks --cluster jarvis-cluster
aws ecs describe-tasks --cluster jarvis-cluster --tasks <task-arn>

# Check CloudWatch logs
aws logs tail /ecs/jarvis-backend --follow

# Rollback to previous task definition
aws ecs update-service \
  --cluster jarvis-cluster \
  --service jarvis-service \
  --task-definition jarvis-backend:5  # Previous version
```

---

## Security Best Practices

### Secrets Management

**Do NOT commit secrets to Git:**

```bash
# ✅ Use AWS Secrets Manager
aws secretsmanager create-secret \
  --name jarvis/prod/anthropic-key \
  --secret-string "sk-ant-..."

# ✅ Use GitHub Secrets for CI/CD
# Settings → Secrets → New repository secret

# ❌ Never use hardcoded API keys
# ❌ Never commit .env files
# ❌ Never expose secrets in logs
```

### Network Security

**Security Groups:**

```bash
# Backend SG: Allow 8000 from ALB only
# RDS SG: Allow 5432 from Backend only
# Redis SG: Allow 6379 from Backend only
# ALB SG: Allow 80, 443 from internet (0.0.0.0/0)
```

### SSL/TLS

```bash
# Generate certificate (or use AWS Certificate Manager)
aws acm request-certificate \
  --domain-name api.aliyarsolutions.com \
  --validation-method DNS

# ALB automatically serves HTTPS
# Redirects HTTP → HTTPS
```

---

## Cost Optimization

### Right-Sizing

```bash
# Monitor actual usage
aws ec2 describe-instances | grep InstanceType

# Adjust based on:
# - CPU utilization (target: 50-70%)
# - Memory utilization (target: 60-80%)
# - Network throughput

# Downsize if consistently < 30% utilized
# Upsize if consistently > 80% utilized
```

### Reserved Instances

```bash
# For predictable workloads, use Reserved Instances
# Saves 30-50% vs On-Demand

# Purchase via AWS Console or CLI
aws ec2 purchase-reserved-instances-offering \
  --reserved-instances-offering-id xxxxx \
  --instance-count 2
```

---

## Disaster Recovery

### Failover Procedure

If primary region (ap-south-2) fails:

```bash
# 1. Update Route 53 to point to DR region (ap-south-1)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{"Name":"api.example.com","Type":"A","SetIdentifier":"ap-south-2","AliasTarget":{"HostedZoneId":"Z123","DNSName":"ap-south-1-lb.example.com","EvaluateTargetHealth":true}}}]}'

# 2. Verify DR resources are running
aws ecs describe-services --cluster jarvis-dr

# 3. Test RDS failover
aws rds failover-db-cluster --db-cluster-identifier jarvis-cluster

# 4. Notify team & update status page
```

---

## Maintenance Windows

### Scheduled Downtime

```bash
# Database maintenance (Tue 03:00-04:00 UTC)
aws rds modify-db-instance \
  --db-instance-identifier jarvis \
  --preferred-maintenance-window "tue:03:00-tue:04:00"

# ECS updates (auto-apply)
# Can trigger rolling updates without downtime
```

---

## Support & Documentation

- **AWS Documentation:** https://docs.aws.amazon.com
- **Terraform Registry:** https://registry.terraform.io
- **Docker Documentation:** https://docs.docker.com
- **Prometheus Docs:** https://prometheus.io/docs

---

**Last Updated:** 2024-07-02  
**Version:** 1.0.0-MVP  
**Maintainer:** JARVIS Infrastructure Team
