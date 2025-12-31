output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs_cluster.name
}

output "service_name" {
  description = "Name of the ECS service"
  value       = module.ecs_service.name
}

output "task_execution_role_arn" {
  description = "ARN of the task execution role"
  value       = module.ecs_service.task_exec_iam_role_arn
}

output "task_role_arn" {
  description = "ARN of the task role"
  value       = module.ecs_service.tasks_iam_role_arn
}
