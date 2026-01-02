o#!/bin/bash
set -e

# Configuration
AWS_PROFILE="vincent"
AWS_REGION="eu-west-1"
ECR_REGISTRY="077590795309.dkr.ecr.eu-west-1.amazonaws.com"
ECR_REPOSITORY="personal-assistant/app"
IMAGE_TAG="latest"
LOCAL_IMAGE_NAME="personal-assistant:local"
ECS_CLUSTER="personal-assistant-default-cluster"
ECS_SERVICE="personal-assistant-default-svc"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Personal Assistant Deployment Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Build Docker image
echo -e "${YELLOW}[1/5] Building Docker image...${NC}"
docker build --platform linux/amd64 --provenance=false -t ${LOCAL_IMAGE_NAME} .
echo -e "${GREEN}✓ Docker image built successfully${NC}"
echo ""

# Step 2: Tag image for ECR
echo -e "${YELLOW}[2/5] Tagging image for ECR...${NC}"
docker tag ${LOCAL_IMAGE_NAME} ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
echo -e "${GREEN}✓ Image tagged successfully${NC}"
echo ""

# Step 3: Login to ECR
echo -e "${YELLOW}[3/5] Logging in to ECR...${NC}"
AWS_PROFILE=${AWS_PROFILE} aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_REGISTRY}
echo -e "${GREEN}✓ Logged in to ECR successfully${NC}"
echo ""

# Step 4: Push image to ECR
echo -e "${YELLOW}[4/5] Pushing image to ECR...${NC}"
docker push ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
echo -e "${GREEN}✓ Image pushed successfully${NC}"
echo ""

# Step 5: Force ECS redeployment
echo -e "${YELLOW}[5/5] Forcing ECS service redeployment...${NC}"
AWS_PROFILE=${AWS_PROFILE} aws ecs update-service \
  --cluster ${ECS_CLUSTER} \
  --service ${ECS_SERVICE} \
  --force-new-deployment \
  --region ${AWS_REGION} \
  --no-cli-pager
echo -e "${GREEN}✓ ECS service redeployment initiated${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}To view logs (wait ~90 seconds for deployment):${NC}"
echo -e "  sleep 90 && AWS_PROFILE=${AWS_PROFILE} aws logs tail /aws/ecs/${ECS_SERVICE}/app --region ${AWS_REGION} --since 3m --format short"
echo ""
