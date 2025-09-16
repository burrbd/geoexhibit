# GeoExhibit configuration file path
variable "config_file" {
  description = "Path to GeoExhibit config.json file"
  type        = string
  default     = "../demo/config.json"
}

# Override variables (optional - will use config.json if not specified)
variable "environment" {
  description = "Environment name (dev, staging, prod) - overrides config.json"
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

# Read and parse GeoExhibit config.json
locals {
  # Load the publisher config.json file
  config_data = jsondecode(file(var.config_file))
  
  # Extract values from config.json structure
  project_name = local.config_data.project.name
  aws_region   = local.config_data.aws.region
  s3_bucket    = local.config_data.aws.s3_bucket
  site_url     = try(local.config_data.map.base_url, "")
  
  # Use override if provided, otherwise default to "dev"
  environment = var.environment != "" ? var.environment : "dev"
}
