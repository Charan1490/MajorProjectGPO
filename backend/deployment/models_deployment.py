"""
Deployment Models for CIS GPO Compliance Tool
Handles data structures for offline GPO deployment and packaging
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class WindowsVersion(Enum):
    """Supported Windows versions for deployment"""
    WINDOWS_10_PRO = "windows_10_pro"
    WINDOWS_10_ENTERPRISE = "windows_10_enterprise"
    WINDOWS_11_PRO = "windows_11_pro"
    WINDOWS_11_ENTERPRISE = "windows_11_enterprise"
    WINDOWS_SERVER_2019 = "windows_server_2019"
    WINDOWS_SERVER_2022 = "windows_server_2022"


class DeploymentStatus(Enum):
    """Deployment package status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"


class PackageFormat(Enum):
    """Supported package formats"""
    LGPO_POL = "lgpo_pol"  # LGPO .pol files
    LGPO_INF = "lgpo_inf"  # LGPO .inf files
    REGISTRY_REG = "registry_reg"  # Registry .reg files
    POWERSHELL_PS1 = "powershell_ps1"  # PowerShell scripts
    BATCH_BAT = "batch_bat"  # Batch scripts


@dataclass
class PolicyExportConfig:
    """Configuration for policy export"""
    target_os: WindowsVersion
    include_formats: List[PackageFormat]
    include_scripts: bool = True
    include_documentation: bool = True
    include_verification: bool = True
    create_zip_package: bool = True
    package_name: Optional[str] = None
    export_path: Optional[str] = None
    
    
@dataclass
class ScriptConfiguration:
    """Configuration for deployment scripts"""
    use_powershell: bool = True
    use_batch: bool = True
    require_admin: bool = True
    create_backup: bool = True
    verify_before_apply: bool = True
    log_changes: bool = True
    rollback_support: bool = True


@dataclass
class PolicyFile:
    """Represents a single policy file for deployment"""
    file_name: str
    file_type: str
    content: Union[str, bytes]
    checksum: str
    size_bytes: int
    registry_path: Optional[str] = None
    policy_category: Optional[str] = None
    description: Optional[str] = None


@dataclass
class DeploymentScript:
    """Represents a deployment script"""
    script_name: str
    script_type: str  # powershell, batch, etc.
    content: str
    description: str
    requires_admin: bool = True
    execution_order: int = 0


@dataclass
class PackageManifest:
    """Manifest file for deployment package"""
    package_id: str
    package_name: str
    created_at: datetime
    target_os: WindowsVersion
    cis_benchmark_version: str
    total_policies: int
    policy_categories: List[str]
    included_formats: List[PackageFormat]
    files: List[Dict[str, Any]]
    scripts: List[Dict[str, Any]]
    checksums: Dict[str, str]
    deployment_instructions: str
    validation_steps: List[str]


@dataclass
class DeploymentPackage:
    """Complete deployment package"""
    package_id: str
    name: str
    description: str
    target_os: WindowsVersion
    status: DeploymentStatus
    created_at: datetime
    updated_at: datetime
    
    # Configuration
    export_config: PolicyExportConfig
    script_config: ScriptConfiguration
    
    # Content
    policy_files: List[PolicyFile] = field(default_factory=list)
    scripts: List[DeploymentScript] = field(default_factory=list)
    manifest: Optional[PackageManifest] = None
    
    # Package info
    package_path: Optional[str] = None
    package_size_bytes: int = 0
    total_files: int = 0
    
    # Validation
    validation_results: Dict[str, Any] = field(default_factory=dict)
    integrity_verified: bool = False
    
    # Source data
    source_policies: List[Dict[str, Any]] = field(default_factory=list)
    source_groups: List[str] = field(default_factory=list)
    source_tags: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Results from package validation"""
    is_valid: bool
    total_checks: int
    passed_checks: int
    failed_checks: int
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    check_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    validation_time: datetime = field(default_factory=datetime.now)


@dataclass
class DeploymentJob:
    """Represents a deployment job in progress"""
    job_id: str
    package_id: str
    status: DeploymentStatus
    progress: int  # 0-100
    current_step: str
    total_steps: int
    completed_steps: int
    start_time: datetime
    end_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    log_messages: List[str] = field(default_factory=list)


class RegistryValueType(Enum):
    """Registry value types"""
    REG_SZ = "REG_SZ"
    REG_DWORD = "REG_DWORD" 
    REG_BINARY = "REG_BINARY"
    REG_EXPAND_SZ = "REG_EXPAND_SZ"
    REG_MULTI_SZ = "REG_MULTI_SZ"


@dataclass
class RegistryEntry:
    """Registry entry for policy application"""
    hive: str  # HKLM, HKCU, etc.
    key_path: str
    value_name: str
    value_type: RegistryValueType
    value_data: Any
    description: str
    policy_id: str
    category: str


@dataclass
class LGPOEntry:
    """LGPO-compatible policy entry"""
    section: str  # Computer Configuration, User Configuration
    category_path: str  # Administrative Templates/System/etc.
    policy_name: str
    setting: str  # Enabled, Disabled, or configured value
    registry_entries: List[RegistryEntry] = field(default_factory=list)
    description: Optional[str] = None
    policy_id: Optional[str] = None


# Utility functions for model serialization
def serialize_deployment_package(package: DeploymentPackage) -> Dict[str, Any]:
    """Serialize deployment package to dictionary"""
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
        "script_config": {
            "use_powershell": package.script_config.use_powershell,
            "use_batch": package.script_config.use_batch,
            "require_admin": package.script_config.require_admin,
            "create_backup": package.script_config.create_backup,
            "verify_before_apply": package.script_config.verify_before_apply,
            "log_changes": package.script_config.log_changes,
            "rollback_support": package.script_config.rollback_support
        },
        "package_path": package.package_path,
        "package_size_bytes": package.package_size_bytes,
        "total_files": package.total_files,
        "validation_results": package.validation_results,
        "integrity_verified": package.integrity_verified,
        "source_groups": package.source_groups,
        "source_tags": package.source_tags
    }


def deserialize_deployment_package(data: Dict[str, Any]) -> DeploymentPackage:
    """Deserialize dictionary to deployment package"""
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
    
    script_config = ScriptConfiguration(
        use_powershell=data["script_config"]["use_powershell"],
        use_batch=data["script_config"]["use_batch"],
        require_admin=data["script_config"]["require_admin"],
        create_backup=data["script_config"]["create_backup"],
        verify_before_apply=data["script_config"]["verify_before_apply"],
        log_changes=data["script_config"]["log_changes"],
        rollback_support=data["script_config"]["rollback_support"]
    )
    
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
        source_tags=data.get("source_tags", [])
    )