#!/usr/bin/env python3
"""
CIS GPO Compliance Tool - Deployment CLI
Command-line interface for offline GPO deployment package creation
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deployment.deployment_manager import DeploymentManager
from deployment.models_deployment import (
    WindowsVersion, PackageFormat, PolicyExportConfig, ScriptConfiguration
)
from deployment.lgpo_utils import LGPOManager
from dashboard_manager import DashboardManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentCLI:
    """Command-line interface for deployment operations"""
    
    def __init__(self):
        self.deployment_manager = DeploymentManager()
        self.dashboard_manager = DashboardManager()
        self.lgpo_manager = LGPOManager()
    
    def create_package_interactive(self):
        """Interactive package creation wizard"""
        print("\n" + "="*60)
        print("CIS GPO Compliance Tool - Deployment Package Creator")
        print("="*60)
        
        # Get package basic info
        name = input("\nPackage name: ").strip()
        if not name:
            print("Error: Package name is required")
            return False
        
        description = input("Package description: ").strip()
        if not description:
            description = f"CIS compliance deployment package - {name}"
        
        # Select target OS
        print("\nSelect target Windows version:")
        versions = list(WindowsVersion)
        for i, version in enumerate(versions, 1):
            print(f"  {i}. {version.value.replace('_', ' ').title()}")
        
        while True:
            try:
                choice = int(input(f"\nSelect version (1-{len(versions)}): "))
                if 1 <= choice <= len(versions):
                    target_os = versions[choice-1]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(versions)}")
            except ValueError:
                print("Please enter a valid number")
        
        # Select policies
        policies = self._select_policies_interactive()
        if not policies:
            print("Error: No policies selected")
            return False
        
        # Select formats
        formats = self._select_formats_interactive()
        
        # Configure scripts
        script_config = self._configure_scripts_interactive()
        
        # Create export configuration
        export_config = PolicyExportConfig(
            target_os=target_os,
            include_formats=formats,
            include_scripts=True,
            include_documentation=True,
            include_verification=True,
            create_zip_package=True,
            package_name=name
        )
        
        # Create package
        print(f"\nCreating deployment package '{name}'...")
        try:
            package_id = self.deployment_manager.create_deployment_package(
                name=name,
                description=description,
                policies=policies,
                export_config=export_config,
                script_config=script_config
            )
            
            # Start package creation
            print("Building package...")
            job_id = self.deployment_manager.start_package_creation(package_id)
            
            # Monitor progress
            self._monitor_job_progress(job_id)
            
            package = self.deployment_manager.get_package(package_id)
            if package.status.value == "completed":
                print(f"\n✅ Package created successfully!")
                print(f"Package ID: {package_id}")
                print(f"Location: {package.package_path}")
                print(f"Size: {package.package_size_bytes / 1024:.1f} KB")
                print(f"Files: {package.total_files}")
                return True
            else:
                print(f"\n❌ Package creation failed")
                return False
                
        except Exception as e:
            print(f"Error creating package: {e}")
            logger.error(f"Package creation error: {e}")
            return False
    
    def _select_policies_interactive(self) -> List[Dict[str, Any]]:
        """Interactive policy selection"""
        print("\nSelect policies to include:")
        print("1. All available policies")
        print("2. Policies by category")
        print("3. Policies by group")
        print("4. Policies by tag")
        print("5. Specific policy IDs")
        
        while True:
            try:
                choice = int(input("\nSelection method (1-5): "))
                if 1 <= choice <= 5:
                    break
                else:
                    print("Please enter a number between 1 and 5")
            except ValueError:
                print("Please enter a valid number")
        
        try:
            if choice == 1:
                # All policies
                policies = self.dashboard_manager.get_all_policies()
                return [p.dict() for p in policies]
            
            elif choice == 2:
                # By category
                categories = set()
                all_policies = self.dashboard_manager.get_all_policies()
                for policy in all_policies:
                    if hasattr(policy, 'category') and policy.category:
                        categories.add(policy.category)
                
                if not categories:
                    print("No categories found")
                    return []
                
                print("\nAvailable categories:")
                cat_list = sorted(list(categories))
                for i, cat in enumerate(cat_list, 1):
                    print(f"  {i}. {cat}")
                
                selected_cats = input("\nEnter category numbers (comma-separated): ").strip()
                selected_policies = []
                
                for cat_num in selected_cats.split(','):
                    try:
                        idx = int(cat_num.strip()) - 1
                        if 0 <= idx < len(cat_list):
                            category = cat_list[idx]
                            cat_policies = [p for p in all_policies if hasattr(p, 'category') and p.category == category]
                            selected_policies.extend([p.dict() for p in cat_policies])
                    except ValueError:
                        continue
                
                return selected_policies
            
            elif choice == 3:
                # By group
                groups = self.dashboard_manager.get_all_groups()
                if not groups:
                    print("No groups found")
                    return []
                
                print("\nAvailable groups:")
                for i, group in enumerate(groups, 1):
                    print(f"  {i}. {group.name} ({len(group.policy_ids)} policies)")
                
                selected_groups = input("\nEnter group numbers (comma-separated): ").strip()
                selected_policies = []
                
                for group_num in selected_groups.split(','):
                    try:
                        idx = int(group_num.strip()) - 1
                        if 0 <= idx < len(groups):
                            group = groups[idx]
                            group_policies = self.dashboard_manager.get_policies_by_group(group.name)
                            selected_policies.extend([p.dict() for p in group_policies])
                    except ValueError:
                        continue
                
                return selected_policies
            
            elif choice == 4:
                # By tag
                tags = self.dashboard_manager.get_all_tags()
                if not tags:
                    print("No tags found")
                    return []
                
                print("\nAvailable tags:")
                for i, tag in enumerate(tags, 1):
                    print(f"  {i}. {tag.name} ({len(tag.policy_ids)} policies)")
                
                selected_tags = input("\nEnter tag numbers (comma-separated): ").strip()
                selected_policies = []
                
                for tag_num in selected_tags.split(','):
                    try:
                        idx = int(tag_num.strip()) - 1
                        if 0 <= idx < len(tags):
                            tag = tags[idx]
                            tag_policies = self.dashboard_manager.get_policies_by_tag(tag.name)
                            selected_policies.extend([p.dict() for p in tag_policies])
                    except ValueError:
                        continue
                
                return selected_policies
            
            elif choice == 5:
                # Specific IDs
                policy_ids = input("\nEnter policy IDs (comma-separated): ").strip()
                selected_policies = []
                
                for policy_id in policy_ids.split(','):
                    policy_id = policy_id.strip()
                    policy = self.dashboard_manager.get_policy(policy_id)
                    if policy:
                        selected_policies.append(policy.dict())
                    else:
                        print(f"Warning: Policy {policy_id} not found")
                
                return selected_policies
                
        except Exception as e:
            print(f"Error selecting policies: {e}")
            return []
        
        return []
    
    def _select_formats_interactive(self) -> List[PackageFormat]:
        """Interactive format selection"""
        print("\nSelect deployment formats:")
        formats = list(PackageFormat)
        format_descriptions = {
            PackageFormat.LGPO_POL: "LGPO .pol files (recommended for Group Policy)",
            PackageFormat.LGPO_INF: "LGPO .inf security template files",
            PackageFormat.REGISTRY_REG: "Registry .reg files for direct import",
            PackageFormat.POWERSHELL_PS1: "PowerShell scripts for automation",
            PackageFormat.BATCH_BAT: "Batch files for simple deployment"
        }
        
        for i, fmt in enumerate(formats, 1):
            desc = format_descriptions.get(fmt, "")
            print(f"  {i}. {fmt.value} - {desc}")
        
        selected_formats = input(f"\nEnter format numbers (comma-separated, default: 1,3,4): ").strip()
        
        if not selected_formats:
            # Default formats
            return [PackageFormat.LGPO_POL, PackageFormat.REGISTRY_REG, PackageFormat.POWERSHELL_PS1]
        
        selected = []
        for fmt_num in selected_formats.split(','):
            try:
                idx = int(fmt_num.strip()) - 1
                if 0 <= idx < len(formats):
                    selected.append(formats[idx])
            except ValueError:
                continue
        
        return selected if selected else [PackageFormat.LGPO_POL, PackageFormat.REGISTRY_REG]
    
    def _configure_scripts_interactive(self) -> ScriptConfiguration:
        """Interactive script configuration"""
        print("\nScript Configuration:")
        
        def ask_yes_no(question: str, default: bool = True) -> bool:
            default_str = "Y/n" if default else "y/N"
            answer = input(f"{question} ({default_str}): ").strip().lower()
            if not answer:
                return default
            return answer in ['y', 'yes']
        
        use_powershell = ask_yes_no("Generate PowerShell scripts?", True)
        use_batch = ask_yes_no("Generate batch wrapper scripts?", True)
        require_admin = ask_yes_no("Require administrator privileges?", True)
        create_backup = ask_yes_no("Create system backup before deployment?", True)
        verify_before_apply = ask_yes_no("Verify settings before applying?", True)
        log_changes = ask_yes_no("Log all changes?", True)
        rollback_support = ask_yes_no("Include rollback scripts?", True)
        
        return ScriptConfiguration(
            use_powershell=use_powershell,
            use_batch=use_batch,
            require_admin=require_admin,
            create_backup=create_backup,
            verify_before_apply=verify_before_apply,
            log_changes=log_changes,
            rollback_support=rollback_support
        )
    
    def _monitor_job_progress(self, job_id: str):
        """Monitor job progress with updates"""
        import time
        
        last_progress = -1
        while True:
            job = self.deployment_manager.get_job_status(job_id)
            if not job:
                print("Job not found")
                break
            
            if job.progress != last_progress:
                print(f"Progress: {job.progress}% - {job.current_step}")
                last_progress = job.progress
            
            if job.status.value in ["completed", "failed"]:
                break
            
            time.sleep(1)
        
        if job and job.status.value == "failed":
            print(f"Error: {job.error_message}")
    
    def list_packages(self):
        """List all deployment packages"""
        packages = self.deployment_manager.get_all_packages()
        
        if not packages:
            print("No deployment packages found")
            return
        
        print("\nDeployment Packages:")
        print("-" * 80)
        print(f"{'ID':<36} {'Name':<20} {'OS':<15} {'Status':<10} {'Policies':<8}")
        print("-" * 80)
        
        for package in packages:
            print(f"{package.package_id:<36} {package.name[:19]:<20} {package.target_os.value:<15} {package.status.value:<10} {len(package.source_policies):<8}")
        
        print(f"\nTotal packages: {len(packages)}")
    
    def show_package_details(self, package_id: str):
        """Show detailed package information"""
        package = self.deployment_manager.get_package(package_id)
        if not package:
            print(f"Package not found: {package_id}")
            return
        
        print(f"\nPackage Details:")
        print("-" * 50)
        print(f"ID: {package.package_id}")
        print(f"Name: {package.name}")
        print(f"Description: {package.description}")
        print(f"Target OS: {package.target_os.value}")
        print(f"Status: {package.status.value}")
        print(f"Created: {package.created_at}")
        print(f"Updated: {package.updated_at}")
        print(f"Policies: {len(package.source_policies)}")
        print(f"Files: {package.total_files}")
        print(f"Size: {package.package_size_bytes / 1024:.1f} KB" if package.package_size_bytes else "N/A")
        print(f"Location: {package.package_path or 'Not built'}")
        
        if package.validation_results:
            print(f"Validation: {'✅ Passed' if package.integrity_verified else '❌ Failed'}")
        
        print(f"\nIncluded Formats:")
        for fmt in package.export_config.include_formats:
            print(f"  - {fmt.value}")
        
        if package.source_groups:
            print(f"\nSource Groups: {', '.join(package.source_groups)}")
        
        if package.source_tags:
            print(f"Source Tags: {', '.join(package.source_tags)}")
    
    def delete_package(self, package_id: str):
        """Delete a deployment package"""
        package = self.deployment_manager.get_package(package_id)
        if not package:
            print(f"Package not found: {package_id}")
            return
        
        print(f"\nPackage: {package.name}")
        print(f"ID: {package_id}")
        confirm = input("\nAre you sure you want to delete this package? (y/N): ").strip().lower()
        
        if confirm in ['y', 'yes']:
            success = self.deployment_manager.delete_package(package_id)
            if success:
                print("Package deleted successfully")
            else:
                print("Failed to delete package")
        else:
            print("Deletion cancelled")
    
    def show_statistics(self):
        """Show deployment statistics"""
        stats = self.deployment_manager.get_package_statistics()
        
        print("\nDeployment Statistics:")
        print("-" * 30)
        print(f"Total Packages: {stats['total_packages']}")
        print(f"Completed: {stats['completed_packages']}")
        print(f"Failed: {stats['failed_packages']}")
        print(f"Pending: {stats['pending_packages']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Active Jobs: {stats['active_jobs']}")
        print(f"Total Policies Packaged: {stats['total_policies_packaged']}")
        
        if stats['os_distribution']:
            print(f"\nOS Distribution:")
            for os_name, count in stats['os_distribution'].items():
                print(f"  {os_name}: {count}")
    
    def check_lgpo_status(self):
        """Check LGPO.exe availability"""
        is_available = self.lgpo_manager.is_available()
        
        print(f"\nLGPO.exe Status:")
        print("-" * 20)
        print(f"Available: {'✅ Yes' if is_available else '❌ No'}")
        
        if is_available:
            version = self.lgpo_manager.get_version()
            print(f"Version: {version or 'Unknown'}")
            print(f"Path: {self.lgpo_manager.lgpo_path}")
        else:
            print("\nTo enable full LGPO functionality:")
            print("1. Download LGPO.exe from Microsoft")
            print("2. Place it in the tools/ directory")
            print("3. Re-run this command to verify")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="CIS GPO Compliance Tool - Deployment CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deployment_cli.py create              # Interactive package creation
  python deployment_cli.py list                # List all packages
  python deployment_cli.py show <package_id>   # Show package details
  python deployment_cli.py delete <package_id> # Delete package
  python deployment_cli.py stats               # Show statistics
  python deployment_cli.py lgpo                # Check LGPO status
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create package command
    create_parser = subparsers.add_parser('create', help='Create deployment package interactively')
    
    # List packages command
    list_parser = subparsers.add_parser('list', help='List all deployment packages')
    
    # Show package command
    show_parser = subparsers.add_parser('show', help='Show package details')
    show_parser.add_argument('package_id', help='Package ID to show')
    
    # Delete package command
    delete_parser = subparsers.add_parser('delete', help='Delete deployment package')
    delete_parser.add_argument('package_id', help='Package ID to delete')
    
    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Show deployment statistics')
    
    # LGPO status command
    lgpo_parser = subparsers.add_parser('lgpo', help='Check LGPO.exe status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        cli = DeploymentCLI()
        
        if args.command == 'create':
            cli.create_package_interactive()
        elif args.command == 'list':
            cli.list_packages()
        elif args.command == 'show':
            cli.show_package_details(args.package_id)
        elif args.command == 'delete':
            cli.delete_package(args.package_id)
        elif args.command == 'stats':
            cli.show_statistics()
        elif args.command == 'lgpo':
            cli.check_lgpo_status()
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"CLI error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()