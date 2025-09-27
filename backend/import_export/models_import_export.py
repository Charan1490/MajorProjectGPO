"""
Import/Export Models for CIS GPO Compliance Tool
Handles data structures for configuration and documentation import/export
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class ImportExportFormat(Enum):
    """Supported import/export formats"""
    JSON = "json"
    CSV = "csv" 
    YAML = "yaml"
    XML = "xml"


class ImportExportType(Enum):
    """Types of data that can be imported/exported"""
    POLICIES = "policies"
    TEMPLATES = "templates" 
    GROUPS = "groups"
    TAGS = "tags"
    DOCUMENTATION = "documentation"
    AUDIT_LOGS = "audit_logs"
    FULL_BACKUP = "full_backup"


class ImportStatus(Enum):
    """Import operation status"""
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    SKIP = "skip"  # Skip conflicting items
    OVERWRITE = "overwrite"  # Replace existing with imported
    MERGE = "merge"  # Merge fields where possible
    RENAME = "rename"  # Rename imported items
    PROMPT = "prompt"  # Ask user for each conflict


class DocumentationType(Enum):
    """Types of documentation"""
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"
    DOCX = "docx"


@dataclass
class ImportValidationResult:
    """Results from import validation"""
    is_valid: bool
    total_items: int
    valid_items: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    preview_data: Optional[Dict[str, Any]] = None


@dataclass
class ImportConflict:
    """Represents a data conflict during import"""
    conflict_id: str
    item_type: str
    existing_id: str
    imported_id: str
    existing_data: Dict[str, Any]
    imported_data: Dict[str, Any]
    suggested_resolution: ConflictResolution
    field_conflicts: List[str] = field(default_factory=list)


@dataclass
class ExportConfiguration:
    """Configuration for export operations"""
    format: ImportExportFormat
    export_type: ImportExportType
    include_metadata: bool = True
    include_history: bool = False
    include_documentation: bool = True
    compress_output: bool = False
    split_large_files: bool = False
    max_file_size_mb: int = 50
    custom_fields: Optional[List[str]] = None
    filter_criteria: Optional[Dict[str, Any]] = None


@dataclass
class ImportConfiguration:
    """Configuration for import operations"""
    format: ImportExportFormat
    import_type: ImportExportType
    conflict_resolution: ConflictResolution = ConflictResolution.PROMPT
    validate_before_import: bool = True
    create_backup_before_import: bool = True
    merge_documentation: bool = True
    preserve_ids: bool = False
    skip_invalid_items: bool = True
    import_metadata: bool = True


@dataclass
class DocumentationItem:
    """Represents imported/exported documentation"""
    doc_id: str
    title: str
    content: str
    doc_type: DocumentationType
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    associated_policies: List[str] = field(default_factory=list)
    associated_groups: List[str] = field(default_factory=list)
    associated_templates: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    checksum: Optional[str] = None


@dataclass
class ImportExportOperation:
    """Tracks import/export operations for audit trail"""
    operation_id: str
    operation_type: str  # import/export
    data_type: ImportExportType
    format: ImportExportFormat
    status: ImportStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    user_id: str = "system"
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    items_processed: int = 0
    items_successful: int = 0
    items_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    conflicts_resolved: List[Dict[str, Any]] = field(default_factory=list)
    backup_created: Optional[str] = None  # Backup file path
    rollback_data: Optional[Dict[str, Any]] = None


@dataclass
class BackupMetadata:
    """Metadata for backup files"""
    backup_id: str
    backup_name: str
    created_at: datetime
    backup_type: ImportExportType
    file_path: str
    file_size: int
    checksum: str
    items_count: int
    created_by: str = "system"
    description: Optional[str] = None


def serialize_import_export_operation(operation: ImportExportOperation) -> Dict[str, Any]:
    """Serialize ImportExportOperation to dictionary"""
    return {
        "operation_id": operation.operation_id,
        "operation_type": operation.operation_type,
        "data_type": operation.data_type.value,
        "format": operation.format.value,
        "status": operation.status.value,
        "started_at": operation.started_at.isoformat() if operation.started_at else None,
        "completed_at": operation.completed_at.isoformat() if operation.completed_at else None,
        "user_id": operation.user_id,
        "file_name": operation.file_name,
        "file_size": operation.file_size,
        "items_processed": operation.items_processed,
        "items_successful": operation.items_successful,
        "items_failed": operation.items_failed,
        "errors": operation.errors,
        "warnings": operation.warnings,
        "conflicts_resolved": operation.conflicts_resolved,
        "backup_created": operation.backup_created,
        "rollback_data": operation.rollback_data
    }


def deserialize_import_export_operation(data: Dict[str, Any]) -> ImportExportOperation:
    """Deserialize dictionary to ImportExportOperation"""
    return ImportExportOperation(
        operation_id=data["operation_id"],
        operation_type=data["operation_type"],
        data_type=ImportExportType(data["data_type"]),
        format=ImportExportFormat(data["format"]),
        status=ImportStatus(data["status"]),
        started_at=datetime.fromisoformat(data["started_at"]) if data["started_at"] else datetime.now(),
        completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        user_id=data.get("user_id", "system"),
        file_name=data.get("file_name"),
        file_size=data.get("file_size"),
        items_processed=data.get("items_processed", 0),
        items_successful=data.get("items_successful", 0),
        items_failed=data.get("items_failed", 0),
        errors=data.get("errors", []),
        warnings=data.get("warnings", []),
        conflicts_resolved=data.get("conflicts_resolved", []),
        backup_created=data.get("backup_created"),
        rollback_data=data.get("rollback_data")
    )


def serialize_documentation_item(doc: DocumentationItem) -> Dict[str, Any]:
    """Serialize DocumentationItem to dictionary"""
    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "content": doc.content,
        "doc_type": doc.doc_type.value,
        "file_name": doc.file_name,
        "file_size": doc.file_size,
        "associated_policies": doc.associated_policies,
        "associated_groups": doc.associated_groups,
        "associated_templates": doc.associated_templates,
        "tags": doc.tags,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        "checksum": doc.checksum
    }


def deserialize_documentation_item(data: Dict[str, Any]) -> DocumentationItem:
    """Deserialize dictionary to DocumentationItem"""
    return DocumentationItem(
        doc_id=data["doc_id"],
        title=data["title"],
        content=data["content"],
        doc_type=DocumentationType(data["doc_type"]),
        file_name=data.get("file_name"),
        file_size=data.get("file_size"),
        associated_policies=data.get("associated_policies", []),
        associated_groups=data.get("associated_groups", []),
        associated_templates=data.get("associated_templates", []),
        tags=data.get("tags", []),
        created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        checksum=data.get("checksum")
    )