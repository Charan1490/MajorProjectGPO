"""
CIS GPO Compliance Tool - Step 3: Dashboard Models
Enhanced data models for comprehensive dashboard functionality including:
- Policy groups and categories
- Tags and labels
- Edit history tracking
- Statistics and compliance metrics
- Documentation and references
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

class PolicyStatus(str, Enum):
    """Policy configuration status"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"
    PENDING = "pending"
    ERROR = "error"

class PolicyPriority(str, Enum):
    """Policy priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ChangeType(str, Enum):
    """Types of changes for history tracking"""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    VALUE_CHANGED = "value_changed"
    TAGGED = "tagged"
    UNTAGGED = "untagged"
    GROUPED = "grouped"
    UNGROUPED = "ungrouped"
    BULK_UPDATE = "bulk_update"
    IMPORTED = "imported"
    EXPORTED = "exported"

class PolicyTag(BaseModel):
    """Tag model for categorizing policies"""
    tag_id: str = Field(..., description="Unique identifier for the tag")
    name: str = Field(..., description="Tag name")
    description: Optional[str] = Field(None, description="Tag description")
    color: str = Field("#1976d2", description="Tag color (hex)")
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = Field("system", description="User who created the tag")
    usage_count: int = Field(0, description="Number of policies using this tag")

class PolicyGroup(BaseModel):
    """Group model for organizing policies"""
    group_id: str = Field(..., description="Unique identifier for the group")
    name: str = Field(..., description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    parent_group_id: Optional[str] = Field(None, description="Parent group for hierarchy")
    policy_ids: List[str] = Field(default_factory=list, description="Policies in this group")
    tag_ids: List[str] = Field(default_factory=list, description="Tags assigned to this group")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str = Field("system", description="User who created the group")
    is_system_group: bool = Field(False, description="Whether this is a system-generated group")
    order: int = Field(0, description="Display order")

class PolicyChangeHistory(BaseModel):
    """History tracking for policy changes"""
    history_id: str = Field(..., description="Unique identifier for this history entry")
    policy_id: str = Field(..., description="Policy that was changed")
    change_type: ChangeType = Field(..., description="Type of change")
    old_value: Optional[Dict[str, Any]] = Field(None, description="Previous value")
    new_value: Optional[Dict[str, Any]] = Field(None, description="New value")
    changed_fields: List[str] = Field(default_factory=list, description="Fields that were modified")
    user_id: str = Field("system", description="User who made the change")
    timestamp: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = Field(None, description="Change notes")
    batch_id: Optional[str] = Field(None, description="Batch ID for bulk operations")

class PolicyDocumentation(BaseModel):
    """Documentation and references for policies"""
    policy_id: str = Field(..., description="Policy this documentation belongs to")
    notes: Optional[str] = Field(None, description="User notes")
    cis_reference: Optional[str] = Field(None, description="CIS benchmark reference")
    rationale: Optional[str] = Field(None, description="Implementation rationale")
    impact_assessment: Optional[str] = Field(None, description="Impact of enabling this policy")
    remediation_steps: Optional[str] = Field(None, description="Steps to remediate issues")
    related_policies: List[str] = Field(default_factory=list, description="Related policy IDs")
    external_links: List[str] = Field(default_factory=list, description="External reference URLs")
    last_updated: datetime = Field(default_factory=datetime.now)
    updated_by: str = Field("system", description="User who last updated documentation")

class EnhancedPolicy(BaseModel):
    """Enhanced policy model with dashboard features"""
    # Core policy fields
    policy_id: str = Field(..., description="Unique policy identifier")
    policy_name: str = Field(..., description="Policy display name")
    title: Optional[str] = Field(None, description="Policy title")
    description: Optional[str] = Field(None, description="Policy description")
    category: Optional[str] = Field(None, description="Policy category")
    subcategory: Optional[str] = Field(None, description="Policy subcategory")
    
    # Configuration fields
    status: PolicyStatus = Field(PolicyStatus.NOT_CONFIGURED, description="Current status")
    priority: PolicyPriority = Field(PolicyPriority.MEDIUM, description="Policy priority")
    required_value: Optional[str] = Field(None, description="Required configuration value")
    current_value: Optional[str] = Field(None, description="Current configuration value")
    registry_path: Optional[str] = Field(None, description="Registry path")
    gpo_path: Optional[str] = Field(None, description="GPO path")
    
    # CIS specific fields
    cis_level: Optional[str] = Field(None, description="CIS compliance level")
    cis_section: Optional[str] = Field(None, description="CIS section number")
    
    # Dashboard enhancements
    tag_ids: List[str] = Field(default_factory=list, description="Applied tags")
    group_ids: List[str] = Field(default_factory=list, description="Groups containing this policy")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Custom user fields")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_modified_by: str = Field("system", description="User who last modified")
    version: int = Field(1, description="Version number for change tracking")
    is_locked: bool = Field(False, description="Whether policy is locked from editing")

class ComplianceStatistics(BaseModel):
    """Compliance and dashboard statistics"""
    total_policies: int = Field(0, description="Total number of policies")
    enabled_policies: int = Field(0, description="Number of enabled policies")
    disabled_policies: int = Field(0, description="Number of disabled policies")
    not_configured_policies: int = Field(0, description="Number of not configured policies")
    pending_policies: int = Field(0, description="Number of pending policies")
    error_policies: int = Field(0, description="Number of policies with errors")
    
    # Priority breakdown
    critical_policies: int = Field(0, description="Number of critical policies")
    high_priority_policies: int = Field(0, description="Number of high priority policies")
    medium_priority_policies: int = Field(0, description="Number of medium priority policies")
    low_priority_policies: int = Field(0, description="Number of low priority policies")
    
    # Coverage metrics
    compliance_percentage: float = Field(0.0, description="Overall compliance percentage")
    enabled_percentage: float = Field(0.0, description="Percentage of policies enabled")
    critical_compliance: float = Field(0.0, description="Critical policy compliance percentage")
    
    # Grouping statistics
    total_groups: int = Field(0, description="Total number of groups")
    ungrouped_policies: int = Field(0, description="Number of ungrouped policies")
    total_tags: int = Field(0, description="Total number of tags")
    untagged_policies: int = Field(0, description="Number of untagged policies")
    
    # Activity metrics
    recent_changes: int = Field(0, description="Changes in last 24 hours")
    total_changes: int = Field(0, description="Total number of changes")
    
    last_updated: datetime = Field(default_factory=datetime.now)

class BulkOperation(BaseModel):
    """Model for bulk operations"""
    operation_id: str = Field(..., description="Unique operation identifier")
    operation_type: str = Field(..., description="Type of bulk operation")
    policy_ids: List[str] = Field(..., description="Policies to operate on")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")
    created_by: str = Field("system", description="User who initiated the operation")
    created_at: datetime = Field(default_factory=datetime.now)

class DashboardExport(BaseModel):
    """Model for dashboard export/import"""
    export_id: str = Field(..., description="Unique export identifier")
    export_type: str = Field(..., description="Type of export (full, partial, templates)")
    policies: List[EnhancedPolicy] = Field(default_factory=list)
    groups: List[PolicyGroup] = Field(default_factory=list)
    tags: List[PolicyTag] = Field(default_factory=list)
    history: List[PolicyChangeHistory] = Field(default_factory=list)
    documentation: List[PolicyDocumentation] = Field(default_factory=list)
    statistics: Optional[ComplianceStatistics] = Field(None)
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = Field("system")
    
# Request/Response models for API endpoints

class CreateTagRequest(BaseModel):
    """Request model for creating tags"""
    name: str = Field(..., description="Tag name")
    description: Optional[str] = Field(None, description="Tag description")
    color: str = Field("#1976d2", description="Tag color")

class CreateGroupRequest(BaseModel):
    """Request model for creating groups"""
    name: str = Field(..., description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    parent_group_id: Optional[str] = Field(None, description="Parent group ID")

class BulkUpdateRequest(BaseModel):
    """Request model for bulk updates"""
    policy_ids: List[str] = Field(..., description="Policies to update")
    updates: Dict[str, Any] = Field(..., description="Fields to update")
    user_note: Optional[str] = Field(None, description="Note about the change")

class PolicyUpdateRequest(BaseModel):
    """Request model for individual policy updates"""
    status: Optional[PolicyStatus] = Field(None, description="Policy status")
    priority: Optional[PolicyPriority] = Field(None, description="Policy priority")
    current_value: Optional[str] = Field(None, description="Current value")
    tag_ids: Optional[List[str]] = Field(None, description="Tag assignments")
    group_ids: Optional[List[str]] = Field(None, description="Group assignments")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")
    user_note: Optional[str] = Field(None, description="Update note")

class SearchRequest(BaseModel):
    """Request model for advanced search"""
    query: Optional[str] = Field(None, description="Text search query")
    status_filter: Optional[List[PolicyStatus]] = Field(None, description="Status filters")
    priority_filter: Optional[List[PolicyPriority]] = Field(None, description="Priority filters")
    tag_filter: Optional[List[str]] = Field(None, description="Tag filters")
    group_filter: Optional[List[str]] = Field(None, description="Group filters")
    category_filter: Optional[List[str]] = Field(None, description="Category filters")
    cis_level_filter: Optional[List[str]] = Field(None, description="CIS level filters")
    date_from: Optional[datetime] = Field(None, description="Filter changes from date")
    date_to: Optional[datetime] = Field(None, description="Filter changes to date")
    limit: int = Field(100, description="Maximum results to return")
    offset: int = Field(0, description="Results offset for pagination")
    sort_by: str = Field("policy_name", description="Field to sort by")
    sort_order: str = Field("asc", description="Sort order (asc/desc)")

class DashboardResponse(BaseModel):
    """Generic dashboard response wrapper"""
    success: bool = Field(True, description="Whether operation succeeded")
    message: str = Field("Operation completed successfully")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.now)