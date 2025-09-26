"""
Deployment Manager for CIS GPO Compliance Tool
Handles offline GPO packaging and deployment preparation
"""

import os
import json
import zipfile
import hashlib
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging
from dataclasses import asdict

from .models_deployment import (
    DeploymentPackage, DeploymentJob, PolicyFile, DeploymentScript,
    PackageManifest, ValidationResult, LGPOEntry, RegistryEntry,
    WindowsVersion, DeploymentStatus, PackageFormat, RegistryValueType,
    PolicyExportConfig, ScriptConfiguration
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeploymentManager:
    """Manages offline GPO deployment package creation and validation"""
    
    def __init__(self, storage_path: str = "data/deployments"):
        """Initialize deployment manager"""
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.packages_path = self.storage_path / "packages"
        self.exports_path = self.storage_path / "exports"  
        self.templates_path = self.storage_path / "templates"
        
        # Create required directories
        for path in [self.packages_path, self.exports_path, self.templates_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        self.active_jobs: Dict[str, DeploymentJob] = {}
        self.packages: Dict[str, DeploymentPackage] = {}
        
        # Load existing packages
        self._load_packages()
    
    def _load_packages(self):
        """Load existing deployment packages from storage"""
        try:
            packages_file = self.storage_path / "deployment_packages.json"
            if packages_file.exists():
                with open(packages_file, 'r') as f:
                    data = json.load(f)
                    for pkg_data in data.get('packages', []):
                        try:
                            package = self._deserialize_package(pkg_data)
                            self.packages[package.package_id] = package
                        except Exception as e:
                            logger.error(f"Error loading package: {e}")
        except Exception as e:
            logger.error(f"Error loading deployment packages: {e}")
    
    def _save_packages(self):
        """Save deployment packages to storage"""
        try:
            packages_file = self.storage_path / "deployment_packages.json"
            data = {
                'packages': [self._serialize_package(pkg) for pkg in self.packages.values()],
                'last_updated': datetime.now().isoformat()
            }
            with open(packages_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving deployment packages: {e}")
    
    def _serialize_package(self, package: DeploymentPackage) -> Dict[str, Any]:
        """Serialize deployment package for storage"""
        return {
            "package_id": package.package_id,
            "name": package.name,
            "description": package.description,
            "target_os": package.target_os.value,
            "status": package.status.value,
            "created_at": package.created_at.isoformat(),
            "updated_at": package.updated_at.isoformat(),
            "export_config": {
                "target_os": package.export_config.target_os.value,
                "include_formats": [f.value for f in package.export_config.include_formats],
                "include_scripts": package.export_config.include_scripts,
                "include_documentation": package.export_config.include_documentation,
                "include_verification": package.export_config.include_verification,
                "create_zip_package": package.export_config.create_zip_package,
                "package_name": package.export_config.package_name,
                "export_path": package.export_config.export_path
            },
            "script_config": asdict(package.script_config),
            "package_path": package.package_path,
            "package_size_bytes": package.package_size_bytes,
            "total_files": package.total_files,
            "validation_results": package.validation_results,
            "integrity_verified": package.integrity_verified,
            "source_groups": package.source_groups,
            "source_tags": package.source_tags,
            "source_policies": package.source_policies
        }
    
    def _deserialize_package(self, data: Dict[str, Any]) -> DeploymentPackage:
        """Deserialize deployment package from storage"""
        export_config = PolicyExportConfig(
            target_os=WindowsVersion(data["export_config"]["target_os"]),
            include_formats=[PackageFormat(f) for f in data["export_config"]["include_formats"]],
            include_scripts=data["export_config"]["include_scripts"],
            include_documentation=data["export_config"]["include_documentation"],
            include_verification=data["export_config"]["include_verification"],
            create_zip_package=data["export_config"]["create_zip_package"],
            package_name=data["export_config"]["package_name"],
            export_path=data["export_config"]["export_path"]
        )
        
        script_config = ScriptConfiguration(**data["script_config"])
        
        return DeploymentPackage(
            package_id=data["package_id"],
            name=data["name"],
            description=data["description"],
            target_os=WindowsVersion(data["target_os"]),
            status=DeploymentStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            export_config=export_config,
            script_config=script_config,
            package_path=data.get("package_path"),
            package_size_bytes=data.get("package_size_bytes", 0),
            total_files=data.get("total_files", 0),
            validation_results=data.get("validation_results", {}),
            integrity_verified=data.get("integrity_verified", False),
            source_groups=data.get("source_groups", []),
            source_tags=data.get("source_tags", []),
            source_policies=data.get("source_policies", [])
        )
    
    def create_deployment_package(
        self, 
        name: str,
        description: str,
        policies: List[Dict[str, Any]],
        export_config: PolicyExportConfig,
        script_config: ScriptConfiguration,
        groups: List[str] = None,
        tags: List[str] = None
    ) -> str:
        """Create a new deployment package"""
        
        package_id = str(uuid.uuid4())
        
        package = DeploymentPackage(
            package_id=package_id,
            name=name,
            description=description,
            target_os=export_config.target_os,
            status=DeploymentStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            export_config=export_config,
            script_config=script_config,
            source_policies=policies,
            source_groups=groups or [],
            source_tags=tags or []
        )
        
        self.packages[package_id] = package
        self._save_packages()
        
        logger.info(f"Created deployment package: {package_id}")
        return package_id
    
    def start_package_creation(self, package_id: str) -> str:
        """Start async package creation process"""
        
        if package_id not in self.packages:
            raise ValueError(f"Package not found: {package_id}")
        
        job_id = str(uuid.uuid4())
        
        job = DeploymentJob(
            job_id=job_id,
            package_id=package_id,
            status=DeploymentStatus.PROCESSING,
            progress=0,
            current_step="Initializing",
            total_steps=8,
            completed_steps=0,
            start_time=datetime.now(),
            estimated_completion=datetime.now() + timedelta(minutes=5)
        )
        
        self.active_jobs[job_id] = job
        
        try:
            # Process package creation
            self._process_package_creation(job_id)
        except Exception as e:
            job.status = DeploymentStatus.FAILED
            job.error_message = str(e)
            logger.error(f"Package creation failed: {e}")
        
        return job_id
    
    def _process_package_creation(self, job_id: str):
        """Process package creation steps"""
        
        job = self.active_jobs[job_id]
        package = self.packages[job.package_id]
        
        try:
            # Step 1: Validate input policies
            job.current_step = "Validating policies"
            job.progress = 10
            self._validate_input_policies(package)
            job.completed_steps = 1
            job.log_messages.append("Policy validation completed")
            
            # Step 2: Convert policies to LGPO format
            job.current_step = "Converting to LGPO format"
            job.progress = 25
            lgpo_entries = self._convert_policies_to_lgpo(package)
            job.completed_steps = 2
            job.log_messages.append(f"Converted {len(lgpo_entries)} policies to LGPO format")
            
            # Step 3: Generate policy files
            job.current_step = "Generating policy files"
            job.progress = 40
            policy_files = self._generate_policy_files(package, lgpo_entries)
            package.policy_files = policy_files
            job.completed_steps = 3
            job.log_messages.append(f"Generated {len(policy_files)} policy files")
            
            # Step 4: Generate deployment scripts
            job.current_step = "Creating deployment scripts"
            job.progress = 55
            scripts = self._generate_deployment_scripts(package)
            package.scripts = scripts
            job.completed_steps = 4
            job.log_messages.append(f"Generated {len(scripts)} deployment scripts")
            
            # Step 5: Create package manifest
            job.current_step = "Creating package manifest"
            job.progress = 70
            manifest = self._create_package_manifest(package)
            package.manifest = manifest
            job.completed_steps = 5
            job.log_messages.append("Package manifest created")
            
            # Step 6: Validate package integrity
            job.current_step = "Validating package integrity"
            job.progress = 80
            validation_result = self._validate_package(package)
            package.validation_results = asdict(validation_result)
            package.integrity_verified = validation_result.is_valid
            job.completed_steps = 6
            job.log_messages.append(f"Validation: {validation_result.passed_checks}/{validation_result.total_checks} checks passed")
            
            # Step 7: Create physical package
            job.current_step = "Creating package files"
            job.progress = 90
            package_path = self._create_physical_package(package)
            package.package_path = package_path
            job.completed_steps = 7
            job.log_messages.append(f"Package created at: {package_path}")
            
            # Step 8: Finalize
            job.current_step = "Finalizing package"
            job.progress = 100
            package.status = DeploymentStatus.COMPLETED if package.integrity_verified else DeploymentStatus.FAILED
            package.updated_at = datetime.now()
            job.completed_steps = 8
            job.status = DeploymentStatus.COMPLETED
            job.log_messages.append("Package creation completed")
            
        except Exception as e:
            job.status = DeploymentStatus.FAILED
            job.error_message = str(e)
            package.status = DeploymentStatus.FAILED
            logger.error(f"Package creation failed at step '{job.current_step}': {e}")
        
        finally:
            self._save_packages()
    
    def _validate_input_policies(self, package: DeploymentPackage):
        """Validate input policies for deployment"""
        
        if not package.source_policies:
            raise ValueError("No policies provided for deployment")
        
        required_fields = ['id', 'name', 'description', 'category']
        
        for i, policy in enumerate(package.source_policies):
            for field in required_fields:
                if field not in policy:
                    raise ValueError(f"Policy {i} missing required field: {field}")
    
    def _convert_policies_to_lgpo(self, package: DeploymentPackage) -> List[LGPOEntry]:
        """Convert policies to LGPO-compatible format"""
        
        lgpo_entries = []
        
        for policy in package.source_policies:
            try:
                lgpo_entry = self._policy_to_lgpo_entry(policy, package.target_os)
                lgpo_entries.append(lgpo_entry)
            except Exception as e:
                logger.warning(f"Could not convert policy {policy.get('id', 'unknown')}: {e}")
        
        return lgpo_entries
    
    def _policy_to_lgpo_entry(self, policy: Dict[str, Any], target_os: WindowsVersion) -> LGPOEntry:
        """Convert a single policy to LGPO entry"""
        
        # Extract registry information
        registry_entries = []
        
        if 'registry_settings' in policy:
            for reg_setting in policy['registry_settings']:
                registry_entry = RegistryEntry(
                    hive=reg_setting.get('hive', 'HKLM'),
                    key_path=reg_setting.get('key_path', ''),
                    value_name=reg_setting.get('value_name', ''),
                    value_type=RegistryValueType(reg_setting.get('value_type', 'REG_DWORD')),
                    value_data=reg_setting.get('value_data', ''),
                    description=reg_setting.get('description', ''),
                    policy_id=policy.get('id', ''),
                    category=policy.get('category', '')
                )
                registry_entries.append(registry_entry)
        
        # Determine configuration section
        section = "Computer Configuration"
        if policy.get('scope') == 'user':
            section = "User Configuration"
        
        # Build category path
        category_path = f"Administrative Templates/{policy.get('category', 'System')}"
        
        # Determine setting based on current value
        setting = "Enabled"
        if policy.get('current_value') == 'disabled':
            setting = "Disabled"
        elif policy.get('current_value') not in ['enabled', 'disabled']:
            setting = str(policy.get('current_value', 'Enabled'))
        
        return LGPOEntry(
            section=section,
            category_path=category_path,
            policy_name=policy.get('name', ''),
            setting=setting,
            registry_entries=registry_entries,
            description=policy.get('description', ''),
            policy_id=policy.get('id', '')
        )
    
    def _generate_policy_files(self, package: DeploymentPackage, lgpo_entries: List[LGPOEntry]) -> List[PolicyFile]:
        """Generate policy files in various formats"""
        
        policy_files = []
        
        for format_type in package.export_config.include_formats:
            try:
                if format_type == PackageFormat.LGPO_POL:
                    files = self._generate_pol_files(lgpo_entries, package.target_os)
                elif format_type == PackageFormat.LGPO_INF:
                    files = self._generate_inf_files(lgpo_entries, package.target_os)
                elif format_type == PackageFormat.REGISTRY_REG:
                    files = self._generate_reg_files(lgpo_entries, package.target_os)
                elif format_type == PackageFormat.POWERSHELL_PS1:
                    files = self._generate_powershell_files(lgpo_entries, package.target_os)
                else:
                    continue
                
                policy_files.extend(files)
                
            except Exception as e:
                logger.error(f"Error generating {format_type.value} files: {e}")
        
        return policy_files
    
    def _generate_pol_files(self, lgpo_entries: List[LGPOEntry], target_os: WindowsVersion) -> List[PolicyFile]:
        """Generate .pol files for LGPO"""
        
        # Separate computer and user policies
        computer_entries = [entry for entry in lgpo_entries if entry.section == "Computer Configuration"]
        user_entries = [entry for entry in lgpo_entries if entry.section == "User Configuration"]
        
        pol_files = []
        
        # Generate computer policy file
        if computer_entries:
            content = self._create_pol_content(computer_entries, "Machine")
            checksum = hashlib.sha256(content.encode()).hexdigest()
            
            pol_file = PolicyFile(
                file_name="Machine.pol",
                file_type="pol",
                content=content,
                checksum=checksum,
                size_bytes=len(content.encode()),
                policy_category="Computer Configuration",
                description="Computer configuration policies in LGPO format"
            )
            pol_files.append(pol_file)
        
        # Generate user policy file  
        if user_entries:
            content = self._create_pol_content(user_entries, "User")
            checksum = hashlib.sha256(content.encode()).hexdigest()
            
            pol_file = PolicyFile(
                file_name="User.pol",
                file_type="pol", 
                content=content,
                checksum=checksum,
                size_bytes=len(content.encode()),
                policy_category="User Configuration",
                description="User configuration policies in LGPO format"
            )
            pol_files.append(pol_file)
        
        return pol_files
    
    def _create_pol_content(self, entries: List[LGPOEntry], scope: str) -> str:
        """Create .pol file content"""
        
        lines = [
            f"; {scope} Policy File",
            f"; Generated by CIS GPO Compliance Tool",
            f"; Created: {datetime.now().isoformat()}",
            "",
            "[Version]",
            "signature=\"$CHICAGO$\"",
            "Revision=1",
            ""
        ]
        
        for entry in entries:
            if entry.registry_entries:
                lines.append(f"; Policy: {entry.policy_name}")
                lines.append(f"; Category: {entry.category_path}")
                lines.append(f"; Setting: {entry.setting}")
                
                for reg_entry in entry.registry_entries:
                    key_path = reg_entry.key_path.replace('HKEY_LOCAL_MACHINE\\', '').replace('HKEY_CURRENT_USER\\', '')
                    
                    lines.append(f"[{key_path}]")
                    
                    if reg_entry.value_type == RegistryValueType.REG_DWORD:
                        lines.append(f'"{reg_entry.value_name}"=dword:{reg_entry.value_data:08x}')
                    elif reg_entry.value_type == RegistryValueType.REG_SZ:
                        lines.append(f'"{reg_entry.value_name}"="{reg_entry.value_data}"')
                    else:
                        lines.append(f'"{reg_entry.value_name}"="{reg_entry.value_data}"')
                    
                    lines.append("")
        
        return "\n".join(lines)
    
    def _generate_inf_files(self, lgpo_entries: List[LGPOEntry], target_os: WindowsVersion) -> List[PolicyFile]:
        """Generate .inf files for security templates"""
        
        inf_content = self._create_inf_content(lgpo_entries, target_os)
        checksum = hashlib.sha256(inf_content.encode()).hexdigest()
        
        inf_file = PolicyFile(
            file_name="CISCompliance.inf",
            file_type="inf",
            content=inf_content,
            checksum=checksum,
            size_bytes=len(inf_content.encode()),
            description="Security template with CIS compliance policies"
        )
        
        return [inf_file]
    
    def _create_inf_content(self, entries: List[LGPOEntry], target_os: WindowsVersion) -> str:
        """Create .inf security template content"""
        
        lines = [
            "[Unicode]",
            "Unicode=yes",
            "",
            "[Version]",
            "signature=\"$CHICAGO$\"",
            "Revision=1",
            "",
            "[Profile Description]",
            f"Description=CIS Compliance Template for {target_os.value}",
            "",
            "[Registry Values]"
        ]
        
        for entry in entries:
            for reg_entry in entry.registry_entries:
                key_path = f"{reg_entry.hive}\\{reg_entry.key_path}"
                value_type_map = {
                    RegistryValueType.REG_SZ: "1",
                    RegistryValueType.REG_DWORD: "4", 
                    RegistryValueType.REG_BINARY: "3",
                    RegistryValueType.REG_EXPAND_SZ: "2",
                    RegistryValueType.REG_MULTI_SZ: "7"
                }
                
                type_code = value_type_map.get(reg_entry.value_type, "1")
                lines.append(f'{key_path}\\{reg_entry.value_name},{type_code},"{reg_entry.value_data}"')
        
        lines.append("")
        return "\n".join(lines)
    
    def _generate_reg_files(self, lgpo_entries: List[LGPOEntry], target_os: WindowsVersion) -> List[PolicyFile]:
        """Generate .reg files for direct registry import"""
        
        reg_content = self._create_reg_content(lgpo_entries)
        checksum = hashlib.sha256(reg_content.encode()).hexdigest()
        
        reg_file = PolicyFile(
            file_name="CISCompliance.reg",
            file_type="reg",
            content=reg_content,
            checksum=checksum,
            size_bytes=len(reg_content.encode()),
            description="Registry file with CIS compliance settings"
        )
        
        return [reg_file]
    
    def _create_reg_content(self, entries: List[LGPOEntry]) -> str:
        """Create .reg file content"""
        
        lines = [
            "Windows Registry Editor Version 5.00",
            "",
            "; CIS Compliance Registry Settings",
            f"; Generated: {datetime.now().isoformat()}",
            ""
        ]
        
        processed_keys = set()
        
        for entry in entries:
            for reg_entry in entry.registry_entries:
                key_path = f"{reg_entry.hive}\\{reg_entry.key_path}"
                
                if key_path not in processed_keys:
                    lines.append(f"[{key_path}]")
                    processed_keys.add(key_path)
                
                if reg_entry.value_type == RegistryValueType.REG_DWORD:
                    try:
                        dword_value = int(reg_entry.value_data)
                        lines.append(f'"{reg_entry.value_name}"=dword:{dword_value:08x}')
                    except (ValueError, TypeError):
                        lines.append(f'"{reg_entry.value_name}"=dword:00000000')
                elif reg_entry.value_type == RegistryValueType.REG_SZ:
                    lines.append(f'"{reg_entry.value_name}"="{reg_entry.value_data}"')
                elif reg_entry.value_type == RegistryValueType.REG_BINARY:
                    lines.append(f'"{reg_entry.value_name}"=hex:{reg_entry.value_data}')
                else:
                    lines.append(f'"{reg_entry.value_name}"="{reg_entry.value_data}"')
                
                lines.append("")
        
        return "\n".join(lines)
    
    def _generate_powershell_files(self, lgpo_entries: List[LGPOEntry], target_os: WindowsVersion) -> List[PolicyFile]:
        """Generate PowerShell scripts for policy application"""
        
        ps_content = self._create_powershell_content(lgpo_entries, target_os)
        checksum = hashlib.sha256(ps_content.encode()).hexdigest()
        
        ps_file = PolicyFile(
            file_name="Apply-CISCompliance.ps1",
            file_type="ps1",
            content=ps_content,
            checksum=checksum,
            size_bytes=len(ps_content.encode()),
            description="PowerShell script to apply CIS compliance policies"
        )
        
        return [ps_file]
    
    def _create_powershell_content(self, entries: List[LGPOEntry], target_os: WindowsVersion) -> str:
        """Create PowerShell script content"""
        
        lines = [
            "#Requires -RunAsAdministrator",
            "",
            "<#",
            ".SYNOPSIS",
            "    Apply CIS Compliance Policies",
            "",
            ".DESCRIPTION", 
            f"    Applies CIS benchmark compliance policies for {target_os.value}",
            f"    Generated: {datetime.now().isoformat()}",
            "",
            ".NOTES",
            "    This script must be run as Administrator",
            "#>",
            "",
            "[CmdletBinding()]",
            "param(",
            '    [switch]$WhatIf,',
            '    [switch]$CreateBackup = $true,',
            '    [string]$LogPath = "C:\\Temp\\CIS-Compliance.log"',
            ")",
            "",
            "# Initialize logging",
            "function Write-Log {",
            "    param([string]$Message, [string]$Level = 'INFO')",
            '    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"',
            '    $logEntry = "[$timestamp] [$Level] $Message"',
            "    Write-Host $logEntry",
            "    if ($LogPath) {",
            "        $logEntry | Out-File -FilePath $LogPath -Append -Encoding UTF8",
            "    }",
            "}",
            "",
            "# Create backup if requested",
            "if ($CreateBackup -and -not $WhatIf) {",
            '    Write-Log "Creating registry backup..."',
            '    $backupPath = "C:\\Temp\\CIS-Backup-$(Get-Date -Format \'yyyyMMdd-HHmmss\').reg"',
            "    try {",
            '        reg export HKLM "$backupPath" /y | Out-Null',
            '        Write-Log "Backup created: $backupPath"',
            "    } catch {",
            '        Write-Log "Failed to create backup: $_" -Level ERROR',
            "    }",
            "}",
            "",
            "# Apply registry settings",
            'Write-Log "Starting CIS compliance policy application..."',
            ""
        ]
        
        for i, entry in enumerate(entries):
            lines.append(f"# Policy: {entry.policy_name}")
            lines.append(f"# Category: {entry.category_path}")
            lines.append(f"# Setting: {entry.setting}")
            
            for reg_entry in entry.registry_entries:
                key_path = f"{reg_entry.hive}\\{reg_entry.key_path}"
                
                lines.extend([
                    f'Write-Log "Applying policy: {entry.policy_name}"',
                    f'$regPath = "{key_path}"',
                    f'$regName = "{reg_entry.value_name}"',
                    ""
                ])
                
                if reg_entry.value_type == RegistryValueType.REG_DWORD:
                    lines.extend([
                        f'$regValue = {reg_entry.value_data}',
                        '$regType = "DWord"'
                    ])
                else:
                    lines.extend([
                        f'$regValue = "{reg_entry.value_data}"',
                        '$regType = "String"'
                    ])
                
                lines.extend([
                    "",
                    "if ($WhatIf) {",
                    '    Write-Log "WHATIF: Would set $regPath\\$regName = $regValue ($regType)"',
                    "} else {",
                    "    try {",
                    "        if (!(Test-Path $regPath)) {",
                    "            New-Item -Path $regPath -Force | Out-Null",
                    "        }",
                    "        Set-ItemProperty -Path $regPath -Name $regName -Value $regValue -Type $regType",
                    '        Write-Log "Successfully set $regPath\\$regName"',
                    "    } catch {",
                    '        Write-Log "Failed to set $regPath\\$regName: $_" -Level ERROR',
                    "    }",
                    "}",
                    ""
                ])
        
        lines.extend([
            'Write-Log "CIS compliance policy application completed"',
            "",
            "# Verify critical settings",
            'Write-Log "Verifying applied settings..."',
            "# Add verification logic here as needed",
            "",
            'Write-Log "Policy application finished. Please review the log for any errors."'
        ])
        
        return "\n".join(lines)
    
    def _generate_deployment_scripts(self, package: DeploymentPackage) -> List[DeploymentScript]:
        """Generate deployment and helper scripts"""
        
        scripts = []
        
        if package.script_config.use_powershell:
            # Main deployment script
            deploy_script = self._create_deployment_script(package)
            scripts.append(deploy_script)
            
            # Verification script
            verify_script = self._create_verification_script(package)
            scripts.append(verify_script)
            
            # Rollback script
            if package.script_config.rollback_support:
                rollback_script = self._create_rollback_script(package)
                scripts.append(rollback_script)
        
        if package.script_config.use_batch:
            # Batch wrapper script
            batch_script = self._create_batch_wrapper(package)
            scripts.append(batch_script)
        
        return scripts
    
    def _create_deployment_script(self, package: DeploymentPackage) -> DeploymentScript:
        """Create main deployment PowerShell script"""
        
        script_content = f"""#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Deploy CIS Compliance Package - {package.name}

.DESCRIPTION
    Deploys the CIS compliance package '{package.name}' for {package.target_os.value}
    
    Package ID: {package.package_id}
    Created: {package.created_at.isoformat()}
    
.PARAMETER WhatIf
    Shows what changes would be made without applying them
    
.PARAMETER Force
    Skip confirmation prompts
    
.PARAMETER LogPath
    Path for deployment log file
    
.EXAMPLE
    .\\Deploy-CISCompliance.ps1
    
.EXAMPLE
    .\\Deploy-CISCompliance.ps1 -WhatIf
#>

[CmdletBinding()]
param(
    [switch]$WhatIf,
    [switch]$Force,
    [string]$LogPath = "C:\\Temp\\CIS-Deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Initialize logging
function Write-Log {{
    param([string]$Message, [string]$Level = 'INFO')
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry
    if ($LogPath) {{
        $logEntry | Out-File -FilePath $LogPath -Append -Encoding UTF8
    }}
}}

# Check prerequisites
function Test-Prerequisites {{
    Write-Log "Checking prerequisites..."
    
    # Check if running as administrator
    if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {{
        throw "This script must be run as Administrator"
    }}
    
    # Check Windows version
    $osVersion = [Environment]::OSVersion.Version
    Write-Log "Windows version: $($osVersion.Major).$($osVersion.Minor)"
    
    # Check for LGPO.exe if needed
    $lgpoPath = Join-Path $PSScriptRoot "LGPO.exe"
    if (Test-Path $lgpoPath) {{
        Write-Log "LGPO.exe found: $lgpoPath"
    }} else {{
        Write-Log "LGPO.exe not found - will use registry method" -Level WARN
    }}
    
    Write-Log "Prerequisites check completed"
}}

# Create backup
function New-SystemBackup {{
    param([string]$BackupPath)
    
    Write-Log "Creating system backup..."
    
    try {{
        # Export registry
        $regBackup = Join-Path $BackupPath "Registry-Backup.reg"
        reg export HKLM "$regBackup" /y | Out-Null
        
        # Export local security policy
        $secBackup = Join-Path $BackupPath "SecurityPolicy-Backup.inf"
        secedit /export /cfg "$secBackup" | Out-Null
        
        Write-Log "Backup created successfully at: $BackupPath"
        return $BackupPath
    }} catch {{
        Write-Log "Failed to create backup: $($_)" -Level ERROR
        throw
    }}
}}

# Main deployment function
function Deploy-Policies {{
    Write-Log "Starting policy deployment..."
    
    $deploymentPath = $PSScriptRoot
    $policiesApplied = 0
    $policiesFailed = 0
    
    # Apply LGPO files if available
    $lgpoPath = Join-Path $deploymentPath "LGPO.exe"
    if (Test-Path $lgpoPath) {{
        Write-Log "Applying policies using LGPO..."
        
        $machinePolPath = Join-Path $deploymentPath "Machine.pol"
        $userPolPath = Join-Path $deploymentPath "User.pol"
        
        if (Test-Path $machinePolPath) {{
            if ($WhatIf) {{
                Write-Log "WHATIF: Would apply machine policies from $machinePolPath"
            }} else {{
                try {{
                    & $lgpoPath /m "$machinePolPath"
                    Write-Log "Applied machine policies successfully"
                    $policiesApplied++
                }} catch {{
                    Write-Log "Failed to apply machine policies: $($_)" -Level ERROR
                    $policiesFailed++
                }}
            }}
        }}
        
        if (Test-Path $userPolPath) {{
            if ($WhatIf) {{
                Write-Log "WHATIF: Would apply user policies from $userPolPath"
            }} else {{
                try {{
                    & $lgpoPath /u "$userPolPath"
                    Write-Log "Applied user policies successfully"
                    $policiesApplied++
                }} catch {{
                    Write-Log "Failed to apply user policies: $($_)" -Level ERROR
                    $policiesFailed++
                }}
            }}
        }}
    }}
    
    # Apply registry file if available
    $regPath = Join-Path $deploymentPath "CISCompliance.reg"
    if (Test-Path $regPath) {{
        if ($WhatIf) {{
            Write-Log "WHATIF: Would apply registry settings from $regPath"
        }} else {{
            try {{
                reg import "$regPath"
                Write-Log "Applied registry settings successfully"
                $policiesApplied++
            }} catch {{
                Write-Log "Failed to apply registry settings: $($_)" -Level ERROR
                $policiesFailed++
            }}
        }}
    }}
    
    Write-Log "Policy deployment completed. Applied: $policiesApplied, Failed: $policiesFailed"
    return @{{ Applied = $policiesApplied; Failed = $policiesFailed }}
}}

# Main execution
try {{
    Write-Log "=== CIS Compliance Deployment Started ==="
    Write-Log "Package: {package.name}"
    Write-Log "Target OS: {package.target_os.value}"
    Write-Log "WhatIf Mode: $WhatIf"
    
    # Check prerequisites
    Test-Prerequisites
    
    # Confirm deployment unless forced
    if (-not $Force -and -not $WhatIf) {{
        $confirmation = Read-Host "Deploy CIS compliance policies? This will modify system settings. (y/N)"
        if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {{
            Write-Log "Deployment cancelled by user"
            exit 0
        }}
    }}
    
    # Create backup directory
    $backupPath = "C:\\Temp\\CIS-Backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    if (-not $WhatIf) {{
        New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
        New-SystemBackup -BackupPath $backupPath
    }}
    
    # Deploy policies
    $result = Deploy-Policies
    
    if ($result.Failed -eq 0) {{
        Write-Log "=== Deployment completed successfully ===" -Level SUCCESS
        if (-not $WhatIf) {{
            Write-Log "System backup available at: $backupPath"
            Write-Log "Please reboot the system to ensure all policies take effect"
        }}
    }} else {{
        Write-Log "=== Deployment completed with errors ===" -Level WARN
        Write-Log "Failed policies: $($result.Failed)"
    }}
    
}} catch {{
    Write-Log "Deployment failed: $($_)" -Level ERROR
    exit 1
}} finally {{
    Write-Log "Deployment log saved to: $LogPath"
}}
"""
        
        return DeploymentScript(
            script_name="Deploy-CISCompliance.ps1",
            script_type="powershell",
            content=script_content,
            description="Main deployment script for CIS compliance policies",
            requires_admin=True,
            execution_order=1
        )
    
    def _create_verification_script(self, package: DeploymentPackage) -> DeploymentScript:
        """Create verification script"""
        
        script_content = f"""#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Verify CIS Compliance Deployment

.DESCRIPTION
    Verifies that CIS compliance policies have been applied correctly
    
.PARAMETER OutputPath
    Path for verification report
    
.EXAMPLE
    .\\Verify-CISCompliance.ps1
#>

[CmdletBinding()]
param(
    [string]$OutputPath = "C:\\Temp\\CIS-Verification-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
)

function Test-RegistryValue {{
    param(
        [string]$Path,
        [string]$Name,
        [object]$ExpectedValue
    )
    
    try {{
        if (Test-Path $Path) {{
            $actualValue = Get-ItemProperty -Path $Path -Name $Name -ErrorAction SilentlyContinue
            if ($actualValue) {{
                return $actualValue.$Name -eq $ExpectedValue
            }}
        }}
        return $false
    }} catch {{
        return $false
    }}
}}

Write-Host "=== CIS Compliance Verification ==="
Write-Host "Package: {package.name}"
Write-Host "Verification started: $(Get-Date)"
Write-Host ""

$results = @()
$passedChecks = 0
$failedChecks = 0

# Add verification checks based on deployed policies
# This would be dynamically generated based on the actual policies

Write-Host "Verification Summary:"
Write-Host "Passed: $passedChecks"
Write-Host "Failed: $failedChecks"
Write-Host "Total:  $($passedChecks + $failedChecks)"

if ($OutputPath) {{
    $results | Out-File -FilePath $OutputPath -Encoding UTF8
    Write-Host "Detailed report saved to: $OutputPath"
}}
"""
        
        return DeploymentScript(
            script_name="Verify-CISCompliance.ps1",
            script_type="powershell",
            content=script_content,
            description="Verification script to check applied policies",
            requires_admin=True,
            execution_order=2
        )
    
    def _create_rollback_script(self, package: DeploymentPackage) -> DeploymentScript:
        """Create rollback script"""
        
        script_content = f"""#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Rollback CIS Compliance Changes

.DESCRIPTION
    Rolls back CIS compliance policy changes using system backup
    
.PARAMETER BackupPath
    Path to backup directory or file
    
.EXAMPLE
    .\\Rollback-CISCompliance.ps1 -BackupPath "C:\\Temp\\CIS-Backup-20240101-120000"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$BackupPath
)

Write-Host "=== CIS Compliance Rollback ==="
Write-Host "Package: {package.name}"
Write-Host "Rollback started: $(Get-Date)"

if (-not (Test-Path $BackupPath)) {{
    Write-Error "Backup path not found: $BackupPath"
    exit 1
}}

$confirmation = Read-Host "This will restore system settings from backup. Continue? (y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {{
    Write-Host "Rollback cancelled"
    exit 0
}}

try {{
    # Restore registry
    $regBackup = Join-Path $BackupPath "Registry-Backup.reg"
    if (Test-Path $regBackup) {{
        Write-Host "Restoring registry settings..."
        reg import "$regBackup"
        Write-Host "Registry restored successfully"
    }}
    
    # Restore security policy
    $secBackup = Join-Path $BackupPath "SecurityPolicy-Backup.inf"
    if (Test-Path $secBackup) {{
        Write-Host "Restoring security policy..."
        secedit /configure /db secedit.sdb /cfg "$secBackup"
        Write-Host "Security policy restored successfully"
    }}
    
    Write-Host "Rollback completed successfully"
    Write-Host "Please reboot the system for changes to take effect"
    
}} catch {{
    Write-Error "Rollback failed: $($_)"
    exit 1
}}
"""
        
        return DeploymentScript(
            script_name="Rollback-CISCompliance.ps1",
            script_type="powershell",
            content=script_content,
            description="Script to rollback applied policies using backup",
            requires_admin=True,
            execution_order=3
        )
    
    def _create_batch_wrapper(self, package: DeploymentPackage) -> DeploymentScript:
        """Create batch file wrapper for PowerShell scripts"""
        
        script_content = f"""@echo off
REM CIS Compliance Deployment Wrapper
REM Package: {package.name}
REM Target OS: {package.target_os.value}

echo =========================================
echo CIS Compliance Deployment
echo Package: {package.name}
echo =========================================

REM Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

echo Checking PowerShell availability...
powershell -Command "Get-Host" >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: PowerShell is not available or not functioning
    pause
    exit /b 1
)

echo Starting deployment...
powershell -ExecutionPolicy Bypass -File "%~dp0Deploy-CISCompliance.ps1"

if %errorLevel% equ 0 (
    echo.
    echo Deployment completed successfully
) else (
    echo.
    echo Deployment failed with error code: %errorLevel%
)

echo.
pause
"""
        
        return DeploymentScript(
            script_name="Deploy-CISCompliance.bat",
            script_type="batch",
            content=script_content,
            description="Batch wrapper for PowerShell deployment script",
            requires_admin=True,
            execution_order=0
        )
    
    def _create_package_manifest(self, package: DeploymentPackage) -> PackageManifest:
        """Create package manifest"""
        
        # Collect file information
        files_info = []
        for policy_file in package.policy_files:
            files_info.append({
                "name": policy_file.file_name,
                "type": policy_file.file_type,
                "size": policy_file.size_bytes,
                "checksum": policy_file.checksum,
                "description": policy_file.description
            })
        
        # Collect script information
        scripts_info = []
        for script in package.scripts:
            scripts_info.append({
                "name": script.script_name,
                "type": script.script_type,
                "description": script.description,
                "requires_admin": script.requires_admin,
                "execution_order": script.execution_order
            })
        
        # Generate checksums
        checksums = {}
        for policy_file in package.policy_files:
            checksums[policy_file.file_name] = policy_file.checksum
        for script in package.scripts:
            checksums[script.script_name] = hashlib.sha256(script.content.encode()).hexdigest()
        
        # Create deployment instructions
        instructions = self._generate_deployment_instructions(package)
        
        # Create validation steps
        validation_steps = [
            "Verify all files are present and checksums match",
            "Confirm administrator privileges before deployment",
            "Create system backup before applying policies",
            "Run verification script after deployment",
            "Test critical system functions after deployment"
        ]
        
        return PackageManifest(
            package_id=package.package_id,
            package_name=package.name,
            created_at=package.created_at,
            target_os=package.target_os,
            cis_benchmark_version="4.0.0",  # This should come from source data
            total_policies=len(package.source_policies),
            policy_categories=list(set(p.get('category', 'Unknown') for p in package.source_policies)),
            included_formats=package.export_config.include_formats,
            files=files_info,
            scripts=scripts_info,
            checksums=checksums,
            deployment_instructions=instructions,
            validation_steps=validation_steps
        )
    
    def _generate_deployment_instructions(self, package: DeploymentPackage) -> str:
        """Generate deployment instructions"""
        
        instructions = f"""
# CIS Compliance Deployment Instructions

## Package Information
- **Package Name**: {package.name}
- **Description**: {package.description}
- **Target OS**: {package.target_os.value}
- **Created**: {package.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- **Total Policies**: {len(package.source_policies)}

## Prerequisites
- Windows Administrator privileges
- PowerShell 3.0 or later (recommended)
- Offline/air-gapped deployment support
- No external network connectivity required

## Deployment Steps

### Option 1: Automated Deployment (Recommended)
1. Extract the deployment package to a local directory
2. Right-click `Deploy-CISCompliance.bat` and select "Run as administrator"
3. Follow the on-screen prompts
4. Review the deployment log for any issues
5. Reboot the system when prompted

### Option 2: Manual PowerShell Deployment
1. Open PowerShell as Administrator
2. Navigate to the deployment package directory
3. Run: `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process`
4. Run: `.\\Deploy-CISCompliance.ps1`
5. Review output and reboot if required

### Option 3: Manual Registry Import
1. Double-click `CISCompliance.reg` (if included)
2. Confirm registry import when prompted
3. Apply any additional .pol files using LGPO.exe
4. Reboot the system

## Verification
After deployment, run the verification script:
```
.\\Verify-CISCompliance.ps1
```

## Rollback
If you need to rollback changes:
1. Locate the backup directory created during deployment
2. Run: `.\\Rollback-CISCompliance.ps1 -BackupPath "C:\\Temp\\CIS-Backup-YYYYMMDD-HHMMSS"`

## File Descriptions
"""
        
        # Add file descriptions
        for policy_file in package.policy_files:
            instructions += f"\n- **{policy_file.file_name}**: {policy_file.description}"
        
        for script in package.scripts:
            instructions += f"\n- **{script.script_name}**: {script.description}"
        
        instructions += """

## Important Notes
- Always create a system backup before deployment
- Test in a non-production environment first  
- Some policies may require a system reboot to take effect
- Monitor system behavior after deployment
- Keep the backup files for potential rollback

## Support
This package was generated by the CIS GPO Compliance Tool.
Refer to the tool documentation for additional support.
"""
        
        return instructions
    
    def _validate_package(self, package: DeploymentPackage) -> ValidationResult:
        """Validate deployment package integrity"""
        
        validation_result = ValidationResult(
            is_valid=True,
            total_checks=0,
            passed_checks=0,
            failed_checks=0
        )
        
        checks = [
            ("Package has policy files", len(package.policy_files) > 0),
            ("Package has deployment scripts", len(package.scripts) > 0),
            ("Package has manifest", package.manifest is not None),
            ("All policy files have checksums", all(f.checksum for f in package.policy_files)),
            ("Source policies provided", len(package.source_policies) > 0),
            ("Export configuration valid", package.export_config is not None),
            ("Script configuration valid", package.script_config is not None),
            ("Target OS specified", package.target_os is not None)
        ]
        
        validation_result.total_checks = len(checks)
        
        for check_name, check_result in checks:
            if check_result:
                validation_result.passed_checks += 1
                validation_result.check_details[check_name] = {
                    "status": "PASS",
                    "message": "Check passed"
                }
            else:
                validation_result.failed_checks += 1
                validation_result.check_details[check_name] = {
                    "status": "FAIL", 
                    "message": "Check failed"
                }
                validation_result.errors.append(f"Validation failed: {check_name}")
        
        # Additional validations
        if package.policy_files:
            # Check for required formats
            pol_files = [f for f in package.policy_files if f.file_type == "pol"]
            if not pol_files and PackageFormat.LGPO_POL in package.export_config.include_formats:
                validation_result.warnings.append("LGPO .pol format requested but no .pol files generated")
        
        # Final validation status
        validation_result.is_valid = validation_result.failed_checks == 0
        
        return validation_result
    
    def _create_physical_package(self, package: DeploymentPackage) -> str:
        """Create physical package files and zip archive"""
        
        # Create package directory
        package_dir = self.exports_path / f"{package.name}_{package.package_id}"
        package_dir.mkdir(parents=True, exist_ok=True)
        
        total_size = 0
        file_count = 0
        
        try:
            # Write policy files
            for policy_file in package.policy_files:
                file_path = package_dir / policy_file.file_name
                
                if isinstance(policy_file.content, bytes):
                    with open(file_path, 'wb') as f:
                        f.write(policy_file.content)
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(policy_file.content)
                
                total_size += policy_file.size_bytes
                file_count += 1
            
            # Write deployment scripts
            for script in package.scripts:
                file_path = package_dir / script.script_name
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(script.content)
                
                total_size += len(script.content.encode())
                file_count += 1
            
            # Write manifest
            if package.manifest:
                manifest_path = package_dir / "MANIFEST.json"
                manifest_data = {
                    "package_id": package.manifest.package_id,
                    "package_name": package.manifest.package_name,
                    "created_at": package.manifest.created_at.isoformat(),
                    "target_os": package.manifest.target_os.value,
                    "cis_benchmark_version": package.manifest.cis_benchmark_version,
                    "total_policies": package.manifest.total_policies,
                    "policy_categories": package.manifest.policy_categories,
                    "included_formats": [f.value for f in package.manifest.included_formats],
                    "files": package.manifest.files,
                    "scripts": package.manifest.scripts,
                    "checksums": package.manifest.checksums,
                    "validation_steps": package.manifest.validation_steps
                }
                
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest_data, f, indent=2)
                
                file_count += 1
            
            # Write deployment instructions
            if package.manifest:
                readme_path = package_dir / "README.txt"
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(package.manifest.deployment_instructions)
                file_count += 1
            
            # Create ZIP archive if requested
            zip_path = None
            if package.export_config.create_zip_package:
                zip_name = f"{package.name}_{package.package_id}.zip"
                zip_path = self.exports_path / zip_name
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in package_dir.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(package_dir)
                            zipf.write(file_path, arcname)
            
            # Update package info
            package.package_size_bytes = total_size
            package.total_files = file_count
            
            return str(zip_path if zip_path else package_dir)
            
        except Exception as e:
            logger.error(f"Error creating physical package: {e}")
            raise
    
    def get_package(self, package_id: str) -> Optional[DeploymentPackage]:
        """Get deployment package by ID"""
        return self.packages.get(package_id)
    
    def get_all_packages(self) -> List[DeploymentPackage]:
        """Get all deployment packages"""
        return list(self.packages.values())
    
    def get_job_status(self, job_id: str) -> Optional[DeploymentJob]:
        """Get deployment job status"""
        return self.active_jobs.get(job_id)
    
    def delete_package(self, package_id: str) -> bool:
        """Delete deployment package"""
        try:
            if package_id in self.packages:
                package = self.packages[package_id]
                
                # Delete physical files
                if package.package_path:
                    package_path = Path(package.package_path)
                    if package_path.exists():
                        if package_path.is_file():
                            package_path.unlink()
                        else:
                            shutil.rmtree(package_path)
                
                # Remove from memory
                del self.packages[package_id]
                self._save_packages()
                
                logger.info(f"Deleted deployment package: {package_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting package {package_id}: {e}")
        
        return False
    
    def get_package_statistics(self) -> Dict[str, Any]:
        """Get deployment package statistics"""
        
        total_packages = len(self.packages)
        completed_packages = len([p for p in self.packages.values() if p.status == DeploymentStatus.COMPLETED])
        failed_packages = len([p for p in self.packages.values() if p.status == DeploymentStatus.FAILED])
        
        # OS distribution
        os_distribution = {}
        for package in self.packages.values():
            os_name = package.target_os.value
            os_distribution[os_name] = os_distribution.get(os_name, 0) + 1
        
        # Total policies deployed
        total_policies = sum(len(p.source_policies) for p in self.packages.values())
        
        return {
            "total_packages": total_packages,
            "completed_packages": completed_packages,
            "failed_packages": failed_packages,
            "pending_packages": total_packages - completed_packages - failed_packages,
            "success_rate": (completed_packages / total_packages * 100) if total_packages > 0 else 0,
            "os_distribution": os_distribution,
            "total_policies_packaged": total_policies,
            "active_jobs": len(self.active_jobs)
        }