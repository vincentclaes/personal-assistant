# Personal Assistant

## Deployment Commands

### Build and Push Docker Image

```bash
# Build Docker image for linux/amd64 platform (required for ECS Fargate)
docker build --platform linux/amd64 --provenance=false -t personal-assistant:local .

# Test the image locally (interactive mode)
docker run -it --env-file .env -e TZ=Europe/Brussels -e TIMEZONE=Europe/Brussels personal-assistant:local

# Tag the image for ECR
docker tag personal-assistant:local 077590795309.dkr.ecr.eu-west-1.amazonaws.com/personal-assistant/app:latest

# Login to ECR (if not already authenticated)
AWS_PROFILE=vincent aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin 077590795309.dkr.ecr.eu-west-1.amazonaws.com

# Push image to ECR
docker push 077590795309.dkr.ecr.eu-west-1.amazonaws.com/personal-assistant/app:latest
```

### Deploy with Terraform

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform (first time only)
AWS_PROFILE=vincent terraform init

# Apply Terraform configuration
AWS_PROFILE=vincent terraform apply -auto-approve

# Navigate back to project root
cd ..
```

### Force New ECS Deployment

```bash
# Force ECS to deploy the latest Docker image
AWS_PROFILE=vincent aws ecs update-service \
  --cluster personal-assistant-default-cluster \
  --service personal-assistant-default-svc \
  --force-new-deployment \
  --region eu-west-1
```

### View Logs

```bash
# Tail CloudWatch logs (wait 90 seconds for deployment)
sleep 90 && AWS_PROFILE=vincent aws logs tail /aws/ecs/personal-assistant-default-svc/app \
  --region eu-west-1 \
  --since 3m \
  --format short
```

### Complete Deployment Pipeline

```bash
# Build, tag, and push Docker image
docker build --platform linux/amd64 --provenance=false -t personal-assistant:local . && \
docker tag personal-assistant:local 077590795309.dkr.ecr.eu-west-1.amazonaws.com/personal-assistant/app:latest && \
docker push 077590795309.dkr.ecr.eu-west-1.amazonaws.com/personal-assistant/app:latest

# Apply Terraform changes
cd terraform && AWS_PROFILE=vincent terraform apply -auto-approve && cd ..

# View logs after deployment
sleep 90 && AWS_PROFILE=vincent aws logs tail /aws/ecs/personal-assistant-default-svc/app \
  --region eu-west-1 \
  --since 3m \
  --format short
```

## Environment Variables

The following environment variables are configured in Terraform ([terraform/main.tf](terraform/main.tf)):

- `TELEGRAM_API_KEY` - Telegram bot token
- `QORE_PASSWORD` - Gym booking system password
- `OPENAI_API_KEY` - OpenAI API key for browser automation
- `BROWSER_HEADLESS` - Set to "true" for headless browser mode
- `TIMEZONE` - Set to "Europe/Brussels"
- `DB_PATH` - Database path (set to "/tmp/app.db" for writable storage)
- `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` - All set to "/tmp" for writable directories

## Infrastructure

- **ECR Repository**: `077590795309.dkr.ecr.eu-west-1.amazonaws.com/personal-assistant/app`
- **ECS Cluster**: `personal-assistant-default-cluster`
- **ECS Service**: `personal-assistant-default-svc`
- **AWS Region**: `eu-west-1`
- **AWS Profile**: `vincent`
