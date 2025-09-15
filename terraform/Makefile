# GeoExhibit Infrastructure Makefile
# Manages Terraform deployment and Lambda package builds

.PHONY: help build-lambda deploy-infra deploy-lambda deploy plan init clean

# Default target
help:
	@echo "GeoExhibit Infrastructure Deployment"
	@echo ""
	@echo "Targets:"
	@echo "  init          Initialize Terraform backend"
	@echo "  plan          Show Terraform execution plan"
	@echo "  build-lambda  Build TiTiler Lambda package"
	@echo "  deploy-infra  Deploy infrastructure only"
	@echo "  deploy-lambda Deploy Lambda function only"
	@echo "  deploy        Build Lambda and deploy everything"
	@echo "  clean         Clean build artifacts"
	@echo ""
	@echo "Prerequisites:"
	@echo "  1. Run: ./setup-aws-permissions.sh"
	@echo "  2. Copy terraform.tfvars.example to terraform.tfvars"
	@echo "  3. Edit terraform.tfvars with your settings"

# Initialize Terraform
init:
	terraform init

# Show execution plan
plan: init
	terraform plan

# Build Lambda package using Docker
build-lambda:
	@echo "Building TiTiler Lambda package..."
	sudo docker build -t geoexhibit-titiler lambda/titiler/
	sudo docker run --rm geoexhibit-titiler cat /tmp/lambda-package.zip > lambda/titiler/lambda-package.zip
	@echo "Lambda package built: lambda/titiler/lambda-package.zip"

# Deploy infrastructure only
deploy-infra: init
	terraform apply -target=aws_s3_bucket.analyses \
		-target=aws_s3_bucket_versioning.analyses \
		-target=aws_s3_bucket_public_access_block.analyses \
		-target=aws_s3_bucket_server_side_encryption_configuration.analyses \
		-target=aws_s3_bucket_cors_configuration.analyses \
		-target=aws_iam_role.titiler_role \
		-target=aws_iam_role_policy.titiler_s3 \
		-target=aws_iam_role_policy_attachment.titiler_logs \
		-target=aws_cloudfront_origin_access_identity.analyses \
		-target=aws_s3_bucket_policy.analyses \
		-target=aws_cloudfront_distribution.titiler \
		-auto-approve

# Deploy Lambda function only (requires existing infrastructure)
deploy-lambda: build-lambda
	terraform apply -target=aws_s3_object.lambda_package \
		-target=aws_lambda_function.titiler \
		-target=aws_lambda_function_url.titiler \
		-auto-approve

# Deploy everything (checks for lambda package first)
deploy: check-lambda-package init
	terraform apply -auto-approve

# Check if lambda package exists before deploy
check-lambda-package:
	@if [ ! -f lambda/titiler/lambda-package.zip ]; then \
		echo "Error: lambda-package.zip not found"; \
		echo "Run 'make build-lambda' first to build the Lambda package"; \
		exit 1; \
	fi

# Clean build artifacts
clean:
	rm -f lambda/titiler/lambda-package.zip
	docker rmi -f geoexhibit-titiler 2>/dev/null || true
	@echo "Build artifacts cleaned"

# Check if terraform.tfvars exists
check-config:
	@if [ ! -f terraform.tfvars ]; then \
		echo "Error: terraform.tfvars not found"; \
		echo "Copy terraform.tfvars.example to terraform.tfvars and edit it"; \
		exit 1; \
	fi

# Override targets to check config first
deploy-infra: check-config
deploy-lambda: check-config  
deploy: check-config
plan: check-config