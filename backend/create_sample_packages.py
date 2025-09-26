#!/usr/bin/env python3
"""
Sample Deployment Package Creation Script
Demonstrates how to create CIS compliance deployment packages programmatically
"""

import os
import sys
import json
import requests
from typing import List, Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
SAMPLE_PACKAGES = [
    {
        "name": "CIS Windows 10 Enterprise Baseline",
        "description": "Core CIS compliance policies for Windows 10 Enterprise",
        "target_os": "windows_10_enterprise",
        "policy_selection": "category",
        "categories": ["Security Settings", "Administrative Templates"],
        "formats": ["lgpo_pol", "registry_reg", "powershell_ps1"],
        "scripts": {
            "use_powershell": True,
            "use_batch": True,
            "create_backup": True,
            "verify_before_apply": True,
            "rollback_support": True
        }
    },
    {
        "name": "CIS Server 2022 Hardening",
        "description": "Server hardening policies based on CIS benchmarks",
        "target_os": "windows_server_2022", 
        "policy_selection": "all",
        "formats": ["lgpo_pol", "lgpo_inf", "powershell_ps1"],
        "scripts": {
            "use_powershell": True,
            "use_batch": True,
            "require_admin": True,
            "create_backup": True,
            "log_changes": True
        }
    },
    {
        "name": "CIS Critical Security Controls",
        "description": "High-priority security controls for immediate deployment",
        "target_os": "windows_11_enterprise",
        "policy_selection": "tags",
        "tags": ["critical", "security", "high-priority"],
        "formats": ["registry_reg", "powershell_ps1"],
        "scripts": {
            "use_powershell": True,
            "create_backup": True,
            "verify_before_apply": True
        }
    }
]


def check_api_health() -> bool:
    """Check if the API is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False


def get_available_policies() -> List[Dict[str, Any]]:
    """Get available policies from dashboard"""
    try:
        response = requests.get(f"{API_BASE_URL}/dashboard/policies")
        if response.status_code == 200 and response.json().get('success'):
            return response.json()['data']['policies']
        return []
    except Exception as e:
        print(f"Error fetching policies: {e}")
        return []


def get_available_groups() -> List[Dict[str, Any]]:
    """Get available policy groups"""
    try:
        response = requests.get(f"{API_BASE_URL}/dashboard/groups")
        if response.status_code == 200 and response.json().get('success'):
            return response.json()['data']['groups']
        return []
    except Exception as e:
        print(f"Error fetching groups: {e}")
        return []


def get_available_tags() -> List[Dict[str, Any]]:
    """Get available policy tags"""
    try:
        response = requests.get(f"{API_BASE_URL}/dashboard/tags")
        if response.status_code == 200 and response.json().get('success'):
            return response.json()['data']['tags']
        return []
    except Exception as e:
        print(f"Error fetching tags: {e}")
        return []


def create_deployment_package(config: Dict[str, Any]) -> str:
    """Create a deployment package"""
    
    # Build request payload
    payload = {
        "name": config["name"],
        "description": config["description"],
        "target_os": config["target_os"],
        "include_formats": config["formats"],
        "include_scripts": config["scripts"].get("use_powershell", True),
        "include_documentation": True,
        "include_verification": True,
        "create_zip_package": True,
        "use_powershell": config["scripts"].get("use_powershell", True),
        "use_batch": config["scripts"].get("use_batch", True),
        "require_admin": config["scripts"].get("require_admin", True),
        "create_backup": config["scripts"].get("create_backup", True),
        "verify_before_apply": config["scripts"].get("verify_before_apply", True),
        "log_changes": config["scripts"].get("log_changes", True),
        "rollback_support": config["scripts"].get("rollback_support", True)
    }
    
    # Add policy selection parameters
    if config["policy_selection"] == "groups":
        payload["group_names"] = config.get("groups", [])
    elif config["policy_selection"] == "tags":
        payload["tag_names"] = config.get("tags", [])
    elif config["policy_selection"] == "categories":
        # For demo purposes, we'll use all policies
        # In a real implementation, you'd filter by category
        pass
    
    try:
        response = requests.post(f"{API_BASE_URL}/deployment/packages", json=payload)
        
        if response.status_code == 200 and response.json().get('success'):
            return response.json()['data']['package_id']
        else:
            error_msg = response.json().get('detail', 'Unknown error')
            print(f"Error creating package '{config['name']}': {error_msg}")
            return None
            
    except Exception as e:
        print(f"Error creating package '{config['name']}': {e}")
        return None


def build_package(package_id: str) -> str:
    """Start building a deployment package"""
    try:
        response = requests.post(f"{API_BASE_URL}/deployment/packages/{package_id}/build")
        
        if response.status_code == 200 and response.json().get('success'):
            return response.json()['data']['job_id']
        else:
            error_msg = response.json().get('detail', 'Unknown error')
            print(f"Error building package {package_id}: {error_msg}")
            return None
            
    except Exception as e:
        print(f"Error building package {package_id}: {e}")
        return None


def monitor_job(job_id: str, package_name: str) -> bool:
    """Monitor job progress"""
    import time
    
    print(f"Building package '{package_name}'...")
    last_progress = -1
    
    while True:
        try:
            response = requests.get(f"{API_BASE_URL}/deployment/jobs/{job_id}")
            
            if response.status_code == 200 and response.json().get('success'):
                job = response.json()['data']
                
                if job['progress'] != last_progress:
                    print(f"  Progress: {job['progress']}% - {job['current_step']}")
                    last_progress = job['progress']
                
                if job['status'] == 'completed':
                    print(f"  ✅ Package '{package_name}' completed successfully")
                    return True
                elif job['status'] == 'failed':
                    print(f"  ❌ Package '{package_name}' failed: {job.get('error_message', 'Unknown error')}")
                    return False
                
                time.sleep(2)
            else:
                print(f"  Error monitoring job: {response.text}")
                return False
                
        except Exception as e:
            print(f"  Error monitoring job: {e}")
            return False


def list_packages():
    """List all deployment packages"""
    try:
        response = requests.get(f"{API_BASE_URL}/deployment/packages")
        
        if response.status_code == 200 and response.json().get('success'):
            packages = response.json()['data']['packages']
            
            print(f"\nDeployment Packages ({len(packages)} total):")
            print("-" * 80)
            print(f"{'Name':<30} {'OS':<20} {'Status':<12} {'Policies':<10}")
            print("-" * 80)
            
            for pkg in packages:
                name = pkg['name'][:29] + "..." if len(pkg['name']) > 29 else pkg['name']
                os_name = pkg['target_os'].replace('_', ' ').title()
                status = pkg['status'].title()
                policies = len(pkg.get('source_policies', []))
                
                print(f"{name:<30} {os_name:<20} {status:<12} {policies:<10}")
            
            return packages
        else:
            print("Error fetching packages")
            return []
            
    except Exception as e:
        print(f"Error listing packages: {e}")
        return []


def get_package_statistics():
    """Get and display deployment statistics"""
    try:
        response = requests.get(f"{API_BASE_URL}/deployment/statistics")
        
        if response.status_code == 200 and response.json().get('success'):
            stats = response.json()['data']
            
            print(f"\nDeployment Statistics:")
            print("-" * 30)
            print(f"Total Packages: {stats['total_packages']}")
            print(f"Completed: {stats['completed_packages']}")
            print(f"Failed: {stats['failed_packages']}")
            print(f"Pending: {stats['pending_packages']}")
            print(f"Success Rate: {stats['success_rate']:.1f}%")
            print(f"Policies Packaged: {stats['total_policies_packaged']}")
            
            if stats.get('os_distribution'):
                print(f"\nOS Distribution:")
                for os_name, count in stats['os_distribution'].items():
                    print(f"  {os_name.replace('_', ' ').title()}: {count}")
                    
        else:
            print("Error fetching statistics")
            
    except Exception as e:
        print(f"Error getting statistics: {e}")


def download_package(package_id: str, output_path: str = None):
    """Download a deployment package"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/deployment/packages/{package_id}/download",
            stream=True
        )
        
        if response.status_code == 200:
            # Determine filename
            if not output_path:
                content_disposition = response.headers.get('content-disposition', '')
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"')
                else:
                    filename = f"deployment-package-{package_id}.zip"
                output_path = filename
            
            # Download file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Package downloaded: {output_path}")
            print(f"File size: {os.path.getsize(output_path) / 1024:.1f} KB")
            return output_path
            
        else:
            print(f"Error downloading package: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error downloading package: {e}")
        return None


def create_sample_packages():
    """Create all sample packages"""
    
    print("Creating sample deployment packages...")
    print("=" * 50)
    
    created_packages = []
    
    for config in SAMPLE_PACKAGES:
        print(f"\nCreating package: {config['name']}")
        
        # Create package
        package_id = create_deployment_package(config)
        if not package_id:
            continue
            
        # Build package
        job_id = build_package(package_id)
        if not job_id:
            continue
            
        # Monitor build progress
        success = monitor_job(job_id, config['name'])
        if success:
            created_packages.append({
                'id': package_id,
                'name': config['name'],
                'config': config
            })
    
    print(f"\n✅ Created {len(created_packages)} packages successfully")
    
    return created_packages


def main():
    """Main script execution"""
    
    print("CIS GPO Deployment Package Creation Script")
    print("=" * 50)
    
    # Check API availability
    if not check_api_health():
        print("❌ API is not available. Please ensure the backend server is running.")
        print(f"Expected URL: {API_BASE_URL}")
        sys.exit(1)
    
    print("✅ API is available")
    
    # Get available data
    policies = get_available_policies()
    groups = get_available_groups()
    tags = get_available_tags()
    
    print(f"📊 Found {len(policies)} policies, {len(groups)} groups, {len(tags)} tags")
    
    if len(policies) == 0:
        print("⚠️  No policies found. Please ensure the dashboard has policies loaded.")
        print("   Run the dashboard import process first.")
        
        # Show current packages anyway
        list_packages()
        get_package_statistics()
        sys.exit(0)
    
    # Show menu
    while True:
        print(f"\nOptions:")
        print("1. Create sample packages")
        print("2. List existing packages")
        print("3. Show statistics")
        print("4. Download package")
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            created = create_sample_packages()
            if created:
                print(f"\nCreated packages:")
                for pkg in created:
                    print(f"  - {pkg['name']} (ID: {pkg['id']})")
        
        elif choice == '2':
            list_packages()
        
        elif choice == '3':
            get_package_statistics()
        
        elif choice == '4':
            packages = list_packages()
            if packages:
                package_id = input("\nEnter package ID to download: ").strip()
                package = next((p for p in packages if p['package_id'] == package_id), None)
                
                if package and package['status'] == 'completed':
                    download_package(package_id)
                elif package:
                    print(f"Package status is '{package['status']}', not ready for download")
                else:
                    print("Package not found")
        
        elif choice == '5':
            print("Goodbye!")
            break
        
        else:
            print("Invalid option. Please select 1-5.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)