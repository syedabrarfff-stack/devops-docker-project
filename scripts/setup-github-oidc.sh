#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# JARVIS — GitHub Actions OIDC Setup (with verification)
# Run ONCE from AWS CloudShell (ap-south-2) to enable secretless CI/CD.
# After this, every git push auto-deploys without any GitHub secrets configured.
# ═══════════════════════════════════════════════════════════════════════════════
set -e
REGION=ap-south-2
REPO="syedabrarfff-stack/devops-docker-project"
ROLE_NAME="JarvisGitHubActionsRole"
OIDC_URL="https://token.actions.githubusercontent.com"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account: $ACCOUNT_ID"
echo "Region:      $REGION"
echo ""

# ── 1. Create OIDC provider ───────────────────────────────────────────────────
echo "── Step 1: OIDC Provider ──────────────────────────────────────────────────"

EXISTING=$(aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[*].Arn" \
  --output text 2>/dev/null | tr '\t' '\n' | grep "token.actions.githubusercontent.com" || true)

if [ -n "$EXISTING" ]; then
  echo "✅ OIDC provider already exists: $EXISTING"
else
  echo "Creating OIDC provider..."
  CREATED_ARN=$(aws iam create-openid-connect-provider \
    --url "$OIDC_URL" \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
    --query "OpenIDConnectProviderArn" \
    --output text)
  echo "✅ OIDC provider created: $CREATED_ARN"
fi

# ── 2. Create IAM role ────────────────────────────────────────────────────────
echo ""
echo "── Step 2: IAM Role ───────────────────────────────────────────────────────"

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

ROLE_EXISTS=$(aws iam get-role --role-name "$ROLE_NAME" --query "Role.Arn" --output text 2>/dev/null || echo "")

if [ -n "$ROLE_EXISTS" ]; then
  echo "Role exists — updating trust policy..."
  aws iam update-assume-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-document file:///tmp/trust.json
  echo "✅ Role trust policy updated: $ROLE_EXISTS"
else
  echo "Creating IAM role..."
  ROLE_ARN=$(aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document file:///tmp/trust.json \
    --description "GitHub Actions OIDC role for JARVIS deployment" \
    --query "Role.Arn" \
    --output text)
  echo "✅ Role created: $ROLE_ARN"
fi

# ── 3. Attach policies ────────────────────────────────────────────────────────
echo ""
echo "── Step 3: Policies ───────────────────────────────────────────────────────"

attach_policy() {
  local POLICY_ARN="$1"
  local NAME="$2"
  aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "$POLICY_ARN" 2>/dev/null \
    && echo "✅ Attached $NAME" \
    || echo "ℹ  $NAME already attached"
}

attach_policy "arn:aws:iam::aws:policy/AmazonSSMFullAccess" "AmazonSSMFullAccess"
attach_policy "arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess" "AmazonEC2ReadOnlyAccess"
attach_policy "arn:aws:iam::aws:policy/AmazonSESFullAccess" "AmazonSESFullAccess"

# ── 4. Verify ─────────────────────────────────────────────────────────────────
echo ""
echo "── Verification ───────────────────────────────────────────────────────────"

OIDC_VERIFIED=$(aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[*].Arn" \
  --output text 2>/dev/null | tr '\t' '\n' | grep "token.actions.githubusercontent.com" || true)

ROLE_VERIFIED=$(aws iam get-role --role-name "$ROLE_NAME" --query "Role.Arn" --output text 2>/dev/null || echo "")

POLICIES=$(aws iam list-attached-role-policies --role-name "$ROLE_NAME" \
  --query "AttachedPolicies[*].PolicyName" --output text 2>/dev/null || echo "")

if [ -n "$OIDC_VERIFIED" ] && [ -n "$ROLE_VERIFIED" ]; then
  echo ""
  echo "╔══════════════════════════════════════════════════╗"
  echo "║   ✅ OIDC SETUP COMPLETE AND VERIFIED            ║"
  echo "╠══════════════════════════════════════════════════╣"
  echo "║  OIDC Provider: token.actions.githubusercontent   ║"
  echo "║  Role ARN: $ROLE_VERIFIED"
  echo "║  Policies: $POLICIES"
  echo "╠══════════════════════════════════════════════════╣"
  echo "║  GitHub Actions will now authenticate via OIDC.  ║"
  echo "║  Every git push auto-deploys. No secrets needed. ║"
  echo "╚══════════════════════════════════════════════════╝"
else
  echo "❌ SETUP INCOMPLETE"
  [ -z "$OIDC_VERIFIED" ] && echo "  ❌ OIDC provider NOT found — check IAM permissions (iam:CreateOpenIDConnectProvider)"
  [ -z "$ROLE_VERIFIED" ] && echo "  ❌ Role NOT found — check IAM permissions (iam:CreateRole)"
  echo ""
  echo "  If you see permission errors, run this in AWS Console → CloudShell (root/admin account)."
  exit 1
fi
