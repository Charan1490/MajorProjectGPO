"""
Audit Engine Data Models - Step 6
Comprehensive data structures for audit operations, results, and reporting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any, Union
import json
import hashlib
import uuid

# =================================================================
# ENUMS FOR AUDIT SYSTEM
# =================================================================

class AuditStatus(Enum):
    """Status of audit operations"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ComplianceResult(Enum):
    """Individual policy compliance results"""
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"
    MANUAL_REVIEW = "manual_review"

class AuditSeverity(Enum):
    """Severity levels for audit findings"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"

class WindowsVersion(Enum):
    """Supported Windows versions for auditing"""
    WINDOWS_10 = "windows_10"
    WINDOWS_11 = "windows_11"
    WINDOWS_SERVER_2019 = "windows_server_2019"
    WINDOWS_SERVER_2022 = "windows_server_2022"
    WINDOWS_SERVER_2025 = "windows_server_2025"

class AuditScope(Enum):
    """Scope of audit operations"""
    FULL_SYSTEM = "full_system"
    SELECTED_POLICIES = "selected_policies"
    POLICY_GROUP = "policy_group"
    CIS_LEVEL = "cis_level"
    CUSTOM_FILTER = "custom_filter"

class ReportFormat(Enum):
    """Available report formats"""
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"

class AuditMethod(Enum):
    """Methods for conducting audits"""
    POWERSHELL = "powershell"
    REGISTRY_DIRECT = "registry_direct"
    WMI = "wmi"
    GROUP_POLICY = "group_policy"
    FILE_SYSTEM = "file_system"

# =================================================================
# CORE DATA STRUCTURES
# =================================================================

@dataclass
class SystemInfo:
    """Target system information"""
    hostname: str
    os_version: str
    os_build: str
    architecture: str
    domain: Optional[str] = None
    workgroup: Optional[str] = None
    install_date: Optional[datetime] = None
    last_boot: Optional[datetime] = None
    total_memory: Optional[int] = None
    cpu_info: Optional[str] = None
    scan_timestamp: datetime = field(default_factory=datetime.now)
    system_hash: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class PolicyAuditResult:
    """Result of auditing a single policy"""
    policy_id: str
    policy_name: str
    policy_title: str
    category: str
    cis_level: int
    description: str
    
    # Audit Results
    result: ComplianceResult
    severity: AuditSeverity
    current_value: Optional[str] = None
    expected_value: Optional[str] = None
    registry_path: Optional[str] = None
    registry_key: Optional[str] = None
    
    # Analysis
    rationale: Optional[str] = None
    impact: Optional[str] = None
    remediation: Optional[str] = None
    audit_method: AuditMethod = AuditMethod.POWERSHELL
    
    # Error Handling
    error_message: Optional[str] = None
    audit_timestamp: datetime = field(default_factory=datetime.now)
    execution_time_ms: int = 0
    
    # Additional Context
    group_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    related_policies: List[str] = field(default_factory=list)

@dataclass
class AuditConfiguration:
    """Configuration for audit operations"""
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "CIS Audit Scan"
    description: str = "Automated CIS benchmark compliance audit"
    
    # Scope Configuration
    scope: AuditScope = AuditScope.FULL_SYSTEM
    policy_ids: List[str] = field(default_factory=list)
    group_names: List[str] = field(default_factory=list)
    cis_levels: List[int] = field(default_factory=lambda: [1, 2])
    categories: List[str] = field(default_factory=list)
    
    # Execution Configuration
    parallel_execution: bool = True
    max_workers: int = 10
    timeout_seconds: int = 300
    retry_failed: bool = True
    max_retries: int = 3
    
    # Output Configuration
    generate_report: bool = True
    report_formats: List[ReportFormat] = field(default_factory=lambda: [ReportFormat.HTML, ReportFormat.CSV])
    include_passed: bool = True
    include_failed: bool = True
    include_errors: bool = True
    
    # System Configuration
    target_system: str = "localhost"
    use_remote_access: bool = False
    credential_file: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "audit_engine"

@dataclass
class AuditSummary:
    """Summary statistics for audit results"""
    total_policies: int = 0
    passed_policies: int = 0
    failed_policies: int = 0
    error_policies: int = 0
    not_applicable_policies: int = 0
    manual_review_policies: int = 0
    
    # By Severity
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    
    # By Category
    category_breakdown: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # By CIS Level
    level_breakdown: Dict[int, Dict[str, int]] = field(default_factory=dict)
    
    # Performance Metrics
    total_execution_time_ms: int = 0
    average_policy_time_ms: float = 0.0
    
    # Compliance Scoring
    compliance_percentage: float = 0.0
    security_score: float = 0.0

@dataclass
class AuditRun:
    """Complete audit run with results and metadata"""
    audit_id: str
    configuration: AuditConfiguration
    system_info: SystemInfo
    
    # Status and Timing
    status: AuditStatus = AuditStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Results
    policy_results: List[PolicyAuditResult] = field(default_factory=list)
    summary: Optional[AuditSummary] = None
    
    # Progress Tracking
    progress_percentage: int = 0
    current_policy: Optional[str] = None
    completed_policies: int = 0
    
    # Error Handling
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    # Report Generation
    report_paths: Dict[str, str] = field(default_factory=dict)
    report_generated: bool = False
    
    # Integrity and Versioning
    config_hash: str = field(init=False)
    results_hash: str = field(init=False)
    
    def __post_init__(self):
        """Calculate configuration and results hashes"""
        config_str = json.dumps(self.configuration.__dict__, default=str, sort_keys=True)
        self.config_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]
        
        results_str = json.dumps([r.__dict__ for r in self.policy_results], default=str, sort_keys=True)
        self.results_hash = hashlib.sha256(results_str.encode()).hexdigest()[:16]

@dataclass
class RemediationSuggestion:
    """Suggested remediation for failed policies"""
    policy_id: str
    policy_name: str
    current_issue: str
    recommended_action: str
    
    # Implementation Details
    powershell_command: Optional[str] = None
    registry_modification: Optional[Dict[str, str]] = None
    group_policy_setting: Optional[str] = None
    manual_steps: List[str] = field(default_factory=list)
    
    # Risk Assessment
    risk_level: AuditSeverity = AuditSeverity.MEDIUM
    impact_assessment: str = ""
    prerequisites: List[str] = field(default_factory=list)
    
    # References
    cis_reference: Optional[str] = None
    microsoft_docs: Optional[str] = None
    additional_resources: List[str] = field(default_factory=list)

@dataclass
class AuditTrend:
    """Historical trending data for audits"""
    trend_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    system_id: str = ""
    
    # Time Series Data
    audit_dates: List[datetime] = field(default_factory=list)
    compliance_scores: List[float] = field(default_factory=list)
    total_policies: List[int] = field(default_factory=list)
    failed_policies: List[int] = field(default_factory=list)
    
    # Category Trends
    category_trends: Dict[str, List[float]] = field(default_factory=dict)
    severity_trends: Dict[str, List[int]] = field(default_factory=dict)
    
    # Analysis
    trend_direction: str = "stable"  # improving, declining, stable
    trend_strength: float = 0.0  # -1.0 to 1.0
    
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class ReportTemplate:
    """Template configuration for report generation"""
    template_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Standard CIS Audit Report"
    description: str = "Comprehensive CIS benchmark compliance report"
    
    # Report Structure
    include_executive_summary: bool = True
    include_detailed_results: bool = True
    include_remediation_guide: bool = True
    include_trend_analysis: bool = True
    include_system_info: bool = True
    
    # Filtering Options
    show_passed_policies: bool = False
    show_failed_policies: bool = True
    show_errors: bool = True
    minimum_severity: AuditSeverity = AuditSeverity.LOW
    
    # Styling
    company_name: str = "Organization"
    company_logo: Optional[str] = None
    report_title: str = "CIS Benchmark Compliance Report"
    custom_css: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.now)

# =================================================================
# SERIALIZATION FUNCTIONS
# =================================================================

def serialize_audit_run(audit_run: AuditRun) -> Dict[str, Any]:
    """Convert AuditRun to JSON-serializable dictionary"""
    def convert_value(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, '__dict__'):
            return {k: convert_value(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, list):
            return [convert_value(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: convert_value(v) for k, v in obj.items()}
        return obj
    
    return convert_value(audit_run)

def serialize_policy_result(policy_result: PolicyAuditResult) -> Dict[str, Any]:
    """Convert PolicyAuditResult to JSON-serializable dictionary"""
    result_dict = policy_result.__dict__.copy()
    
    # Convert enums to values
    result_dict['result'] = policy_result.result.value
    result_dict['severity'] = policy_result.severity.value
    result_dict['audit_method'] = policy_result.audit_method.value
    
    # Convert datetime to string
    if result_dict['audit_timestamp']:
        result_dict['audit_timestamp'] = policy_result.audit_timestamp.isoformat()
    
    return result_dict

def serialize_system_info(system_info: SystemInfo) -> Dict[str, Any]:
    """Convert SystemInfo to JSON-serializable dictionary"""
    info_dict = system_info.__dict__.copy()
    
    # Convert datetime fields
    datetime_fields = ['install_date', 'last_boot', 'scan_timestamp']
    for field in datetime_fields:
        if info_dict.get(field):
            info_dict[field] = info_dict[field].isoformat()
    
    return info_dict

def serialize_audit_summary(summary: AuditSummary) -> Dict[str, Any]:
    """Convert AuditSummary to JSON-serializable dictionary"""
    return summary.__dict__.copy()

def deserialize_audit_run(data: Dict[str, Any]) -> AuditRun:
    """Convert dictionary back to AuditRun object"""
    # This would implement the reverse conversion
    # For now, returning a placeholder implementation
    pass

# =================================================================
# VALIDATION FUNCTIONS
# =================================================================

def validate_audit_configuration(config: AuditConfiguration) -> List[str]:
    """Validate audit configuration and return list of errors"""
    errors = []
    
    if not config.name.strip():
        errors.append("Audit name cannot be empty")
    
    if config.scope == AuditScope.SELECTED_POLICIES and not config.policy_ids:
        errors.append("Policy IDs must be specified for selected policies scope")
    
    if config.scope == AuditScope.POLICY_GROUP and not config.group_names:
        errors.append("Group names must be specified for policy group scope")
    
    if config.timeout_seconds < 10:
        errors.append("Timeout must be at least 10 seconds")
    
    if config.max_workers < 1 or config.max_workers > 50:
        errors.append("Max workers must be between 1 and 50")
    
    return errors

def validate_policy_audit_result(result: PolicyAuditResult) -> List[str]:
    """Validate policy audit result and return list of errors"""
    errors = []
    
    if not result.policy_id.strip():
        errors.append("Policy ID cannot be empty")
    
    if not result.policy_name.strip():
        errors.append("Policy name cannot be empty")
    
    if result.cis_level < 1 or result.cis_level > 3:
        errors.append("CIS level must be 1, 2, or 3")
    
    if result.execution_time_ms < 0:
        errors.append("Execution time cannot be negative")
    
    return errors

# =================================================================
# UTILITY FUNCTIONS
# =================================================================

def calculate_compliance_score(results: List[PolicyAuditResult]) -> float:
    """Calculate overall compliance score from audit results"""
    if not results:
        return 0.0
    
    total_policies = len(results)
    passed_policies = sum(1 for r in results if r.result == ComplianceResult.PASS)
    
    return (passed_policies / total_policies) * 100.0

def calculate_security_score(results: List[PolicyAuditResult]) -> float:
    """Calculate weighted security score based on severity"""
    if not results:
        return 0.0
    
    severity_weights = {
        AuditSeverity.CRITICAL: 10,
        AuditSeverity.HIGH: 8,
        AuditSeverity.MEDIUM: 5,
        AuditSeverity.LOW: 2,
        AuditSeverity.INFORMATIONAL: 1
    }
    
    total_weight = 0
    passed_weight = 0
    
    for result in results:
        weight = severity_weights.get(result.severity, 1)
        total_weight += weight
        
        if result.result == ComplianceResult.PASS:
            passed_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    return (passed_weight / total_weight) * 100.0

def generate_audit_summary(results: List[PolicyAuditResult]) -> AuditSummary:
    """Generate comprehensive summary from audit results"""
    summary = AuditSummary()
    
    # Basic counts
    summary.total_policies = len(results)
    summary.passed_policies = sum(1 for r in results if r.result == ComplianceResult.PASS)
    summary.failed_policies = sum(1 for r in results if r.result == ComplianceResult.FAIL)
    summary.error_policies = sum(1 for r in results if r.result == ComplianceResult.ERROR)
    summary.not_applicable_policies = sum(1 for r in results if r.result == ComplianceResult.NOT_APPLICABLE)
    summary.manual_review_policies = sum(1 for r in results if r.result == ComplianceResult.MANUAL_REVIEW)
    
    # Severity counts
    summary.critical_issues = sum(1 for r in results if r.severity == AuditSeverity.CRITICAL and r.result == ComplianceResult.FAIL)
    summary.high_issues = sum(1 for r in results if r.severity == AuditSeverity.HIGH and r.result == ComplianceResult.FAIL)
    summary.medium_issues = sum(1 for r in results if r.severity == AuditSeverity.MEDIUM and r.result == ComplianceResult.FAIL)
    summary.low_issues = sum(1 for r in results if r.severity == AuditSeverity.LOW and r.result == ComplianceResult.FAIL)
    
    # Category breakdown
    for result in results:
        if result.category not in summary.category_breakdown:
            summary.category_breakdown[result.category] = {
                'total': 0, 'passed': 0, 'failed': 0, 'error': 0
            }
        
        summary.category_breakdown[result.category]['total'] += 1
        
        if result.result == ComplianceResult.PASS:
            summary.category_breakdown[result.category]['passed'] += 1
        elif result.result == ComplianceResult.FAIL:
            summary.category_breakdown[result.category]['failed'] += 1
        elif result.result == ComplianceResult.ERROR:
            summary.category_breakdown[result.category]['error'] += 1
    
    # Performance metrics
    if results:
        summary.total_execution_time_ms = sum(r.execution_time_ms for r in results)
        summary.average_policy_time_ms = summary.total_execution_time_ms / len(results)
    
    # Compliance scoring
    summary.compliance_percentage = calculate_compliance_score(results)
    summary.security_score = calculate_security_score(results)
    
    return summary