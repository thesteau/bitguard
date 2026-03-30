terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region where the EC2 instance will be created."
  type        = string
}

variable "project_name" {
  description = "Project name used in tags and resource names."
  type        = string
  default     = "bitguard-api"
}

variable "environment" {
  description = "Environment label used in tags."
  type        = string
  default     = "dev"
}

variable "instance_type" {
  description = "EC2 instance type."
  type        = string
  default     = "t3.micro"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GiB."
  type        = number
  default     = 30
}

variable "root_volume_type" {
  description = "Root EBS volume type."
  type        = string
  default     = "gp3"
}

variable "ssh_public_key" {
  description = "Public SSH key contents. Leave empty to skip creating an EC2 key pair."
  type        = string
  default     = ""
  sensitive   = true
}

variable "ssh_allowed_cidrs" {
  description = "CIDR blocks allowed to SSH into the instance."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "app_port" {
  description = "Application port to expose on the EC2 instance."
  type        = number
  default     = 8000
}

variable "app_allowed_cidrs" {
  description = "CIDR blocks allowed to reach the application port."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "instance_name" {
  description = "Name tag for the EC2 instance."
  type        = string
  default     = "bitguard-api-ec2"
}

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_subnet" "selected" {
  id = data.aws_subnets.default.ids[0]
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

resource "aws_security_group" "ec2" {
  name        = "${var.project_name}-${var.environment}-ec2-sg"
  description = "Security group for the ${var.project_name} EC2 instance"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_allowed_cidrs
  }

  ingress {
    description = "Application"
    from_port   = var.app_port
    to_port     = var.app_port
    protocol    = "tcp"
    cidr_blocks = var.app_allowed_cidrs
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-ec2-sg"
  })
}

resource "aws_key_pair" "ec2" {
  count      = trimspace(var.ssh_public_key) != "" ? 1 : 0
  key_name   = "${var.project_name}-${var.environment}-key"
  public_key = trimspace(var.ssh_public_key)

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-key"
  })
}

resource "aws_instance" "api" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnet.selected.id
  vpc_security_group_ids      = [aws_security_group.ec2.id]
  associate_public_ip_address = true
  key_name                    = length(aws_key_pair.ec2) > 0 ? aws_key_pair.ec2[0].key_name : null

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = var.root_volume_type
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = merge(local.common_tags, {
    Name = var.instance_name
  })
}

output "instance_id" {
  description = "EC2 instance ID."
  value       = aws_instance.api.id
}

output "public_ip" {
  description = "Public IPv4 address."
  value       = aws_instance.api.public_ip
}

output "public_dns" {
  description = "Public DNS hostname."
  value       = aws_instance.api.public_dns
}

output "ubuntu_ami_id" {
  description = "Ubuntu AMI selected for the instance."
  value       = data.aws_ami.ubuntu.id
}

output "ssh_command" {
  description = "SSH command for the instance when a key pair is configured."
  value       = length(aws_key_pair.ec2) > 0 ? "ssh ubuntu@${aws_instance.api.public_ip}" : "No EC2 key pair created. Set TF_VAR_ssh_public_key to enable SSH."
}
