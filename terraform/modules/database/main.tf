resource "aws_db_instance" "default" {
  allocated_storage    = var.db_allocated_storage
  engine               = var.db_engine
  engine_version       = var.db_engine_version
  instance_class       = var.db_instance_class
  name                 = var.db_name
  username             = var.db_username
  password             = var.db_password
  parameter_group_name = aws_db_parameter_group.default.name
  db_subnet_group_name = aws_db_subnet_group.default.name
  skip_final_snapshot  = true // Set to false in production
  vpc_security_group_ids = var.vpc_security_group_ids


  tags = {
    Name = "${var.db_name}-instance"
  }
}

resource "aws_db_subnet_group" "default" {
  name       = "${var.db_name}-sng"
  subnet_ids = var.database_subnet_ids

  tags = {
    Name = "${var.db_name}-sng"
  }
}

resource "aws_db_parameter_group" "default" {
  name   = "${var.db_name}-pg"
  family = "${var.db_engine}${var.db_engine_version_major}" # e.g., postgres13

  parameter {
    name  = "log_connections"
    value = "1"
  }

  tags = {
    Name = "${var.db_name}-pg"
  }
}
