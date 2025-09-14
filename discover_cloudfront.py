#!/usr/bin/env python3
"""
Script to discover the deployed CloudFront URL for GeoExhibit infrastructure.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def discover_cloudfront_url():
    """Discover CloudFront distribution URL for GeoExhibit project."""
    try:
        # Initialize CloudFront client
        cloudfront = boto3.client('cloudfront')
        
        print("🔍 Discovering CloudFront distributions...")
        
        # List all distributions
        response = cloudfront.list_distributions()
        
        if 'DistributionList' not in response or not response['DistributionList'].get('Items'):
            print("❌ No CloudFront distributions found")
            return None
            
        distributions = response['DistributionList']['Items']
        print(f"📊 Found {len(distributions)} CloudFront distributions")
        
        # Look for distributions that might be related to GeoExhibit
        geoexhibit_distributions = []
        
        for dist in distributions:
            dist_id = dist['Id']
            domain_name = dist['DomainName']
            status = dist['Status']
            comment = dist.get('Comment', '')
            
            # Check if this looks like a GeoExhibit distribution
            is_geoexhibit = (
                'geoexhibit' in comment.lower() or
                'sa-fire-analyses' in comment.lower() or
                'fire' in comment.lower() or
                any('geoexhibit' in str(origin.get('DomainName', '')) 
                    for origin in dist.get('Origins', {}).get('Items', []))
            )
            
            if is_geoexhibit or len(distributions) == 1:  # If only one distribution, assume it's ours
                geoexhibit_distributions.append({
                    'id': dist_id,
                    'domain': domain_name,
                    'status': status,
                    'comment': comment
                })
                print(f"  ✅ Found potential GeoExhibit distribution:")
                print(f"     ID: {dist_id}")
                print(f"     Domain: {domain_name}")
                print(f"     Status: {status}")
                print(f"     Comment: {comment}")
        
        if len(geoexhibit_distributions) == 1:
            cloudfront_url = f"https://{geoexhibit_distributions[0]['domain']}"
            print(f"🎯 Discovered CloudFront URL: {cloudfront_url}")
            return cloudfront_url
        elif len(geoexhibit_distributions) > 1:
            print(f"⚠️  Found {len(geoexhibit_distributions)} potential distributions:")
            for i, dist in enumerate(geoexhibit_distributions):
                print(f"  {i+1}. https://{dist['domain']} ({dist['status']})")
            # Use the first deployed one
            deployed = [d for d in geoexhibit_distributions if d['status'] == 'Deployed']
            if deployed:
                cloudfront_url = f"https://{deployed[0]['domain']}"
                print(f"🎯 Using first deployed distribution: {cloudfront_url}")
                return cloudfront_url
        else:
            print("❌ No GeoExhibit-related distributions found")
            if distributions:
                print("📋 All distributions:")
                for dist in distributions:
                    print(f"  • https://{dist['DomainName']} ({dist['Status']})")
            return None
            
    except NoCredentialsError:
        print("❌ AWS credentials not found")
        return None
    except ClientError as e:
        print(f"❌ AWS API error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error discovering CloudFront: {e}")
        return None


def main():
    """Main function."""
    cloudfront_url = discover_cloudfront_url()
    
    if cloudfront_url:
        print(f"\n🚀 Ready to test infrastructure:")
        print(f"python3 terraform/validate-infrastructure.py {cloudfront_url}")
        print(f"python3 steel_thread_validation_complete.py {cloudfront_url}")
        return cloudfront_url
    else:
        print("\n❌ Could not discover CloudFront URL")
        print("💡 If infrastructure is deployed, you can manually provide the CloudFront URL")
        return None


if __name__ == "__main__":
    main()