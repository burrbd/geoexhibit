# GeoExhibit - Terraform Infrastructure

Terraform configuration for deploying the GeoExhibit infrastructure on AWS.

## Setup

### Prerequisites
- AWS CLI v2 installed (see AWS documentation)
- Docker installed (for Lambda package building)  
- Terraform >= 1.0 installed

### Deployment Steps

```bash
# 1. Configure AWS credentials
aws configure

# 2. Create IAM permissions (requires temporary AdministratorAccess)
./setup-aws-permissions.sh

# 3. Configure terraform variables  
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings
# Important: Set s3_bucket to match your publisher config.json

# 4. Build Lambda package (required before terraform apply)
make build-lambda

# 5. Deploy infrastructure
make deploy

# 6. Validate deployment
python validate-infrastructure.py https://YOUR_CLOUDFRONT_URL
```

### For Cursor Agents
The Makefile automates AWS CLI and Terraform installation for agent environments. The build process handles Lambda package creation automatically.

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

## Validation

After deployment, validate the infrastructure:

```bash
# Get CloudFront URL from terraform output
CLOUDFRONT_URL=$(terraform output -raw cloudfront_url)

# Run validation tests
python validate-infrastructure.py $CLOUDFRONT_URL
```

The validation script tests:
- Health endpoint responds correctly
- CORS headers are configured
- TileJSON endpoint works with demo STAC data
- Actual tile requests return valid images

## Manual Testing

Test endpoints manually:

```bash
# Health check
curl https://YOUR_CLOUDFRONT_URL/health

# TileJSON for demo data
STAC_URL="https://geoexhibit-demo.s3.ap-southeast-2.amazonaws.com/jobs/01K4XRE3K3KQDMTZ60XY1XWMN4/stac/items/01K4XRE3KB6H2JPVKHE77YE7QA.json"
curl "https://YOUR_CLOUDFRONT_URL/stac/tilejson.json?url=$STAC_URL&format=webp"

# Sample tile
curl "https://YOUR_CLOUDFRONT_URL/stac/tiles/8/128/128.png?url=$STAC_URL&format=webp"
```

## TODO

1. **Test with custom site URL** - Configure CORS with specific domain and validate web map integration
2. **Optimize Lambda package size** - Consider minimal titiler.core + TilerFactory
3. **Web map integration** - Update web_scaffold to use deployed endpoints