variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "aws_profile" {
  description = "AWS profile to use"
  type        = string
  default     = "vincent"
}

variable "name" {
  description = "Base name for resources"
  type        = string
  default     = "personal-assistant"
}

variable "ecr_image_uri" {
  description = "ECR image URI to deploy"
  type        = string
  default     = "077590795309.dkr.ecr.eu-west-1.amazonaws.com/personal-assistant/app:latest"
}

variable "cpu" {
  description = "CPU units for ECS task (256 = 0.25 vCPU)"
  type        = number
  default     = 2048
}

variable "memory" {
  description = "Memory for ECS task in MiB"
  type        = number
  default     = 4096
}

variable "telegram_api_key" {
  description = "Telegram Bot API Key"
  type        = string
  sensitive   = true
}

variable "qore_password" {
  description = "Qore gym booking password"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API Key"
  type        = string
  sensitive   = true
}
