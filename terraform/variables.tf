variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "db_username" {
  description = "Database username"
  type        = string
  sensitive   = true
}

variable "app_image" {
  description = "Docker image for the application (e.g., account_id.dkr.ecr.region.amazonaws.com/image_name:tag)"
  type        = string
  default     = "nginx:latest" # Placeholder, replace with actual ETL image
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}
