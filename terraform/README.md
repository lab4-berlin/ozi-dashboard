# Terraform Infrastructure for AS Stats Application

This directory contains Terraform scripts to provision the necessary AWS infrastructure for the AS Stats application. This includes a VPC, an RDS PostgreSQL database, and an ECS Fargate service to run the ETL application.

> **Note:** For local development, use Docker Compose as described below. Terraform is intended for provisioning production infrastructure on AWS.

## Prerequisites

- [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli) installed (version specified in `main.tf` `required_version`)
- AWS Account and configured AWS credentials (e.g., via AWS CLI, environment variables, or IAM roles). Ensure the credentials have permissions to create the resources defined in the scripts.
- Docker image for the application pushed to a registry (e.g., ECR) and the image URI ready.

## Local Development

For local development and testing, you can use Docker Compose instead of provisioning AWS infrastructure. The `docker-compose.yml` file in the project root defines services for both PostgreSQL and the ETL application, mirroring the production setup managed by Terraform.

- To start the local stack:
  ```sh
  docker-compose up --build
  ```
- Environment variables for database credentials and names are managed via a `.env` file or defaults in `docker-compose.yml`.
- The ETL service will wait for the database to become healthy before starting.
- Database schema initialization is handled automatically via the mounted SQL script.

Refer to the main project `README.md` for more details on local development.

## Setup and Deployment

### 1. Configure Variables

The main variables are defined in `variables.tf`. You can override their default values in several ways. The following variables should match those used in your Docker Compose setup for consistency:

```hcl
aws_region   = "your-aws-region" // e.g., "us-east-1"
db_username  = "yourdbuser"      // Should match POSTGRES_USER/OZI_DATABASE_USER
db_password  = "yourdbpassword"  // Should match POSTGRES_PASSWORD/OZI_DATABASE_PASSWORD
db_name      = "yourdbname"      // Should match POSTGRES_DB/OZI_DATABASE_NAME
app_image    = "your_account_id.dkr.ecr.your_aws_region.amazonaws.com/your_app_image:latest"
# Optional: Override other variables like instance types, CIDR blocks, etc.
# vpc_cidr_block      = "10.0.0.0/16"
# public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
```

  **Important:** Add `terraform.tfvars` to your `.gitignore` file if it contains sensitive information. For production, consider using a secrets manager.

- **Environment Variables:** You can set variables as environment variables prefixed with `TF_VAR_`. For example:
  ```bash
  export TF_VAR_aws_region="us-east-1"
  export TF_VAR_db_username="yourdbuser"
  export TF_VAR_db_password="yourdbpassword"
  export TF_VAR_app_image="your_app_ecr_image_uri"
  ```
  This is particularly useful for sensitive data in CI/CD pipelines.

- **Command-line flags:** Use the `-var` flag when running `plan` or `apply`:
  ```bash
  terraform plan -var="aws_region=us-east-1" -var="db_username=yourdbuser" ...
  ```

### 2. Initialize Terraform

Navigate to the `terraform` directory and run the `init` command. This will download the necessary provider plugins and initialize the backend.

```bash
cd /path/to/your/repo/terraform
terraform init
```

### 3. Plan Changes

Run the `plan` command to see what infrastructure Terraform will create, modify, or destroy. Review the plan carefully.

```bash
terraform plan
```
If you created a `terraform.tfvars` file, it will be loaded automatically. Otherwise, you might need to pass variables using other methods described above if they don't have defaults or if you wish to override defaults.

### 4. Apply Changes

If the plan looks correct, apply the changes to create the infrastructure.

```bash
terraform apply
```
Terraform will ask for confirmation before proceeding. Type `yes` to confirm.

This command will also automatically use `terraform.tfvars` if present.

## Outputs

After a successful `apply`, Terraform will display any defined outputs. These are also stored in the state file and can be queried using `terraform output`. Key outputs include:

- The RDS database provisioned by Terraform does not automatically run initialization SQL scripts like Docker Compose does. You must manually initialize the schema (e.g., using `psql` or a migration tool) after the database is created, or automate this step in your CI/CD pipeline.
- `db_endpoint`: The connection endpoint for the RDS database.
- `app_url`: (Currently a placeholder) Intended for the URL of the deployed application if a load balancer or App Runner is used.
- Module-specific outputs can also be queried if needed, e.g., `terraform output -module=vpc vpc_id`.

## Updating Infrastructure

If you make changes to the Terraform configuration files (`.tf`), re-run `terraform plan` and `terraform apply` to update your infrastructure.

## Destroying Infrastructure

To remove all resources created by this Terraform configuration, run the `destroy` command. This is irreversible.

```bash
terraform destroy
```
Terraform will ask for confirmation before proceeding. Type `yes` to confirm.

## Modules

The infrastructure is organized into modules located in the `modules/` directory:
- **vpc**: Defines the Virtual Private Cloud, subnets, and basic security groups.
- **database**: Defines the RDS PostgreSQL instance.
- **application**: Defines the ECS Fargate service for running the ETL application.

Each module has its own `main.tf`, `variables.tf`, and `outputs.tf`. The root `main.tf` instantiates these modules and connects them.
