"""
Data models for automated remediation and rollback system
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import json


class RemediationStatus(Enum):
    """Remediation operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIALLY_COMPLETED = "partially_completed"


class RemediationType(Enum):
    """Types of remediation actions"""
    REGISTRY_CHANGE = "registry_change"
    GROUP_POLICY = "group_policy"
    LOCAL_POLICY = "local_policy"
    SECURITY_SETTING = "security_setting"
    SERVICE_CONFIG = "service_config"
    FILE_PERMISSION = "file_permission"
    USER_RIGHT = "user_right"
    AUDIT_POLICY = "audit_policy"
    FIREWALL_RULE = "firewall_rule"
    CUSTOM_SCRIPT = "custom_script"


class RemediationSeverity(Enum):
    """Severity levels for remediation actions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BackupType(Enum):
    """Types of system backups"""
    FULL_SYSTEM = "full_system"
    REGISTRY_ONLY = "registry_only"
    GROUP_POLICY = "group_policy"
    SECURITY_SETTINGS = "security_settings"
    SELECTIVE = "selective"


class RollbackStatus(Enum):
    """Rollback operation status"""
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CORRUPTED = "corrupted"


@dataclass
class SystemBackup:
    """Represents a system backup point"""
    backup_id: str
    name: str
    description: str
    backup_type: BackupType
    created_at: datetime
    created_by: str
    size_bytes: int
    backup_path: str
    
    # What was backed up
    affected_policies: List[str] = field(default_factory=list)
    affected_registry_keys: List[str] = field(default_factory=list)
    affected_gpos: List[str] = field(default_factory=list)
    
    # Backup metadata
    system_info: Dict[str, Any] = field(default_factory=dict)
    checksum: Optional[str] = None
    compression_used: bool = True
    encryption_used: bool = False
    
    # Status
    status: RollbackStatus = RollbackStatus.AVAILABLE
    expiry_date: Optional[datetime] = None
    validation_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RemediationAction:
    """Represents a single remediation action"""
    action_id: str
    policy_id: str
    policy_title: str
    remediation_type: RemediationType
    severity: RemediationSeverity
    
    # Current and target values
    current_value: Optional[str] = None
    target_value: Optional[str] = None
    registry_key: Optional[str] = None
    registry_value: Optional[str] = None
    
    # Action details
    description: str = ""
    command: Optional[str] = None
    script_content: Optional[str] = None
    requires_reboot: bool = False
    
    # Risk assessment
    risk_level: str = "medium"
    impact_description: str = ""
    reversible: bool = True
    
    # Status
    status: RemediationStatus = RemediationStatus.PENDING
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None
    execution_time_seconds: Optional[float] = None


@dataclass
class RemediationPlan:
    """Represents a complete remediation plan"""
    plan_id: str
    name: str
    description: str
    created_at: datetime
    created_by: str
    
    # Source audit information
    source_audit_id: str
    target_system: str
    
    # Actions to perform
    actions: List[RemediationAction] = field(default_factory=list)
    
    # Configuration
    create_backup: bool = True
    backup_type: BackupType = BackupType.SELECTIVE
    require_confirmation: bool = True
    continue_on_error: bool = False
    
    # Execution settings
    max_parallel_actions: int = 3
    timeout_minutes: int = 60
    retry_failed_actions: bool = True
    max_retries: int = 3
    
    # Status
    status: RemediationStatus = RemediationStatus.PENDING
    progress_percentage: int = 0
    current_action: Optional[str] = None
    
    # Results
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    skipped_actions: int = 0
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    # Associated backup
    backup_id: Optional[str] = None


@dataclass
class RemediationResult:
    """Results of a remediation operation"""
    result_id: str
    plan_id: str
    action_id: str
    
    # Execution details
    executed_at: datetime
    executed_by: str
    execution_time_seconds: float
    
    # Results
    success: bool
    status_before: Optional[str] = None
    status_after: Optional[str] = None
    changes_made: List[str] = field(default_factory=list)
    
    # Error handling
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retry_count: int = 0
    
    # Verification
    verification_passed: bool = False
    verification_details: Dict[str, Any] = field(default_factory=dict)
    
    # Rollback information
    rollback_required: bool = False
    rollback_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RemediationSession:
    """Represents an active remediation session"""
    session_id: str
    plan_id: str
    operator: str
    start_time: datetime
    
    # Current state
    current_phase: str = "initialization"
    current_action_index: int = 0
    progress_percentage: int = 0
    
    # Results tracking
    completed_actions: List[str] = field(default_factory=list)
    failed_actions: List[str] = field(default_factory=list)
    pending_actions: List[str] = field(default_factory=list)
    
    # Logs
    log_messages: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    
    # Status
    status: RemediationStatus = RemediationStatus.PENDING
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class RollbackPlan:
    """Plan for rolling back changes"""
    rollback_id: str
    name: str
    description: str
    backup_id: str
    created_at: datetime
    created_by: str
    
    # Target information
    target_system: str
    rollback_scope: List[str] = field(default_factory=list)  # What to rollback
    
    # Configuration
    selective_rollback: bool = False
    selected_policies: List[str] = field(default_factory=list)
    verify_before_rollback: bool = True
    create_pre_rollback_backup: bool = True
    
    # Execution settings
    timeout_minutes: int = 30
    require_confirmation: bool = True
    
    # Status
    status: RemediationStatus = RemediationStatus.PENDING
    progress_percentage: int = 0
    
    # Results
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    
    # Verification
    verification_results: Dict[str, Any] = field(default_factory=dict)


# Serialization functions
def serialize_system_backup(backup: SystemBackup) -> Dict[str, Any]:
    """Serialize system backup for JSON storage"""
    return {
        "backup_id": backup.backup_id,
        "name": backup.name,
        "description": backup.description,
        "backup_type": backup.backup_type.value,
        "created_at": backup.created_at.isoformat(),
        "created_by": backup.created_by,
        "size_bytes": backup.size_bytes,
        "backup_path": backup.backup_path,
        "affected_policies": backup.affected_policies,
        "affected_registry_keys": backup.affected_registry_keys,
        "affected_gpos": backup.affected_gpos,
        "system_info": backup.system_info,
        "checksum": backup.checksum,
        "compression_used": backup.compression_used,
        "encryption_used": backup.encryption_used,
        "status": backup.status.value,
        "expiry_date": backup.expiry_date.isoformat() if backup.expiry_date else None,
        "validation_results": backup.validation_results
    }


def deserialize_system_backup(data: Dict[str, Any]) -> SystemBackup:
    """Deserialize system backup from JSON"""
    return SystemBackup(
        backup_id=data["backup_id"],
        name=data["name"],
        description=data["description"],
        backup_type=BackupType(data["backup_type"]),
        created_at=datetime.fromisoformat(data["created_at"]),
        created_by=data["created_by"],
        size_bytes=data["size_bytes"],
        backup_path=data["backup_path"],
        affected_policies=data.get("affected_policies", []),
        affected_registry_keys=data.get("affected_registry_keys", []),
        affected_gpos=data.get("affected_gpos", []),
        system_info=data.get("system_info", {}),
        checksum=data.get("checksum"),
        compression_used=data.get("compression_used", True),
        encryption_used=data.get("encryption_used", False),
        status=RollbackStatus(data.get("status", "available")),
        expiry_date=datetime.fromisoformat(data["expiry_date"]) if data.get("expiry_date") else None,
        validation_results=data.get("validation_results", {})
    )


def serialize_remediation_plan(plan: RemediationPlan) -> Dict[str, Any]:
    """Serialize remediation plan for JSON storage"""
    return {
        "plan_id": plan.plan_id,
        "name": plan.name,
        "description": plan.description,
        "created_at": plan.created_at.isoformat(),
        "created_by": plan.created_by,
        "source_audit_id": plan.source_audit_id,
        "target_system": plan.target_system,
        "actions": [serialize_remediation_action(action) for action in plan.actions],
        "create_backup": plan.create_backup,
        "backup_type": plan.backup_type.value,
        "require_confirmation": plan.require_confirmation,
        "continue_on_error": plan.continue_on_error,
        "max_parallel_actions": plan.max_parallel_actions,
        "timeout_minutes": plan.timeout_minutes,
        "retry_failed_actions": plan.retry_failed_actions,
        "max_retries": plan.max_retries,
        "status": plan.status.value,
        "progress_percentage": plan.progress_percentage,
        "current_action": plan.current_action,
        "total_actions": plan.total_actions,
        "successful_actions": plan.successful_actions,
        "failed_actions": plan.failed_actions,
        "skipped_actions": plan.skipped_actions,
        "start_time": plan.start_time.isoformat() if plan.start_time else None,
        "end_time": plan.end_time.isoformat() if plan.end_time else None,
        "estimated_completion": plan.estimated_completion.isoformat() if plan.estimated_completion else None,
        "backup_id": plan.backup_id
    }


def serialize_remediation_action(action: RemediationAction) -> Dict[str, Any]:
    """Serialize remediation action for JSON storage"""
    return {
        "action_id": action.action_id,
        "policy_id": action.policy_id,
        "policy_title": action.policy_title,
        "remediation_type": action.remediation_type.value,
        "severity": action.severity.value,
        "current_value": action.current_value,
        "target_value": action.target_value,
        "registry_key": action.registry_key,
        "registry_value": action.registry_value,
        "description": action.description,
        "command": action.command,
        "script_content": action.script_content,
        "requires_reboot": action.requires_reboot,
        "risk_level": action.risk_level,
        "impact_description": action.impact_description,
        "reversible": action.reversible,
        "status": action.status.value,
        "error_message": action.error_message,
        "executed_at": action.executed_at.isoformat() if action.executed_at else None,
        "execution_time_seconds": action.execution_time_seconds
    }


def validate_remediation_plan(plan: RemediationPlan) -> List[str]:
    """Validate remediation plan for consistency and safety"""
    errors = []
    
    if not plan.actions:
        errors.append("Remediation plan must have at least one action")
    
    if not plan.source_audit_id:
        errors.append("Source audit ID is required")
    
    if not plan.target_system:
        errors.append("Target system is required")
    
    # Validate individual actions
    for i, action in enumerate(plan.actions):
        if not action.policy_id:
            errors.append(f"Action {i+1}: Policy ID is required")
        
        if action.remediation_type == RemediationType.REGISTRY_CHANGE:
            if not action.registry_key:
                errors.append(f"Action {i+1}: Registry key is required for registry changes")
        
        if action.severity == RemediationSeverity.CRITICAL and not action.reversible:
            errors.append(f"Action {i+1}: Critical actions must be reversible")
    
    # Check for conflicting actions
    registry_keys = []
    for action in plan.actions:
        if action.remediation_type == RemediationType.REGISTRY_CHANGE and action.registry_key:
            if action.registry_key in registry_keys:
                errors.append(f"Multiple actions affect the same registry key: {action.registry_key}")
            registry_keys.append(action.registry_key)
    
    return errors