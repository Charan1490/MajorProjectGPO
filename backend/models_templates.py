"""
Models for GPO Template Management (Step 2)
Extends the existing CIS benchmark data with template management capabilities
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import uuid

class PolicyStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    CUSTOM = "custom"

class PolicyType(str, Enum):
    REGISTRY = "registry"
    SECURITY_POLICY = "security_policy"
    AUDIT_POLICY = "audit_policy"
    USER_RIGHTS = "user_rights"
    ADMINISTRATIVE_TEMPLATE = "administrative_template"

class PolicyEdit(BaseModel):
    """Tracks individual policy edits/changes"""
    edit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    field_name: str
    old_value: Any
    new_value: Any
    user_note: Optional[str] = None
    
class PolicyItem(BaseModel):
    """Extended policy item with template management capabilities"""
    # Original CIS data
    policy_id: str
    cis_id: Optional[str] = None
    policy_name: str
    category: str = "Uncategorized"
    subcategory: Optional[str] = None
    description: str = ""
    rationale: str = ""
    registry_path: Optional[str] = None
    gpo_path: Optional[str] = None
    cis_level: Optional[str] = None
    
    # Template management extensions
    policy_type: PolicyType = PolicyType.REGISTRY
    status: PolicyStatus = PolicyStatus.ENABLED
    custom_value: Optional[str] = None
    required_value: Optional[str] = None
    user_notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # Change tracking
    edits: List[PolicyEdit] = Field(default_factory=list)
    is_modified: bool = False
    
    # Grouping
    template_ids: List[str] = Field(default_factory=list)
    
class PolicyTemplate(BaseModel):
    """GPO deployment template containing grouped policies"""
    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Template metadata
    cis_level: Optional[str] = None  # Level 1, Level 2, Custom
    tags: List[str] = Field(default_factory=list)
    
    # Policy assignments
    policy_ids: List[str] = Field(default_factory=list)
    
    # Template settings
    is_active: bool = True
    is_default: bool = False
    
class PolicyGroup(BaseModel):
    """Logical grouping of policies (can be part of multiple templates)"""
    group_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    color: Optional[str] = None  # For UI visualization
    
    policy_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    
class TemplateExport(BaseModel):
    """Export format for templates"""
    template: PolicyTemplate
    policies: List[PolicyItem]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    export_timestamp: datetime = Field(default_factory=datetime.now)

class BulkEditRequest(BaseModel):
    """Request for bulk editing multiple policies"""
    policy_ids: List[str]
    changes: Dict[str, Any]
    user_note: Optional[str] = None

class TemplateCreateRequest(BaseModel):
    """Request to create a new template"""
    name: str
    description: Optional[str] = None
    cis_level: Optional[str] = None
    policy_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

class TemplateUpdateRequest(BaseModel):
    """Request to update an existing template"""
    name: Optional[str] = None
    description: Optional[str] = None
    cis_level: Optional[str] = None
    policy_ids: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

class PolicySearchRequest(BaseModel):
    """Advanced search/filter request"""
    query: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    policy_types: List[PolicyType] = Field(default_factory=list)
    statuses: List[PolicyStatus] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    cis_levels: List[str] = Field(default_factory=list)
    is_modified: Optional[bool] = None
    template_id: Optional[str] = None