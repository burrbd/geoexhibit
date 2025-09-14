output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = "https://${aws_cloudfront_distribution.titiler.domain_name}"
}

output "s3_bucket_name" {
  description = "S3 bucket name for analysis data"
  value       = aws_s3_bucket.analyses.bucket
}

# ECR repository output removed - using ZIP-based Lambda deployment

output "aws_region" {
  description = "AWS region"
  value       = local.aws_region
}

output "config_summary" {
  description = "Configuration values read from config.json"
  value = {
    config_file  = var.config_file
    project_name = local.project_name
    aws_region   = local.aws_region
    s3_bucket    = local.s3_bucket
    site_url     = local.site_url
    environment  = local.environment
  }
}



output "lambda_function_name" {
  description = "TiTiler Lambda function name"
  value       = aws_lambda_function.titiler.function_name
}

output "lambda_function_arn" {
  description = "TiTiler Lambda function ARN"
  value       = aws_lambda_function.titiler.arn
}

output "lambda_function_url" {
  description = "Lambda Function URL (direct access)"
  value       = aws_lambda_function_url.titiler.function_url
}

output "example_tilejson_url" {
  description = "Example TileJSON URL for testing"
  value       = "https://${aws_cloudfront_distribution.titiler.domain_name}/stac/tilejson.json?url=https://example.com/stac-data/items/job-id/aoi-id.json&format=webp"
}

output "example_tile_url" {
  description = "Example tile URL for testing"
  value       = "https://${aws_cloudfront_distribution.titiler.domain_name}/stac/tiles/{z}/{x}/{y}.png?url=https://example.com/stac-data/items/job-id/aoi-id.json&format=webp"
}

output "lambda_package_hash" {
  description = "Hash of the current Lambda package"
  value       = local.lambda_package_hash
}

output "lambda_package_s3_key" {
  description = "S3 key of the current Lambda package"
  value       = local.lambda_package_key
}
