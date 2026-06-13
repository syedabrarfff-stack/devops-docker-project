#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# JARVIS — GitHub Actions OIDC Setup
# Run ONCE from AWS CloudShell (ap-south-2) to enable secretless CI/CD.
# After this, every git push auto-deploys without any GitHub secrets configured.
# ═══════════════════════════════════════════════════════════════════════════════
set -e
REGION=ap-south-2
REPO="syedabrarfff-stack/devops-docker-project"
ROLE_NAME="JarvisGitHubActionsRole"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# 1. Create OIDC provider (once per account)
echo "Creating OIDC provider..."
aws iam create-openid-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  2>/dev/null && echo "OIDC provider created" || echo "OIDC provider already exists"

# 2. Create IAM role with trust policy for this repo
echo "Creating IAM role..."
cat > /tmp/trust.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:${REPO}:*"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document file:///tmp/trust.json \
  --description "GitHub Actions OIDC role for JARVIS deployment" \
  2>/dev/null && echo "Role created" || echo "Role already exists"

# 3. Attach required policies
echo "Attaching policies..."
aws iam attach-role-policy --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMFullAccess
aws iam attach-role-policy --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess
aws iam attach-role-policy --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonSESFullAccess

echo ""
echo "✅ OIDC setup complete!"
echo "Role ARN: arn:aws:iam::${ACCOUNT_ID}:role/$ROLE_NAME"
echo ""
echo "GitHub Actions will now authenticate automatically on every push."
echo "No GitHub secrets needed."
