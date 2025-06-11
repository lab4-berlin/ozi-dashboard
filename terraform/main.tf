terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "vpc" {
  source = "./modules/vpc"
  # Optionally override vpc_cidr_block or public_subnet_cidrs here if needed
  # vpc_cidr_block = "10.1.0.0/16"
  # public_subnet_cidrs = ["10.1.1.0/24", "10.1.2.0/24"]
}

module "database" {
  source = "./modules/database"

  db_name     = "asstatsdb" # Or make this a variable
  db_username = var.db_username
  db_password = var.db_password

  # Use subnets from the VPC module.
  # Ensure your VPC module outputs subnet IDs intended for databases (e.g., private subnets)
  # For this example, using public subnets. In production, use private subnets.
  database_subnet_ids = module.vpc.public_subnet_ids

  # Use the default security group from the VPC module or a dedicated DB security group
  vpc_security_group_ids = [module.vpc.default_security_group_id]

  # Variables for engine, instance class etc. will use their defaults in the module
  # unless overridden here.
}

module "application" {
  source = "./modules/application"

  app_name  = "as-stats-etl" # Or make this a variable
  app_image = var.app_image
  aws_region = var.aws_region # Pass the region for CloudWatch logs etc.

  # Network configuration from the VPC module
  app_subnets         = module.vpc.public_subnet_ids # Use public subnets for Fargate tasks for simplicity
  app_security_groups = [module.vpc.default_security_group_id] # Use VPC's default SG

  # Environment variables for the application
  # This is where you'd pass database connection details, API keys, etc.
  app_environment_variables = [
    { name = "DB_HOST", value = module.database.db_instance_endpoint },
    { name = "DB_PORT", value = tostring(module.database.db_instance_port) }, # Ensure port is a string
    { name = "DB_NAME", value = module.database.db_instance_name }, # Or the specific DB name like "asstatsdb"
    { name = "DB_USER", value = var.db_username },
    { name = "DB_PASSWORD", value = var.db_password },
    # Add other necessary environment variables here
    # { name = "CLOUDFLARE_API_TOKEN", value = var.cloudflare_api_token }, # Example
    # { name = "RIPE_API_KEY", value = var.ripe_api_key } # Example
  ]

  # Other variables (cpu, memory, desired_count) will use defaults from the module
  # unless overridden.
  # app_cpu    = 512
  # app_memory = 1024
}
