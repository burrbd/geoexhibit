terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = local.aws_region
}

# ECR repository removed - using ZIP-based Lambda deployment

# S3 Bucket for analysis data
resource "aws_s3_bucket" "analyses" {
  bucket = local.s3_bucket
  
  tags = {
    Project = local.project_name
    Environment = local.environment
  }
}

# S3 Bucket versioning
resource "aws_s3_bucket_versioning" "analyses" {
  bucket = aws_s3_bucket.analyses.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket public access block
resource "aws_s3_bucket_public_access_block" "analyses" {
  bucket = aws_s3_bucket.analyses.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "analyses" {
  bucket = aws_s3_bucket.analyses.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket CORS configuration
resource "aws_s3_bucket_cors_configuration" "analyses" {
  bucket = aws_s3_bucket.analyses.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = local.site_url != "" ? [local.site_url] : ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# IAM Role for TiTiler Lambda
resource "aws_iam_role" "titiler_role" {
  name = "${local.project_name}-titiler-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project = local.project_name
    Environment = local.environment
  }
}

# IAM Policy for TiTiler Lambda to access S3
resource "aws_iam_role_policy" "titiler_s3" {
  name = "${local.project_name}-titiler-s3"
  role = aws_iam_role.titiler_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "ReadCOGs"
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.analyses.arn}/jobs/*"
      },
      {
        Sid = "ListBucket" 
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = "${aws_s3_bucket.analyses.arn}"
      },
      {
        Sid = "ReadSTACData"
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.analyses.arn}/jobs/*/stac/*"
      },
    ]
  })
}

# IAM Policy for TiTiler Lambda CloudWatch logs
resource "aws_iam_role_policy_attachment" "titiler_logs" {
  role       = aws_iam_role.titiler_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ECR permissions for Lambda to pull container images
# ECR permissions removed - using ZIP-based Lambda deployment

# Upload Lambda package to S3 with hash-based naming
# Docker build/push handled separately from infrastructure

locals {
  # Lambda package path - must be built before terraform apply
  lambda_package_path = "lambda/titiler/lambda-package.zip"
  lambda_package_exists = fileexists(local.lambda_package_path)
  lambda_package_hash = local.lambda_package_exists ? filebase64sha256(local.lambda_package_path) : "no-package"
  lambda_package_key  = "lambda-packages/titiler-lambda-${substr(local.lambda_package_hash, 0, 16)}.zip"
}

# Lambda package upload - only if package exists
resource "aws_s3_object" "lambda_package" {
  count  = local.lambda_package_exists ? 1 : 0
  bucket = aws_s3_bucket.analyses.bucket
  key    = local.lambda_package_key
  source = local.lambda_package_path
  etag   = filemd5(local.lambda_package_path)
  
  tags = {
    Project = local.project_name
    Environment = local.environment
    LambdaVersion = substr(local.lambda_package_hash, 0, 16)
  }
}

resource "aws_lambda_function" "titiler" {
  function_name = "${local.project_name}-titiler"
  role         = aws_iam_role.titiler_role.arn
  timeout      = var.lambda_timeout
  memory_size  = var.lambda_memory_size
  architectures = ["x86_64"]
  publish      = true  # Publish version for CloudFront
  
  s3_bucket        = local.lambda_package_exists ? aws_s3_object.lambda_package[0].bucket : null
  s3_key          = local.lambda_package_exists ? aws_s3_object.lambda_package[0].key : null
  s3_object_version = local.lambda_package_exists ? aws_s3_object.lambda_package[0].version_id : null
  source_code_hash = local.lambda_package_exists ? local.lambda_package_hash : null
  handler          = "handler.handler"
  runtime          = "python3.12"
  
  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.analyses.bucket
      PROJECT_NAME = local.project_name
      SITE_URL = local.site_url
      # GDAL optimization for Lambda
      GDAL_DISABLE_READDIR_ON_OPEN = "EMPTY_DIR"
      CPL_VSIL_CURL_ALLOWED_EXTENSIONS = ".tif,.tiff,.cog"
      VSI_CACHE = "TRUE"
      VSI_CACHE_SIZE = "16777216"
    }
  }

  tags = {
    Project = local.project_name
    Environment = local.environment
  }
}

# Lambda Function URL (FURL) for direct access
resource "aws_lambda_function_url" "titiler" {
  function_name      = aws_lambda_function.titiler.function_name
  authorization_type = "NONE"
  
  cors {
    allow_credentials = true
    allow_origins     = local.site_url != "" ? [local.site_url] : ["*"]
    allow_methods     = ["GET", "HEAD"]
    allow_headers     = ["*"]
    expose_headers    = ["ETag", "Content-Length", "Content-Type"]
    max_age          = 86400
  }
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "titiler" {
  depends_on = [aws_lambda_function_url.titiler]
  
  enabled             = true
  is_ipv6_enabled    = true
  default_root_object = "index.html"
  
  # Lambda Function URL origin
  origin {
    domain_name = replace(replace(aws_lambda_function_url.titiler.function_url, "https://", ""), "/", "")
    origin_id   = "lambda-titiler"

    custom_origin_config {
      http_port              = 443
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }
  
  # S3 bucket origin for static assets
  origin {
    domain_name = aws_s3_bucket.analyses.bucket_regional_domain_name
    origin_id   = "s3-analyses"
    origin_path = ""  # No path prefix - we'll handle routing in cache behaviors
    
    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.analyses.cloudfront_access_identity_path
    }
  }
  
  # Lambda cache behavior for tile endpoints
  ordered_cache_behavior {
    path_pattern     = "/stac/tiles/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "lambda-titiler"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true  # Cache by full query string
      headers      = []    # No header variation
      
      cookies {
        forward = "none"
      }
    }
    
    # Cache tiles for a long time
    default_ttl = 86400      # 1 day
    max_ttl     = 604800     # 7 days
    min_ttl     = 0
    
    # Enable compression
    compress = true
  }

  # Lambda cache behavior for STAC API endpoints
  ordered_cache_behavior {
    path_pattern     = "/stac/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "lambda-titiler"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true  # Cache by full query string
      headers      = []    # No header variation
      
      cookies {
        forward = "none"
      }
    }
    
    # Medium cache for STAC API responses
    default_ttl = 300       # 5 minutes
    max_ttl     = 3600      # 1 hour max
    min_ttl     = 0
    
    # Enable compression
    compress = true
  }

  # Default cache behavior (Lambda) - for health, API docs, etc.
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "lambda-titiler"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true  # Cache by full query string
      headers      = []    # No header variation
      
      cookies {
        forward = "none"
      }
    }
    
    # Short cache for dynamic content
    default_ttl = 0         # No cache
    max_ttl     = 3600      # 1 hour max
    min_ttl     = 0
    
    # Enable compression
    compress = true
  }
  
  # S3 cache behavior for STAC data files (collections, items)
  ordered_cache_behavior {
    path_pattern     = "/jobs/*/stac/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "s3-analyses"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      headers      = []

      cookies {
        forward = "none"
      }
    }

    default_ttl = 86400      # 1 day
    max_ttl     = 604800     # 7 days  
    min_ttl     = 0

    compress = true
  }

  # S3 cache behavior for PMTiles (enable Range requests)
  ordered_cache_behavior {
    path_pattern     = "/jobs/*/pmtiles/*.pmtiles"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "s3-analyses"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      headers      = ["Range"]  # Enable Range requests for PMTiles
      
      cookies {
        forward = "none"
      }
    }
    
    default_ttl = 86400      # 1 day
    max_ttl     = 604800     # 7 days
    min_ttl     = 0
    
    compress = true
  }
  
  # Error pages
  custom_error_response {
    error_code         = 404
    response_code      = "200"
    response_page_path = "/index.html"
  }
  
  # Price class (use only North America and Europe for cost optimization)
  price_class = "PriceClass_100"
  
  # Viewer certificate
  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version      = "TLSv1.2_2021"
  }
  
  # Geographic restrictions (none - global access)
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  tags = {
    Project = local.project_name
    Environment = local.environment
  }
}

# CloudFront Origin Access Identity for S3
resource "aws_cloudfront_origin_access_identity" "analyses" {
  comment = "OAI for ${local.project_name} analyses bucket"
}

# S3 bucket policy for CloudFront access
resource "aws_s3_bucket_policy" "analyses" {
  bucket = aws_s3_bucket.analyses.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "CloudFrontAccess"
        Effect    = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.analyses.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.analyses.arn}/*"
      }
    ]
  })
}
