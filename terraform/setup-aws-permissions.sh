#!/bin/bash
# AWS IAM Setup Script for GeoExhibit Toolkit
# This script creates the minimum IAM permissions needed to deploy the infrastructure

set -e

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "AWS CLI not configured"
    exit 1
fi

CURRENT_USER=$(aws sts get-caller-identity --query 'Arn' --output text | cut -d'/' -f2)
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

echo "Setting up permissions for user $CURRENT_USER in account $ACCOUNT_ID"

POLICY_DOCUMENT=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformPermissions",
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "iam:*",
        "lambda:*",
        "cloudfront:*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
EOF
)

POLICY_ARN=$(aws iam create-policy \
  --policy-name "GeoExhibit-TerraformPermissions" \
  --policy-document "$POLICY_DOCUMENT" \
  --description "Permissions for deploying GeoExhibit infrastructure" \
  --query 'Policy.Arn' \
  --output text 2>/dev/null || \
  aws iam get-policy --policy-arn "arn:aws:iam::$ACCOUNT_ID:policy/GeoExhibit-TerraformPermissions" --query 'Policy.Arn' --output text)

echo "Policy created: $POLICY_ARN"

aws iam attach-user-policy \
  --user-name "$CURRENT_USER" \
  --policy-arn "$POLICY_ARN"

echo "Policy attached to user $CURRENT_USER"
