"""
Enhanced ADMX/ADML Template Generator
Generates Windows Group Policy Administrative Template files (ADMX/ADML)
from CIS benchmark policies with full schema compliance and validation.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import uuid
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

from models_templates import PolicyItem, PolicyType, PolicyTemplate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# ADMX/ADML SCHEMA DEFINITIONS
# ============================================================================

class ADMXElementType(str, Enum):
    """ADMX element types for policy definitions"""
    BOOLEAN = "boolean"
    ENUM = "enum"
    TEXT = "text"
    MULTITEXT = "multiText"
    DECIMAL = "decimal"
    LIST = "list"
    
class ADMXPresentationType(str, Enum):
    """ADMX presentation element types"""
    CHECKBOX = "checkBox"
    COMBOBOX = "comboBox"
    TEXTBOX = "textBox"
    DROPDOWN = "dropdownList"
    LISTBOX = "listBox"
    DECIMAL_TEXTBOX = "decimalTextBox"

@dataclass
class ADMXCategory:
    """ADMX Policy Category"""
    name: str
    display_name: str
    parent: Optional[str] = None
    explain_text: Optional[str] = None

@dataclass
class ADMXPolicy:
    """ADMX Policy Definition"""
    name: str
    display_name: str
    explain_text: str
    key: str
    value_name: Optional[str] = None
    value_type: ADMXElementType = ADMXElementType.BOOLEAN
    class_type: str = "Machine"  # Machine or User
    enabled_value: Optional[Any] = None
    disabled_value: Optional[Any] = None
    category: str = "CISBenchmark"
    supported_on: str = "windows:SUPPORTED_Windows11"
    registry_key: Optional[str] = None
    
@dataclass
class ADMXPresentation:
    """ADMX Presentation Definition"""
    policy_name: str
    elements: List[Tuple[ADMXPresentationType, str, Optional[str]]]  # (type, ref_id, label)


# ============================================================================
# ADMX GENERATOR
# ============================================================================

class EnhancedADMXGenerator:
    """
    Enhanced ADMX/ADML generator with full Windows schema compliance
    """
    
    # ADMX Schema namespaces
    ADMX_NAMESPACE = "http://schemas.microsoft.com/GroupPolicy/2006/07/PolicyDefinitions"
    XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
    
    # Registry value type mapping
    REGISTRY_TYPES = {
        "REG_SZ": "string",
        "REG_DWORD": "decimal",
        "REG_QWORD": "decimal",
        "REG_BINARY": "string",
        "REG_MULTI_SZ": "multiText",
        "REG_EXPAND_SZ": "string"
    }
    
    def __init__(self, 
                 namespace: str = "CISBenchmark",
                 prefix: str = "CIS",
                 version: str = "1.0.0.0"):
        """
        Initialize ADMX generator
        
        Args:
            namespace: Namespace for ADMX file
            prefix: Prefix for policy names
            version: Version number for the template
        """
        self.namespace = namespace
        self.prefix = prefix
        self.version = version
        self.categories: Dict[str, ADMXCategory] = {}
        self.policies: List[ADMXPolicy] = []
        self.presentations: List[ADMXPresentation] = []
        
    def generate_from_template(self, 
                               template: PolicyTemplate, 
                               policies: List[PolicyItem]) -> Tuple[str, str]:
        """
        Generate ADMX and ADML content from a policy template
        
        Args:
            template: PolicyTemplate object
            policies: List of PolicyItem objects
            
        Returns:
            Tuple of (admx_content, adml_content)
        """
        logger.info(f"Generating ADMX/ADML for template: {template.name}")
        
        # Reset state
        self.categories = {}
        self.policies = []
        self.presentations = []
        
        # Create default categories
        self._create_default_categories()
        
        # Convert policies to ADMX format
        for policy in policies:
            try:
                admx_policy = self._convert_policy_to_admx(policy)
                if admx_policy:
                    self.policies.append(admx_policy)
                    
                    # Create presentation if needed
                    presentation = self._create_presentation(policy, admx_policy)
                    if presentation:
                        self.presentations.append(presentation)
            except Exception as e:
                logger.warning(f"Failed to convert policy {policy.policy_name}: {e}")
                continue
        
        # Generate ADMX XML
        admx_content = self._generate_admx_xml(template)
        
        # Generate ADML XML
        adml_content = self._generate_adml_xml(template)
        
        logger.info(f"Generated ADMX with {len(self.policies)} policies")
        
        return admx_content, adml_content
    
    def _create_default_categories(self):
        """Create default policy categories"""
        # Root category
        root = ADMXCategory(
            name="CISBenchmark",
            display_name="CIS Benchmark Policies",
            explain_text="CIS Security Benchmark compliance policies for Windows"
        )
        self.categories["CISBenchmark"] = root
        
        # Sub-categories based on common CIS sections
        categories = [
            ("AccountPolicies", "Account Policies", "Password and account lockout policies"),
            ("LocalPolicies", "Local Policies", "Audit policies, user rights, and security options"),
            ("EventLog", "Event Log", "Event log configuration policies"),
            ("RestrictedGroups", "Restricted Groups", "Group membership restrictions"),
            ("SystemServices", "System Services", "Windows service configuration"),
            ("Registry", "Registry", "Direct registry-based policies"),
            ("FileSystem", "File System", "File and folder permission policies"),
            ("WindowsFirewall", "Windows Firewall", "Windows Firewall configuration"),
            ("AdvancedAudit", "Advanced Audit Policy", "Advanced audit policy configuration"),
            ("NetworkSecurity", "Network Security", "Network security and communication policies"),
            ("InteractiveLo gon", "Interactive Logon", "Interactive logon policies"),
            ("MicrosoftDefender", "Microsoft Defender", "Microsoft Defender configuration"),
        ]
        
        for name, display, explain in categories:
            cat = ADMXCategory(
                name=name,
                display_name=display,
                parent="CISBenchmark",
                explain_text=explain
            )
            self.categories[name] = cat
    
    def _convert_policy_to_admx(self, policy: PolicyItem) -> Optional[ADMXPolicy]:
        """
        Convert a PolicyItem to ADMXPolicy
        
        Args:
            policy: PolicyItem to convert
            
        Returns:
            ADMXPolicy object or None if conversion fails
        """
        # Extract registry information
        registry_key, registry_value = self._parse_registry_path(policy.registry_path)
        
        if not registry_key:
            # Try to extract from GPO path
            registry_key, registry_value = self._extract_registry_from_gpo(policy.gpo_path)
        
        if not registry_key:
            logger.debug(f"No registry path found for policy: {policy.policy_name}")
            return None
        
        # Determine policy name (sanitize for XML)
        policy_name = self._sanitize_name(policy.policy_name)
        if not policy_name.startswith(self.prefix):
            policy_name = f"{self.prefix}_{policy_name}"
        
        # Determine category
        category = self._determine_category(policy)
        
        # Determine value type and values
        value_type, enabled_value, disabled_value = self._determine_value_type(policy)
        
        # Create ADMX policy
        admx_policy = ADMXPolicy(
            name=policy_name,
            display_name=policy.policy_name[:250],  # ADMX has 250 char limit
            explain_text=self._create_explain_text(policy),
            key=registry_key,
            value_name=registry_value,
            value_type=value_type,
            class_type=self._determine_class_type(registry_key),
            enabled_value=enabled_value,
            disabled_value=disabled_value,
            category=category,
            supported_on="windows:SUPPORTED_Windows11",
            registry_key=registry_key
        )
        
        return admx_policy
    
    def _parse_registry_path(self, registry_path: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse registry path into key and value name
        
        Args:
            registry_path: Registry path string
            
        Returns:
            Tuple of (registry_key, value_name)
        """
        if not registry_path:
            return None, None
        
        # Clean the path
        path = registry_path.strip()
        
        # Handle different formats:
        # 1. HKLM\Software\Path:ValueName
        # 2. HKLM\Software\Path (no value name)
        # 3. HKEY_LOCAL_MACHINE\Software\Path:ValueName
        
        # Normalize HKEY_ prefixes
        path = path.replace("HKEY_LOCAL_MACHINE", "HKLM")
        path = path.replace("HKEY_CURRENT_USER", "HKCU")
        path = path.replace("HKEY_CLASSES_ROOT", "HKCR")
        path = path.replace("HKEY_USERS", "HKU")
        path = path.replace("HKEY_CURRENT_CONFIG", "HKCC")
        
        # Split on : to separate value name
        if ':' in path:
            parts = path.rsplit(':', 1)
            registry_key = parts[0].strip()
            value_name = parts[1].strip()
        elif '\\\\' in path:
            # Double backslash at end means default value
            registry_key = path.rstrip('\\')
            value_name = None
        else:
            # No value name specified
            registry_key = path
            value_name = None
        
        # Ensure key starts with valid root
        valid_roots = ["HKLM\\", "HKCU\\", "HKCR\\", "HKU\\", "HKCC\\"]
        if not any(registry_key.startswith(root) for root in valid_roots):
            return None, None
        
        return registry_key, value_name
    
    def _extract_registry_from_gpo(self, gpo_path: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract registry information from GPO path
        
        Args:
            gpo_path: GPO path string
            
        Returns:
            Tuple of (registry_key, value_name)
        """
        if not gpo_path:
            return None, None
        
        # Common GPO to registry mappings
        gpo_registry_map = {
            "Computer Configuration\\Policies\\Windows Settings\\Security Settings\\Local Policies\\Security Options": 
                "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa",
            "Computer Configuration\\Policies\\Windows Settings\\Security Settings\\Account Policies\\Password Policy":
                "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
            "Computer Configuration\\Policies\\Windows Settings\\Security Settings\\Event Log":
                "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\EventLog",
            "Computer Configuration\\Policies\\Administrative Templates\\System":
                "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\System",
            "Computer Configuration\\Policies\\Administrative Templates\\Network":
                "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Network",
        }
        
        # Try to find matching registry path
        for gpo, reg in gpo_registry_map.items():
            if gpo in gpo_path:
                return reg, None
        
        return None, None
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize policy name for XML attribute usage
        
        Args:
            name: Original policy name
            
        Returns:
            Sanitized name safe for XML
        """
        # Remove/replace special characters
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'\s+', '_', name)
        name = name.strip('_')
        
        # Limit length (ADMX names should be reasonable)
        if len(name) > 100:
            name = name[:100]
        
        # Ensure it starts with a letter
        if name and not name[0].isalpha():
            name = "Policy_" + name
        
        return name or f"Policy_{uuid.uuid4().hex[:8]}"
    
    def _determine_category(self, policy: PolicyItem) -> str:
        """
        Determine the best category for a policy
        
        Args:
            policy: PolicyItem
            
        Returns:
            Category name
        """
        category_keywords = {
            "AccountPolicies": ["password", "account", "lockout", "logon"],
            "LocalPolicies": ["audit", "security option", "user rights"],
            "EventLog": ["event log", "logging"],
            "SystemServices": ["service", "services"],
            "WindowsFirewall": ["firewall", "network protection"],
            "AdvancedAudit": ["advanced audit", "audit policy"],
            "NetworkSecurity": ["network", "smb", "netbios"],
            "InteractiveLogon": ["interactive logon", "logon", "smartcard"],
            "MicrosoftDefender": ["defender", "antivirus", "windows defender"],
        }
        
        # Check policy name and description for keywords
        text = (policy.policy_name + " " + policy.description + " " + policy.category).lower()
        
        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        # Default to Registry if registry-based, otherwise LocalPolicies
        return "Registry" if policy.policy_type == PolicyType.REGISTRY else "LocalPolicies"
    
    def _determine_class_type(self, registry_key: str) -> str:
        """
        Determine if policy is Machine or User class
        
        Args:
            registry_key: Registry key path
            
        Returns:
            "Machine" or "User"
        """
        if registry_key.startswith("HKCU\\") or registry_key.startswith("HKU\\"):
            return "User"
        return "Machine"
    
    def _determine_value_type(self, policy: PolicyItem) -> Tuple[ADMXElementType, Any, Any]:
        """
        Determine ADMX element type and values
        
        Args:
            policy: PolicyItem
            
        Returns:
            Tuple of (element_type, enabled_value, disabled_value)
        """
        required_value = policy.required_value or policy.custom_value
        
        if not required_value:
            # Default to boolean
            return ADMXElementType.BOOLEAN, 1, 0
        
        # Analyze the required value
        value_str = str(required_value).lower()
        
        # Boolean values
        if value_str in ['enabled', 'disabled', 'true', 'false', '1', '0']:
            if value_str in ['enabled', 'true', '1']:
                return ADMXElementType.BOOLEAN, 1, 0
            else:
                return ADMXElementType.BOOLEAN, 0, 1
        
        # Numeric values
        if value_str.isdigit() or value_str.replace('-', '').isdigit():
            return ADMXElementType.DECIMAL, int(value_str), 0
        
        # List values (comma-separated)
        if ',' in value_str or ';' in value_str:
            return ADMXElementType.MULTITEXT, value_str, ""
        
        # Text values
        return ADMXElementType.TEXT, required_value, ""
    
    def _create_explain_text(self, policy: PolicyItem) -> str:
        """
        Create comprehensive explain text for policy
        
        Args:
            policy: PolicyItem
            
        Returns:
            Formatted explain text
        """
        parts = []
        
        if policy.description:
            parts.append(policy.description)
        
        if policy.rationale:
            parts.append(f"\n\nRationale:\n{policy.rationale}")
        
        if policy.required_value:
            parts.append(f"\n\nRecommended Value: {policy.required_value}")
        
        if policy.cis_level:
            parts.append(f"\n\nCIS Level: {policy.cis_level}")
        
        if policy.registry_path:
            parts.append(f"\n\nRegistry: {policy.registry_path}")
        
        explain_text = "".join(parts)
        
        # ADMX has 2000 character limit for explain text
        if len(explain_text) > 1900:
            explain_text = explain_text[:1900] + "..."
        
        return explain_text or "No description available"
    
    def _create_presentation(self, policy: PolicyItem, admx_policy: ADMXPolicy) -> Optional[ADMXPresentation]:
        """
        Create presentation definition for policy
        
        Args:
            policy: PolicyItem
            admx_policy: ADMXPolicy
            
        Returns:
            ADMXPresentation object or None
        """
        elements = []
        
        # Add presentation elements based on value type
        if admx_policy.value_type == ADMXElementType.TEXT:
            elements.append((
                ADMXPresentationType.TEXTBOX,
                f"{admx_policy.name}_Text",
                "Value:"
            ))
        elif admx_policy.value_type == ADMXElementType.DECIMAL:
            elements.append((
                ADMXPresentationType.DECIMAL_TEXTBOX,
                f"{admx_policy.name}_Decimal",
                "Value:"
            ))
        elif admx_policy.value_type == ADMXElementType.ENUM:
            elements.append((
                ADMXPresentationType.DROPDOWN,
                f"{admx_policy.name}_Enum",
                "Select:"
            ))
        elif admx_policy.value_type == ADMXElementType.MULTITEXT:
            elements.append((
                ADMXPresentationType.LISTBOX,
                f"{admx_policy.name}_List",
                "Values:"
            ))
        
        if elements:
            return ADMXPresentation(
                policy_name=admx_policy.name,
                elements=elements
            )
        
        return None
    
    def _generate_admx_xml(self, template: PolicyTemplate) -> str:
        """
        Generate ADMX XML content
        
        Args:
            template: PolicyTemplate
            
        Returns:
            XML string
        """
        # Create root element with namespaces
        root = ET.Element('policyDefinitions', {
            'xmlns:xsd': self.XSD_NAMESPACE,
            'xmlns:xsi': self.XSD_NAMESPACE,
            'revision': self.version,
            'schemaVersion': '1.0',
            'xmlns': self.ADMX_NAMESPACE
        })
        
        # Add policy namespaces
        policy_namespaces = ET.SubElement(root, 'policyNamespaces')
        target = ET.SubElement(policy_namespaces, 'target', {
            'prefix': self.prefix,
            'namespace': f'{self.namespace}.Policies'
        })
        using = ET.SubElement(policy_namespaces, 'using', {
            'prefix': 'windows',
            'namespace': 'Microsoft.Policies.Windows'
        })
        
        # Add superseded ADM files (optional, for legacy compatibility)
        superseded_adm = ET.SubElement(root, 'supersededAdm', {
            'fileName': 'CISBenchmark.adm'
        })
        
        # Add resources
        resources = ET.SubElement(root, 'resources', {
            'minRequiredRevision': '1.0'
        })
        
        # Add categories
        categories = ET.SubElement(root, 'categories')
        for cat_name, category in self.categories.items():
            cat_elem = ET.SubElement(categories, 'category', {
                'name': category.name,
                'displayName': f'$(string.{category.name})'
            })
            if category.parent:
                parent_category = ET.SubElement(cat_elem, 'parentCategory', {
                    'ref': category.parent
                })
        
        # Add policies
        policies_elem = ET.SubElement(root, 'policies')
        for policy in self.policies:
            self._add_policy_element(policies_elem, policy)
        
        # Convert to pretty XML string
        xml_str = self._prettify_xml(root)
        
        return xml_str
    
    def _add_policy_element(self, parent: ET.Element, policy: ADMXPolicy):
        """
        Add a policy element to the ADMX
        
        Args:
            parent: Parent XML element
            policy: ADMXPolicy to add
        """
        policy_elem = ET.SubElement(parent, 'policy', {
            'name': policy.name,
            'class': policy.class_type,
            'displayName': f'$(string.{policy.name})',
            'explainText': f'$(string.{policy.name}_Help)',
            'key': policy.key,
            'presentation': f'$(presentation.{policy.name})'
        })
        
        if policy.value_name:
            policy_elem.set('valueName', policy.value_name)
        
        # Add parent category
        parent_category = ET.SubElement(policy_elem, 'parentCategory', {
            'ref': policy.category
        })
        
        # Add supported on
        supported_on = ET.SubElement(policy_elem, 'supportedOn', {
            'ref': policy.supported_on
        })
        
        # Add enable/disable values based on type
        if policy.value_type == ADMXElementType.BOOLEAN:
            if policy.enabled_value is not None:
                enabled_value = ET.SubElement(policy_elem, 'enabledValue')
                decimal_elem = ET.SubElement(enabled_value, 'decimal', {
                    'value': str(policy.enabled_value)
                })
            
            if policy.disabled_value is not None:
                disabled_value = ET.SubElement(policy_elem, 'disabledValue')
                decimal_elem = ET.SubElement(disabled_value, 'decimal', {
                    'value': str(policy.disabled_value)
                })
        
        elif policy.value_type == ADMXElementType.DECIMAL:
            elements = ET.SubElement(policy_elem, 'elements')
            decimal_elem = ET.SubElement(elements, 'decimal', {
                'id': f'{policy.name}_Decimal',
                'valueName': policy.value_name or 'Value',
                'minValue': '0',
                'maxValue': '999999'
            })
            if policy.enabled_value is not None:
                decimal_elem.set('defaultValue', str(policy.enabled_value))
        
        elif policy.value_type == ADMXElementType.TEXT:
            elements = ET.SubElement(policy_elem, 'elements')
            text_elem = ET.SubElement(elements, 'text', {
                'id': f'{policy.name}_Text',
                'valueName': policy.value_name or 'Value',
                'maxLength': '1024'
            })
            if policy.enabled_value:
                text_elem.set('defaultValue', str(policy.enabled_value))
        
        elif policy.value_type == ADMXElementType.MULTITEXT:
            elements = ET.SubElement(policy_elem, 'elements')
            multitext_elem = ET.SubElement(elements, 'multiText', {
                'id': f'{policy.name}_List',
                'valueName': policy.value_name or 'Values',
                'maxLength': '1024'
            })
    
    def _generate_adml_xml(self, template: PolicyTemplate) -> str:
        """
        Generate ADML XML content (language resources)
        
        Args:
            template: PolicyTemplate
            
        Returns:
            XML string
        """
        # Create root element
        root = ET.Element('policyDefinitionResources', {
            'xmlns:xsd': self.XSD_NAMESPACE,
            'xmlns:xsi': self.XSD_NAMESPACE,
            'revision': self.version,
            'schemaVersion': '1.0',
            'xmlns': self.ADMX_NAMESPACE
        })
        
        # Add display name
        display_name = ET.SubElement(root, 'displayName')
        display_name.text = template.name
        
        # Add description
        description = ET.SubElement(root, 'description')
        description.text = template.description or f"CIS Benchmark policies for {template.name}"
        
        # Add resources
        resources = ET.SubElement(root, 'resources')
        
        # Add string table
        string_table = ET.SubElement(resources, 'stringTable')
        
        # Add category strings
        for cat_name, category in self.categories.items():
            string_elem = ET.SubElement(string_table, 'string', {'id': category.name})
            string_elem.text = category.display_name
            
            if category.explain_text:
                string_elem = ET.SubElement(string_table, 'string', {'id': f'{category.name}_Help'})
                string_elem.text = category.explain_text
        
        # Add policy strings
        for policy in self.policies:
            # Display name
            string_elem = ET.SubElement(string_table, 'string', {'id': policy.name})
            string_elem.text = policy.display_name
            
            # Help text
            string_elem = ET.SubElement(string_table, 'string', {'id': f'{policy.name}_Help'})
            string_elem.text = policy.explain_text
        
        # Add presentation table
        presentation_table = ET.SubElement(resources, 'presentationTable')
        
        for presentation in self.presentations:
            pres_elem = ET.SubElement(presentation_table, 'presentation', {
                'id': presentation.policy_name
            })
            
            for elem_type, ref_id, label in presentation.elements:
                if elem_type == ADMXPresentationType.TEXTBOX:
                    elem = ET.SubElement(pres_elem, 'textBox', {'refId': ref_id})
                    label_elem = ET.SubElement(elem, 'label')
                    label_elem.text = label
                
                elif elem_type == ADMXPresentationType.DECIMAL_TEXTBOX:
                    elem = ET.SubElement(pres_elem, 'decimalTextBox', {'refId': ref_id})
                    label_elem = ET.SubElement(elem, 'label')
                    label_elem.text = label
                
                elif elem_type == ADMXPresentationType.DROPDOWN:
                    elem = ET.SubElement(pres_elem, 'dropdownList', {'refId': ref_id})
                    label_elem = ET.SubElement(elem, 'label')
                    label_elem.text = label
                
                elif elem_type == ADMXPresentationType.LISTBOX:
                    elem = ET.SubElement(pres_elem, 'listBox', {'refId': ref_id})
                    label_elem = ET.SubElement(elem, 'label')
                    label_elem.text = label
        
        # Convert to pretty XML string
        xml_str = self._prettify_xml(root)
        
        return xml_str
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """
        Return a pretty-printed XML string
        
        Args:
            elem: XML Element
            
        Returns:
            Formatted XML string
        """
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty = reparsed.toprettyxml(indent="  ")
        
        # Remove extra blank lines
        lines = [line for line in pretty.split('\n') if line.strip()]
        return '\n'.join(lines)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def generate_admx_from_template(template: PolicyTemplate, policies: List[PolicyItem],
                                namespace: str = "CISBenchmark",
                                prefix: str = "CIS") -> Tuple[str, str]:
    """
    Convenience function to generate ADMX/ADML from template
    
    Args:
        template: PolicyTemplate
        policies: List of PolicyItem objects
        namespace: ADMX namespace
        prefix: Policy prefix
        
    Returns:
        Tuple of (admx_content, adml_content)
    """
    generator = EnhancedADMXGenerator(namespace=namespace, prefix=prefix)
    return generator.generate_from_template(template, policies)
