"""
ADMX/ADML Template Validation Framework
Validates generated ADMX/ADML templates against Windows Group Policy schemas
and best practices
"""

import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# VALIDATION RESULT MODELS
# ============================================================================

class ValidationSeverity(str, Enum):
    """Severity levels for validation issues"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationIssue:
    """Single validation issue"""
    severity: ValidationSeverity
    message: str
    element: Optional[str] = None
    line_number: Optional[int] = None
    recommendation: Optional[str] = None

@dataclass
class ValidationResult:
    """Complete validation result"""
    is_valid: bool
    issues: List[ValidationIssue]
    warnings_count: int = 0
    errors_count: int = 0
    info_count: int = 0
    
    def add_issue(self, issue: ValidationIssue):
        """Add an issue and update counters"""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.errors_count += 1
            self.is_valid = False
        elif issue.severity == ValidationSeverity.WARNING:
            self.warnings_count += 1
        elif issue.severity == ValidationSeverity.INFO:
            self.info_count += 1
    
    def __str__(self) -> str:
        """String representation of validation result"""
        status = "✅ VALID" if self.is_valid else "❌ INVALID"
        return (f"{status} - Errors: {self.errors_count}, "
                f"Warnings: {self.warnings_count}, Info: {self.info_count}")


# ============================================================================
# ADMX/ADML VALIDATOR
# ============================================================================

class TemplateValidator:
    """
    Comprehensive validator for ADMX/ADML templates
    """
    
    # ADMX Schema namespace
    ADMX_NAMESPACE = "{http://schemas.microsoft.com/GroupPolicy/2006/07/PolicyDefinitions}"
    
    # Valid registry roots
    VALID_REGISTRY_ROOTS = ['HKLM\\', 'HKCU\\', 'HKCR\\', 'HKU\\', 'HKCC\\']
    
    # Maximum lengths
    MAX_POLICY_NAME_LENGTH = 100
    MAX_DISPLAY_NAME_LENGTH = 250
    MAX_EXPLAIN_TEXT_LENGTH = 2000
    MAX_VALUE_NAME_LENGTH = 255
    
    # Required ADMX elements
    REQUIRED_ADMX_ELEMENTS = [
        'policyDefinitions',
        'policyNamespaces',
        'resources',
        'categories',
        'policies'
    ]
    
    # Required ADML elements
    REQUIRED_ADML_ELEMENTS = [
        'policyDefinitionResources',
        'displayName',
        'description',
        'resources'
    ]
    
    def __init__(self):
        """Initialize validator"""
        self.result = ValidationResult(is_valid=True, issues=[])
    
    def validate_admx(self, admx_content: str) -> ValidationResult:
        """
        Validate ADMX template content
        
        Args:
            admx_content: ADMX XML content string
            
        Returns:
            ValidationResult object
        """
        self.result = ValidationResult(is_valid=True, issues=[])
        
        try:
            # Parse XML
            root = ET.fromstring(admx_content)
            
            # Validate structure
            self._validate_admx_structure(root)
            
            # Validate namespaces
            self._validate_admx_namespaces(root)
            
            # Validate categories
            self._validate_admx_categories(root)
            
            # Validate policies
            self._validate_admx_policies(root)
            
            # Validate references
            self._validate_admx_references(root)
            
        except ET.ParseError as e:
            self.result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"XML parsing error: {str(e)}",
                recommendation="Check XML syntax and structure"
            ))
        except Exception as e:
            self.result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Validation error: {str(e)}",
                recommendation="Review ADMX content for errors"
            ))
        
        return self.result
    
    def validate_adml(self, adml_content: str) -> ValidationResult:
        """
        Validate ADML template content
        
        Args:
            adml_content: ADML XML content string
            
        Returns:
            ValidationResult object
        """
        self.result = ValidationResult(is_valid=True, issues=[])
        
        try:
            # Parse XML
            root = ET.fromstring(adml_content)
            
            # Validate structure
            self._validate_adml_structure(root)
            
            # Validate string resources
            self._validate_adml_strings(root)
            
            # Validate presentations
            self._validate_adml_presentations(root)
            
        except ET.ParseError as e:
            self.result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"XML parsing error: {str(e)}",
                recommendation="Check XML syntax and structure"
            ))
        except Exception as e:
            self.result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Validation error: {str(e)}",
                recommendation="Review ADML content for errors"
            ))
        
        return self.result
    
    def validate_pair(self, admx_content: str, adml_content: str) -> ValidationResult:
        """
        Validate ADMX/ADML pair for consistency
        
        Args:
            admx_content: ADMX XML content
            adml_content: ADML XML content
            
        Returns:
            ValidationResult object
        """
        self.result = ValidationResult(is_valid=True, issues=[])
        
        try:
            # Parse both files
            admx_root = ET.fromstring(admx_content)
            adml_root = ET.fromstring(adml_content)
            
            # Extract string references from ADMX
            admx_refs = self._extract_admx_string_references(admx_root)
            
            # Extract string definitions from ADML
            adml_strings = self._extract_adml_string_definitions(adml_root)
            
            # Check for missing strings
            missing_strings = admx_refs - adml_strings
            if missing_strings:
                for string_id in missing_strings:
                    self.result.add_issue(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Missing ADML string definition: {string_id}",
                        element=string_id,
                        recommendation=f"Add string definition for '{string_id}' in ADML stringTable"
                    ))
            
            # Check for unused strings
            unused_strings = adml_strings - admx_refs
            if unused_strings:
                for string_id in unused_strings:
                    self.result.add_issue(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Unused ADML string definition: {string_id}",
                        element=string_id,
                        recommendation="Consider removing unused string definitions"
                    ))
            
            # Validate presentation references
            self._validate_presentation_consistency(admx_root, adml_root)
            
        except Exception as e:
            self.result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Pair validation error: {str(e)}",
                recommendation="Review ADMX/ADML consistency"
            ))
        
        return self.result
    
    def _validate_admx_structure(self, root: ET.Element):
        """Validate ADMX structure and required elements"""
        # Check root element
        if not root.tag.endswith('policyDefinitions'):
            self.result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Root element must be 'policyDefinitions'",
                element=root.tag
            ))
        
        # Check required attributes
        required_attrs = ['revision', 'schemaVersion']
        for attr in required_attrs:
            if attr not in root.attrib:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Missing recommended attribute: {attr}",
                    element='policyDefinitions',
                    recommendation=f"Add {attr} attribute to root element"
                ))
        
        # Check for required child elements
        for elem_name in self.REQUIRED_ADMX_ELEMENTS[1:]:  # Skip root
            if root.find(f".//{self.ADMX_NAMESPACE}{elem_name}") is None:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing required element: {elem_name}",
                    element=elem_name,
                    recommendation=f"Add {elem_name} element to ADMX"
                ))
    
    def _validate_admx_namespaces(self, root: ET.Element):
        """Validate policy namespaces"""
        namespaces = root.find(f"{self.ADMX_NAMESPACE}policyNamespaces")
        if namespaces is None:
            return
        
        # Check for target namespace
        target = namespaces.find(f"{self.ADMX_NAMESPACE}target")
        if target is None:
            self.result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Missing target namespace definition",
                element="policyNamespaces",
                recommendation="Add target namespace with prefix and namespace attributes"
            ))
        else:
            # Validate target attributes
            if 'prefix' not in target.attrib or 'namespace' not in target.attrib:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Target namespace missing required attributes",
                    element="target",
                    recommendation="Add both 'prefix' and 'namespace' attributes"
                ))
    
    def _validate_admx_categories(self, root: ET.Element):
        """Validate policy categories"""
        categories_elem = root.find(f"{self.ADMX_NAMESPACE}categories")
        if categories_elem is None:
            return
        
        category_names = set()
        
        for category in categories_elem.findall(f"{self.ADMX_NAMESPACE}category"):
            name = category.get('name')
            display_name = category.get('displayName')
            
            if not name:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Category missing 'name' attribute",
                    element="category"
                ))
                continue
            
            # Check for duplicates
            if name in category_names:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Duplicate category name: {name}",
                    element=name
                ))
            category_names.add(name)
            
            # Check display name format
            if display_name and not display_name.startswith('$(string.'):
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Category '{name}' displayName should reference ADML string",
                    element=name,
                    recommendation="Use $(string.CategoryName) format"
                ))
    
    def _validate_admx_policies(self, root: ET.Element):
        """Validate policy definitions"""
        policies_elem = root.find(f"{self.ADMX_NAMESPACE}policies")
        if policies_elem is None:
            self.result.add_issue(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="No policies defined",
                element="policies",
                recommendation="Add policy definitions"
            ))
            return
        
        policy_names = set()
        
        for policy in policies_elem.findall(f"{self.ADMX_NAMESPACE}policy"):
            name = policy.get('name')
            class_type = policy.get('class')
            key = policy.get('key')
            
            # Check required attributes
            if not name:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Policy missing 'name' attribute",
                    element="policy"
                ))
                continue
            
            # Check name length
            if len(name) > self.MAX_POLICY_NAME_LENGTH:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Policy name too long: {name} ({len(name)} chars)",
                    element=name,
                    recommendation=f"Keep policy names under {self.MAX_POLICY_NAME_LENGTH} characters"
                ))
            
            # Check for duplicates
            if name in policy_names:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Duplicate policy name: {name}",
                    element=name
                ))
            policy_names.add(name)
            
            # Validate class
            if class_type not in ['Machine', 'User', 'Both']:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid policy class: {class_type} for policy {name}",
                    element=name,
                    recommendation="Class must be 'Machine', 'User', or 'Both'"
                ))
            
            # Validate registry key
            if key:
                if not any(key.startswith(root) for root in self.VALID_REGISTRY_ROOTS):
                    self.result.add_issue(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid registry key for policy {name}: {key}",
                        element=name,
                        recommendation=f"Key must start with one of: {', '.join(self.VALID_REGISTRY_ROOTS)}"
                    ))
            
            # Check for parent category
            parent_category = policy.find(f"{self.ADMX_NAMESPACE}parentCategory")
            if parent_category is None:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Policy {name} has no parent category",
                    element=name,
                    recommendation="Assign policy to a category"
                ))
    
    def _validate_admx_references(self, root: ET.Element):
        """Validate internal references in ADMX"""
        # Collect all category names
        categories_elem = root.find(f"{self.ADMX_NAMESPACE}categories")
        category_names = set()
        if categories_elem is not None:
            for category in categories_elem.findall(f"{self.ADMX_NAMESPACE}category"):
                name = category.get('name')
                if name:
                    category_names.add(name)
        
        # Check policy category references
        policies_elem = root.find(f"{self.ADMX_NAMESPACE}policies")
        if policies_elem is not None:
            for policy in policies_elem.findall(f"{self.ADMX_NAMESPACE}policy"):
                policy_name = policy.get('name', 'unknown')
                parent_category = policy.find(f"{self.ADMX_NAMESPACE}parentCategory")
                if parent_category is not None:
                    ref = parent_category.get('ref')
                    if ref and ref not in category_names:
                        self.result.add_issue(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            message=f"Policy {policy_name} references undefined category: {ref}",
                            element=policy_name,
                            recommendation=f"Define category '{ref}' or update reference"
                        ))
    
    def _validate_adml_structure(self, root: ET.Element):
        """Validate ADML structure"""
        if not root.tag.endswith('policyDefinitionResources'):
            self.result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Root element must be 'policyDefinitionResources'",
                element=root.tag
            ))
        
        # Check for required elements
        for elem_name in ['displayName', 'description']:
            elem = root.find(f".//{self.ADMX_NAMESPACE}{elem_name}")
            if elem is None or not elem.text:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Missing or empty {elem_name}",
                    element=elem_name,
                    recommendation=f"Add descriptive {elem_name}"
                ))
    
    def _validate_adml_strings(self, root: ET.Element):
        """Validate ADML string resources"""
        string_table = root.find(f".//{self.ADMX_NAMESPACE}stringTable")
        if string_table is None:
            self.result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Missing stringTable element",
                element="stringTable",
                recommendation="Add stringTable with string definitions"
            ))
            return
        
        string_ids = set()
        
        for string_elem in string_table.findall(f"{self.ADMX_NAMESPACE}string"):
            string_id = string_elem.get('id')
            text = string_elem.text
            
            if not string_id:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="String element missing 'id' attribute",
                    element="string"
                ))
                continue
            
            # Check for duplicates
            if string_id in string_ids:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Duplicate string ID: {string_id}",
                    element=string_id
                ))
            string_ids.add(string_id)
            
            # Check for empty text
            if not text or not text.strip():
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Empty string text for ID: {string_id}",
                    element=string_id,
                    recommendation="Provide meaningful text for all strings"
                ))
            
            # Check text length
            if text and len(text) > self.MAX_EXPLAIN_TEXT_LENGTH:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"String text too long for ID: {string_id} ({len(text)} chars)",
                    element=string_id,
                    recommendation=f"Keep text under {self.MAX_EXPLAIN_TEXT_LENGTH} characters"
                ))
    
    def _validate_adml_presentations(self, root: ET.Element):
        """Validate ADML presentation definitions"""
        presentation_table = root.find(f".//{self.ADMX_NAMESPACE}presentationTable")
        if presentation_table is None:
            # Presentations are optional
            return
        
        presentation_ids = set()
        
        for presentation in presentation_table.findall(f"{self.ADMX_NAMESPACE}presentation"):
            pres_id = presentation.get('id')
            
            if not pres_id:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Presentation missing 'id' attribute",
                    element="presentation"
                ))
                continue
            
            # Check for duplicates
            if pres_id in presentation_ids:
                self.result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Duplicate presentation ID: {pres_id}",
                    element=pres_id
                ))
            presentation_ids.add(pres_id)
    
    def _extract_admx_string_references(self, root: ET.Element) -> Set[str]:
        """Extract all string references from ADMX"""
        refs = set()
        
        # Pattern for $(string.ID)
        pattern = r'\$\(string\.([^)]+)\)'
        
        # Search in all text and attributes
        for elem in root.iter():
            # Check attributes
            for attr_value in elem.attrib.values():
                matches = re.findall(pattern, attr_value)
                refs.update(matches)
            
            # Check text
            if elem.text:
                matches = re.findall(pattern, elem.text)
                refs.update(matches)
        
        return refs
    
    def _extract_adml_string_definitions(self, root: ET.Element) -> Set[str]:
        """Extract all string definitions from ADML"""
        string_ids = set()
        
        string_table = root.find(f".//{self.ADMX_NAMESPACE}stringTable")
        if string_table is not None:
            for string_elem in string_table.findall(f"{self.ADMX_NAMESPACE}string"):
                string_id = string_elem.get('id')
                if string_id:
                    string_ids.add(string_id)
        
        return string_ids
    
    def _validate_presentation_consistency(self, admx_root: ET.Element, adml_root: ET.Element):
        """Validate presentation references between ADMX and ADML"""
        # Extract presentation references from ADMX policies
        admx_presentation_refs = set()
        policies_elem = admx_root.find(f"{self.ADMX_NAMESPACE}policies")
        if policies_elem is not None:
            for policy in policies_elem.findall(f"{self.ADMX_NAMESPACE}policy"):
                presentation_attr = policy.get('presentation')
                if presentation_attr:
                    # Extract ID from $(presentation.ID) format
                    match = re.search(r'\$\(presentation\.([^)]+)\)', presentation_attr)
                    if match:
                        admx_presentation_refs.add(match.group(1))
        
        # Extract presentation definitions from ADML
        adml_presentation_defs = set()
        presentation_table = adml_root.find(f".//{self.ADMX_NAMESPACE}presentationTable")
        if presentation_table is not None:
            for presentation in presentation_table.findall(f"{self.ADMX_NAMESPACE}presentation"):
                pres_id = presentation.get('id')
                if pres_id:
                    adml_presentation_defs.add(pres_id)
        
        # Check for missing presentations
        missing = admx_presentation_refs - adml_presentation_defs
        for pres_id in missing:
            self.result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Missing ADML presentation definition: {pres_id}",
                element=pres_id,
                recommendation=f"Add presentation definition for '{pres_id}' in ADML"
            ))


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def validate_admx(admx_content: str) -> ValidationResult:
    """Validate ADMX content"""
    validator = TemplateValidator()
    return validator.validate_admx(admx_content)

def validate_adml(adml_content: str) -> ValidationResult:
    """Validate ADML content"""
    validator = TemplateValidator()
    return validator.validate_adml(adml_content)

def validate_admx_adml_pair(admx_content: str, adml_content: str) -> ValidationResult:
    """Validate ADMX/ADML pair"""
    validator = TemplateValidator()
    return validator.validate_pair(admx_content, adml_content)
