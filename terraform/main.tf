terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }

  backend "s3" {
    bucket         = "terraform-state-backend-077590795309"
    key            = "personal-assistant/app.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "terraform-state-backend-077590795309"
    encrypt        = true
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# Default VPC for minimalism
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security group: outbound only
resource "aws_security_group" "task" {
  name   = "${var.name}-${terraform.workspace}-task-sg"
  vpc_id = data.aws_vpc.default.id

  # No ingress rules at all

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name      = "${var.name}-${terraform.workspace}-task-sg"
    Workspace = terraform.workspace
  }
}

# ECS cluster
module "ecs_cluster" {
  source  = "terraform-aws-modules/ecs/aws//modules/cluster"
  version = "6.6.0"

  name = "${var.name}-${terraform.workspace}-cluster"

  tags = {
    Workspace = terraform.workspace
  }
}

# ECS Fargate service (no LB, no ports)
module "ecs_service" {
  source  = "terraform-aws-modules/ecs/aws//modules/service"
  version = "6.6.0"

  name        = "${var.name}-${terraform.workspace}-svc"
  cluster_arn = module.ecs_cluster.arn
  launch_type = "FARGATE"

  cpu    = var.cpu
  memory = var.memory

  desired_count = 1

  subnet_ids         = data.aws_subnets.default.ids
  security_group_ids = [aws_security_group.task.id]
  assign_public_ip   = true

  # Let the module create IAM roles
  create_task_exec_iam_role = true
  create_tasks_iam_role     = true

  container_definitions = {
    app = {
      image = var.ecr_image_uri

      # No port_mappings block at all - this service doesn't expose ports

      enable_cloudwatch_logging              = true
      cloudwatch_log_group_retention_in_days = 7

      # Disable readonly root filesystem to allow writes to /tmp
      readonly_root_filesystem = false

      # Environment variables for the application
      environment = [
        {
          name  = "TELEGRAM_API_KEY"
          value = var.telegram_api_key
        },
        {
          name  = "QORE_PASSWORD"
          value = var.qore_password
        },
        {
          name  = "OPENAI_API_KEY"
          value = var.openai_api_key
        },
        {
          name  = "BROWSER_HEADLESS"
          value = "true"
        },
        {
          name  = "TIMEZONE"
          value = "Europe/Brussels"
        },
        {
          name  = "HOME"
          value = "/tmp"
        },
        {
          name  = "XDG_CONFIG_HOME"
          value = "/tmp"
        },
        {
          name  = "XDG_DATA_HOME"
          value = "/tmp"
        },
        {
          name  = "XDG_CACHE_HOME"
          value = "/tmp"
        },
        {
          name  = "DB_PATH"
          value = "/tmp/app.db"
        }
      ]

      essential = true
    }
  }

  tags = {
    Workspace = terraform.workspace
  }
}
