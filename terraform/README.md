# GeoExhibit - Terraform Infrastructure

Terraform configuration for deploying the GeoExhibit infrastructure on AWS.

## Setup

```bash
# Configure AWS credentials
aws configure

# Create IAM permissions
./setup-aws-permissions.sh

# Deploy infrastructure
make deploy
```

## Configuration

Edit `variables.tf` to customize:

- `project_name`: Resource naming (default: "geoexhibit")
- `environment`: Environment name (default: "dev")
- `aws_region`: AWS region (default: "ap-southeast-2")
- `site_url`: CORS origin (default: "")

## Commands

```bash
make deploy-infra   # Deploy infrastructure
make build-lambda   # Build Lambda package
make deploy-lambda  # Deploy Lambda function
make deploy         # Deploy everything
make clean          # Clean build artifacts
```

## What Gets Created

- **S3 Bucket**: Stores COG tiles and STAC metadata
- **Lambda Function**: TiTiler with STAC extension (x86_64, 1536MB)
- **Lambda Function URL**: Direct HTTPS endpoint
- **CloudFront Distribution**: Global CDN with routing
- **IAM Roles**: Lambda permissions for S3 access

## API Endpoints

- **Tiles**: `{cloudfront_url}/tiles/stac/tiles/{z}/{x}/{y}.png?url={stac_item_url}&format=webp`
- **TileJSON**: `{cloudfront_url}/tiles/stac/tilejson.json?url={stac_item_url}&format=webp`
- **STAC Data**: `{cloudfront_url}/stac-data/collections/{project}/collection.json`
- **Health**: `{cloudfront_url}/health`

## Architecture

```
Browser → CloudFront → TiTiler (Lambda) → COG (S3)
         ↓
    STAC Data (S3)
```

- `/tiles/*` → Lambda (dynamic tiling)
- `/stac-data/*` → S3 (static metadata)

## TODO

1. **Attempt lambda using stripped back fast api app** - Replace `titiler.application` with minimal `titiler.core` + `TilerFactory` to reduce package size
2. **Test the endpoints using a custom site url** - Configure CORS with specific domain and validate tile serving
3. **Work out how to generate and host the "static" web map** - Create web map interface for visualizing analysis results