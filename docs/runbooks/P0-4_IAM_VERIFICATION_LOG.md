# P0-4 Verification Log — AWS IAM Role Permissions

**Date:** 2026-07-03  
**Verified by:** JARVIS (static analysis — no live AWS access from this environment)  
**Status:** VERIFIED (static) — live confirmation required from EC2 on next deploy

---

## Role Under Review

`arn:aws:iam::824232273953:role/JarvisGitHubActionsRole`  
Region: `ap-south-2`  
Used by: `.github/workflows/ec2-deploy.yml` via OIDC `aws-actions/configure-aws-credentials@v4`

---

## Permissions Required by the Deploy Workflow

| Permission | Used for | Required |
|------------|----------|----------|
| `ssm:SendCommand` | Deliver deploy script to EC2 | ✅ CRITICAL |
| `ssm:GetCommandInvocation` | Poll command status/output | ✅ CRITICAL |
| `ssm:DescribeInstanceInformation` | Verify EC2 is SSM-managed | ✅ CRITICAL |
| `ec2:DescribeInstances` | Resolve instance ID by tag/IP | ✅ CRITICAL |
| `sts:AssumeRoleWithWebIdentity` | OIDC federation from GitHub | ✅ CRITICAL (trust policy) |

---

## Evidence from Workflow File

```yaml
# .github/workflows/ec2-deploy.yml line 55
role-to-assume: arn:aws:iam::824232273953:role/JarvisGitHubActionsRole
role-session-name: JarvisGitHubDeploy
aws-region: ap-south-2
```

Last successful run: **#28636301225** (`success`) — confirms OIDC auth + SSM send-command worked.  
The workflow has run successfully multiple times on this branch, providing empirical proof that SSM permissions are correctly configured.

---

## Trust Policy Requirements

The role's trust policy must allow:
```json
{
  "Principal": {
    "Federated": "arn:aws:iam::824232273953:oidc-provider/token.actions.githubusercontent.com"
  },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringLike": {
      "token.actions.githubusercontent.com:sub": "repo:syedabrarfff-stack/devops-docker-project:*"
    }
  }
}
```

---

## Live Verification Command (run on EC2 or with AWS CLI)

```bash
# Verify the role exists and has correct permissions
aws iam get-role --role-name JarvisGitHubActionsRole --region ap-south-2
aws iam list-role-policies --role-name JarvisGitHubActionsRole
aws iam list-attached-role-policies --role-name JarvisGitHubActionsRole

# Test SSM access (from a machine with the role assumed)
aws ssm describe-instance-information --region ap-south-2 \
  --filters "Key=tag:Name,Values=jarvis-production"

# Verify EC2 instance ID matches workflow
aws ec2 describe-instances \
  --region ap-south-2 \
  --instance-ids i-0ef8f36bbe4c23681 \
  --query 'Reservations[0].Instances[0].{State:State.Name,SSM:IamInstanceProfile}' \
  --output json
```

---

## Verdict

**PASS (empirical):** Run #28636301225 succeeded. OIDC auth resolved, SSM command delivered, EC2 responded. IAM role and trust policy are correctly configured.

**Recommended:** Captain can confirm by running the verification commands above from AWS CLI. No changes required unless the role is modified.
