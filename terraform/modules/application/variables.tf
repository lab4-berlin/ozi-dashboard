variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "etl-app"
}

variable "app_image" {
  description = "Docker image for the application (e.g., account_id.dkr.ecr.region.amazonaws.com/image_name:tag)"
  type        = string
}

variable "app_cpu" {
  description = "CPU units for the Fargate task (e.g., 256, 512, 1024)"
  type        = number
  default     = 256
}

variable "app_memory" {
  description = "Memory in MiB for the Fargate task (e.g., 512, 1024, 2048)"
  type        = number
  default     = 512
}

variable "app_port" {
  description = "Port the application container listens on"
  type        = number
  default     = 80 # Default, but ETL might not need a port if it's batch processing
}

variable "app_desired_count" {
  description = "Desired number of tasks to run for the service"
  type        = number
  default     = 1
}

variable "app_environment_variables" {
  description = "A list of environment variables for the container. Each element is an object with 'name' and 'value' keys."
  type        = list(object({ name = string, value = string }))
  default     = []
  # Example:
  # [
  #   { name = "DATABASE_URL", value = "..." },
  #   { name = "API_KEY", value = "..." }
  # ]
}

variable "app_subnets" {
  description = "List of subnet IDs for the Fargate tasks"
  type        = list(string)
}

variable "app_security_groups" {
  description = "List of security group IDs for the Fargate tasks"
  type        = list(string)
}

variable "aws_region" {
  description = "AWS region for CloudWatch logs and other regional resources"
  type        = string
}
