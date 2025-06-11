output "db_instance_endpoint" {
  description = "The connection endpoint for the database instance."
  value       = aws_db_instance.default.endpoint
}

output "db_instance_port" {
  description = "The port on which the database instance is listening."
  value       = aws_db_instance.default.port
}

output "db_instance_name" {
  description = "The name of the database instance."
  value       = aws_db_instance.default.name
}

output "db_parameter_group_name" {
  description = "The name of the database parameter group."
  value       = aws_db_parameter_group.default.name
}
