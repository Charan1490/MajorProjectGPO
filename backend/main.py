"""
CIS Benchmark PDF Parser Main Application
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import json
import os
from datetime import datetime
import uuid
import aiofiles
from typing import Dict, List, Optional, Any

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

# Pydantic request models for deployment endpoints
class CreatePackageRequest(BaseModel):
    name: str
    description: str
    target_os: str
    policy_ids: Optional[List[str]] = None
    group_names: Optional[List[str]] = None
    tag_names: Optional[List[str]] = None
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

# Initialize Deployment Manager (Step 4)
deployment_manager = DeploymentManager()

# Initialize LGPO Manager (Step 4)
lgpo_manager = LGPOManager()

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
        return {
            "templates": [template.dict() for template in templates],
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
        policies = []
        
        # Get specific policies by ID
        if request.policy_ids:
            for policy_id in request.policy_ids:
                if policy_id in dashboard_manager.policies_cache:
                    policy = dashboard_manager.policies_cache[policy_id]
                    policy_dict = policy.dict()
                    # Map policy_id to id field
                    if 'policy_id' in policy_dict:
                        policy_dict['id'] = policy_dict['policy_id']
                    policies.append(policy_dict)
        
        # Get policies by groups
        if request.group_names:
            # Find group IDs by name first
            group_ids = []
            for group_name in request.group_names:
                for group in dashboard_manager.groups_cache.values():
                    if group.name == group_name:
                        group_ids.append(group.group_id)
                        break
            
            # Get policies that belong to these groups
            for policy in dashboard_manager.policies_cache.values():
                if any(gid in policy.group_ids for gid in group_ids):
                    policy_dict = policy.dict()
                    # Map policy_id to id field
                    if 'policy_id' in policy_dict:
                        policy_dict['id'] = policy_dict['policy_id']
                    policies.append(policy_dict)
        
        # Get policies by tags
        if request.tag_names:
            # Find tag IDs by name first
            tag_ids = []
            for tag_name in request.tag_names:
                for tag in dashboard_manager.tags_cache.values():
                    if tag.name == tag_name:
                        tag_ids.append(tag.tag_id)
                        break
            
            # Get policies that have these tags
            for policy in dashboard_manager.policies_cache.values():
                if any(tid in policy.tag_ids for tid in tag_ids):
                    policy_dict = policy.dict()
                    # Map policy_id to id field
                    if 'policy_id' in policy_dict:
                        policy_dict['id'] = policy_dict['policy_id']
                    policies.append(policy_dict)
        
        # If no specific filters, get all policies
        if not policies:
            all_policies = dashboard_manager.get_all_policies()
            policies = all_policies  # These are already dict objects
        
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
        from fastapi.responses import FileResponse
        
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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)