#!/bin/bash
# SES VERIFICATION DIAGNOSTIC
# Run this on a machine with AWS CLI configured and credentials for ap-south-2

set -e

echo "=== SES DOMAIN VERIFICATION DIAGNOSTIC ==="
echo ""

DOMAIN="aliyarsolutions.com"
REGION="ap-south-2"

echo "1. Checking domain identity status..."
aws ses get-identity-verification-attributes \
  --identities "$DOMAIN" \
  --region "$REGION" 2>/dev/null || echo "ERROR: AWS CLI not configured or no access"

echo ""
echo "2. Checking DKIM status..."
aws sesv2 get-email-identity \
  --email-identity "$DOMAIN" \
  --region "$REGION" 2>/dev/null || echo "ERROR: Domain not added to SES yet"

echo ""
echo "3. Checking account production access..."
aws sesv2 get-account \
  --region "$REGION" 2>/dev/null | jq '.ProductionAccessEnabled, .SendingEnabled, .ReviewDetails' || echo "ERROR: Cannot access account"

echo ""
echo "4. Checking SES sending quota..."
aws ses get-send-quota \
  --region "$REGION" 2>/dev/null | jq '.Max24HourSend, .MaxSendRate, .SentLast24Hours' || echo "ERROR: Cannot access quota"

echo ""
echo "5. Checking DNS propagation (DKIM records)..."
echo "Looking for DKIM CNAME records in aliyarsolutions.com..."
dig +short aliyarsolutions.com CNAME 2>/dev/null || echo "dig not available, use: nslookup aliyarsolutions.com"

echo ""
echo "6. Checking SPF record..."
dig +short aliyarsolutions.com TXT 2>/dev/null | grep -i spf || echo "No SPF record found"

echo ""
echo "=== DIAGNOSTIC COMPLETE ==="
echo ""
echo "If all checks above show values (not errors), SES is ready."
echo "If ProductionAccessEnabled is false, request production access in SES Console."
echo "If DKIM records show as CNAME, domain is verified."
