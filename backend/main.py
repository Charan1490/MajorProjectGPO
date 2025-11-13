"""
CIS Benchmark PDF Parser Main Application
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import json
import os
from datetime import datetime
import uuid
import aiofiles
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
# Use explicit path to ensure .env is found regardless of working directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from pdf_parser import extract_policies_from_pdf
from models import PolicyExtractionResponse, PolicyItem, ExtractionStatus

# Import template management modules (Step 2)
from template_manager import TemplateManager
from models_templates import (
    PolicyItem as TemplatePolicy, PolicyTemplate, PolicyGroup, 
    BulkEditRequest, TemplateCreateRequest, TemplateUpdateRequest,
    PolicySearchRequest, TemplateExport
)

# Import dashboard management modules (Step 3)
from dashboard_manager import DashboardManager
from models_dashboard import (
    EnhancedPolicy, PolicyGroup as DashboardPolicyGroup, PolicyTag, 
    PolicyChangeHistory, PolicyDocumentation, ComplianceStatistics,
    CreateTagRequest, CreateGroupRequest, BulkUpdateRequest as DashboardBulkUpdateRequest,
    PolicyUpdateRequest, SearchRequest, DashboardResponse,
    PolicyStatus, PolicyPriority, ChangeType
)

# Import deployment management modules (Step 4)  
from deployment.deployment_manager import DeploymentManager
from deployment.models_deployment import (
    DeploymentPackage, DeploymentJob, PolicyExportConfig, ScriptConfiguration,
    WindowsVersion, PackageFormat, DeploymentStatus, ValidationResult,
    serialize_deployment_package, deserialize_deployment_package
)
from deployment.lgpo_utils import LGPOManager

# Import import/export management modules (Step 5)
from import_export.import_export_manager import ImportExportManager
from import_export.documentation_manager import DocumentationManager
from import_export.models_import_export import (
    ImportExportOperation, ImportValidationResult, ImportConflict,
    ExportConfiguration, ImportConfiguration, DocumentationItem,
    ImportExportFormat, ImportExportType, ImportStatus, ConflictResolution,
    DocumentationType, serialize_import_export_operation
)

# Import audit management modules (Step 6)
from audit_engine.audit_manager import AuditManager
from audit_engine.models_audit import (
    AuditRun, AuditConfiguration, PolicyAuditResult, AuditSummary,
    AuditStatus, ComplianceResult, AuditSeverity, AuditScope, ReportFormat,
    serialize_audit_run
)

# Import automated remediation and rollback modules (Step 7)
from remediation.remediation_manager import RemediationManager
from remediation.models_remediation import (
    RemediationPlan, RemediationSession, RemediationStatus, RemediationSeverity,
    BackupType, SystemBackup, RollbackPlan
)

# Pydantic request models for deployment endpoints
class CreatePackageRequest(BaseModel):
    name: str
    description: str
    target_os: str
    template_id: Optional[str] = None  # NEW: Select policies from a template
    policy_ids: Optional[List[str]] = None
    group_names: Optional[List[str]] = None
    tag_names: Optional[List[str]] = None
    categories: Optional[List[str]] = None  # NEW: Select policies by category
    include_formats: Optional[List[str]] = None
    include_scripts: bool = True
    include_documentation: bool = True
    include_verification: bool = True
    create_zip_package: bool = True
    use_powershell: bool = True
    use_batch: bool = True
    require_admin: bool = True
    create_backup: bool = True
    verify_before_apply: bool = True
    log_changes: bool = True
    rollback_support: bool = True

# Pydantic request models for import/export endpoints
class ExportRequest(BaseModel):
    export_type: str  # policies, templates, groups, tags, documentation, full_backup
    format: str  # json, csv, yaml, xml
    item_ids: Optional[List[str]] = None
    group_names: Optional[List[str]] = None
    tag_names: Optional[List[str]] = None
    include_metadata: bool = True
    include_history: bool = False
    include_documentation: bool = True
    compress_output: bool = False
    filter_criteria: Optional[Dict[str, Any]] = None

class ImportRequest(BaseModel):
    import_type: str  # policies, templates, groups, tags, documentation
    format: str  # json, csv, yaml, xml
    conflict_resolution: str = "prompt"  # skip, overwrite, merge, rename, prompt
    validate_before_import: bool = True
    create_backup_before_import: bool = True
    merge_documentation: bool = True
    preserve_ids: bool = False
    skip_invalid_items: bool = True

class DocumentationRequest(BaseModel):
    title: str
    content: Optional[str] = None
    doc_type: str = "text"
    associated_policies: Optional[List[str]] = None
    associated_groups: Optional[List[str]] = None
    associated_templates: Optional[List[str]] = None
    tags: Optional[List[str]] = None

class AssociateDocumentationRequest(BaseModel):
    doc_id: str
    policy_ids: Optional[List[str]] = None
    group_ids: Optional[List[str]] = None
    template_ids: Optional[List[str]] = None

# Pydantic request models for audit endpoints
class AuditConfigurationRequest(BaseModel):
    name: str
    description: str = ""
    scope: str = "full_system"  # full_system, selected_policies, policy_group, cis_level, custom_filter
    policy_ids: Optional[List[str]] = None
    group_names: Optional[List[str]] = None
    cis_levels: Optional[List[int]] = None
    categories: Optional[List[str]] = None
    parallel_execution: bool = True
    max_workers: int = 10
    timeout_seconds: int = 300
    generate_report: bool = True
    report_formats: Optional[List[str]] = None
    target_system: str = "localhost"

class GenerateReportRequest(BaseModel):
    audit_id: str
    format: str = "html"  # html, pdf, csv, json, excel
    template_name: str = "standard"  # standard, executive, technical


# Pydantic request models for remediation endpoints
class CreateRemediationPlanRequest(BaseModel):
    name: str
    description: str
    audit_id: str
    target_system: str = "localhost"
    selective_policies: Optional[List[str]] = None
    severity_filter: Optional[str] = None
    create_backup: bool = True
    backup_type: str = "selective"
    require_confirmation: bool = True
    continue_on_error: bool = False


class ExecuteRemediationRequest(BaseModel):
    plan_id: str
    operator: str
    confirm_high_risk: bool = False
    dry_run: bool = False


class CreateBackupRequest(BaseModel):
    name: str
    description: str
    backup_type: str  # full_system, registry_only, group_policy, security_settings, selective
    policies: Optional[List[str]] = None
    registry_keys: Optional[List[str]] = None
    gpos: Optional[List[str]] = None


class CreateRollbackPlanRequest(BaseModel):
    name: str
    description: str
    backup_id: str
    selective_rollback: bool = False
    selected_policies: Optional[List[str]] = None


class ExecuteRollbackRequest(BaseModel):
    rollback_id: str
    operator: str
    force_execution: bool = False

# Create the FastAPI app
app = FastAPI(
    title="CIS Benchmark PDF Parser",
    description="Service to extract policy settings from CIS Benchmark PDFs",
    version="1.0.0"
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("results", exist_ok=True)

# Store extraction status
extraction_tasks: Dict[str, ExtractionStatus] = {}

# Initialize Template Manager (Step 2)
template_manager = TemplateManager()

# Initialize Dashboard Manager (Step 3)
dashboard_manager = DashboardManager()

# Initialize Deployment Manager (Step 4) with enhanced capabilities
gemini_api_key = os.getenv('GEMINI_API_KEY')
deployment_manager = DeploymentManager(gemini_api_key=gemini_api_key)

# Initialize LGPO Manager (Step 4)
lgpo_manager = LGPOManager()

# Initialize Import/Export Manager (Step 5)
import_export_manager = ImportExportManager()

# Initialize Documentation Manager (Step 5)
documentation_manager = DocumentationManager()

# Initialize Audit Manager (Step 6)
audit_manager = AuditManager()

# Initialize Remediation Manager (Step 7)
remediation_manager = RemediationManager()

# Initialize Realtime Monitoring Manager (Step 3 - Enhanced)
from realtime_manager import realtime_manager

# Utility function to save task status to file
def save_task_status(task_id: str, status: ExtractionStatus):
    """Save task status to a JSON file for persistence"""
    status_file = os.path.join("results", f"status_{task_id}.json")
    with open(status_file, 'w') as f:
        json.dump(status.dict(), f, indent=2)

# Utility function to load task status from file
def load_task_status(task_id: str) -> Optional[ExtractionStatus]:
    """Load task status from a JSON file"""
    status_file = os.path.join("results", f"status_{task_id}.json")
    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            data = json.load(f)
            return ExtractionStatus(**data)
    return None

# Utility function to get or create task status
def get_task_status(task_id: str) -> Optional[ExtractionStatus]:
    """Get task status from memory or load from file"""
    if task_id in extraction_tasks:
        return extraction_tasks[task_id]
    
    # Try to load from file
    status = load_task_status(task_id)
    if status:
        extraction_tasks[task_id] = status
        return status
    
    return None

@app.post("/upload-pdf/", response_model=Dict[str, str])
async def upload_pdf(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Upload a CIS Benchmark PDF file for parsing.
    Returns a task ID that can be used to check the status and retrieve results.
    """
    print(f"Upload request received for file: {file.filename}")
    
    # Validate file is a PDF
    if not file.filename.lower().endswith('.pdf'):
        print(f"Error: File {file.filename} is not a PDF")
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Generate a unique ID for this task
    task_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Create a filename for the uploaded PDF
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join("uploads", filename)
    
    print(f"Saving uploaded file to {file_path}")
    
    # Save the uploaded file
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    # Get file size for logging
    file_size = os.path.getsize(file_path)
    print(f"File saved successfully. Size: {file_size} bytes")
    
    # Initialize extraction status
    extraction_tasks[task_id] = ExtractionStatus(
        task_id=task_id,
        status="processing",
        message="PDF uploaded, extraction starting",
        progress=0,
        file_name=file.filename,
        result_path=None
    )
    
    # Save initial status to file
    save_task_status(task_id, extraction_tasks[task_id])
    
    # Start extraction in the background
    print(f"Starting background extraction for task {task_id}")
    background_tasks.add_task(process_pdf, task_id, file_path)
    
    return {"task_id": task_id}

async def process_pdf(task_id: str, file_path: str):
    """
    Process the PDF file and extract policies.
    Updates the extraction status as it progresses.
    """
    print(f"Starting PDF processing for task {task_id}, file: {file_path}")
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file size for verification
        file_size = os.path.getsize(file_path)
        print(f"Processing file with size: {file_size} bytes")
        
        # Update status to processing
        extraction_tasks[task_id].status = "processing"
        extraction_tasks[task_id].message = "PDF Uploaded Successfully"
        extraction_tasks[task_id].details = "Initializing PDF processing engine and preparing for extraction"
        extraction_tasks[task_id].progress = 10
        print(f"Status updated: progress 10%")
        
        print(f"Calling extract_policies_from_pdf for file: {file_path}")
        # Extract policies from the PDF
        policies = extract_policies_from_pdf(file_path, 
                                             progress_callback=lambda p, op=None, det=None: update_progress(task_id, p, op, det))
        
        print(f"Extraction completed. Found {len(policies)} policies.")
        
        # Save the results to a JSON file
        result_filename = f"policies_{task_id}.json"
        result_path = os.path.join("results", result_filename)
        
        print(f"Saving results to {result_path}")
        with open(result_path, 'w') as f:
            json.dump([p.dict() for p in policies], f, indent=2)
        
        # Update status to completed
        extraction_tasks[task_id].status = "completed"
        extraction_tasks[task_id].message = f"Successfully extracted {len(policies)} policies"
        extraction_tasks[task_id].details = f"PDF processing complete. Found {len(policies)} policy items that you can now view and export."
        extraction_tasks[task_id].progress = 100
        extraction_tasks[task_id].result_path = result_path
        
        # Save final status to file
        save_task_status(task_id, extraction_tasks[task_id])
        
        print(f"Processing completed for task {task_id}")
        
    except Exception as e:
        # Update status to failed with more detailed error information
        extraction_tasks[task_id].status = "failed"
        extraction_tasks[task_id].message = f"Extraction failed: {str(e)}"
        extraction_tasks[task_id].progress = 0
        
        # More detailed logging
        import traceback
        error_details = traceback.format_exc()
        print(f"Error processing PDF for task {task_id}: {e}")
        print(f"Error details:\n{error_details}")
        
        # Include error details in the status
        extraction_tasks[task_id].details = f"An error occurred during processing. Technical details: {str(e)}"
        
        # Save error status to file
        save_task_status(task_id, extraction_tasks[task_id])

def update_progress(task_id: str, progress: int, current_operation: str = None, details: str = None):
    """Update the progress of a task with detailed information"""
    if task_id in extraction_tasks:
        # Log the progress update
        operation_msg = f", operation: {current_operation}" if current_operation else ""
        details_msg = f", details: {details}" if details else ""
        print(f"Updating progress for task {task_id}: {progress}%{operation_msg}{details_msg}")
        
        extraction_tasks[task_id].progress = progress
        
        # Update message and details if provided
        if current_operation:
            extraction_tasks[task_id].message = current_operation
        
        if details:
            extraction_tasks[task_id].details = details
        elif progress < 20:
            extraction_tasks[task_id].details = "Initializing PDF processing and extracting document structure"
        elif progress < 40:
            extraction_tasks[task_id].details = "Analyzing document sections and identifying policy blocks"
        elif progress < 60:
            extraction_tasks[task_id].details = "Extracting policy settings and table data from document"
        elif progress < 80:
            extraction_tasks[task_id].details = "Processing extracted text and identifying policy attributes"
        elif progress < 95:
            extraction_tasks[task_id].details = "Finalizing policy extraction and preparing results"
        else:
            extraction_tasks[task_id].details = "Extraction complete, results ready for viewing"
            
        # Save progress updates to file (only for major milestones to avoid too many file writes)
        if progress in [25, 50, 75, 100] or extraction_tasks[task_id].status in ["completed", "failed"]:
            save_task_status(task_id, extraction_tasks[task_id])
    else:
        print(f"Warning: Task {task_id} not found when trying to update progress to {progress}%")

@app.get("/status/{task_id}", response_model=ExtractionStatus)
async def get_task_status_endpoint(task_id: str):
    """
    Get the status of a policy extraction task
    """
    status = get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return status

@app.get("/results/{task_id}")
async def get_results(task_id: str):
    """
    Get the extracted policies for a completed task
    """
    status = get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if status.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Task is not completed. Current status: {status.status}"
        )
    
    if not status.result_path or not os.path.exists(status.result_path):
        raise HTTPException(status_code=404, detail="Results file not found")
    
    with open(status.result_path, 'r') as f:
        policies = json.load(f)
    
    return {"policies": policies}

@app.get("/download/{task_id}")
async def download_results(task_id: str, format: str = "json"):
    """
    Download the extracted policies in the specified format (json or csv)
    """
    status = get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if status.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Task is not completed. Current status: {status.status}"
        )
    
    if not status.result_path or not os.path.exists(status.result_path):
        raise HTTPException(status_code=404, detail="Results file not found")
    
    with open(status.result_path, 'r') as f:
        policies = json.load(f)
    
    # For JSON, just return the policies
    if format.lower() == "json":
        return {"policies": policies}
    
    # For CSV, convert policies to CSV format
    # This would be implemented in a real application
    # For now, we'll just return an error
    raise HTTPException(status_code=400, detail="CSV format not implemented yet")

@app.get("/completed-tasks")
async def get_completed_tasks():
    """
    Get a list of all completed extraction tasks by scanning the results directory
    """
    completed_tasks = []
    
    # Scan the results directory for policy JSON files
    if os.path.exists("results"):
        for filename in os.listdir("results"):
            if filename.startswith("policies_") and filename.endswith(".json"):
                task_id = filename[9:-5]  # Remove "policies_" prefix and ".json" suffix
                
                # Try to get the status
                status = get_task_status(task_id)
                if status and status.status == "completed":
                    completed_tasks.append({
                        "task_id": task_id,
                        "file_name": status.file_name,
                        "message": status.message,
                        "result_path": status.result_path
                    })
                else:
                    # If no status file exists, create a basic one from the JSON file
                    json_path = os.path.join("results", filename)
                    if os.path.exists(json_path):
                        try:
                            with open(json_path, 'r') as f:
                                policies = json.load(f)
                            
                            completed_tasks.append({
                                "task_id": task_id,
                                "file_name": "Unknown PDF",
                                "message": f"Found {len(policies)} extracted policies",
                                "result_path": json_path
                            })
                        except Exception as e:
                            print(f"Error reading {json_path}: {e}")
    
    return {"completed_tasks": completed_tasks}


# ================================
# STEP 2: GPO TEMPLATE MANAGEMENT ENDPOINTS
# ================================

@app.post("/import-cis-policies/{task_id}")
async def import_cis_policies_to_templates(task_id: str):
    """Import CIS policies from Step 1 extraction into template system"""
    try:
        # Load the extracted policies from Step 1
        result_path = os.path.join("results", f"policies_{task_id}.json")
        if not os.path.exists(result_path):
            raise HTTPException(status_code=404, detail="CIS extraction not found")
        
        with open(result_path, 'r') as f:
            cis_data = json.load(f)
        
        # Import into template system
        imported = template_manager.import_cis_policies(cis_data)
        
        return {
            "message": f"Imported {len(imported)} policies",
            "imported_policies": imported
        }
    except Exception as e:
        print(f"Error importing CIS policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/template-policies/")
async def get_all_template_policies():
    """Get all policies in the template system"""
    try:
        policies = template_manager.get_all_policies()
        return {
            "policies": [policy.dict() for policy in policies],
            "total_count": len(policies)
        }
    except Exception as e:
        print(f"Error fetching policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/template-policies/{policy_id}")
async def get_template_policy(policy_id: str):
    """Get a specific policy by ID"""
    try:
        policy = template_manager.get_policy(policy_id)
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")
        return policy.dict()
    except Exception as e:
        print(f"Error fetching policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/template-policies/{policy_id}")
async def update_template_policy(policy_id: str, updates: Dict[str, Any], user_note: Optional[str] = None):
    """Update a policy"""
    try:
        policy = template_manager.update_policy(policy_id, updates, user_note)
        return policy.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error updating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/template-policies/bulk-update")
async def bulk_update_template_policies(request: BulkEditRequest):
    """Update multiple policies at once"""
    try:
        updated = template_manager.bulk_update_policies(request)
        return {
            "updated_policies": {k: v.dict() for k, v in updated.items()},
            "updated_count": len(updated)
        }
    except Exception as e:
        print(f"Error bulk updating policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/template-policies/search")
async def search_template_policies(request: PolicySearchRequest):
    """Search and filter policies"""
    try:
        results = template_manager.search_policies(request)
        return {
            "policies": [policy.dict() for policy in results],
            "total_count": len(results)
        }
    except Exception as e:
        print(f"Error searching policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Template Management Endpoints
@app.post("/templates/", response_model=Dict[str, Any])
async def create_template(request: TemplateCreateRequest):
    """Create a new template"""
    try:
        template = template_manager.create_template(
            name=request.name,
            description=request.description,
            cis_level=request.cis_level,
            policy_ids=request.policy_ids,
            tags=request.tags
        )
        return template.dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/templates/")
async def get_all_templates():
    """Get all templates"""
    try:
        templates = template_manager.get_all_templates()
        # Add policy_count to each template
        templates_with_count = []
        for template in templates:
            template_dict = template.dict()
            template_dict['policy_count'] = len(template.policy_ids)
            templates_with_count.append(template_dict)
        
        return {
            "templates": templates_with_count,
            "total_count": len(templates)
        }
    except Exception as e:
        print(f"Error fetching templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template by ID"""
    try:
        template = template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template.dict()
    except Exception as e:
        print(f"Error fetching template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/templates/{template_id}/export")
async def get_template_with_policies(template_id: str):
    """Get template with all its policies for editing/viewing"""
    try:
        export_data = template_manager.get_template_with_policies(template_id)
        if not export_data:
            raise HTTPException(status_code=404, detail="Template not found")
        return export_data.dict()
    except Exception as e:
        print(f"Error exporting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/templates/{template_id}")
async def update_template(template_id: str, request: TemplateUpdateRequest):
    """Update a template"""
    try:
        updates = {k: v for k, v in request.dict(exclude_unset=True).items()}
        template = template_manager.update_template(template_id, updates)
        return template.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """Delete a template"""
    try:
        success = template_manager.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"message": "Template deleted successfully"}
    except Exception as e:
        print(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/templates/{template_id}/duplicate")
async def duplicate_template(template_id: str, new_name: str):
    """Duplicate a template"""
    try:
        new_template = template_manager.duplicate_template(template_id, new_name)
        return new_template.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error duplicating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Export endpoints
@app.get("/templates/{template_id}/export/json")
async def export_template_json(template_id: str):
    """Export template as JSON"""
    try:
        export_data = template_manager.export_template_json(template_id)
        return export_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error exporting template JSON: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/templates/{template_id}/export/csv")
async def export_template_csv(template_id: str):
    """Export template as CSV"""
    try:
        csv_data = template_manager.export_template_csv(template_id)
        return JSONResponse(
            content={"csv_data": csv_data},
            headers={"Content-Type": "application/json"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error exporting template CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Group Management Endpoints
@app.post("/groups/")
async def create_group(name: str, description: Optional[str] = None, 
                      color: Optional[str] = None, policy_ids: List[str] = None,
                      tags: List[str] = None):
    """Create a new policy group"""
    try:
        group = template_manager.create_group(name, description, color, policy_ids, tags)
        return group.dict()
    except Exception as e:
        print(f"Error creating group: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/groups/")
async def get_all_groups():
    """Get all groups"""
    try:
        groups = template_manager.get_all_groups()
        return {
            "groups": [group.dict() for group in groups],
            "total_count": len(groups)
        }
    except Exception as e:
        print(f"Error fetching groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# Step 3: Dashboard API Endpoints
# ==============================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Dashboard Data Import/Export

@app.post("/dashboard/import-from-templates")
async def import_policies_to_dashboard():
    """Import all policies from template system to dashboard"""
    try:
        # Get all policies from template system
        template_policies = template_manager.get_all_policies()
        
        # Convert to list of dicts for dashboard import
        policy_dicts = []
        for policy in template_policies:
            policy_dict = policy.dict() if hasattr(policy, 'dict') else policy
            policy_dicts.append(policy_dict)
        
        # Import to dashboard
        result = dashboard_manager.import_policies_from_template_system(policy_dicts)
        
        return DashboardResponse(
            success=True,
            message=f"Successfully imported {result['imported_policies']} policies and updated {result['updated_policies']} policies",
            data=result
        ).dict()
    except Exception as e:
        print(f"Error importing policies to dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Policy Management

@app.get("/dashboard/policies", response_model=Dict[str, Any])
async def get_dashboard_policies(
    include_metadata: bool = True,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all dashboard policies with optional filtering"""
    try:
        policies = dashboard_manager.get_all_policies(include_metadata=include_metadata)
        
        # Apply basic filters
        if status:
            policies = [p for p in policies if p.get('status') == status]
        if priority:
            policies = [p for p in policies if p.get('priority') == priority]
        if category:
            policies = [p for p in policies if p.get('category') == category]
        
        return DashboardResponse(
            success=True,
            message=f"Retrieved {len(policies)} policies",
            data={
                "policies": policies,
                "total_count": len(policies)
            }
        ).dict()
    except Exception as e:
        print(f"Error fetching dashboard policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dashboard/policies/search", response_model=Dict[str, Any])
async def search_dashboard_policies(request: SearchRequest):
    """Advanced search for dashboard policies"""
    try:
        policies, total_count = dashboard_manager.search_policies(request)
        
        return DashboardResponse(
            success=True,
            message=f"Found {len(policies)} policies matching search criteria",
            data={
                "policies": policies,
                "total_count": total_count,
                "page_size": len(policies),
                "offset": request.offset,
                "limit": request.limit
            }
        ).dict()
    except Exception as e:
        print(f"Error searching policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/dashboard/policies/{policy_id}")
async def update_dashboard_policy(policy_id: str, request: PolicyUpdateRequest):
    """Update individual policy"""
    try:
        success = dashboard_manager.update_policy(policy_id, request, user_id="api_user")
        
        if not success:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        return DashboardResponse(
            success=True,
            message="Policy updated successfully",
            data={"policy_id": policy_id}
        ).dict()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dashboard/policies/bulk-update")
async def bulk_update_dashboard_policies(request: DashboardBulkUpdateRequest):
    """Perform bulk updates on multiple policies"""
    try:
        result = dashboard_manager.bulk_update_policies(request, user_id="api_user")
        
        return DashboardResponse(
            success=True,
            message=f"Updated {result['updated_count']} policies successfully",
            data=result
        ).dict()
    except Exception as e:
        print(f"Error in bulk update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/policies/{policy_id}/history")
async def get_policy_history(policy_id: str, limit: int = 100):
    """Get history for specific policy"""
    try:
        history = dashboard_manager.get_policy_history(policy_id, limit=limit)
        
        return DashboardResponse(
            success=True,
            message=f"Retrieved {len(history)} history entries",
            data={
                "history": history,
                "policy_id": policy_id
            }
        ).dict()
    except Exception as e:
        print(f"Error fetching policy history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dashboard/history/{history_id}/revert")
async def revert_policy_change(history_id: str):
    """Revert a policy to a previous state"""
    try:
        success = dashboard_manager.revert_policy_change(history_id, user_id="api_user")
        
        if not success:
            raise HTTPException(status_code=404, detail="History entry not found or cannot be reverted")
        
        return DashboardResponse(
            success=True,
            message="Policy change reverted successfully",
            data={"history_id": history_id}
        ).dict()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error reverting change: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Group Management

@app.get("/dashboard/groups")
async def get_dashboard_groups(include_hierarchy: bool = True):
    """Get all dashboard groups"""
    try:
        groups = dashboard_manager.get_all_groups(include_hierarchy=include_hierarchy)
        
        return DashboardResponse(
            success=True,
            message=f"Retrieved {len(groups)} groups",
            data={
                "groups": groups,
                "total_count": len(groups)
            }
        ).dict()
    except Exception as e:
        print(f"Error fetching groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dashboard/groups")
async def create_dashboard_group(request: CreateGroupRequest):
    """Create new policy group"""
    try:
        group = dashboard_manager.create_group(
            name=request.name,
            description=request.description,
            parent_group_id=request.parent_group_id,
            user_id="api_user"
        )
        
        return DashboardResponse(
            success=True,
            message="Group created successfully",
            data=group.dict()
        ).dict()
    except Exception as e:
        print(f"Error creating group: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/dashboard/groups/{group_id}")
async def update_dashboard_group(
    group_id: str, 
    name: Optional[str] = None,
    description: Optional[str] = None,
    policy_ids: Optional[List[str]] = None
):
    """Update group information"""
    try:
        success = dashboard_manager.update_group(
            group_id=group_id,
            name=name,
            description=description,
            policy_ids=policy_ids,
            user_id="api_user"
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Group not found")
        
        return DashboardResponse(
            success=True,
            message="Group updated successfully",
            data={"group_id": group_id}
        ).dict()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating group: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/dashboard/groups/{group_id}")
async def delete_dashboard_group(group_id: str):
    """Delete policy group"""
    try:
        success = dashboard_manager.delete_group(group_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Group not found or cannot be deleted")
        
        return DashboardResponse(
            success=True,
            message="Group deleted successfully",
            data={"group_id": group_id}
        ).dict()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting group: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Tag Management

@app.get("/dashboard/tags")
async def get_dashboard_tags():
    """Get all dashboard tags"""
    try:
        tags = dashboard_manager.get_all_tags()
        
        return DashboardResponse(
            success=True,
            message=f"Retrieved {len(tags)} tags",
            data={
                "tags": tags,
                "total_count": len(tags)
            }
        ).dict()
    except Exception as e:
        print(f"Error fetching tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dashboard/tags")
async def create_dashboard_tag(request: CreateTagRequest):
    """Create new policy tag"""
    try:
        tag = dashboard_manager.create_tag(
            name=request.name,
            description=request.description,
            color=request.color,
            user_id="api_user"
        )
        
        return DashboardResponse(
            success=True,
            message="Tag created successfully",
            data=tag.dict()
        ).dict()
    except Exception as e:
        print(f"Error creating tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/dashboard/tags/{tag_id}")
async def update_dashboard_tag(
    tag_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None
):
    """Update tag information"""
    try:
        success = dashboard_manager.update_tag(
            tag_id=tag_id,
            name=name,
            description=description,
            color=color
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        return DashboardResponse(
            success=True,
            message="Tag updated successfully",
            data={"tag_id": tag_id}
        ).dict()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/dashboard/tags/{tag_id}")
async def delete_dashboard_tag(tag_id: str):
    """Delete policy tag"""
    try:
        success = dashboard_manager.delete_tag(tag_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        return DashboardResponse(
            success=True,
            message="Tag deleted successfully",
            data={"tag_id": tag_id}
        ).dict()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Statistics and Dashboard Overview

@app.get("/dashboard/statistics")
async def get_dashboard_statistics():
    """Get comprehensive dashboard statistics"""
    try:
        stats = dashboard_manager.get_dashboard_statistics()
        
        return DashboardResponse(
            success=True,
            message="Statistics retrieved successfully",
            data=stats
        ).dict()
    except Exception as e:
        print(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/compliance-summary")
async def get_compliance_summary():
    """Get compliance summary by category and priority"""
    try:
        summary = dashboard_manager.get_compliance_summary()
        
        return DashboardResponse(
            success=True,
            message="Compliance summary retrieved successfully",
            data=summary
        ).dict()
    except Exception as e:
        print(f"Error fetching compliance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/recent-changes")
async def get_recent_changes(hours: int = 24, limit: int = 100):
    """Get recent changes across all policies"""
    try:
        changes = dashboard_manager.get_recent_changes(hours=hours, limit=limit)
        
        return DashboardResponse(
            success=True,
            message=f"Retrieved {len(changes)} recent changes",
            data={
                "changes": changes,
                "hours": hours,
                "limit": limit
            }
        ).dict()
    except Exception as e:
        print(f"Error fetching recent changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/batch-changes/{batch_id}")
async def get_batch_changes(batch_id: str):
    """Get all changes from a specific batch operation"""
    try:
        changes = dashboard_manager.get_batch_changes(batch_id)
        
        return DashboardResponse(
            success=True,
            message=f"Retrieved {len(changes)} batch changes",
            data={
                "changes": changes,
                "batch_id": batch_id
            }
        ).dict()
    except Exception as e:
        print(f"Error fetching batch changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Documentation Management

@app.get("/dashboard/policies/{policy_id}/documentation")
async def get_policy_documentation(policy_id: str):
    """Get documentation for specific policy"""
    try:
        documentation = dashboard_manager.get_policy_documentation(policy_id)
        
        return DashboardResponse(
            success=True,
            message="Documentation retrieved successfully",
            data={
                "policy_id": policy_id,
                "documentation": documentation
            }
        ).dict()
    except Exception as e:
        print(f"Error fetching documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/dashboard/policies/{policy_id}/documentation")
async def update_policy_documentation(
    policy_id: str,
    notes: Optional[str] = None,
    cis_reference: Optional[str] = None,
    rationale: Optional[str] = None,
    impact_assessment: Optional[str] = None,
    remediation_steps: Optional[str] = None,
    related_policies: Optional[List[str]] = None,
    external_links: Optional[List[str]] = None
):
    """Update policy documentation"""
    try:
        success = dashboard_manager.update_policy_documentation(
            policy_id=policy_id,
            notes=notes,
            cis_reference=cis_reference,
            rationale=rationale,
            impact_assessment=impact_assessment,
            remediation_steps=remediation_steps,
            related_policies=related_policies,
            external_links=external_links,
            user_id="api_user"
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        return DashboardResponse(
            success=True,
            message="Documentation updated successfully",
            data={"policy_id": policy_id}
        ).dict()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Export/Import Management

@app.post("/dashboard/export")
async def export_dashboard_data(
    export_type: str = "full",
    policy_ids: Optional[List[str]] = None
):
    """Export dashboard data for backup or sharing"""
    try:
        export_data = dashboard_manager.export_dashboard_data(
            export_type=export_type,
            policy_ids=policy_ids
        )
        
        return DashboardResponse(
            success=True,
            message="Dashboard data exported successfully",
            data=export_data.dict()
        ).dict()
    except Exception as e:
        print(f"Error exporting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dashboard/import")
async def import_dashboard_data(import_data: Dict[str, Any], merge: bool = True):
    """Import dashboard data from export"""
    try:
        # Convert dict to DashboardExport object
        from models_dashboard import DashboardExport
        export_obj = DashboardExport(**import_data)
        
        result = dashboard_manager.import_dashboard_data(export_obj, merge=merge)
        
        return DashboardResponse(
            success=True,
            message="Dashboard data imported successfully",
            data=result
        ).dict()
    except Exception as e:
        print(f"Error importing dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =================================================================
# DEPLOYMENT API ENDPOINTS (Step 4)
# =================================================================

@app.get("/deployment/packages")
async def get_deployment_packages():
    """Get all deployment packages"""
    try:
        packages = deployment_manager.get_all_packages()
        serialized_packages = [serialize_deployment_package(pkg) for pkg in packages]
        
        return {
            "success": True,
            "message": "Deployment packages retrieved successfully",
            "data": {
                "packages": serialized_packages,
                "total": len(serialized_packages)
            }
        }
    except Exception as e:
        print(f"Error getting deployment packages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deployment/packages/{package_id}")
async def get_deployment_package(package_id: str):
    """Get deployment package by ID"""
    try:
        package = deployment_manager.get_package(package_id)
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        return {
            "success": True,
            "message": "Package retrieved successfully",
            "data": serialize_deployment_package(package)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting deployment package: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deployment/packages")
async def create_deployment_package(request: CreatePackageRequest):
    """Create new deployment package"""
    try:
        # Get policies from dashboard based on filters
        # Use mutually exclusive selection logic
        policies = []
        
        # Priority 1: Get policies from a template
        if request.template_id:
            try:
                template_export = template_manager.get_template_with_policies(request.template_id)
                if template_export and template_export.policies:
                    # Convert template policies to dashboard format
                    for template_policy in template_export.policies:
                        policy_dict = template_policy.dict()
                        # Map policy_id to id field
                        if 'policy_id' in policy_dict:
                            policy_dict['id'] = policy_dict['policy_id']
                        policies.append(policy_dict)
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"Template not found or error loading template: {str(e)}")
        
        # Priority 2: Get specific policies by ID
        elif request.policy_ids:
            for policy_id in request.policy_ids:
                if policy_id in dashboard_manager.policies_cache:
                    policy = dashboard_manager.policies_cache[policy_id]
                    policy_dict = policy.dict()
                    # Map policy_id to id field
                    if 'policy_id' in policy_dict:
                        policy_dict['id'] = policy_dict['policy_id']
                    policies.append(policy_dict)
        
        # Priority 3: Get policies by groups
        elif request.group_names:
            # Find group IDs by name first
            group_ids = []
            for group_name in request.group_names:
                for group in dashboard_manager.groups_cache.values():
                    if group.name == group_name:
                        group_ids.append(group.group_id)
                        break
            
            # Get policies that belong to these groups
            if group_ids:
                for policy in dashboard_manager.policies_cache.values():
                    if any(gid in policy.group_ids for gid in group_ids):
                        policy_dict = policy.dict()
                        # Map policy_id to id field
                        if 'policy_id' in policy_dict:
                            policy_dict['id'] = policy_dict['policy_id']
                        policies.append(policy_dict)
        
        # Priority 4: Get policies by tags
        elif request.tag_names:
            # Find tag IDs by name first
            tag_ids = []
            for tag_name in request.tag_names:
                for tag in dashboard_manager.tags_cache.values():
                    if tag.name == tag_name:
                        tag_ids.append(tag.tag_id)
                        break
            
            # Get policies that have these tags
            if tag_ids:
                for policy in dashboard_manager.policies_cache.values():
                    if any(tid in policy.tag_ids for tid in tag_ids):
                        policy_dict = policy.dict()
                        # Map policy_id to id field
                        if 'policy_id' in policy_dict:
                            policy_dict['id'] = policy_dict['policy_id']
                        policies.append(policy_dict)
        
        # Priority 5: Get policies by categories
        elif request.categories:
            # Get policies that match the specified categories
            for policy in dashboard_manager.policies_cache.values():
                policy_category = policy.category if hasattr(policy, 'category') else policy.dict().get('category', '')
                if policy_category in request.categories:
                    policy_dict = policy.dict()
                    # Map policy_id to id field
                    if 'policy_id' in policy_dict:
                        policy_dict['id'] = policy_dict['policy_id']
                    policies.append(policy_dict)
        
        # Priority 6 (Fallback): Get all policies if no specific filter
        else:
            all_policies = dashboard_manager.get_all_policies()
            policies = all_policies  # These are already dict objects
        
        # Debug logging
        print(f"DEBUG: Dashboard policies count: {len(dashboard_manager.policies_cache)}")
        print(f"DEBUG: Selected policies count: {len(policies)}")
        print(f"DEBUG: Selection method - template: {request.template_id}, policy_ids: {request.policy_ids}, groups: {request.group_names}, tags: {request.tag_names}, categories: {request.categories}")
        
        # Map policy_id to id field expected by deployment manager
        for policy in policies:
            if 'policy_id' in policy and 'id' not in policy:
                policy['id'] = policy['policy_id']
            # Ensure required fields have defaults if missing
            if 'name' not in policy:
                policy['name'] = policy.get('title', policy.get('policy_name', 'Unknown Policy'))
            if 'description' not in policy:
                policy['description'] = policy.get('description', 'No description available')
            if 'category' not in policy:
                policy['category'] = policy.get('category', 'Uncategorized')
        
        # Remove duplicates
        seen_ids = set()
        unique_policies = []
        for policy in policies:
            if policy.get('id') not in seen_ids:
                unique_policies.append(policy)
                seen_ids.add(policy.get('id'))
        
        if not unique_policies:
            raise HTTPException(status_code=400, detail="No policies found for deployment")
        
        # Create export configuration
        formats = []
        if request.include_formats:
            for fmt in request.include_formats:
                try:
                    formats.append(PackageFormat(fmt))
                except ValueError:
                    pass
        else:
            # Default formats
            formats = [PackageFormat.LGPO_POL, PackageFormat.REGISTRY_REG, PackageFormat.POWERSHELL_PS1]
        
        export_config = PolicyExportConfig(
            target_os=WindowsVersion(request.target_os),
            include_formats=formats,
            include_scripts=request.include_scripts,
            include_documentation=request.include_documentation,
            include_verification=request.include_verification,
            create_zip_package=request.create_zip_package,
            package_name=request.name
        )
        
        # Create script configuration
        script_config = ScriptConfiguration(
            use_powershell=request.use_powershell,
            use_batch=request.use_batch,
            require_admin=request.require_admin,
            create_backup=request.create_backup,
            verify_before_apply=request.verify_before_apply,
            log_changes=request.log_changes,
            rollback_support=request.rollback_support
        )
        
        # Create deployment package
        package_id = deployment_manager.create_deployment_package(
            name=request.name,
            description=request.description,
            policies=unique_policies,
            export_config=export_config,
            script_config=script_config,
            groups=request.group_names or [],
            tags=request.tag_names or []
        )
        
        return {
            "success": True,
            "message": "Deployment package created successfully",
            "data": {
                "package_id": package_id,
                "policies_count": len(unique_policies)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating deployment package: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deployment/packages/{package_id}/build")
async def build_deployment_package(package_id: str, background_tasks: BackgroundTasks):
    """Start building deployment package"""
    try:
        package = deployment_manager.get_package(package_id)
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        if package.status in [DeploymentStatus.PROCESSING, DeploymentStatus.COMPLETED]:
            return {
                "success": False,
                "message": f"Package is already {package.status.value}",
                "data": {"package_id": package_id, "status": package.status.value}
            }
        
        # Start package creation in background
        job_id = deployment_manager.start_package_creation(package_id)
        
        return {
            "success": True,
            "message": "Package build started",
            "data": {
                "package_id": package_id,
                "job_id": job_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error starting package build: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deployment/jobs/{job_id}")
async def get_deployment_job_status(job_id: str):
    """Get deployment job status"""
    try:
        job = deployment_manager.get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "success": True,
            "message": "Job status retrieved successfully",
            "data": {
                "job_id": job.job_id,
                "package_id": job.package_id,
                "status": job.status.value,
                "progress": job.progress,
                "current_step": job.current_step,
                "completed_steps": job.completed_steps,
                "total_steps": job.total_steps,
                "start_time": job.start_time.isoformat(),
                "estimated_completion": job.estimated_completion.isoformat() if job.estimated_completion else None,
                "error_message": job.error_message,
                "log_messages": job.log_messages[-10:]  # Last 10 log messages
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/deployment/packages/{package_id}")
async def delete_deployment_package(package_id: str):
    """Delete deployment package"""
    try:
        success = deployment_manager.delete_package(package_id)
        if not success:
            raise HTTPException(status_code=404, detail="Package not found or could not be deleted")
        
        return {
            "success": True,
            "message": "Package deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting package: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deployment/statistics")
async def get_deployment_statistics():
    """Get deployment statistics"""
    try:
        stats = deployment_manager.get_package_statistics()
        
        return {
            "success": True,
            "message": "Statistics retrieved successfully",
            "data": stats
        }
        
    except Exception as e:
        print(f"Error getting deployment statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deployment/windows-versions")
async def get_supported_windows_versions():
    """Get supported Windows versions for deployment"""
    try:
        versions = [
            {
                "value": version.value,
                "name": version.value.replace('_', ' ').title(),
                "description": f"Deployment package for {version.value.replace('_', ' ').title()}"
            }
            for version in WindowsVersion
        ]
        
        return {
            "success": True,
            "message": "Supported Windows versions retrieved successfully",
            "data": {
                "versions": versions,
                "total": len(versions)
            }
        }
        
    except Exception as e:
        print(f"Error getting Windows versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deployment/package-formats")
async def get_supported_package_formats():
    """Get supported package formats"""
    try:
        formats = [
            {
                "value": fmt.value,
                "name": fmt.value.replace('_', ' ').upper(),
                "description": {
                    PackageFormat.LGPO_POL: "LGPO .pol files for Group Policy import",
                    PackageFormat.LGPO_INF: "LGPO .inf security template files",
                    PackageFormat.REGISTRY_REG: "Registry .reg files for direct import",
                    PackageFormat.POWERSHELL_PS1: "PowerShell scripts for automated deployment",
                    PackageFormat.BATCH_BAT: "Batch files for Windows deployment"
                }.get(fmt, "Unknown format")
            }
            for fmt in PackageFormat
        ]
        
        return {
            "success": True,
            "message": "Supported package formats retrieved successfully",
            "data": {
                "formats": formats,
                "total": len(formats)
            }
        }
        
    except Exception as e:
        print(f"Error getting package formats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deployment/lgpo/status")
async def get_lgpo_status():
    """Get LGPO.exe availability status"""
    try:
        is_available = lgpo_manager.is_available()
        version = lgpo_manager.get_version() if is_available else None
        
        return {
            "success": True,
            "message": "LGPO status retrieved successfully",
            "data": {
                "available": is_available,
                "version": version,
                "path": lgpo_manager.lgpo_path,
                "installation_instructions": lgpo_manager.get_installation_instructions()
            }
        }
        
    except Exception as e:
        print(f"Error getting LGPO status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deployment/packages/{package_id}/download")
async def download_deployment_package(package_id: str):
    """Download deployment package"""
    try:
        package = deployment_manager.get_package(package_id)
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        if package.status != DeploymentStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Package is not ready for download")
        
        if not package.package_path or not os.path.exists(package.package_path):
            raise HTTPException(status_code=404, detail="Package file not found")
        
        filename = os.path.basename(package.package_path)
        
        return FileResponse(
            path=package.package_path,
            filename=filename,
            media_type='application/zip' if filename.endswith('.zip') else 'application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading package: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deployment/packages/{package_id}/validate")
async def validate_deployment_package(package_id: str):
    """Validate deployment package integrity"""
    try:
        package = deployment_manager.get_package(package_id)
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        # Run validation
        validation_result = deployment_manager._validate_package(package)
        
        return {
            "success": True,
            "message": "Package validation completed",
            "data": {
                "is_valid": validation_result.is_valid,
                "total_checks": validation_result.total_checks,
                "passed_checks": validation_result.passed_checks,
                "failed_checks": validation_result.failed_checks,
                "warnings": validation_result.warnings,
                "errors": validation_result.errors,
                "check_details": validation_result.check_details,
                "validation_time": validation_result.validation_time.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error validating package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =================================================================
# IMPORT/EXPORT API ENDPOINTS (Step 5)
# =================================================================

@app.post("/import-export/export")
async def export_data(request: ExportRequest, background_tasks: BackgroundTasks):
    """Export data in specified format"""
    try:
        # Get data based on export type
        data_to_export = []
        
        if request.export_type == "policies":
            # Export policies from dashboard
            if request.item_ids:
                for policy_id in request.item_ids:
                    if policy_id in dashboard_manager.policies_cache:
                        data_to_export.append(dashboard_manager.policies_cache[policy_id].dict())
            else:
                all_policies = dashboard_manager.get_all_policies(include_metadata=request.include_metadata)
                data_to_export = all_policies
        
        elif request.export_type == "templates":
            # Export templates
            if request.item_ids:
                for template_id in request.item_ids:
                    template = template_manager.get_template(template_id)
                    if template:
                        data_to_export.append(template.dict())
            else:
                templates = template_manager.get_all_templates()
                data_to_export = [t.dict() for t in templates]
        
        elif request.export_type == "groups":
            # Export groups from dashboard
            if request.group_names:
                for group_name in request.group_names:
                    for group in dashboard_manager.groups_cache.values():
                        if group.name == group_name:
                            data_to_export.append(group.dict())
                            break
            else:
                groups = dashboard_manager.get_all_groups()
                data_to_export = groups
        
        elif request.export_type == "tags":
            # Export tags from dashboard
            if request.tag_names:
                for tag_name in request.tag_names:
                    for tag in dashboard_manager.tags_cache.values():
                        if tag.name == tag_name:
                            data_to_export.append(tag.dict())
                            break
            else:
                tags = dashboard_manager.get_all_tags()
                data_to_export = tags
        
        elif request.export_type == "documentation":
            # Export documentation
            data_to_export = []
            for doc in documentation_manager.documentation_cache.values():
                if request.item_ids is None or doc.doc_id in request.item_ids:
                    data_to_export.append(doc.__dict__)
        
        elif request.export_type == "full_backup":
            # Full system backup
            data_to_export = {
                "policies": dashboard_manager.get_all_policies(include_metadata=request.include_metadata),
                "templates": [t.dict() for t in template_manager.get_all_templates()],
                "groups": dashboard_manager.get_all_groups(),
                "tags": dashboard_manager.get_all_tags(),
                "documentation": [doc.__dict__ for doc in documentation_manager.documentation_cache.values()]
            }
        
        # Apply filters
        if request.filter_criteria and isinstance(data_to_export, list):
            filtered_data = []
            for item in data_to_export:
                should_include = True
                for key, value in request.filter_criteria.items():
                    if key in item and item[key] != value:
                        should_include = False
                        break
                if should_include:
                    filtered_data.append(item)
            data_to_export = filtered_data
        
        # Create export configuration
        export_config = ExportConfiguration(
            export_type=ImportExportType(request.export_type),
            format=ImportExportFormat(request.format),
            include_metadata=request.include_metadata,
            include_history=request.include_history,
            include_documentation=request.include_documentation,
            compress_output=request.compress_output
        )
        
        # Perform export
        operation_id = import_export_manager.export_data(
            data=data_to_export,
            config=export_config
        )
        
        operation = import_export_manager.get_operation(operation_id)
        
        return {
            "success": True,
            "message": f"Export started successfully",
            "data": {
                "operation_id": operation_id,
                "export_type": request.export_type,
                "format": request.format,
                "status": operation.status.value,
                "items_count": len(data_to_export) if isinstance(data_to_export, list) else 1
            }
        }
        
    except Exception as e:
        print(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/import-export/validate")
async def validate_import_file(file: UploadFile = File(...)):
    """Validate import file before importing"""
    try:
        # Save uploaded file temporarily
        temp_filename = f"temp_validate_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        temp_path = os.path.join("uploads", temp_filename)
        
        async with aiofiles.open(temp_path, 'wb') as temp_file:
            content = await file.read()
            await temp_file.write(content)
        
        # Validate the file
        validation_result = import_export_manager.validate_import_file(temp_path)
        
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return {
            "success": True,
            "message": "File validation completed",
            "data": {
                "is_valid": validation_result.is_valid,
                "detected_format": validation_result.detected_format.value if validation_result.detected_format else None,
                "detected_type": validation_result.detected_type.value if validation_result.detected_type else None,
                "total_items": validation_result.total_items,
                "valid_items": validation_result.valid_items,
                "invalid_items": validation_result.invalid_items,
                "warnings": validation_result.warnings,
                "errors": validation_result.errors
            }
        }
        
    except Exception as e:
        print(f"Error validating import file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/import-export/import")
async def import_data(request: ImportRequest, file: UploadFile = File(...)):
    """Import data from file"""
    try:
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"import_{timestamp}_{file.filename}"
        file_path = os.path.join("uploads", filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create import configuration
        import_config = ImportConfiguration(
            import_type=ImportExportType(request.import_type),
            format=ImportExportFormat(request.format),
            conflict_resolution=ConflictResolution(request.conflict_resolution),
            validate_before_import=request.validate_before_import,
            create_backup_before_import=request.create_backup_before_import,
            merge_documentation=request.merge_documentation,
            preserve_ids=request.preserve_ids,
            skip_invalid_items=request.skip_invalid_items
        )
        
        # Perform import
        operation_id = import_export_manager.import_data(file_path, import_config)
        operation = import_export_manager.get_operation(operation_id)
        
        return {
            "success": True,
            "message": "Import started successfully",
            "data": {
                "operation_id": operation_id,
                "import_type": request.import_type,
                "format": request.format,
                "status": operation.status.value
            }
        }
        
    except Exception as e:
        print(f"Error importing data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/import-export/operations")
async def get_import_export_operations(
    operation_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get import/export operations with filtering"""
    try:
        operations = []
        for operation in import_export_manager.operations_cache.values():
            # Apply filters
            if operation_type and operation.operation_type.value != operation_type:
                continue
            if status and operation.status.value != status:
                continue
            
            operations.append(serialize_import_export_operation(operation))
        
        # Sort by timestamp (newest first)
        operations.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply pagination
        total = len(operations)
        operations = operations[offset:offset + limit]
        
        return {
            "success": True,
            "message": f"Retrieved {len(operations)} operations",
            "data": {
                "operations": operations,
                "total": total,
                "offset": offset,
                "limit": limit
            }
        }
        
    except Exception as e:
        print(f"Error getting operations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/import-export/operations/{operation_id}")
async def get_import_export_operation(operation_id: str):
    """Get specific import/export operation"""
    try:
        operation = import_export_manager.get_operation(operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Operation not found")
        
        return {
            "success": True,
            "message": "Operation retrieved successfully",
            "data": serialize_import_export_operation(operation)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/import-export/operations/{operation_id}/rollback")
async def rollback_import_operation(operation_id: str):
    """Rollback an import operation"""
    try:
        success = import_export_manager.rollback_import(operation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Operation not found or cannot be rolled back")
        
        return {
            "success": True,
            "message": "Import operation rolled back successfully",
            "data": {"operation_id": operation_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error rolling back operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/import-export/operations/{operation_id}")
async def delete_import_export_operation(operation_id: str):
    """Delete import/export operation record"""
    try:
        success = import_export_manager.delete_operation(operation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Operation not found")
        
        return {
            "success": True,
            "message": "Operation deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/import-export/download/{operation_id}")
async def download_export_file(operation_id: str):
    """Download exported file"""
    try:
        operation = import_export_manager.get_operation(operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Operation not found")
        
        if operation.operation_type != ImportExportType.EXPORT:
            raise HTTPException(status_code=400, detail="Operation is not an export")
        
        if operation.status != ImportStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Export is not completed")
        
        if not operation.file_path or not os.path.exists(operation.file_path):
            raise HTTPException(status_code=404, detail="Export file not found")
        
        filename = os.path.basename(operation.file_path)
        
        return FileResponse(
            path=operation.file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading export: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================================================================
# DOCUMENTATION MANAGEMENT API ENDPOINTS (Step 5)
# =================================================================

@app.post("/documentation")
async def create_documentation(request: DocumentationRequest):
    """Create new documentation item"""
    try:
        doc_id = documentation_manager.create_documentation(
            title=request.title,
            content=request.content,
            doc_type=DocumentationType(request.doc_type),
            associated_policies=request.associated_policies,
            associated_groups=request.associated_groups,
            associated_templates=request.associated_templates,
            tags=request.tags
        )
        
        return {
            "success": True,
            "message": "Documentation created successfully",
            "data": {"doc_id": doc_id}
        }
        
    except Exception as e:
        print(f"Error creating documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documentation/import")
async def import_documentation_file(file: UploadFile = File(...)):
    """Import documentation from file"""
    try:
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"doc_{timestamp}_{file.filename}"
        file_path = os.path.join("uploads", filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Import documentation
        doc_id = documentation_manager.import_documentation_file(file_path)
        
        return {
            "success": True,
            "message": "Documentation imported successfully",
            "data": {"doc_id": doc_id, "file_path": file_path}
        }
        
    except Exception as e:
        print(f"Error importing documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documentation")
async def get_all_documentation(
    doc_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get all documentation items"""
    try:
        all_docs = list(documentation_manager.documentation_cache.values())
        
        # Apply type filter
        if doc_type:
            all_docs = [doc for doc in all_docs if doc.doc_type.value == doc_type]
        
        # Sort by creation time (newest first)
        all_docs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        total = len(all_docs)
        docs = all_docs[offset:offset + limit]
        
        # Convert to dict
        docs_data = [doc.__dict__ for doc in docs]
        for doc_data in docs_data:
            # Convert datetime to string
            if 'created_at' in doc_data and doc_data['created_at']:
                doc_data['created_at'] = doc_data['created_at'].isoformat()
            if 'updated_at' in doc_data and doc_data['updated_at']:
                doc_data['updated_at'] = doc_data['updated_at'].isoformat()
            # Convert enum to string
            if 'doc_type' in doc_data and hasattr(doc_data['doc_type'], 'value'):
                doc_data['doc_type'] = doc_data['doc_type'].value
        
        return {
            "success": True,
            "message": f"Retrieved {len(docs)} documentation items",
            "data": {
                "documentation": docs_data,
                "total": total,
                "offset": offset,
                "limit": limit
            }
        }
        
    except Exception as e:
        print(f"Error getting documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documentation/{doc_id}")
async def get_documentation(doc_id: str):
    """Get specific documentation item"""
    try:
        doc = documentation_manager.get_documentation(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Documentation not found")
        
        doc_data = doc.__dict__.copy()
        # Convert datetime to string
        if 'created_at' in doc_data and doc_data['created_at']:
            doc_data['created_at'] = doc_data['created_at'].isoformat()
        if 'updated_at' in doc_data and doc_data['updated_at']:
            doc_data['updated_at'] = doc_data['updated_at'].isoformat()
        # Convert enum to string
        if 'doc_type' in doc_data and hasattr(doc_data['doc_type'], 'value'):
            doc_data['doc_type'] = doc_data['doc_type'].value
        
        return {
            "success": True,
            "message": "Documentation retrieved successfully",
            "data": doc_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/documentation/{doc_id}")
async def update_documentation(
    doc_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None
):
    """Update documentation item"""
    try:
        success = documentation_manager.update_documentation(
            doc_id=doc_id,
            title=title,
            content=content,
            tags=tags
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Documentation not found")
        
        return {
            "success": True,
            "message": "Documentation updated successfully",
            "data": {"doc_id": doc_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documentation/{doc_id}")
async def delete_documentation(doc_id: str):
    """Delete documentation item"""
    try:
        success = documentation_manager.delete_documentation(doc_id)
        if not success:
            raise HTTPException(status_code=404, detail="Documentation not found")
        
        return {
            "success": True,
            "message": "Documentation deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documentation/{doc_id}/associate")
async def associate_documentation(doc_id: str, request: AssociateDocumentationRequest):
    """Associate documentation with policies, groups, or templates"""
    try:
        success = documentation_manager.associate_documentation(
            doc_id=doc_id,
            policy_ids=request.policy_ids,
            group_ids=request.group_ids,
            template_ids=request.template_ids
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Documentation not found")
        
        return {
            "success": True,
            "message": "Documentation associations updated successfully",
            "data": {"doc_id": doc_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error associating documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documentation/search")
async def search_documentation(
    query: str,
    doc_type: Optional[str] = None,
    policy_id: Optional[str] = None,
    group_id: Optional[str] = None,
    template_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50
):
    """Search documentation"""
    try:
        results = documentation_manager.search_documentation(
            query=query,
            doc_type=DocumentationType(doc_type) if doc_type else None,
            policy_id=policy_id,
            group_id=group_id,
            template_id=template_id,
            tags=tags,
            limit=limit
        )
        
        # Convert to dict
        docs_data = []
        for doc in results:
            doc_data = doc.__dict__.copy()
            # Convert datetime to string
            if 'created_at' in doc_data and doc_data['created_at']:
                doc_data['created_at'] = doc_data['created_at'].isoformat()
            if 'updated_at' in doc_data and doc_data['updated_at']:
                doc_data['updated_at'] = doc_data['updated_at'].isoformat()
            # Convert enum to string
            if 'doc_type' in doc_data and hasattr(doc_data['doc_type'], 'value'):
                doc_data['doc_type'] = doc_data['doc_type'].value
            docs_data.append(doc_data)
        
        return {
            "success": True,
            "message": f"Found {len(results)} documentation items",
            "data": {
                "documentation": docs_data,
                "query": query,
                "total": len(results)
            }
        }
        
    except Exception as e:
        print(f"Error searching documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documentation/statistics")
async def get_documentation_statistics():
    """Get documentation statistics"""
    try:
        stats = documentation_manager.get_documentation_statistics()
        
        return {
            "success": True,
            "message": "Documentation statistics retrieved successfully",
            "data": stats
        }
        
    except Exception as e:
        print(f"Error getting documentation statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =================================================================
# AUDIT, TEST & REPORTING API ENDPOINTS (Step 6)
# =================================================================

@app.post("/audit/configurations")
async def create_audit_configuration(request: AuditConfigurationRequest):
    """Create new audit configuration"""
    try:
        # Convert string scope to enum
        scope = AuditScope(request.scope)
        
        # Convert report formats
        report_formats = []
        if request.report_formats:
            for fmt in request.report_formats:
                try:
                    report_formats.append(ReportFormat(fmt))
                except ValueError:
                    pass
        else:
            report_formats = [ReportFormat.HTML, ReportFormat.CSV]
        
        # Create configuration
        config = audit_manager.create_audit_configuration(
            name=request.name,
            description=request.description,
            scope=scope,
            policy_ids=request.policy_ids or [],
            group_names=request.group_names or [],
            cis_levels=request.cis_levels or [1, 2],
            categories=request.categories or [],
            parallel_execution=request.parallel_execution,
            max_workers=request.max_workers,
            timeout_seconds=request.timeout_seconds,
            generate_report=request.generate_report,
            report_formats=report_formats,
            target_system=request.target_system
        )
        
        return {
            "success": True,
            "message": "Audit configuration created successfully",
            "data": {
                "audit_id": config.audit_id,
                "name": config.name,
                "scope": config.scope.value,
                "created_at": config.created_at.isoformat()
            }
        }
        
    except Exception as e:
        print(f"Error creating audit configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/configurations")
async def get_audit_configurations():
    """Get all audit configurations"""
    try:
        configurations = []
        for config_id, config in audit_manager.configuration_cache.items():
            config_data = config.__dict__ if hasattr(config, '__dict__') else config
            configurations.append({
                "audit_id": config_id,
                "name": config_data.get("name", "Unknown"),
                "description": config_data.get("description", ""),
                "scope": config_data.get("scope", "full_system"),
                "created_at": config_data.get("created_at", "")
            })
        
        return {
            "success": True,
            "message": f"Retrieved {len(configurations)} audit configurations",
            "data": {
                "configurations": configurations,
                "total": len(configurations)
            }
        }
        
    except Exception as e:
        print(f"Error getting audit configurations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audit/start")
async def start_audit(request: AuditConfigurationRequest):
    """Start a new audit with the given configuration"""
    try:
        # Create configuration
        scope = AuditScope(request.scope)
        
        config = AuditConfiguration(
            name=request.name,
            description=request.description,
            scope=scope,
            policy_ids=request.policy_ids or [],
            group_names=request.group_names or [],
            cis_levels=request.cis_levels or [1, 2],
            categories=request.categories or [],
            parallel_execution=request.parallel_execution,
            max_workers=request.max_workers,
            timeout_seconds=request.timeout_seconds,
            generate_report=request.generate_report,
            target_system=request.target_system
        )
        
        # Start audit
        audit_id = audit_manager.start_audit(config, "dashboard")
        
        return {
            "success": True,
            "message": "Audit started successfully",
            "data": {
                "audit_id": audit_id,
                "name": config.name,
                "scope": config.scope.value
            }
        }
        
    except Exception as e:
        print(f"Error starting audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/runs")
async def get_audit_runs(
    status: Optional[str] = None,
    limit: int = 50
):
    """Get audit runs with optional status filtering"""
    try:
        history = audit_manager.get_audit_history(limit)
        
        # Filter by status if provided
        if status:
            history = [h for h in history if h.get('status') == status]
        
        return {
            "success": True,
            "message": f"Retrieved {len(history)} audit runs",
            "data": {
                "audit_runs": history,
                "total": len(history)
            }
        }
        
    except Exception as e:
        print(f"Error getting audit runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/runs/{audit_id}")
async def get_audit_run(audit_id: str):
    """Get specific audit run with detailed results"""
    try:
        audit_run = audit_manager.get_audit_status(audit_id)
        if not audit_run:
            raise HTTPException(status_code=404, detail="Audit run not found")
        
        # Serialize the audit run
        serialized_run = serialize_audit_run(audit_run)
        
        return {
            "success": True,
            "message": "Audit run retrieved successfully",
            "data": serialized_run
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting audit run: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/runs/{audit_id}/status")
async def get_audit_status(audit_id: str):
    """Get current status of an audit run"""
    try:
        audit_run = audit_manager.get_audit_status(audit_id)
        if not audit_run:
            raise HTTPException(status_code=404, detail="Audit run not found")
        
        return {
            "success": True,
            "message": "Audit status retrieved successfully",
            "data": {
                "audit_id": audit_run.audit_id,
                "name": audit_run.configuration.name,
                "status": audit_run.status.value,
                "progress_percentage": audit_run.progress_percentage,
                "current_policy": audit_run.current_policy,
                "completed_policies": audit_run.completed_policies,
                "start_time": audit_run.start_time.isoformat() if audit_run.start_time else None,
                "end_time": audit_run.end_time.isoformat() if audit_run.end_time else None,
                "duration_seconds": audit_run.duration_seconds,
                "error_message": audit_run.error_message,
                "compliance_percentage": audit_run.summary.compliance_percentage if audit_run.summary else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting audit status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audit/runs/{audit_id}/cancel")
async def cancel_audit_run(audit_id: str):
    """Cancel a running audit"""
    try:
        success = audit_manager.cancel_audit(audit_id)
        if not success:
            raise HTTPException(status_code=404, detail="Audit run not found or cannot be cancelled")
        
        return {
            "success": True,
            "message": "Audit run cancelled successfully",
            "data": {"audit_id": audit_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error cancelling audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/audit/runs/{audit_id}")
async def delete_audit_run(audit_id: str):
    """Delete audit run and associated data"""
    try:
        success = audit_manager.delete_audit(audit_id)
        if not success:
            raise HTTPException(status_code=404, detail="Audit run not found or cannot be deleted")
        
        return {
            "success": True,
            "message": "Audit run deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting audit run: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audit/reports/generate")
async def generate_audit_report(request: GenerateReportRequest):
    """Generate audit report in specified format"""
    try:
        report_format = ReportFormat(request.format)
        
        report_path = audit_manager.generate_report(
            request.audit_id,
            report_format,
            request.template_name
        )
        
        return {
            "success": True,
            "message": "Report generated successfully",
            "data": {
                "audit_id": request.audit_id,
                "format": request.format,
                "template": request.template_name,
                "report_path": report_path,
                "download_url": f"/audit/reports/download/{request.audit_id}?format={request.format}"
            }
        }
        
    except Exception as e:
        print(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/reports/download/{audit_id}")
async def download_audit_report(audit_id: str, format: str = "html"):
    """Download generated audit report"""
    try:
        # Find the report file
        audit_run = audit_manager.get_audit_status(audit_id)
        if not audit_run:
            raise HTTPException(status_code=404, detail="Audit run not found")
        
        # Get report path from audit run or generate new report
        report_path = None
        if format in audit_run.report_paths:
            report_path = audit_run.report_paths[format]
        else:
            # Generate report if not exists
            report_format = ReportFormat(format)
            report_path = audit_manager.generate_report(audit_id, report_format)
        
        if not report_path or not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Report file not found")
        
        filename = os.path.basename(report_path)
        
        # Determine media type
        media_type_map = {
            "html": "text/html",
            "csv": "text/csv",
            "json": "application/json",
            "pdf": "application/pdf",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        
        media_type = media_type_map.get(format, "application/octet-stream")
        
        return FileResponse(
            path=report_path,
            filename=filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/statistics")
async def get_audit_statistics():
    """Get comprehensive audit statistics"""
    try:
        stats = audit_manager.get_audit_statistics()
        
        return {
            "success": True,
            "message": "Audit statistics retrieved successfully",
            "data": stats
        }
        
    except Exception as e:
        print(f"Error getting audit statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/trends")
async def get_compliance_trends(days: int = 30, system_id: Optional[str] = None):
    """Get compliance trends over specified period"""
    try:
        trends = audit_manager.get_compliance_trends(system_id, days)
        
        return {
            "success": True,
            "message": "Compliance trends retrieved successfully",
            "data": trends
        }
        
    except Exception as e:
        print(f"Error getting compliance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/search")
async def search_audit_results(
    query: str,
    audit_ids: Optional[List[str]] = None,
    result_types: Optional[List[str]] = None,
    limit: int = 100
):
    """Search audit results across multiple audits"""
    try:
        # Convert result types to enums if provided
        compliance_results = None
        if result_types:
            compliance_results = []
            for result_type in result_types:
                try:
                    compliance_results.append(ComplianceResult(result_type))
                except ValueError:
                    pass
        
        results = audit_manager.search_audit_results(
            query=query,
            audit_ids=audit_ids,
            result_types=compliance_results
        )
        
        # Limit results
        results = results[:limit]
        
        return {
            "success": True,
            "message": f"Found {len(results)} matching results",
            "data": {
                "results": results,
                "query": query,
                "total": len(results)
            }
        }
        
    except Exception as e:
        print(f"Error searching audit results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audit/compare")
async def compare_audit_runs(audit_id1: str, audit_id2: str):
    """Compare results between two audit runs"""
    try:
        comparison = audit_manager.compare_audits(audit_id1, audit_id2)
        
        return {
            "success": True,
            "message": "Audit comparison completed successfully",
            "data": comparison
        }
        
    except Exception as e:
        print(f"Error comparing audits: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/runs/{audit_id}/remediation")
async def get_remediation_summary(audit_id: str):
    """Get remediation summary for failed policies"""
    try:
        remediation = audit_manager.get_remediation_summary(audit_id)
        
        return {
            "success": True,
            "message": "Remediation summary retrieved successfully",
            "data": remediation
        }
        
    except Exception as e:
        print(f"Error getting remediation summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audit/export")
async def export_audit_data(audit_ids: Optional[List[str]] = None):
    """Export audit data for backup or analysis"""
    try:
        export_file = audit_manager.export_audit_data(audit_ids)
        
        return {
            "success": True,
            "message": "Audit data exported successfully",
            "data": {
                "export_file": export_file,
                "download_url": f"/audit/export/download/{os.path.basename(export_file)}"
            }
        }
        
    except Exception as e:
        print(f"Error exporting audit data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/export/download/{filename}")
async def download_audit_export(filename: str):
    """Download exported audit data"""
    try:
        export_path = os.path.join(audit_manager.data_dir, filename)
        
        if not os.path.exists(export_path):
            raise HTTPException(status_code=404, detail="Export file not found")
        
        return FileResponse(
            path=export_path,
            filename=filename,
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading export: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audit/cleanup")
async def cleanup_old_audits(days_to_keep: int = 90):
    """Clean up old audit results"""
    try:
        deleted_count = audit_manager.cleanup_old_audits(days_to_keep)
        
        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} old audit results",
            "data": {
                "deleted_count": deleted_count,
                "days_to_keep": days_to_keep
            }
        }
        
    except Exception as e:
        print(f"Error cleaning up audits: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/system-info")
async def get_system_info():
    """Get current system information for audit context"""
    try:
        system_info = audit_manager.audit_engine.get_system_info()
        
        return {
            "success": True,
            "message": "System information retrieved successfully",
            "data": {
                "hostname": system_info.hostname,
                "os_version": system_info.os_version,
                "os_build": system_info.os_build,
                "architecture": system_info.architecture,
                "domain": system_info.domain,
                "workgroup": system_info.workgroup,
                "scan_timestamp": system_info.scan_timestamp.isoformat(),
                "last_boot": system_info.last_boot.isoformat() if system_info.last_boot else None,
                "total_memory": system_info.total_memory,
                "cpu_info": system_info.cpu_info
            }
        }
        
    except Exception as e:
        print(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================
# REMEDIATION ENDPOINTS (STEP 7)
# =============================================

@app.post("/remediation/plan/create")
async def create_remediation_plan(request: CreateRemediationPlanRequest):
    """Create a new remediation plan from audit results"""
    try:
        plan = remediation_manager.create_remediation_plan(
            name=request.name,
            description=request.description,
            audit_id=request.audit_id,
            target_system=request.target_system,
            selective_policies=request.selective_policies,
            severity_filter=RemediationSeverity(request.severity_filter) if request.severity_filter else None,
            create_backup=request.create_backup,
            backup_type=BackupType(request.backup_type),
            require_confirmation=request.require_confirmation,
            continue_on_error=request.continue_on_error
        )
        
        return {
            "success": True,
            "message": "Remediation plan created successfully",
            "data": {
                "plan_id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "total_actions": len(plan.actions),
                "high_risk_actions": len([a for a in plan.actions if a.severity == RemediationSeverity.HIGH]),
                "backup_required": plan.backup_required,
                "requires_reboot": plan.requires_reboot,
                "estimated_duration": plan.estimated_duration,
                "created_at": plan.created_at.isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error creating remediation plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/remediation/plans")
async def list_remediation_plans():
    """Get all remediation plans with summary information"""
    try:
        plans = remediation_manager.list_remediation_plans()
        
        plans_data = []
        for plan in plans:
            plans_data.append({
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "status": plan.status.value,
                "target_system": plan.target_system,
                "total_actions": len(plan.actions),
                "completed_actions": len([a for a in plan.actions if a.status == RemediationStatus.COMPLETED]),
                "backup_required": plan.backup_required,
                "requires_reboot": plan.requires_reboot,
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
            })
        
        return {
            "success": True,
            "message": f"Retrieved {len(plans)} remediation plans",
            "data": {
                "plans": plans_data,
                "total_count": len(plans)
            }
        }
        
    except Exception as e:
        print(f"Error listing remediation plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/remediation/plan/{plan_id}")
async def get_remediation_plan_details(plan_id: str):
    """Get detailed information about a specific remediation plan"""
    try:
        plan = remediation_manager.get_remediation_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Remediation plan not found")
        
        actions_data = []
        for action in plan.actions:
            actions_data.append({
                "id": action.id,
                "type": action.type.value,
                "description": action.description,
                "policy_id": action.policy_id,
                "severity": action.severity.value,
                "status": action.status.value,
                "target_key": action.target_key,
                "target_value": action.target_value,
                "backup_value": action.backup_value,
                "requires_reboot": action.requires_reboot,
                "estimated_duration": action.estimated_duration,
                "error_message": action.error_message
            })
        
        return {
            "success": True,
            "message": "Remediation plan details retrieved successfully",
            "data": {
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "status": plan.status.value,
                "target_system": plan.target_system,
                "audit_id": plan.audit_id,
                "backup_id": plan.backup_id,
                "actions": actions_data,
                "backup_required": plan.backup_required,
                "requires_reboot": plan.requires_reboot,
                "estimated_duration": plan.estimated_duration,
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
                "execution_log": plan.execution_log
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting remediation plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/remediation/plan/{plan_id}/execute")
async def execute_remediation_plan(plan_id: str, request: ExecuteRemediationRequest):
    """Execute a remediation plan"""
    try:
        if request.plan_id != plan_id:
            raise HTTPException(status_code=400, detail="Plan ID mismatch")
        
        session = remediation_manager.execute_remediation_plan(
            plan_id=plan_id,
            operator=request.operator,
            confirm_high_risk=request.confirm_high_risk,
            dry_run=request.dry_run
        )
        
        return {
            "success": True,
            "message": "Remediation execution started successfully" if not request.dry_run else "Dry run completed successfully",
            "data": {
                "session_id": session.id,
                "plan_id": session.plan_id,
                "operator": session.operator,
                "dry_run": session.dry_run,
                "status": session.status.value,
                "started_at": session.started_at.isoformat(),
                "total_actions": session.total_actions,
                "completed_actions": session.completed_actions,
                "failed_actions": session.failed_actions,
                "warnings": session.warnings
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error executing remediation plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/remediation/session/{session_id}/status")
async def get_remediation_session_status(session_id: str):
    """Get the status of a remediation session"""
    try:
        session = remediation_manager.get_remediation_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Remediation session not found")
        
        return {
            "success": True,
            "message": "Remediation session status retrieved successfully",
            "data": {
                "session_id": session.id,
                "plan_id": session.plan_id,
                "status": session.status.value,
                "progress": (session.completed_actions / session.total_actions * 100) if session.total_actions > 0 else 0,
                "operator": session.operator,
                "dry_run": session.dry_run,
                "started_at": session.started_at.isoformat(),
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "total_actions": session.total_actions,
                "completed_actions": session.completed_actions,
                "failed_actions": session.failed_actions,
                "warnings": session.warnings,
                "error_message": session.error_message,
                "requires_reboot": session.requires_reboot
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting remediation session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/remediation/plan/{plan_id}/cancel")
async def cancel_remediation_plan(plan_id: str):
    """Cancel an active remediation plan execution"""
    try:
        result = remediation_manager.cancel_remediation_plan(plan_id)
        
        return {
            "success": True,
            "message": "Remediation plan cancelled successfully",
            "data": {
                "plan_id": plan_id,
                "cancelled": result,
                "cancelled_at": datetime.now().isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error cancelling remediation plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================
# BACKUP ENDPOINTS
# =============================================

@app.post("/backup/create")
async def create_backup(request: CreateBackupRequest):
    """Create a system backup"""
    try:
        backup = remediation_manager.create_backup(
            name=request.name,
            description=request.description,
            backup_type=BackupType(request.backup_type),
            policies=request.policies,
            registry_keys=request.registry_keys,
            gpos=request.gpos
        )
        
        return {
            "success": True,
            "message": "System backup created successfully",
            "data": {
                "backup_id": backup.id,
                "name": backup.name,
                "description": backup.description,
                "backup_type": backup.backup_type.value,
                "file_path": backup.file_path,
                "file_size": backup.file_size,
                "created_at": backup.created_at.isoformat(),
                "system_info": {
                    "hostname": backup.system_info.hostname,
                    "os_version": backup.system_info.os_version,
                    "scan_timestamp": backup.system_info.scan_timestamp.isoformat()
                }
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/backup/list")
async def list_backups():
    """Get all available system backups"""
    try:
        backups = remediation_manager.list_backups()
        
        backups_data = []
        for backup in backups:
            backups_data.append({
                "id": backup.id,
                "name": backup.name,
                "description": backup.description,
                "backup_type": backup.backup_type.value,
                "file_path": backup.file_path,
                "file_size": backup.file_size,
                "policies_included": len(backup.policies_included) if backup.policies_included else 0,
                "created_at": backup.created_at.isoformat(),
                "hostname": backup.system_info.hostname,
                "os_version": backup.system_info.os_version
            })
        
        return {
            "success": True,
            "message": f"Retrieved {len(backups)} backups",
            "data": {
                "backups": backups_data,
                "total_count": len(backups)
            }
        }
        
    except Exception as e:
        print(f"Error listing backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/backup/{backup_id}")
async def get_backup_details(backup_id: str):
    """Get detailed information about a specific backup"""
    try:
        backup = remediation_manager.get_backup(backup_id)
        if not backup:
            raise HTTPException(status_code=404, detail="Backup not found")
        
        return {
            "success": True,
            "message": "Backup details retrieved successfully",
            "data": {
                "id": backup.id,
                "name": backup.name,
                "description": backup.description,
                "backup_type": backup.backup_type.value,
                "file_path": backup.file_path,
                "file_size": backup.file_size,
                "policies_included": backup.policies_included,
                "registry_keys": backup.registry_keys,
                "gpos": backup.gpos,
                "integrity_hash": backup.integrity_hash,
                "validation_status": backup.validation_status,
                "created_at": backup.created_at.isoformat(),
                "system_info": {
                    "hostname": backup.system_info.hostname,
                    "os_version": backup.system_info.os_version,
                    "os_build": backup.system_info.os_build,
                    "architecture": backup.system_info.architecture,
                    "scan_timestamp": backup.system_info.scan_timestamp.isoformat()
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting backup details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup/{backup_id}/validate")
async def validate_backup(backup_id: str):
    """Validate the integrity of a backup"""
    try:
        is_valid = remediation_manager.validate_backup(backup_id)
        
        return {
            "success": True,
            "message": "Backup validation completed",
            "data": {
                "backup_id": backup_id,
                "is_valid": is_valid,
                "validated_at": datetime.now().isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error validating backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/backup/{backup_id}")
async def delete_backup(backup_id: str):
    """Delete a system backup"""
    try:
        result = remediation_manager.delete_backup(backup_id)
        
        return {
            "success": True,
            "message": "Backup deleted successfully",
            "data": {
                "backup_id": backup_id,
                "deleted": result,
                "deleted_at": datetime.now().isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error deleting backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================
# ROLLBACK ENDPOINTS
# =============================================

@app.post("/rollback/plan/create")
async def create_rollback_plan(request: CreateRollbackPlanRequest):
    """Create a rollback plan from a backup"""
    try:
        rollback_plan = remediation_manager.create_rollback_plan(
            name=request.name,
            description=request.description,
            backup_id=request.backup_id,
            selective_rollback=request.selective_rollback,
            selected_policies=request.selected_policies
        )
        
        return {
            "success": True,
            "message": "Rollback plan created successfully",
            "data": {
                "rollback_id": rollback_plan.id,
                "name": rollback_plan.name,
                "description": rollback_plan.description,
                "backup_id": rollback_plan.backup_id,
                "selective_rollback": rollback_plan.selective_rollback,
                "selected_policies": rollback_plan.selected_policies,
                "requires_reboot": rollback_plan.requires_reboot,
                "estimated_duration": rollback_plan.estimated_duration,
                "created_at": rollback_plan.created_at.isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error creating rollback plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rollback/plans")
async def list_rollback_plans():
    """Get all rollback plans"""
    try:
        plans = remediation_manager.list_rollback_plans()
        
        plans_data = []
        for plan in plans:
            plans_data.append({
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "backup_id": plan.backup_id,
                "selective_rollback": plan.selective_rollback,
                "policies_count": len(plan.selected_policies) if plan.selected_policies else 0,
                "requires_reboot": plan.requires_reboot,
                "estimated_duration": plan.estimated_duration,
                "created_at": plan.created_at.isoformat()
            })
        
        return {
            "success": True,
            "message": f"Retrieved {len(plans)} rollback plans",
            "data": {
                "plans": plans_data,
                "total_count": len(plans)
            }
        }
        
    except Exception as e:
        print(f"Error listing rollback plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rollback/plan/{rollback_id}")
async def get_rollback_plan_details(rollback_id: str):
    """Get detailed information about a rollback plan"""
    try:
        plan = remediation_manager.get_rollback_plan(rollback_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Rollback plan not found")
        
        return {
            "success": True,
            "message": "Rollback plan details retrieved successfully",
            "data": {
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "backup_id": plan.backup_id,
                "selective_rollback": plan.selective_rollback,
                "selected_policies": plan.selected_policies,
                "requires_reboot": plan.requires_reboot,
                "estimated_duration": plan.estimated_duration,
                "compatibility_checked": plan.compatibility_checked,
                "compatibility_issues": plan.compatibility_issues,
                "created_at": plan.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting rollback plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rollback/plan/{rollback_id}/execute")
async def execute_rollback_plan(rollback_id: str, request: ExecuteRollbackRequest):
    """Execute a rollback plan"""
    try:
        if request.rollback_id != rollback_id:
            raise HTTPException(status_code=400, detail="Rollback ID mismatch")
        
        result = remediation_manager.execute_rollback_plan(
            rollback_id=rollback_id,
            operator=request.operator,
            force_execution=request.force_execution
        )
        
        return {
            "success": True,
            "message": "Rollback execution completed successfully",
            "data": {
                "rollback_id": rollback_id,
                "operator": request.operator,
                "executed_at": datetime.now().isoformat(),
                "result": result,
                "requires_reboot": result.get("requires_reboot", False)
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error executing rollback plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================
# REMEDIATION STATISTICS & REPORTING
# =============================================

@app.get("/remediation/statistics")
async def get_remediation_statistics():
    """Get comprehensive remediation statistics"""
    try:
        stats = remediation_manager.get_comprehensive_statistics()
        
        return {
            "success": True,
            "message": "Remediation statistics retrieved successfully",
            "data": stats
        }
        
    except Exception as e:
        print(f"Error getting remediation statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/remediation/health")
async def get_remediation_health():
    """Get remediation system health status"""
    try:
        health = remediation_manager.get_system_health()
        
        return {
            "success": True,
            "message": "Remediation system health retrieved successfully",
            "data": health
        }
        
    except Exception as e:
        print(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/remediation/export")
async def export_remediation_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "json"
):
    """Export remediation data for reporting"""
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        export_file = remediation_manager.export_remediation_data(
            start_date=start_dt,
            end_date=end_dt,
            format=format
        )
        
        return {
            "success": True,
            "message": "Remediation data exported successfully",
            "data": {
                "export_file": export_file,
                "format": format,
                "start_date": start_date,
                "end_date": end_date,
                "download_url": f"/remediation/export/download/{os.path.basename(export_file)}"
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error exporting remediation data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/remediation/export/download/{filename}")
async def download_remediation_export(filename: str):
    """Download exported remediation data"""
    try:
        export_path = os.path.join(remediation_manager.data_dir, filename)
        
        if not os.path.exists(export_path):
            raise HTTPException(status_code=404, detail="Export file not found")
        
        return FileResponse(
            path=export_path,
            filename=filename,
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading remediation export: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/remediation/maintenance")
async def run_remediation_maintenance():
    """Run maintenance tasks for the remediation system"""
    try:
        results = remediation_manager.run_maintenance()
        
        return {
            "success": True,
            "message": "Remediation maintenance completed successfully",
            "data": {
                "maintenance_results": results,
                "completed_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        print(f"Error running maintenance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MODULE 3 ENHANCED: REAL-TIME MONITORING & WEBSOCKET ENDPOINTS
# ============================================================================

@app.websocket("/ws/realtime")
async def websocket_realtime_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time monitoring
    Provides live updates for:
    - Policy changes
    - Deployment status
    - Audit results
    - System metrics
    - Compliance trends
    """
    await websocket.accept()
    await realtime_manager.connect_client(websocket)
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle ping/pong for connection keepalive
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
            # Handle client requests for specific data
            elif message.get("type") == "request_stats":
                stats = realtime_manager.get_statistics()
                await websocket.send_json({
                    "type": "statistics",
                    "data": stats
                })
    
    except WebSocketDisconnect:
        realtime_manager.disconnect_client(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        realtime_manager.disconnect_client(websocket)

@app.get("/api/monitoring/statistics")
async def get_monitoring_statistics():
    """Get current real-time monitoring statistics"""
    try:
        stats = realtime_manager.get_statistics()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        print(f"Error getting monitoring statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/metrics/current")
async def get_current_metrics():
    """Get current system metrics"""
    try:
        metrics = realtime_manager.get_system_metrics()
        return {
            "success": True,
            "data": metrics.to_dict()
        }
    except Exception as e:
        print(f"Error getting current metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitoring/start")
async def start_monitoring():
    """Start real-time monitoring background tasks"""
    try:
        await realtime_manager.start_monitoring()
        return {
            "success": True,
            "message": "Real-time monitoring started"
        }
    except Exception as e:
        print(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitoring/stop")
async def stop_monitoring():
    """Stop real-time monitoring background tasks"""
    try:
        await realtime_manager.stop_monitoring()
        return {
            "success": True,
            "message": "Real-time monitoring stopped"
        }
    except Exception as e:
        print(f"Error stopping monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitoring/test-event")
async def send_test_event():
    """Send a test event for debugging"""
    try:
        await realtime_manager.notify_system_alert(
            severity="info",
            title="Test Event",
            message="This is a test notification from the monitoring system",
            data={"test": True, "timestamp": datetime.now().isoformat()}
        )
        return {
            "success": True,
            "message": "Test event sent"
        }
    except Exception as e:
        print(f"Error sending test event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MODULE 3 ENHANCED: ADMX INTEGRATION ENDPOINTS
# ============================================================================

@app.post("/api/templates/{template_id}/export/admx")
async def export_template_to_admx(
    template_id: str,
    namespace: str = "CISBenchmark",
    prefix: str = "CIS",
    validate: bool = True
):
    """
    Export template to ADMX/ADML format
    Integrates Module 2 ADMX generation into dashboard
    """
    try:
        # Export using template manager's ADMX functionality
        admx_content, adml_content, validation_result = template_manager.export_template_admx(
            template_id=template_id,
            namespace=namespace,
            prefix=prefix,
            validate=validate
        )
        
        # Notify via real-time monitoring
        template = template_manager.get_template(template_id)
        await realtime_manager.notify_system_alert(
            severity="success" if validation_result.is_valid else "warning",
            title="ADMX Export Completed",
            message=f"Template '{template.name}' exported to ADMX/ADML",
            data={
                "template_id": template_id,
                "template_name": template.name,
                "validation_errors": validation_result.errors_count,
                "validation_warnings": validation_result.warnings_count
            }
        )
        
        return {
            "success": True,
            "data": {
                "admx_content": admx_content,
                "adml_content": adml_content,
                "validation": {
                    "is_valid": validation_result.is_valid,
                    "errors_count": validation_result.errors_count,
                    "warnings_count": validation_result.warnings_count,
                    "info_count": validation_result.info_count,
                    "issues": [
                        {
                            "severity": issue.severity,
                            "message": issue.message,
                            "location": issue.location,
                            "recommendation": issue.recommendation
                        }
                        for issue in validation_result.issues
                    ]
                }
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error exporting template to ADMX: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/templates/{template_id}/save-admx")
async def save_template_admx_files(
    template_id: str,
    output_dir: str = "admx_output",
    namespace: str = "CISBenchmark",
    prefix: str = "CIS"
):
    """Save template as ADMX/ADML files to disk"""
    try:
        result = template_manager.save_admx_to_files(
            template_id=template_id,
            output_dir=output_dir,
            namespace=namespace,
            prefix=prefix
        )
        
        # Notify success
        template = template_manager.get_template(template_id)
        await realtime_manager.notify_system_alert(
            severity="success",
            title="ADMX Files Saved",
            message=f"Template '{template.name}' saved as ADMX/ADML files",
            data={
                "template_id": template_id,
                "admx_file": result["admx_file"],
                "adml_file": result["adml_file"]
            }
        )
        
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error saving ADMX files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/templates/bulk-export-admx")
async def bulk_export_templates_admx(
    template_ids: List[str],
    output_dir: str = "admx_bulk_output",
    namespace: str = "CISBenchmark",
    prefix: str = "CIS"
):
    """Bulk export multiple templates to ADMX/ADML"""
    try:
        results = template_manager.bulk_export_admx(
            template_ids=template_ids,
            output_dir=output_dir,
            namespace=namespace,
            prefix=prefix
        )
        
        successful = len([r for r in results if r.get("success", False)])
        
        # Notify completion
        await realtime_manager.notify_system_alert(
            severity="success" if successful == len(template_ids) else "warning",
            title="Bulk ADMX Export Completed",
            message=f"Exported {successful}/{len(template_ids)} templates successfully",
            data={
                "total": len(template_ids),
                "successful": successful,
                "failed": len(template_ids) - successful
            }
        )
        
        return {
            "success": True,
            "data": {
                "results": results,
                "summary": {
                    "total": len(template_ids),
                    "successful": successful,
                    "failed": len(template_ids) - successful
                }
            }
        }
    except Exception as e:
        print(f"Error in bulk ADMX export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MODULE 3 ENHANCED: ADVANCED ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/api/analytics/compliance-trends")
async def get_compliance_trends(days: int = 30):
    """Get compliance trends over time"""
    try:
        # Get all dashboard policies
        all_policies = dashboard_manager.get_all_policies()
        
        # Calculate current compliance
        compliant = len([p for p in all_policies if p.status == "compliant"])
        non_compliant = len([p for p in all_policies if p.status == "non_compliant"])
        pending = len([p for p in all_policies if p.status == "pending"])
        
        # Update realtime compliance trend
        await realtime_manager.update_compliance_trend(
            total_policies=len(all_policies),
            compliant=compliant,
            non_compliant=non_compliant,
            pending=pending
        )
        
        # Get historical trends from realtime manager
        trends = [trend.to_dict() for trend in realtime_manager.compliance_history]
        
        return {
            "success": True,
            "data": {
                "current": {
                    "total": len(all_policies),
                    "compliant": compliant,
                    "non_compliant": non_compliant,
                    "pending": pending,
                    "compliance_rate": (compliant / len(all_policies) * 100) if all_policies else 0
                },
                "trends": trends
            }
        }
    except Exception as e:
        print(f"Error getting compliance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/deployment-success-rate")
async def get_deployment_success_rate(days: int = 30):
    """Get deployment success rate analytics"""
    try:
        # Get all deployment jobs
        all_jobs = deployment_manager.get_all_jobs()
        
        # Calculate success rates
        total = len(all_jobs)
        completed = len([j for j in all_jobs if j.status == "completed"])
        failed = len([j for j in all_jobs if j.status == "failed"])
        running = len([j for j in all_jobs if j.status == "running"])
        
        success_rate = (completed / total * 100) if total > 0 else 0
        
        return {
            "success": True,
            "data": {
                "total_deployments": total,
                "completed": completed,
                "failed": failed,
                "running": running,
                "success_rate": success_rate,
                "recent_jobs": [
                    {
                        "job_id": job.job_id,
                        "package_name": job.package_name,
                        "status": job.status,
                        "created_at": job.created_at,
                        "completed_at": job.completed_at
                    }
                    for job in sorted(all_jobs, key=lambda x: x.created_at, reverse=True)[:10]
                ]
            }
        }
    except Exception as e:
        print(f"Error getting deployment success rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/audit-history")
async def get_audit_history_analytics(limit: int = 50):
    """Get audit history with trends"""
    try:
        # Get all audit runs
        all_runs = audit_manager.get_all_runs()
        
        # Sort by date
        sorted_runs = sorted(
            all_runs,
            key=lambda x: x.start_time,
            reverse=True
        )[:limit]
        
        # Calculate trends
        compliance_over_time = []
        for run in sorted_runs:
            if run.summary:
                compliance_over_time.append({
                    "timestamp": run.start_time,
                    "compliance_rate": run.summary.compliance_rate,
                    "compliant": run.summary.compliant_count,
                    "non_compliant": run.summary.non_compliant_count
                })
        
        return {
            "success": True,
            "data": {
                "total_audits": len(all_runs),
                "recent_audits": [
                    {
                        "audit_id": run.audit_id,
                        "name": run.name,
                        "status": run.status,
                        "compliance_rate": run.summary.compliance_rate if run.summary else 0,
                        "start_time": run.start_time,
                        "end_time": run.end_time
                    }
                    for run in sorted_runs
                ],
                "compliance_trends": compliance_over_time
            }
        }
    except Exception as e:
        print(f"Error getting audit history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/policy-statistics")
async def get_advanced_policy_statistics():
    """Get comprehensive policy statistics"""
    try:
        # Get template policies
        template_policies = template_manager.get_all_policies()
        
        # Get dashboard policies
        dashboard_policies = dashboard_manager.get_all_policies()
        
        # Get all templates
        templates = template_manager.get_all_templates()
        
        # Calculate statistics
        template_stats = {
            "total_policies": len(template_policies),
            "total_templates": len(templates),
            "policies_by_cis_level": {},
            "policies_by_category": {}
        }
        
        # Group by CIS level
        for policy in template_policies:
            level = policy.cis_level or "Unknown"
            template_stats["policies_by_cis_level"][level] = \
                template_stats["policies_by_cis_level"].get(level, 0) + 1
        
        # Group by category
        for policy in template_policies:
            category = policy.category or "Uncategorized"
            template_stats["policies_by_category"][category] = \
                template_stats["policies_by_category"].get(category, 0) + 1
        
        dashboard_stats = {
            "total_policies": len(dashboard_policies),
            "policies_by_status": {},
            "policies_by_priority": {}
        }
        
        # Group by status
        for policy in dashboard_policies:
            status = policy.status
            dashboard_stats["policies_by_status"][status] = \
                dashboard_stats["policies_by_status"].get(status, 0) + 1
        
        # Group by priority
        for policy in dashboard_policies:
            priority = policy.priority
            dashboard_stats["policies_by_priority"][priority] = \
                dashboard_stats["policies_by_priority"].get(priority, 0) + 1
        
        return {
            "success": True,
            "data": {
                "template_statistics": template_stats,
                "dashboard_statistics": dashboard_stats,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        print(f"Error getting policy statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UTILITY ENDPOINTS - FOR SETUP AND TROUBLESHOOTING
# ============================================================================

@app.post("/utilities/import-policies-to-dashboard")
async def import_policies_to_dashboard():
    """
    Utility endpoint to import policies from test_output.json into dashboard
    This populates the dashboard with policies so they can be used for deployment
    """
    try:
        import json
        
        # Load policies from test_output.json
        test_output_file = Path("test_output.json")
        if not test_output_file.exists():
            raise HTTPException(status_code=404, detail="test_output.json not found. Please run PDF parser first.")
        
        with open(test_output_file, 'r') as f:
            policies_data = json.load(f)
        
        imported_count = 0
        skipped_count = 0
        
        # Import each policy into dashboard
        for policy_data in policies_data:
            try:
                # Create enhanced policy for dashboard
                enhanced_policy = {
                    "policy_id": policy_data.get("id", str(uuid.uuid4())),
                    "name": policy_data.get("policy_name", "Unknown Policy"),
                    "title": policy_data.get("policy_name", "Unknown Policy"),
                    "description": policy_data.get("description", ""),
                    "category": policy_data.get("category", "Uncategorized"),
                    "subcategory": policy_data.get("subcategory", ""),
                    "registry_path": policy_data.get("registry_path"),
                    "gpo_path": policy_data.get("gpo_path"),
                    "required_value": policy_data.get("required_value", ""),
                    "current_value": None,
                    "cis_level": policy_data.get("cis_level", 1),
                    "rationale": policy_data.get("rationale", ""),
                    "impact": policy_data.get("impact", ""),
                    "references": policy_data.get("references", []),
                    "page_number": policy_data.get("page_number"),
                    "section_number": policy_data.get("section_number", ""),
                    "status": "not_configured",
                    "priority": "medium",
                    "is_enabled": True,
                    "group_ids": [],
                    "tag_ids": [],
                    "metadata": {
                        "source": "pdf_parser",
                        "raw_text": policy_data.get("raw_text", "")[:500]  # Limit size
                    }
                }
                
                # Try to assign to appropriate group based on category
                category_lower = enhanced_policy["category"].lower()
                for group in dashboard_manager.groups_cache.values():
                    group_name_lower = group.name.lower()
                    if (category_lower in group_name_lower or 
                        group_name_lower in category_lower or
                        ("security" in category_lower and "security" in group_name_lower)):
                        enhanced_policy["group_ids"].append(group.group_id)
                        break
                
                # Try to assign appropriate tags
                if "password" in enhanced_policy["name"].lower():
                    for tag in dashboard_manager.tags_cache.values():
                        if tag.name == "Password Policy":
                            enhanced_policy["tag_ids"].append(tag.tag_id)
                            break
                elif "firewall" in enhanced_policy["name"].lower():
                    for tag in dashboard_manager.tags_cache.values():
                        if tag.name == "Firewall":
                            enhanced_policy["tag_ids"].append(tag.tag_id)
                            break
                elif enhanced_policy["cis_level"] == 1:
                    for tag in dashboard_manager.tags_cache.values():
                        if tag.name == "Critical":
                            enhanced_policy["tag_ids"].append(tag.tag_id)
                            break
                
                # Check if policy already exists
                if enhanced_policy["policy_id"] not in dashboard_manager.policies_cache:
                    # Create the policy using dashboard manager
                    from models_dashboard import EnhancedPolicy
                    policy_obj = EnhancedPolicy(**enhanced_policy)
                    dashboard_manager.policies_cache[policy_obj.policy_id] = policy_obj
                    imported_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                print(f"Error importing policy: {e}")
                skipped_count += 1
                continue
        
        # Save the updated dashboard data
        dashboard_manager._save_all_data()
        
        # Update group policy counts
        for group in dashboard_manager.groups_cache.values():
            policy_count = sum(1 for p in dashboard_manager.policies_cache.values() if group.group_id in p.group_ids)
            group.policy_ids = [p.policy_id for p in dashboard_manager.policies_cache.values() if group.group_id in p.group_ids]
        
        # Update tag usage counts
        for tag in dashboard_manager.tags_cache.values():
            tag.usage_count = sum(1 for p in dashboard_manager.policies_cache.values() if tag.tag_id in p.tag_ids)
        
        # Save again with updated counts
        dashboard_manager._save_all_data()
        
        return {
            "success": True,
            "message": f"Successfully imported {imported_count} policies into dashboard",
            "data": {
                "imported": imported_count,
                "skipped": skipped_count,
                "total_policies": len(dashboard_manager.policies_cache),
                "total_groups": len(dashboard_manager.groups_cache),
                "total_tags": len(dashboard_manager.tags_cache)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error importing policies: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CACHE AND DATA CLEARING UTILITIES
# ============================================================================

@app.post("/utilities/clear-extraction-data")
async def clear_extraction_data():
    """
    Clear all extracted policies, results, uploaded files, and reset dashboard/template data.
    This clears:
    - uploads/ (uploaded PDFs)
    - results/ (extraction results and status files)
    - test_output.json (if exists)
    - dashboard_data/policies.json (resets to empty {})
    - templates_data/policies.json (resets to empty {})
    - In-memory caches (dashboard_manager, template_manager)
    
    Use this to completely reset the system and start fresh.
    Groups and tags structure will be preserved but policy associations will be cleared.
    """
    try:
        cleared_items = {
            "uploads": 0,
            "results": 0,
            "test_output": False,
            "dashboard_policies": 0,
            "template_policies": 0,
            "groups_reset": 0,
            "tags_reset": 0
        }
        
        # Clear uploads directory
        if os.path.exists("uploads"):
            for filename in os.listdir("uploads"):
                file_path = os.path.join("uploads", filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        cleared_items["uploads"] += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        # Clear results directory
        if os.path.exists("results"):
            for filename in os.listdir("results"):
                file_path = os.path.join("results", filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        cleared_items["results"] += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        # Clear test_output.json if exists
        if os.path.exists("test_output.json"):
            try:
                os.unlink("test_output.json")
                cleared_items["test_output"] = True
            except Exception as e:
                print(f"Error deleting test_output.json: {e}")
        
        # Clear dashboard policies
        dashboard_policies_path = os.path.join("dashboard_data", "policies.json")
        if os.path.exists(dashboard_policies_path):
            try:
                with open(dashboard_policies_path, 'r') as f:
                    policies = json.load(f)
                    cleared_items["dashboard_policies"] = len(policies)
                
                # Reset to empty
                with open(dashboard_policies_path, 'w') as f:
                    json.dump({}, f, indent=2)
                
                # Clear in-memory cache
                dashboard_manager.policies_cache.clear()
            except Exception as e:
                print(f"Error clearing dashboard policies: {e}")
        
        # Clear template policies
        template_policies_path = os.path.join("templates_data", "policies.json")
        if os.path.exists(template_policies_path):
            try:
                with open(template_policies_path, 'r') as f:
                    policies = json.load(f)
                    cleared_items["template_policies"] = len(policies)
                
                # Reset to empty
                with open(template_policies_path, 'w') as f:
                    json.dump({}, f, indent=2)
                
                # Clear in-memory cache
                template_manager.policies_cache.clear()
            except Exception as e:
                print(f"Error clearing template policies: {e}")
        
        # Clear policy_ids from groups in dashboard
        groups_path = os.path.join("dashboard_data", "groups.json")
        if os.path.exists(groups_path):
            try:
                with open(groups_path, 'r') as f:
                    groups = json.load(f)
                
                for group_id, group in groups.items():
                    if "policy_ids" in group and len(group["policy_ids"]) > 0:
                        cleared_items["groups_reset"] += 1
                        group["policy_ids"] = []
                
                with open(groups_path, 'w') as f:
                    json.dump(groups, f, indent=2)
                
                # Update in-memory cache
                dashboard_manager.load_groups()
            except Exception as e:
                print(f"Error clearing group policy associations: {e}")
        
        # Reset usage_count for tags in dashboard
        tags_path = os.path.join("dashboard_data", "tags.json")
        if os.path.exists(tags_path):
            try:
                with open(tags_path, 'r') as f:
                    tags = json.load(f)
                
                for tag_id, tag in tags.items():
                    if "usage_count" in tag and tag["usage_count"] > 0:
                        cleared_items["tags_reset"] += 1
                        tag["usage_count"] = 0
                
                with open(tags_path, 'w') as f:
                    json.dump(tags, f, indent=2)
                
                # Update in-memory cache
                dashboard_manager.load_tags()
            except Exception as e:
                print(f"Error resetting tag usage counts: {e}")
        
        # Clear in-memory extraction tasks
        extraction_tasks.clear()
        
        print(f"✅ Cleared all extraction and policy data: {cleared_items}")
        
        return {
            "success": True,
            "message": "All extraction and policy data cleared successfully",
            "details": cleared_items,
            "note": "System reset complete. Groups and tags structure preserved but empty. AI cache remains intact."
        }
        
    except Exception as e:
        print(f"Error clearing extraction data: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/utilities/clear-ai-cache")
async def clear_ai_cache():
    """
    Clear AI generation cache and temporary files.
    This clears:
    - Gemini AI response cache (if any)
    - Temporary generated files
    - In-memory generation history
    
    Does NOT clear:
    - Extracted policies
    - Dashboard data
    - Templates
    - Uploaded files
    
    Use this to force fresh AI responses.
    """
    try:
        cleared_items = {
            "ai_cache_entries": 0,
            "temp_files": 0
        }
        
        # Clear any cached AI responses (if you have a cache directory)
        cache_dir = os.path.join("data", "ai_cache")
        if os.path.exists(cache_dir):
            for filename in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        cleared_items["ai_cache_entries"] += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        # Clear temporary files
        temp_patterns = [
            "temp_*.json",
            "generated_*.tmp",
            "cache_*.json"
        ]
        
        for pattern in temp_patterns:
            import glob
            for file_path in glob.glob(pattern):
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        cleared_items["temp_files"] += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        print(f"✅ Cleared AI cache: {cleared_items}")
        
        return {
            "success": True,
            "message": "AI cache cleared successfully",
            "details": cleared_items,
            "note": "Extracted policies and dashboard data remain intact. Next AI operations will generate fresh responses."
        }
        
    except Exception as e:
        print(f"Error clearing AI cache: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# APPLICATION STARTUP/SHUTDOWN HANDLERS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize monitoring on application startup"""
    print("🚀 Starting CIS Benchmark GPO Tool")
    print("📊 Initializing real-time monitoring...")
    await realtime_manager.start_monitoring()
    print("✅ Real-time monitoring started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    print("🛑 Shutting down CIS Benchmark GPO Tool")
    print("📊 Stopping real-time monitoring...")
    await realtime_manager.stop_monitoring()
    print("✅ Real-time monitoring stopped")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)