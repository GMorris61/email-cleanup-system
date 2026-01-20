# Terraform Deployment Guide

Deploy the Email Cleanup System to AWS Lambda using Terraform Infrastructure as Code.

## Prerequisites

- AWS Account
- [Terraform](https://www.terraform.io/downloads.html) installed (>= 1.0)
- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials
- Gmail credentials stored in AWS Secrets Manager (see main LAMBDA_SETUP.md, Step 2)

## Quick Start

### Step 1: Prepare Lambda Deployment Package

```bash
# From the project root directory
mkdir lambda-deployment
cd lambda-deployment

# Copy files
cp ../email_cleanup.py .
cp ../lambda_handler.py .
cp ../config.py .
cp ../requirements.txt .

# Install dependencies
pip install -r requirements.txt -t .

# Remove unnecessary files
rm -rf requirements.txt *.dist-info __pycache__

# Create ZIP
zip -r ../terraform/lambda-deployment.zip .
cd ..
```

### Step 2: Initialize Terraform

```bash
cd terraform
terraform init
```

This downloads the AWS provider and sets up the Terraform working directory.

### Step 3: Review Plan

```bash
terraform plan
```

This shows what resources will be created. You should see:
- IAM role for Lambda
- IAM policy for Secrets Manager access
- Lambda function
- CloudWatch Event Rule (EventBridge)
- Lambda permission

### Step 4: Deploy

```bash
terraform apply
```

Type `yes` when prompted. Terraform will create all resources.

### Step 5: Verify Deployment

```bash
# View outputs
terraform output

# Check Lambda in console
aws lambda list-functions --region us-east-1

# Check EventBridge rule
aws events list-rules --region us-east-1
```

## Configuration

Edit `terraform.tfvars` to customize (optional):

```hcl
aws_region         = "us-east-1"
eventbridge_enabled = true
```

## Testing

### Test Lambda Manually

```bash
aws lambda invoke \
  --function-name email-cleanup-system \
  --region us-east-1 \
  response.json

cat response.json
```

### View CloudWatch Logs

```bash
aws logs tail /aws/lambda/email-cleanup-system --follow --region us-east-1
```

## Updating

If you update the Lambda code:

```bash
# Rebuild the ZIP
cd lambda-deployment
rm -rf *
cp ../email_cleanup.py .
cp ../lambda_handler.py .
cp ../config.py .
cp ../requirements.txt .
pip install -r requirements.txt -t .
rm -rf requirements.txt *.dist-info __pycache__
zip -r ../terraform/lambda-deployment.zip .
cd ..

# Redeploy
cd terraform
terraform apply
```

## Destroying Resources

**WARNING:** This will delete all Lambda resources.

```bash
cd terraform
terraform destroy
```

Type `yes` when prompted.

## Terraform State

- **Local state**: `terraform.tfstate` (for testing only)
- **Remote state** (recommended for production): Configure S3 backend

Example S3 backend config:

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "email-cleanup/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

## File Structure

```
terraform/
├── main.tf           # Main configuration
├── variables.tf      # Input variables
├── terraform.tfvars  # Variable values (optional)
└── lambda-deployment.zip  # Lambda code package
```

## What Gets Created

| Resource | Name | Purpose |
|----------|------|---------|
| IAM Role | `email-cleanup-lambda-role` | Permissions for Lambda |
| Lambda | `email-cleanup-system` | The cleanup function |
| EventBridge Rule | `email-cleanup-daily` | Scheduled trigger (9 AM daily) |
| IAM Policy | `lambda-secrets-policy` | Secrets Manager access |

## Scheduling

Default schedule: **9 AM every day** (cron: `0 9 * * ? *`)

To change:
1. Edit `main.tf`
2. Modify the `schedule_expression` in `aws_cloudwatch_event_rule`
3. Run `terraform apply`

Example schedules:
- Daily 9 AM: `cron(0 9 * * ? *)`
- Weekly Monday 9 AM: `cron(0 9 ? * MON *)`
- Hourly: `cron(0 * * * ? *)`
- Every 30 minutes: `rate(30 minutes)`

## Cost

- **Lambda**: Free tier covers 1M invocations/month
- **CloudWatch Logs**: Free tier covers 5GB/month
- **EventBridge**: Free tier covers 10 rules
- **Secrets Manager**: ~$0.40/month

**Estimated monthly cost: ~$0.40**

## Troubleshooting

### "terraform init" fails
```bash
# Check AWS credentials
aws sts get-caller-identity

# Check region
echo $AWS_REGION
```

### "terraform apply" fails with permission error
- Verify IAM user has `lambda:*`, `iam:*`, `events:*` permissions
- Check AWS credentials are correct

### Lambda function can't read Secrets Manager
- Verify secret name is `gmail-credentials`
- Check IAM policy includes correct secret ARN
- Verify secret exists in same region

### EventBridge not triggering Lambda
- Check rule is ENABLED: `aws events list-rules --region us-east-1`
- Verify Lambda permission exists: `terraform output`
- Check CloudWatch logs for errors

## Rollback

If something goes wrong:

```bash
# Destroy everything
terraform destroy

# Or destroy specific resource
terraform destroy -target aws_lambda_function.email_cleanup
```

## Next Steps

1. Test the Lambda function
2. Monitor CloudWatch logs
3. Verify emails are being cleaned up
4. Consider moving state to S3 for production
5. Add CloudWatch alarms for failures

---

**Documentation**: See main README.md and LAMBDA_SETUP.md for more info.
