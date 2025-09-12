variable "project_name" {
  description = "Name of the project (used for resource naming)"
  type        = string
  default     = "geoexhibit"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "ap-southeast-2"
}

variable "domain_name" {
  description = "Domain name for Cloudflare configuration (optional)"
  type        = string
  default     = ""
}

variable "site_url" {
  description = "Site URL for CORS configuration (optional)"
  type        = string
  default     = ""
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 15  # Optimized for faster tiles
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB (1536-2048 for faster tiles)"
  type        = number
  default     = 2048  # Optimized for performance
}
