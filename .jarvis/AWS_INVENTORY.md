# AWS INVENTORY
_Account: 824232273953 | Primary: ap-south-2 (Hyderabad) | DR: ap-south-1 (Mumbai)_

## Terraform State
- Bucket: `jarvis-terraform-state-824232273953`
- Key: `production/terraform.tfstate`
- Lock Table: `jarvis-terraform-locks`
- Status: 51 resources pending apply

## Resources (Terraform-managed)
### Compute
- **ECS Cluster:** jarvis-production (Fargate)
- **ECS Service (Backend):** jarvis-backend — desired count configurable
- **ECS Service (Frontend):** jarvis-frontend
- **Task Definitions:** backend + frontend containers

### Networking
- **VPC:** jarvis-production VPC
- **Subnets:** Public (ALB) + Private (ECS, RDS)
- **ALB:** Application Load Balancer → ECS
- **Route53:** aliyarsolutions.com → ALB
- **Security Groups:** ALB-SG, ECS-SG, RDS-SG, Redis-SG

### Database
- **RDS PostgreSQL 16:** jarvis-production-db
- **pgvector extension:** enabled
- **Backup:** 7-day retention
- **Multi-AZ:** configurable

### Cache
- **ElastiCache Redis 7:** jarvis-production-redis
- **Used for:** Rate limiting, session cache, APScheduler

### Storage
- **S3 Bucket:** jarvis invoices/PDFs (AWS_S3_BUCKET)
- **Terraform State Bucket:** jarvis-terraform-state-824232273953

### Secrets
- **AWS Secrets Manager:** all secrets via AWS_SSM_PREFIX
- **Never in code. Never in commits.**

### CI/CD
- **GitHub Actions Role:** JarvisGitHubActionsRole
- **Action:** .github/workflows/deploy.yml → ECR → ECS blue/green
- **Health Gates:** /health (liveness) + /readyz (deep readiness)

### Email
- **AWS SES:** outbound email via send_outbound_email()
- **SES Inbound:** /ses_inbound route for reply handling

### Monitoring
- **CloudWatch:** ECS metrics, RDS metrics, ALB access logs
- **Grafana:** infrastructure/grafana/ — jarvis_main.json dashboard
- **Prometheus:** monitoring/prometheus.yml
- **AlertManager:** monitoring/alertmanager.yml

## Captain Actions Required
- [ ] `terraform init && terraform plan` — review 51 resources
- [ ] `terraform apply` — deploys all AWS infrastructure
- [ ] Attach AdministratorAccess to JarvisGitHubActionsRole in IAM
- [ ] Point aliyarsolutions.com CNAME → ALB DNS (Route53 or registrar)
- [ ] Set STRIPE_WEBHOOK_SECRET in AWS Secrets Manager

## Local Docker Stack (development)
- Redis: localhost:6379
- PostgreSQL: localhost:5432 (jarvis/jarvis_secret)
- Backend: localhost:8000
- Frontend: localhost:3000
- Nginx: localhost:80
- Grafana: localhost:3001
- Prometheus: localhost:9090
