"""
GPO Template Management Service (Step 2)
Handles template creation, editing, grouping, and policy management
"""

import json
import os
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import uuid
import logging

from models_templates import (
    PolicyItem, PolicyTemplate, PolicyGroup, PolicyEdit, PolicyStatus,
    PolicyType, TemplateExport, BulkEditRequest, PolicySearchRequest
)
from enhanced_admx_generator import EnhancedADMXGenerator, generate_admx_from_template
from template_validator import TemplateValidator, ValidationResult
from complex_policy_support import ComplexPolicyAnalyzer

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages GPO templates and policy editing functionality"""
    
    def __init__(self, data_dir: str = "templates_data"):
        self.data_dir = data_dir
        self.policies_file = os.path.join(data_dir, "policies.json")
        self.templates_file = os.path.join(data_dir, "templates.json")
        self.groups_file = os.path.join(data_dir, "groups.json")
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize storage files if they don't exist
        self._init_storage_files()
    
    def _init_storage_files(self):
        """Initialize empty storage files if they don't exist"""
        if not os.path.exists(self.policies_file):
            self._save_policies({})
        if not os.path.exists(self.templates_file):
            self._save_templates({})
        if not os.path.exists(self.groups_file):
            self._save_groups({})
    
    def _load_policies(self) -> Dict[str, PolicyItem]:
        """Load all policies from storage"""
        try:
            with open(self.policies_file, 'r') as f:
                data = json.load(f)
                return {k: PolicyItem(**v) for k, v in data.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_policies(self, policies: Dict[str, PolicyItem]):
        """Save policies to storage"""
        data = {k: v.dict() if isinstance(v, PolicyItem) else v for k, v in policies.items()}
        with open(self.policies_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _load_templates(self) -> Dict[str, PolicyTemplate]:
        """Load all templates from storage"""
        try:
            with open(self.templates_file, 'r') as f:
                data = json.load(f)
                return {k: PolicyTemplate(**v) for k, v in data.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_templates(self, templates: Dict[str, PolicyTemplate]):
        """Save templates to storage"""
        data = {k: v.dict() if isinstance(v, PolicyTemplate) else v for k, v in templates.items()}
        with open(self.templates_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _load_groups(self) -> Dict[str, PolicyGroup]:
        """Load all groups from storage"""
        try:
            with open(self.groups_file, 'r') as f:
                data = json.load(f)
                return {k: PolicyGroup(**v) for k, v in data.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_groups(self, groups: Dict[str, PolicyGroup]):
        """Save groups to storage"""
        data = {k: v.dict() if isinstance(v, PolicyGroup) else v for k, v in groups.items()}
        with open(self.groups_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    # Policy Management
    def import_cis_policies(self, cis_data: List[Dict]) -> Dict[str, str]:
        """Import CIS benchmark policies from Step 1"""
        policies = self._load_policies()
        imported = {}
        
        for policy_data in cis_data:
            try:
                # Generate policy ID if not present
                policy_id = policy_data.get('id', str(uuid.uuid4()))
                
                # Create PolicyItem from CIS data - mapping CIS field names to our model
                policy_item = PolicyItem(
                    policy_id=policy_id,
                    cis_id=policy_data.get('cis_id', policy_data.get('subcategory', '')),
                    policy_name=policy_data.get('policy_name', policy_data.get('subcategory', 'Unknown Policy')),
                    category=policy_data.get('category', 'Uncategorized'),
                    subcategory=policy_data.get('subcategory', ''),
                    description=policy_data.get('description', ''),
                    rationale=policy_data.get('rationale', ''),
                    registry_path=policy_data.get('registry_path'),
                    gpo_path=policy_data.get('gpo_path'),
                    cis_level=str(policy_data.get('cis_level', '1')),
                    required_value=policy_data.get('required_value', policy_data.get('value')),
                    policy_type=self._determine_policy_type(policy_data)
                )
                
                policies[policy_id] = policy_item
                imported[policy_id] = policy_item.policy_name
                
            except Exception as e:
                print(f"Error importing policy {policy_data.get('id', 'unknown')}: {e}")
                continue
        
        self._save_policies(policies)
        return imported
    
    def _determine_policy_type(self, policy_data: Dict) -> PolicyType:
        """Determine policy type based on policy data"""
        if policy_data.get('registry_path'):
            return PolicyType.REGISTRY
        elif policy_data.get('gpo_path'):
            if 'security' in policy_data.get('gpo_path', '').lower():
                return PolicyType.SECURITY_POLICY
            elif 'audit' in policy_data.get('gpo_path', '').lower():
                return PolicyType.AUDIT_POLICY
            elif 'user rights' in policy_data.get('gpo_path', '').lower():
                return PolicyType.USER_RIGHTS
            else:
                return PolicyType.ADMINISTRATIVE_TEMPLATE
        else:
            return PolicyType.REGISTRY
    
    def get_all_policies(self) -> List[PolicyItem]:
        """Get all policies"""
        policies = self._load_policies()
        return list(policies.values())
    
    def get_policy(self, policy_id: str) -> Optional[PolicyItem]:
        """Get a specific policy by ID"""
        policies = self._load_policies()
        return policies.get(policy_id)
    
    def update_policy(self, policy_id: str, updates: Dict[str, Any], user_note: Optional[str] = None) -> PolicyItem:
        """Update a policy and track changes"""
        policies = self._load_policies()
        policy = policies.get(policy_id)
        
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")
        
        # Track changes
        for field, new_value in updates.items():
            if hasattr(policy, field):
                old_value = getattr(policy, field)
                if old_value != new_value:
                    edit = PolicyEdit(
                        field_name=field,
                        old_value=old_value,
                        new_value=new_value,
                        user_note=user_note
                    )
                    policy.edits.append(edit)
                    setattr(policy, field, new_value)
                    policy.is_modified = True
        
        policies[policy_id] = policy
        self._save_policies(policies)
        return policy
    
    def bulk_update_policies(self, request: BulkEditRequest) -> Dict[str, PolicyItem]:
        """Update multiple policies at once"""
        updated = {}
        for policy_id in request.policy_ids:
            try:
                updated[policy_id] = self.update_policy(policy_id, request.changes, request.user_note)
            except ValueError:
                # Skip policies that don't exist
                continue
        return updated
    
    def search_policies(self, request: PolicySearchRequest) -> List[PolicyItem]:
        """Search and filter policies"""
        policies = self._load_policies()
        results = list(policies.values())
        
        # Apply filters
        if request.query:
            query_lower = request.query.lower()
            results = [p for p in results if 
                      query_lower in p.policy_name.lower() or
                      query_lower in p.description.lower() or
                      query_lower in p.category.lower()]
        
        if request.categories:
            results = [p for p in results if p.category in request.categories]
        
        if request.policy_types:
            results = [p for p in results if p.policy_type in request.policy_types]
        
        if request.statuses:
            results = [p for p in results if p.status in request.statuses]
        
        if request.tags:
            results = [p for p in results if any(tag in p.tags for tag in request.tags)]
        
        if request.cis_levels:
            results = [p for p in results if p.cis_level in request.cis_levels]
        
        if request.is_modified is not None:
            results = [p for p in results if p.is_modified == request.is_modified]
        
        if request.template_id:
            results = [p for p in results if request.template_id in p.template_ids]
        
        return results
    
    # Template Management
    def create_template(self, name: str, description: Optional[str] = None, 
                       cis_level: Optional[str] = None, policy_ids: List[str] = None, 
                       tags: List[str] = None) -> PolicyTemplate:
        """Create a new template"""
        templates = self._load_templates()
        policies = self._load_policies()
        
        policy_ids = policy_ids or []
        tags = tags or []
        
        # Validate policy IDs exist
        for policy_id in policy_ids:
            if policy_id not in policies:
                raise ValueError(f"Policy {policy_id} not found")
        
        template = PolicyTemplate(
            name=name,
            description=description,
            cis_level=cis_level,
            policy_ids=policy_ids,
            tags=tags
        )
        
        # Update policies to reference this template
        for policy_id in policy_ids:
            if template.template_id not in policies[policy_id].template_ids:
                policies[policy_id].template_ids.append(template.template_id)
        
        templates[template.template_id] = template
        self._save_templates(templates)
        self._save_policies(policies)
        
        return template
    
    def get_all_templates(self) -> List[PolicyTemplate]:
        """Get all templates"""
        templates = self._load_templates()
        return list(templates.values())
    
    def get_template(self, template_id: str) -> Optional[PolicyTemplate]:
        """Get a specific template by ID"""
        templates = self._load_templates()
        return templates.get(template_id)
    
    def update_template(self, template_id: str, updates: Dict[str, Any]) -> PolicyTemplate:
        """Update a template"""
        templates = self._load_templates()
        template = templates.get(template_id)
        
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Handle policy_ids updates specially
        if 'policy_ids' in updates:
            self._update_template_policy_assignments(template, updates['policy_ids'])
        
        # Update other fields
        for field, value in updates.items():
            if hasattr(template, field) and field != 'policy_ids':
                setattr(template, field, value)
        
        template.updated_at = datetime.now()
        templates[template_id] = template
        self._save_templates(templates)
        
        return template
    
    def _update_template_policy_assignments(self, template: PolicyTemplate, new_policy_ids: List[str]):
        """Update policy assignments for a template"""
        policies = self._load_policies()
        
        # Remove template from old policies
        for old_policy_id in template.policy_ids:
            if old_policy_id in policies and template.template_id in policies[old_policy_id].template_ids:
                policies[old_policy_id].template_ids.remove(template.template_id)
        
        # Add template to new policies
        for new_policy_id in new_policy_ids:
            if new_policy_id in policies and template.template_id not in policies[new_policy_id].template_ids:
                policies[new_policy_id].template_ids.append(template.template_id)
        
        template.policy_ids = new_policy_ids
        self._save_policies(policies)
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template"""
        templates = self._load_templates()
        if template_id not in templates:
            return False
        
        # Remove template references from policies
        policies = self._load_policies()
        for policy in policies.values():
            if template_id in policy.template_ids:
                policy.template_ids.remove(template_id)
        
        del templates[template_id]
        self._save_templates(templates)
        self._save_policies(policies)
        
        return True
    
    def duplicate_template(self, template_id: str, new_name: str) -> PolicyTemplate:
        """Duplicate an existing template"""
        templates = self._load_templates()
        original = templates.get(template_id)
        
        if not original:
            raise ValueError(f"Template {template_id} not found")
        
        # Create new template with same settings
        new_template = self.create_template(
            name=new_name,
            description=f"Copy of {original.description or original.name}",
            cis_level=original.cis_level,
            policy_ids=original.policy_ids.copy(),
            tags=original.tags.copy()
        )
        
        return new_template
    
    def get_template_with_policies(self, template_id: str) -> Optional[TemplateExport]:
        """Get template with all its policies"""
        template = self.get_template(template_id)
        if not template:
            return None
        
        policies = self._load_policies()
        template_policies = [policies[pid] for pid in template.policy_ids if pid in policies]
        
        return TemplateExport(
            template=template,
            policies=template_policies,
            metadata={
                "policy_count": len(template_policies),
                "enabled_count": len([p for p in template_policies if p.status == PolicyStatus.ENABLED]),
                "modified_count": len([p for p in template_policies if p.is_modified])
            }
        )
    
    # Group Management
    def create_group(self, name: str, description: Optional[str] = None, 
                     color: Optional[str] = None, policy_ids: List[str] = None, 
                     tags: List[str] = None) -> PolicyGroup:
        """Create a new policy group"""
        groups = self._load_groups()
        
        group = PolicyGroup(
            name=name,
            description=description,
            color=color,
            policy_ids=policy_ids or [],
            tags=tags or []
        )
        
        groups[group.group_id] = group
        self._save_groups(groups)
        
        return group
    
    def get_all_groups(self) -> List[PolicyGroup]:
        """Get all groups"""
        groups = self._load_groups()
        return list(groups.values())
    
    # Export functionality
    def export_template_json(self, template_id: str) -> Dict:
        """Export template as JSON"""
        export_data = self.get_template_with_policies(template_id)
        if not export_data:
            raise ValueError(f"Template {template_id} not found")
        
        return export_data.dict()
    
    def export_template_csv(self, template_id: str) -> str:
        """Export template as CSV"""
        export_data = self.get_template_with_policies(template_id)
        if not export_data:
            raise ValueError(f"Template {template_id} not found")
        
        # Generate CSV content
        csv_lines = [
            "Policy ID,Policy Name,Category,Status,Custom Value,Required Value,Registry Path,GPO Path,CIS Level,Tags,User Notes"
        ]
        
        for policy in export_data.policies:
            csv_lines.append(
                f'"{policy.policy_id}","{policy.policy_name}","{policy.category}",'
                f'"{policy.status}","{policy.custom_value or ""}","{policy.required_value or ""}",'
                f'"{policy.registry_path or ""}","{policy.gpo_path or ""}","{policy.cis_level or ""}",'
                f'"{"; ".join(policy.tags)}","{policy.user_notes or ""}"'
            )
        
        return "\n".join(csv_lines)
    
    # ADMX/ADML Export functionality (Module 2 Enhancement)
    def export_template_admx(self, template_id: str, 
                            namespace: str = "CISBenchmark",
                            prefix: str = "CIS",
                            validate: bool = True) -> Tuple[str, str, Optional[ValidationResult]]:
        """
        Export template as ADMX/ADML Group Policy Administrative Templates
        
        Args:
            template_id: Template ID to export
            namespace: ADMX namespace (default: CISBenchmark)
            prefix: Policy prefix (default: CIS)
            validate: Whether to validate generated templates (default: True)
            
        Returns:
            Tuple of (admx_content, adml_content, validation_result)
            
        Raises:
            ValueError: If template not found
        """
        logger.info(f"Exporting template {template_id} to ADMX/ADML")
        
        # Get template with policies
        export_data = self.get_template_with_policies(template_id)
        if not export_data:
            raise ValueError(f"Template {template_id} not found")
        
        template = export_data.template
        policies = export_data.policies
        
        # Enhance policies with complex policy data
        enhanced_policies = []
        for policy in policies:
            policy_dict = policy.model_dump() if hasattr(policy, 'model_dump') else policy.dict()
            enhanced_dict = ComplexPolicyAnalyzer.enhance_policy_with_complex_data(policy_dict)
            
            # Create enhanced PolicyItem
            try:
                enhanced_policy = PolicyItem(**enhanced_dict)
                enhanced_policies.append(enhanced_policy)
            except Exception as e:
                logger.warning(f"Failed to enhance policy {policy.policy_id}: {e}")
                enhanced_policies.append(policy)
        
        # Generate ADMX/ADML
        admx_content, adml_content = generate_admx_from_template(
            template,
            enhanced_policies,
            namespace=namespace,
            prefix=prefix
        )
        
        # Validate if requested
        validation_result = None
        if validate:
            validator = TemplateValidator()
            validation_result = validator.validate_pair(admx_content, adml_content)
            logger.info(f"Validation result: {validation_result}")
        
        logger.info(f"Generated ADMX/ADML for template {template.name}: {len(enhanced_policies)} policies")
        
        return admx_content, adml_content, validation_result
    
    def save_admx_to_files(self, template_id: str, 
                           output_dir: str = "admx_output",
                           namespace: str = "CISBenchmark",
                           prefix: str = "CIS",
                           validate: bool = True) -> Dict[str, Any]:
        """
        Export template to ADMX/ADML files
        
        Args:
            template_id: Template ID to export
            output_dir: Output directory for files
            namespace: ADMX namespace
            prefix: Policy prefix
            validate: Whether to validate templates
            
        Returns:
            Dictionary with file paths and validation results
        """
        # Get template info
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate ADMX/ADML
        admx_content, adml_content, validation_result = self.export_template_admx(
            template_id,
            namespace=namespace,
            prefix=prefix,
            validate=validate
        )
        
        # Generate file names from template name
        safe_name = "".join(c for c in template.name if c.isalnum() or c in (' ', '-', '_'))
        safe_name = safe_name.replace(' ', '_')
        
        # Save ADMX file
        admx_filename = f"{prefix}_{safe_name}.admx"
        admx_path = os.path.join(output_dir, admx_filename)
        with open(admx_path, 'w', encoding='utf-8') as f:
            f.write(admx_content)
        
        # Save ADML file (en-US language)
        adml_dir = os.path.join(output_dir, "en-US")
        os.makedirs(adml_dir, exist_ok=True)
        adml_filename = f"{prefix}_{safe_name}.adml"
        adml_path = os.path.join(adml_dir, adml_filename)
        with open(adml_path, 'w', encoding='utf-8') as f:
            f.write(adml_content)
        
        result = {
            "template_id": template_id,
            "template_name": template.name,
            "admx_file": admx_path,
            "adml_file": adml_path,
            "namespace": namespace,
            "prefix": prefix,
            "validation": {
                "is_valid": validation_result.is_valid if validation_result else None,
                "errors": validation_result.errors_count if validation_result else 0,
                "warnings": validation_result.warnings_count if validation_result else 0,
            } if validation_result else None
        }
        
        logger.info(f"Saved ADMX/ADML files to {output_dir}")
        
        return result
    
    def bulk_export_admx(self, template_ids: List[str],
                        output_dir: str = "admx_output",
                        namespace: str = "CISBenchmark",
                        prefix: str = "CIS") -> List[Dict[str, Any]]:
        """
        Export multiple templates to ADMX/ADML files
        
        Args:
            template_ids: List of template IDs to export
            output_dir: Output directory
            namespace: ADMX namespace
            prefix: Policy prefix
            
        Returns:
            List of export results
        """
        results = []
        
        for template_id in template_ids:
            try:
                result = self.save_admx_to_files(
                    template_id,
                    output_dir=output_dir,
                    namespace=namespace,
                    prefix=prefix,
                    validate=True
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to export template {template_id}: {e}")
                results.append({
                    "template_id": template_id,
                    "error": str(e),
                    "success": False
                })
        
        return results