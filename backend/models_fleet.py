"""
Fleet Management Models - Phase 1: Central Deployment Server
Handles machine registration, status tracking, and fleet operations
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class MachineStatus(str, Enum):
    """Machine connection status"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEPLOYING = "deploying"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DeploymentPhase(str, Enum):
    """Deployment execution phases"""
    PENDING = "pending"
    VALIDATING = "validating"
    BACKING_UP = "backing_up"
    APPLYING = "applying"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class AgentCapability(str, Enum):
    """Agent feature capabilities"""
    REGISTRY_EDIT = "registry_edit"
    GPO_APPLY = "gpo_apply"
    POWERSHELL = "powershell"
    BACKUP_RESTORE = "backup_restore"
    COMPLIANCE_SCAN = "compliance_scan"


class Machine(BaseModel):
    """Registered machine in the fleet"""
    machine_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hostname: str
    ip_address: str
    os_version: str
    os_build: Optional[str] = None
    agent_version: str
    capabilities: List[AgentCapability] = []
    
    # Status tracking
    status: MachineStatus = MachineStatus.OFFLINE
    last_seen: datetime = Field(default_factory=datetime.now)
    registered_at: datetime = Field(default_factory=datetime.now)
    
    # Compliance metrics
    compliance_score: Optional[float] = None
    policies_applied: int = 0
    policies_failed: int = 0
    last_deployment: Optional[str] = None
    
    # System info
    cpu_usage: Optional[float] = None
    memory_total: Optional[int] = None
    memory_used: Optional[int] = None
    disk_free: Optional[int] = None
    
    # Tags and grouping
    tags: List[str] = []
    groups: List[str] = []
    location: Optional[str] = None
    department: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "hostname": "WIN-PROD-001",
                "ip_address": "192.168.1.100",
                "os_version": "Windows 11 Pro",
                "os_build": "22621.963",
                "agent_version": "1.0.0",
                "status": "online",
                "compliance_score": 85.5,
                "tags": ["production", "finance"],
                "groups": ["domain-controllers"]
            }
        }


class MachineRegistration(BaseModel):
    """Agent registration request"""
    hostname: str
    ip_address: str
    os_version: str
    os_build: Optional[str] = None
    agent_version: str
    capabilities: List[AgentCapability] = []
    
    # Optional metadata
    tags: List[str] = []
    location: Optional[str] = None
    department: Optional[str] = None


class MachineHeartbeat(BaseModel):
    """Agent heartbeat/status update"""
    machine_id: str
    status: MachineStatus = MachineStatus.ONLINE
    
    # Performance metrics
    cpu_usage: Optional[float] = None
    memory_used: Optional[int] = None
    disk_free: Optional[int] = None
    
    # Compliance info
    compliance_score: Optional[float] = None
    policies_applied: Optional[int] = None
    policies_failed: Optional[int] = None


class RemoteDeployment(BaseModel):
    """Remote deployment job configuration"""
    deployment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    
    # Policy selection
    policy_package_id: Optional[str] = None
    policy_ids: Optional[List[str]] = None
    
    # Target selection
    target_machines: Optional[List[str]] = None  # machine_ids
    target_groups: Optional[List[str]] = None
    target_tags: Optional[List[str]] = None
    target_all: bool = False
    
    # Scheduling
    scheduled_at: Optional[datetime] = None
    execute_immediately: bool = True
    
    # Execution options
    create_backup: bool = True
    verify_before_apply: bool = True
    rollback_on_failure: bool = True
    max_failures: int = 0  # 0 = no limit
    parallel_execution: bool = False
    max_parallel: int = 10
    
    # Deployment metadata
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    status: DeploymentPhase = DeploymentPhase.PENDING
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Windows 11 Baseline Deployment",
                "description": "Deploy CIS Level 1 policies to production fleet",
                "policy_package_id": "pkg-123456",
                "target_groups": ["production", "finance"],
                "create_backup": True,
                "rollback_on_failure": True,
                "max_failures": 5
            }
        }


class DeploymentProgress(BaseModel):
    """Real-time deployment progress update"""
    deployment_id: str
    machine_id: str
    hostname: str
    
    phase: DeploymentPhase
    progress_percent: int = 0
    current_step: Optional[str] = None
    
    # Results
    policies_applied: int = 0
    policies_failed: int = 0
    errors: List[str] = []
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "deployment_id": "dep-789",
                "machine_id": "mach-123",
                "hostname": "WIN-PROD-001",
                "phase": "applying",
                "progress_percent": 45,
                "current_step": "Applying registry policies (15/33)",
                "policies_applied": 15,
                "policies_failed": 0
            }
        }


class DeploymentSummary(BaseModel):
    """Overall deployment status"""
    deployment_id: str
    name: str
    status: DeploymentPhase
    
    # Targets
    total_machines: int = 0
    
    # Results
    succeeded: int = 0
    failed: int = 0
    in_progress: int = 0
    pending: int = 0
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    # Details
    machine_results: List[DeploymentProgress] = []


class FleetStatistics(BaseModel):
    """Fleet-wide statistics"""
    total_machines: int = 0
    online_machines: int = 0
    offline_machines: int = 0
    deploying_machines: int = 0
    error_machines: int = 0
    
    # Compliance
    average_compliance_score: float = 0.0
    compliant_machines: int = 0  # >80% score
    non_compliant_machines: int = 0  # <80% score
    
    # Deployments
    active_deployments: int = 0
    completed_deployments_today: int = 0
    failed_deployments_today: int = 0
    
    # Health
    machines_needing_attention: List[str] = []  # hostnames
    recent_errors: List[Dict[str, Any]] = []


class AgentCommand(BaseModel):
    """Command sent to agent"""
    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    command_type: str  # "deploy", "scan", "rollback", "update"
    payload: Dict[str, Any]
    
    # Execution
    timeout_seconds: int = 3600
    priority: int = 5  # 1-10, higher = more urgent
    
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


class AgentCommandResult(BaseModel):
    """Result from agent command execution"""
    command_id: str
    machine_id: str
    success: bool
    
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    started_at: datetime
    completed_at: datetime
    execution_time_seconds: float


class RollbackRequest(BaseModel):
    """Request to rollback a deployment"""
    deployment_id: str
    target_machines: Optional[List[str]] = None  # If None, rollback all
    reason: Optional[str] = None
    
    # Options
    verify_before_rollback: bool = True
    force_rollback: bool = False


class MachineGroupRequest(BaseModel):
    """Bulk machine group/tag assignment"""
    machine_ids: List[str]
    groups_to_add: Optional[List[str]] = None
    groups_to_remove: Optional[List[str]] = None
    tags_to_add: Optional[List[str]] = None
    tags_to_remove: Optional[List[str]] = None


class WebSocketMessage(BaseModel):
    """WebSocket message format for real-time updates"""
    message_type: str  # "deployment_progress", "machine_status", "alert"
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any]
