"""
GPO Template Management Service (Step 2)
Handles template creation, editing, grouping, and policy management
"""

import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid

from models_templates import (
    PolicyItem, PolicyTemplate, PolicyGroup, PolicyEdit, PolicyStatus,
    PolicyType, TemplateExport, BulkEditRequest, PolicySearchRequest
)


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