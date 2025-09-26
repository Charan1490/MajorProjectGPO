"""
PDF Parser module for extracting policies from CIS Benchmark PDFs
"""

import os
import re
import uuid
import PyPDF2
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer, LAParams
import camelot
import pandas as pd
from typing import List, Dict, Any, Callable, Optional, Tuple

from models import PolicyItem

# Regular expressions for identifying sections and policy elements
SECTION_PATTERN = re.compile(r'^(\d+(\.\d+)*)\s+(.+)$')
RECOMMENDATION_PATTERN = re.compile(r'(Profile Applicability:|Description:|Rationale:|Impact:|Default Value:|References:|CIS Controls:)')

def extract_policies_from_pdf(pdf_path: str, progress_callback: Optional[Callable[[int], None]] = None) -> List[PolicyItem]:
    """
    Extract policy items from a CIS Benchmark PDF
    
    Args:
        pdf_path: Path to the PDF file
        progress_callback: Optional callback function to report progress (0-100)
        
    Returns:
        List of PolicyItem objects
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    policies = []
    
    try:
        # Initial processing - extract text content
        if progress_callback:
            progress_callback(10, "Analyzing PDF structure", "Loading PDF document and preparing for text extraction")
            
        # Open the PDF file
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            total_pages = len(pdf_reader.pages)
            
            # Extract metadata if available
            if progress_callback:
                metadata = pdf_reader.metadata
                details = f"PDF document has {total_pages} pages"
                if metadata and metadata.get('/Title'):
                    details += f", title: {metadata.get('/Title')}"
                progress_callback(15, "Reading PDF metadata", details)
            
            # Extract policies using a combination of approaches
            policies = extract_policies_with_combined_approach(pdf_path, pdf_reader, total_pages, progress_callback)
        
        if progress_callback:
            details = f"Successfully extracted {len(policies)} policy items from the document"
            progress_callback(100, "Extraction completed", details)
            
        return policies
    
    except Exception as e:
        print(f"Error extracting policies from PDF: {str(e)}")
        if progress_callback:
            progress_callback(0)  # Reset progress on error
        raise
        
def extract_policies_with_combined_approach(
    pdf_path: str, 
    pdf_reader: PyPDF2.PdfReader, 
    total_pages: int,
    progress_callback: Optional[Callable[[int], None]] = None
) -> List[PolicyItem]:
    """
    Extract policies using a combination of text extraction and table extraction
    
    Args:
        pdf_path: Path to the PDF file
        pdf_reader: PyPDF2.PdfReader object
        total_pages: Total number of pages in the PDF
        progress_callback: Optional callback function to report progress
        
    Returns:
        List of PolicyItem objects
    """
    policies = []
    
    # First pass: Extract text to identify sections and policy blocks
    current_category = ""
    current_subcategory = ""
    section_number = ""
    in_policy_block = False
    current_policy_text = []
    current_page = 0
    
    # Process each page
    for page_num in range(total_pages):
        if progress_callback:
            # Report progress as a percentage (20-70%)
            progress = 20 + int((page_num / total_pages) * 50)
            operation = f"Processing page {page_num + 1}/{total_pages}"
            details = f"Extracting text and identifying policy sections on page {page_num + 1}"
            progress_callback(progress, operation, details)
        
        try:
            # Extract text from the current page
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            
            # Process the text to identify sections and policies
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Check if this line starts a new section
                section_match = SECTION_PATTERN.match(line)
                if section_match:
                    # If we were in a policy block, save the current policy
                    if in_policy_block and current_policy_text:
                        policy = parse_policy_block(
                            current_policy_text,
                            current_category,
                            current_subcategory,
                            section_number,
                            current_page
                        )
                        if policy:
                            policies.append(policy)
                        current_policy_text = []
                    
                    # Update section information
                    section_number = section_match.group(1)
                    section_title = section_match.group(3)
                    
                    # Determine if this is a category or subcategory
                    if len(section_number.split('.')) == 1:
                        current_category = section_title
                        current_subcategory = ""
                    else:
                        current_subcategory = section_title
                    
                    in_policy_block = False
                
                # Check if this line starts a recommendation/policy block
                elif "Ensure" in line and "is set to" in line:
                    # If we were already in a policy block, save the current policy
                    if in_policy_block and current_policy_text:
                        policy = parse_policy_block(
                            current_policy_text,
                            current_category,
                            current_subcategory,
                            section_number,
                            current_page
                        )
                        if policy:
                            policies.append(policy)
                        current_policy_text = []
                    
                    # Start a new policy block
                    in_policy_block = True
                    current_policy_text = [line]
                    current_page = page_num + 1  # 1-based page numbering
                
                # If we're in a policy block, add the line to the current policy text
                elif in_policy_block:
                    current_policy_text.append(line)
        
        except Exception as e:
            print(f"Error processing page {page_num + 1}: {str(e)}")
    
    # Handle any remaining policy block
    if in_policy_block and current_policy_text:
        policy = parse_policy_block(
            current_policy_text,
            current_category,
            current_subcategory,
            section_number,
            current_page
        )
        if policy:
            policies.append(policy)
    
    # Second pass: Try to extract tables with Camelot
    try:
        if progress_callback:
            progress_callback(75, "Extracting tables", "Beginning table extraction from PDF")
        
        # Skip table extraction for very large PDFs (more than 500 pages)
        # Table extraction is resource-intensive and can cause the process to hang
        if total_pages > 500:
            if progress_callback:
                progress_callback(78, "Skipping table extraction", f"Document is very large ({total_pages} pages). Skipping table extraction to improve performance.")
        else:
            if progress_callback:
                progress_callback(76, "Extracting tables", f"Analyzing {total_pages} pages for tabular data")
                
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
            
            if progress_callback:
                progress_callback(77, "Processing tables", f"Found {len(tables)} tables in the document")
            
            for i, table in enumerate(tables):
                if progress_callback and i % 5 == 0:  # Update progress every 5 tables
                    progress_percent = 77 + int((i / len(tables)) * 2)  # Progress between 77-79%
                    progress_callback(progress_percent, "Processing tables", f"Processing table {i+1} of {len(tables)}")
                
                df = table.df
                
                # Process each table row
                for _, row in df.iterrows():
                    # Skip header rows or empty rows
                    if row[0].strip() == "" or "Title" in row[0] or "Recommendation" in row[0]:
                        continue
                
                # Try to extract policy information from the table row
                policy_name = row[0].strip()
                
                if "Ensure" in policy_name and len(policy_name) > 10:
                    # Create a policy item from the table row
                    policy = PolicyItem(
                        id=str(uuid.uuid4()),
                        category=current_category,
                        subcategory=current_subcategory,
                        policy_name=policy_name,
                        description="", 
                        section_number=section_number,
                        page_number=table.page  # Camelot page numbers are 1-based
                    )
                    
                    # Try to populate more fields if columns are available
                    if len(row) > 1:
                        policy.required_value = row[1].strip()
                    
                    if len(row) > 2:
                        # This might be the CIS level
                        level_text = row[2].strip()
                        if "1" in level_text:
                            policy.cis_level = 1
                        elif "2" in level_text:
                            policy.cis_level = 2
                    
                    # Add to policies if not a duplicate
                    if not any(p.policy_name == policy.policy_name for p in policies):
                        policies.append(policy)
    
    except Exception as e:
        print(f"Error extracting tables from PDF: {str(e)}")
        if progress_callback:
            progress_callback(79, "Table extraction error", f"Encountered an error during table extraction: {str(e)}")
    
    # Deduplicate policies based on policy name
    unique_policies = []
    policy_names = set()
    
    for policy in policies:
        if policy.policy_name not in policy_names:
            policy_names.add(policy.policy_name)
            unique_policies.append(policy)
    
    if progress_callback:
        progress_callback(80, "Finalizing extraction", f"Extracted {len(unique_policies)} unique policy items")
    
    return unique_policies

def parse_policy_block(
    lines: List[str],
    category: str,
    subcategory: str,
    section_number: str,
    page_number: int
) -> Optional[PolicyItem]:
    """
    Parse a block of text representing a policy
    
    Args:
        lines: List of text lines in the policy block
        category: Category of the policy
        subcategory: Subcategory of the policy
        section_number: Section number
        page_number: Page number
        
    Returns:
        PolicyItem object or None if parsing failed
    """
    if not lines:
        return None
    
    # The first line typically contains the policy name
    policy_name = lines[0].strip()
    
    # Initialize policy fields
    description = ""
    rationale = ""
    impact = ""
    registry_path = None
    gpo_path = None
    required_value = None
    cis_level = None
    references = []
    
    # Join all lines into a single text for easier processing
    full_text = " ".join(lines)
    raw_text = "\n".join(lines)
    
    # Try to extract the GPO or registry path
    # Common patterns in CIS benchmarks
    registry_matches = re.findall(r'HKEY_[A-Z_\\]+\\\\[A-Za-z0-9_\\]+', full_text)
    if registry_matches:
        registry_path = registry_matches[0].replace("\\\\", "\\")
    
    gpo_matches = re.findall(r'Computer Configuration\\[A-Za-z0-9 \\]+', full_text)
    if gpo_matches:
        gpo_path = gpo_matches[0].replace("\\\\", "\\")
    
    # Try to extract the required value
    if "is set to" in policy_name:
        value_match = re.search(r'is set to ["\'](.*)["\']', policy_name)
        if value_match:
            required_value = value_match.group(1)
        elif "is set to " in policy_name:
            parts = policy_name.split("is set to ")
            if len(parts) > 1:
                required_value = parts[1].strip()
    
    # Process each section
    current_section = None
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Check for section headers
        for pattern in ["Profile Applicability:", "Description:", "Rationale:", "Impact:", "Default Value:", "References:", "CIS Controls:"]:
            if line.startswith(pattern):
                current_section = pattern.rstrip(":")
                continue
        
        # If we're in a section, add the line to the appropriate field
        if current_section:
            if current_section == "Description":
                description += line + " "
            elif current_section == "Rationale":
                rationale += line + " "
            elif current_section == "Impact":
                impact += line + " "
            elif current_section == "References":
                references.append(line)
            elif current_section == "Profile Applicability":
                # Try to extract CIS level
                if "Level 1" in line:
                    cis_level = 1
                elif "Level 2" in line:
                    cis_level = 2
    
    # Clean up the extracted text fields
    description = description.strip()
    rationale = rationale.strip()
    impact = impact.strip()
    
    # Create and return the PolicyItem
    return PolicyItem(
        id=str(uuid.uuid4()),
        category=category,
        subcategory=subcategory,
        policy_name=policy_name,
        description=description,
        rationale=rationale,
        impact=impact,
        registry_path=registry_path,
        gpo_path=gpo_path,
        required_value=required_value,
        cis_level=cis_level,
        references=references,
        raw_text=raw_text,
        page_number=page_number,
        section_number=section_number
    )