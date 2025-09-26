"""
Data models for the CIS Benchmark PDF Parser
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class PolicyItem(BaseModel):
    """Model representing a single policy item extracted from a CIS Benchmark PDF"""
    id: str
    category: str
    subcategory: Optional[str] = None
    policy_name: str
    description: str
    rationale: Optional[str] = None
    impact: Optional[str] = None
    registry_path: Optional[str] = None
    gpo_path: Optional[str] = None
    required_value: Optional[str] = None
    cis_level: Optional[int] = None  # 1 or 2
    references: Optional[List[str]] = None
    raw_text: Optional[str] = None
    page_number: Optional[int] = None
    section_number: Optional[str] = None


class PolicyExtractionResponse(BaseModel):
    """Response model for policy extraction results"""
    total_policies: int
    policies: List[PolicyItem]
    metadata: Dict[str, Any] = {}


class ExtractionStatus(BaseModel):
    """Model representing the status of an extraction task"""
    task_id: str
    status: str = Field(..., description="Status of the extraction task: processing, completed, or failed")
    message: str
    details: Optional[str] = None  # More detailed information about the current process
    progress: int = Field(..., ge=0, le=100, description="Progress percentage, 0-100")
    file_name: str
    result_path: Optional[str] = None