# AWS Commands for Viva — CIRRUS Project

This sheet lists AWS CLI commands worth knowing and testing for your viva. The CIRRUS
project uses **EC2** (to host the FastAPI backend) and **S3** (as a cloud storage
provider), so those two sections matter most — the rest is general AWS CLI fluency.

> Tip: prefix any command with `aws help` or append `help` (e.g. `aws s3 help`) to see
> built-in docs. Add `--region us-east-1` if a command complains about region.

---

## 0. Setup & Identity (always asked first)

```bash
# Check the CLI is installed and its version
aws --version

# Configure credentials interactively (Access Key, Secret Key, region, output)
aws configure

# Where credentials/config live
#   ~/.aws/credentials   and   ~/.aws/config

# Who am I? (confirms your credentials work) — VERY common viva question
aws sts get-caller-identity

# List configured profiles
aws configure list-profiles

# Use a named profile for any command
aws s3 ls --profile myprofile

# Set default output format: json | table | text
aws configure set output table
```

---

## 1. S3 — Object Storage (CIRRUS file storage)

### High-level `s3` commands (easy, file-like)
```bash
# List all buckets
aws s3 ls

# List contents of a bucket
aws s3 ls s3://my-bucket-name

# Create a bucket
aws s3 mb s3://cirrus-demo-bucket

# Remove an empty bucket
aws s3 rb s3://cirrus-demo-bucket

# Upload a file
aws s3 cp myfile.txt s3://cirrus-demo-bucket/

# Download a file
aws s3 cp s3://cirrus-demo-bucket/myfile.txt ./

# Sync a whole folder up (only changed files)
aws s3 sync ./local-folder s3://cirrus-demo-bucket/

# Sync back down
aws s3 sync s3://cirrus-demo-bucket/ ./local-folder

# Delete an object
aws s3 rm s3://cirrus-demo-bucket/myfile.txt

# Recursively delete everything in a bucket
aws s3 rm s3://cirrus-demo-bucket/ --recursive
```

### Low-level `s3api` commands (fine-grained, viva loves these)
```bash
# Create a bucket (note region constraint)
aws s3api create-bucket --bucket cirrus-demo-bucket \
  --region us-east-1

# List objects in detail
aws s3api list-objects-v2 --bucket cirrus-demo-bucket

# Put (upload) an object
aws s3api put-object --bucket cirrus-demo-bucket \
  --key folder/file.txt --body file.txt

# Get (download) an object
aws s3api get-object --bucket cirrus-demo-bucket \
  --key folder/file.txt out.txt

# Show / set bucket versioning
aws s3api get-bucket-versioning --bucket cirrus-demo-bucket
aws s3api put-bucket-versioning --bucket cirrus-demo-bucket \
  --versioning-configuration Status=Enabled

# Generate a temporary pre-signed URL (valid 1 hour)
aws s3 presign s3://cirrus-demo-bucket/file.txt --expires-in 3600
```

**Likely viva questions:** difference between `s3` vs `s3api`; what a bucket policy is;
what a pre-signed URL is; versioning; that bucket names are **globally unique**.

---

## 2. EC2 — Compute (CIRRUS backend host)

```bash
# List all instances (verbose)
aws ec2 describe-instances

# List instances, trimmed to useful columns
aws ec2 describe-instances \
  --query "Reservations[].Instances[].{ID:InstanceId,State:State.Name,IP:PublicIpAddress}" \
  --output table

# Start / stop / reboot / terminate an instance
aws ec2 start-instances     --instance-ids i-0123456789abcdef0
aws ec2 stop-instances      --instance-ids i-0123456789abcdef0
aws ec2 reboot-instances    --instance-ids i-0123456789abcdef0
aws ec2 terminate-instances --instance-ids i-0123456789abcdef0

# Launch a new instance (need an AMI id, type, key pair, security group)
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type t2.micro \
  --key-name my-key \
  --security-group-ids sg-0123456789 \
  --count 1

# Key pairs
aws ec2 describe-key-pairs
aws ec2 create-key-pair --key-name my-key --query "KeyMaterial" --output text > my-key.pem

# Security groups (firewall rules)
aws ec2 describe-security-groups
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789 --protocol tcp --port 22 --cidr 0.0.0.0/0   # SSH
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789 --protocol tcp --port 8000 --cidr 0.0.0.0/0 # FastAPI

# List available AMIs (Amazon Machine Images)
aws ec2 describe-images --owners amazon --filters "Name=name,Values=ubuntu*" --query "Images[:5]"

# Connect to your instance (plain SSH, not AWS CLI)
ssh -i "my-key.pem" ubuntu@your-ec2-public-ip
```

**Likely viva questions:** what an AMI is; instance types (t2.micro = free tier);
security group vs NACL; elastic IP; key pair role in SSH; difference between
**stop** (keeps disk/EBS) and **terminate** (destroys).

---

## 3. IAM — Identity & Access Management (security questions)

```bash
# List users, roles, groups
aws iam list-users
aws iam list-roles
aws iam list-groups

# Show policies attached to a user
aws iam list-attached-user-policies --user-name myuser

# Create a user
aws iam create-user --user-name demo-user

# Attach a managed policy (e.g. read-only S3)
aws iam attach-user-policy --user-name demo-user \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

**Likely viva questions:** difference between **user**, **group**, **role**, **policy**;
why use roles for EC2 instead of hard-coding keys; principle of least privilege.

---

## 4. CloudWatch — Monitoring & Logs

```bash
# List log groups
aws logs describe-log-groups

# Tail a log group live (great demo)
aws logs tail /aws/ec2/cirrus --follow

# List metric alarms
aws cloudwatch describe-alarms
```

---

## 5. Other services worth a one-liner

```bash
# RDS — managed databases
aws rds describe-db-instances

# Lambda — serverless functions
aws lambda list-functions

# DynamoDB — NoSQL
aws dynamodb list-tables

# SNS / SQS — messaging
aws sns list-topics
aws sqs list-queues

# Region & AZ awareness
aws ec2 describe-regions --output table
aws ec2 describe-availability-zones --region us-east-1
```

---

## 6. Handy global flags & patterns

```bash
--region us-east-1        # override region
--profile myprofile       # use a specific credential profile
--output table|json|text  # change output format
--query "..."             # JMESPath filter to trim output
--dry-run                 # EC2: test permissions without acting
--no-cli-pager            # don't open results in a pager
```

---

## 7. Quick concept cheat-sheet (oral answers)

| Term | One-line answer |
|------|-----------------|
| **EC2** | Virtual server in the cloud (IaaS) — hosts CIRRUS backend. |
| **S3** | Object storage; data stored as objects in globally-unique buckets. |
| **AMI** | Template (OS + config) used to launch an EC2 instance. |
| **Security Group** | Stateful virtual firewall controlling inbound/outbound traffic. |
| **IAM Role** | Set of permissions an AWS service can assume — no hard-coded keys. |
| **Region vs AZ** | Region = geographic area; AZ = isolated data center within a region. |
| **Pre-signed URL** | Time-limited URL granting temporary access to a private S3 object. |
| **Elastic IP** | Static public IPv4 address you can attach to an instance. |
| **EBS** | Persistent block storage (virtual disk) attached to EC2. |
| **Free tier** | `t2.micro` EC2 + limited S3 usage free for 12 months. |

---

### Safe practice order for testing
1. `aws --version` → `aws configure` → `aws sts get-caller-identity`
2. S3: `mb` a test bucket → `cp` upload → `ls` → `presign` → `rm --recursive` → `rb`
3. EC2: `describe-instances` (read-only, safe) → `describe-security-groups`
4. Clean up anything you created so you aren't billed.
