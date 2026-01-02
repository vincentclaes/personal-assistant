# Personal Assistant

A Python-based personal assistant with Telegram bot integration and automated scheduling capabilities.

## Project Structure

```text
personal-assistant/
├── personal_assistant/     # Source code
│   ├── app.py             # Main Telegram bot application
│   ├── cli.py             # CLI entrypoint (pa command)
│   └── database.py        # Database configuration
├── tests/                 # Test suite
│   ├── test_app.py
│   ├── test_database.py
│   ├── test_chat_history.py
│   └── test_manage_db.py
├── ci/                    # CI/CD scripts
│   └── deploy-image.sh    # Automated deployment script
├── terraform/             # Infrastructure as code
├── Dockerfile             # Container definition
└── pyproject.toml         # Dependencies
```

## Deployment Commands

### Automated Deployment

Use the automated deployment script to build, push, and deploy in one command:

```bash
./ci/deploy-image.sh
```

This script will:

1. Build the Docker image for linux/amd64
2. Tag the image for ECR
3. Login to ECR
4. Push the image to ECR
5. Force a new ECS deployment

After the script completes, wait ~90 seconds and view the logs with the command shown in the output.

### Manual Deployment Steps

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

## Development

### Running Locally

```bash
# Run the application
uv run python -m personal_assistant.app

# Run tests
uv run python -m pytest

# Run specific test file
uv run python -m pytest tests/test_database.py
```

### Database Management

```bash
# Export database to JSON
uv run pa db export --output backup.json

# Clear user chat history
uv run pa db clear --user-id 12345

# Delete entire user entry
uv run pa db clear --user-id 12345 --full
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
