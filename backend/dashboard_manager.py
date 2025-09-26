"""
CIS GPO Compliance Tool - Step 3: Dashboard Manager
Comprehensive dashboard management with advanced features including:
- Policy grouping and tagging
- History tracking and audit trails
- Advanced search and filtering
- Bulk operations
- Statistics and compliance metrics
- Offline-first data storage
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
import shutil
from pathlib import Path

from models_dashboard import (
    EnhancedPolicy, PolicyGroup, PolicyTag, PolicyChangeHistory,
    PolicyDocumentation, ComplianceStatistics, BulkOperation,
    DashboardExport, PolicyStatus, PolicyPriority, ChangeType,
    SearchRequest, BulkUpdateRequest, PolicyUpdateRequest
)

class DashboardManager:
    """Comprehensive dashboard manager for CIS GPO policies"""
    
    def __init__(self, data_dir: str = "dashboard_data"):
        """Initialize dashboard manager with local storage"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Data storage files
        self.policies_file = self.data_dir / "policies.json"
        self.groups_file = self.data_dir / "groups.json"
        self.tags_file = self.data_dir / "tags.json"
        self.history_file = self.data_dir / "history.json"
        self.documentation_file = self.data_dir / "documentation.json"
        self.statistics_file = self.data_dir / "statistics.json"
        
        # In-memory caches for performance
        self.policies_cache: Dict[str, EnhancedPolicy] = {}
        self.groups_cache: Dict[str, PolicyGroup] = {}
        self.tags_cache: Dict[str, PolicyTag] = {}
        self.history_cache: List[PolicyChangeHistory] = []
        self.documentation_cache: Dict[str, PolicyDocumentation] = {}
        
        # Load existing data
        self._load_all_data()
        
        # Initialize default tags and groups if empty
        if not self.tags_cache:
            self._create_default_tags()
        if not self.groups_cache:
            self._create_default_groups()
    
    def _load_all_data(self):
        """Load all data from storage files"""
        try:
            # Load policies
            if self.policies_file.exists():
                with open(self.policies_file, 'r') as f:
                    policies_data = json.load(f)
                    self.policies_cache = {
                        pid: EnhancedPolicy(**data) for pid, data in policies_data.items()
                    }
            
            # Load groups
            if self.groups_file.exists():
                with open(self.groups_file, 'r') as f:
                    groups_data = json.load(f)
                    self.groups_cache = {
                        gid: PolicyGroup(**data) for gid, data in groups_data.items()
                    }
            
            # Load tags
            if self.tags_file.exists():
                with open(self.tags_file, 'r') as f:
                    tags_data = json.load(f)
                    self.tags_cache = {
                        tid: PolicyTag(**data) for tid, data in tags_data.items()
                    }
            
            # Load history
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history_data = json.load(f)
                    self.history_cache = [
                        PolicyChangeHistory(**item) for item in history_data
                    ]
            
            # Load documentation
            if self.documentation_file.exists():
                with open(self.documentation_file, 'r') as f:
                    docs_data = json.load(f)
                    self.documentation_cache = {
                        pid: PolicyDocumentation(**data) for pid, data in docs_data.items()
                    }
                    
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def _save_all_data(self):
        """Save all data to storage files"""
        try:
            # Save policies
            policies_data = {
                pid: policy.dict() for pid, policy in self.policies_cache.items()
            }
            with open(self.policies_file, 'w') as f:
                json.dump(policies_data, f, indent=2, default=str)
            
            # Save groups
            groups_data = {
                gid: group.dict() for gid, group in self.groups_cache.items()
            }
            with open(self.groups_file, 'w') as f:
                json.dump(groups_data, f, indent=2, default=str)
            
            # Save tags
            tags_data = {
                tid: tag.dict() for tid, tag in self.tags_cache.items()
            }
            with open(self.tags_file, 'w') as f:
                json.dump(tags_data, f, indent=2, default=str)
            
            # Save history (keep last 10000 entries)
            history_data = [
                item.dict() for item in self.history_cache[-10000:]
            ]
            with open(self.history_file, 'w') as f:
                json.dump(history_data, f, indent=2, default=str)
            
            # Save documentation
            docs_data = {
                pid: doc.dict() for pid, doc in self.documentation_cache.items()
            }
            with open(self.documentation_file, 'w') as f:
                json.dump(docs_data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"Error saving data: {e}")
            raise
    
    def _create_default_tags(self):
        """Create default system tags"""
        default_tags = [
            {"name": "Critical", "description": "Critical security policies", "color": "#d32f2f"},
            {"name": "Firewall", "description": "Firewall related policies", "color": "#ff5722"},
            {"name": "Password Policy", "description": "Password and authentication policies", "color": "#673ab7"},
            {"name": "User Rights", "description": "User rights and permissions", "color": "#3f51b5"},
            {"name": "Audit Policy", "description": "System auditing policies", "color": "#2196f3"},
            {"name": "Network Security", "description": "Network security configurations", "color": "#00bcd4"},
            {"name": "System Services", "description": "Windows system services", "color": "#009688"},
            {"name": "Registry Settings", "description": "Registry configuration policies", "color": "#4caf50"},
            {"name": "Level 1", "description": "CIS Level 1 policies", "color": "#8bc34a"},
            {"name": "Level 2", "description": "CIS Level 2 policies", "color": "#cddc39"},
        ]
        
        for tag_data in default_tags:
            tag_id = str(uuid.uuid4())
            tag = PolicyTag(
                tag_id=tag_id,
                **tag_data,
                created_at=datetime.now()
            )
            self.tags_cache[tag_id] = tag
        
        self._save_all_data()
    
    def _create_default_groups(self):
        """Create default system groups"""
        default_groups = [
            {"name": "Security Settings", "description": "Core security configuration policies"},
            {"name": "User Account Control", "description": "UAC and user account policies"},
            {"name": "Windows Firewall", "description": "Windows Firewall policies"},
            {"name": "Audit Policies", "description": "System auditing and logging"},
            {"name": "Administrative Templates", "description": "GPO administrative templates"},
            {"name": "System Services", "description": "Windows system service configurations"},
            {"name": "Network Security", "description": "Network and communication security"},
            {"name": "Uncategorized", "description": "Policies not yet categorized"},
        ]
        
        for group_data in default_groups:
            group_id = str(uuid.uuid4())
            group = PolicyGroup(
                group_id=group_id,
                **group_data,
                is_system_group=True,
                created_at=datetime.now()
            )
            self.groups_cache[group_id] = group
        
        self._save_all_data()
    
    def _add_history_entry(self, policy_id: str, change_type: ChangeType, 
                          old_value: Dict = None, new_value: Dict = None,
                          notes: str = None, user_id: str = "system",
                          batch_id: str = None, changed_fields: List[str] = None):
        """Add entry to change history"""
        history_entry = PolicyChangeHistory(
            history_id=str(uuid.uuid4()),
            policy_id=policy_id,
            change_type=change_type,
            old_value=old_value or {},
            new_value=new_value or {},
            changed_fields=changed_fields or [],
            user_id=user_id,
            notes=notes,
            batch_id=batch_id,
            timestamp=datetime.now()
        )
        self.history_cache.append(history_entry)
        return history_entry
    
    def _update_tag_usage_counts(self):
        """Update usage counts for all tags"""
        tag_usage = Counter()
        for policy in self.policies_cache.values():
            for tag_id in policy.tag_ids:
                tag_usage[tag_id] += 1
        
        for tag_id, count in tag_usage.items():
            if tag_id in self.tags_cache:
                self.tags_cache[tag_id].usage_count = count
        
        # Set unused tags to 0
        for tag_id, tag in self.tags_cache.items():
            if tag_id not in tag_usage:
                tag.usage_count = 0
    
    def _calculate_statistics(self) -> ComplianceStatistics:
        """Calculate comprehensive dashboard statistics"""
        policies = list(self.policies_cache.values())
        total_policies = len(policies)
        
        if total_policies == 0:
            return ComplianceStatistics()
        
        # Status breakdown
        status_counts = Counter(policy.status for policy in policies)
        enabled = status_counts.get(PolicyStatus.ENABLED, 0)
        disabled = status_counts.get(PolicyStatus.DISABLED, 0)
        not_configured = status_counts.get(PolicyStatus.NOT_CONFIGURED, 0)
        pending = status_counts.get(PolicyStatus.PENDING, 0)
        error = status_counts.get(PolicyStatus.ERROR, 0)
        
        # Priority breakdown
        priority_counts = Counter(policy.priority for policy in policies)
        critical = priority_counts.get(PolicyPriority.CRITICAL, 0)
        high = priority_counts.get(PolicyPriority.HIGH, 0)
        medium = priority_counts.get(PolicyPriority.MEDIUM, 0)
        low = priority_counts.get(PolicyPriority.LOW, 0)
        
        # Calculate compliance percentages
        configured_policies = enabled + disabled
        compliance_percentage = (configured_policies / total_policies) * 100 if total_policies > 0 else 0
        enabled_percentage = (enabled / total_policies) * 100 if total_policies > 0 else 0
        
        # Critical policy compliance
        critical_policies = [p for p in policies if p.priority == PolicyPriority.CRITICAL]
        critical_configured = sum(1 for p in critical_policies if p.status in [PolicyStatus.ENABLED, PolicyStatus.DISABLED])
        critical_compliance = (critical_configured / len(critical_policies)) * 100 if critical_policies else 100
        
        # Grouping statistics
        total_groups = len(self.groups_cache)
        grouped_policies = set()
        for policy in policies:
            if policy.group_ids:
                grouped_policies.add(policy.policy_id)
        ungrouped = total_policies - len(grouped_policies)
        
        # Tag statistics
        total_tags = len(self.tags_cache)
        tagged_policies = set()
        for policy in policies:
            if policy.tag_ids:
                tagged_policies.add(policy.policy_id)
        untagged = total_policies - len(tagged_policies)
        
        # Activity metrics
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_changes = sum(1 for h in self.history_cache if h.timestamp > recent_cutoff)
        total_changes = len(self.history_cache)
        
        return ComplianceStatistics(
            total_policies=total_policies,
            enabled_policies=enabled,
            disabled_policies=disabled,
            not_configured_policies=not_configured,
            pending_policies=pending,
            error_policies=error,
            critical_policies=critical,
            high_priority_policies=high,
            medium_priority_policies=medium,
            low_priority_policies=low,
            compliance_percentage=round(compliance_percentage, 2),
            enabled_percentage=round(enabled_percentage, 2),
            critical_compliance=round(critical_compliance, 2),
            total_groups=total_groups,
            ungrouped_policies=ungrouped,
            total_tags=total_tags,
            untagged_policies=untagged,
            recent_changes=recent_changes,
            total_changes=total_changes,
            last_updated=datetime.now()
        )
    
    # Policy Management Methods
    
    def import_policies_from_template_system(self, template_policies: List[Dict]) -> Dict[str, Any]:
        """Import policies from the existing template system"""
        imported_count = 0
        updated_count = 0
        batch_id = str(uuid.uuid4())
        
        for policy_data in template_policies:
            try:
                policy_id = policy_data.get('policy_id')
                if not policy_id:
                    continue
                
                # Convert template policy to enhanced policy
                enhanced_policy = EnhancedPolicy(
                    policy_id=policy_id,
                    policy_name=policy_data.get('policy_name', policy_data.get('title', 'Unknown Policy')),
                    title=policy_data.get('title'),
                    description=policy_data.get('description'),
                    category=policy_data.get('category'),
                    subcategory=policy_data.get('subcategory'),
                    status=PolicyStatus(policy_data.get('status', 'not_configured')),
                    required_value=policy_data.get('required_value'),
                    registry_path=policy_data.get('registry_path'),
                    gpo_path=policy_data.get('gpo_path'),
                    cis_level=policy_data.get('cis_level'),
                    cis_section=policy_data.get('cis_section'),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                # Auto-assign to appropriate groups based on category
                self._auto_assign_groups(enhanced_policy)
                
                # Auto-assign tags based on content
                self._auto_assign_tags(enhanced_policy)
                
                if policy_id in self.policies_cache:
                    # Update existing policy
                    old_policy = self.policies_cache[policy_id]
                    self.policies_cache[policy_id] = enhanced_policy
                    updated_count += 1
                    
                    self._add_history_entry(
                        policy_id=policy_id,
                        change_type=ChangeType.UPDATED,
                        old_value=old_policy.dict(),
                        new_value=enhanced_policy.dict(),
                        notes="Policy updated from template system import",
                        batch_id=batch_id
                    )
                else:
                    # Add new policy
                    self.policies_cache[policy_id] = enhanced_policy
                    imported_count += 1
                    
                    self._add_history_entry(
                        policy_id=policy_id,
                        change_type=ChangeType.IMPORTED,
                        new_value=enhanced_policy.dict(),
                        notes="Policy imported from template system",
                        batch_id=batch_id
                    )
                    
            except Exception as e:
                print(f"Error importing policy {policy_data.get('policy_id', 'unknown')}: {e}")
                continue
        
        # Update tag usage counts
        self._update_tag_usage_counts()
        
        # Save all data
        self._save_all_data()
        
        return {
            "imported_policies": imported_count,
            "updated_policies": updated_count,
            "total_processed": len(template_policies),
            "batch_id": batch_id
        }
    
    def _auto_assign_groups(self, policy: EnhancedPolicy):
        """Automatically assign policy to appropriate groups based on content"""
        category_mappings = {
            "security": ["Security Settings"],
            "firewall": ["Windows Firewall"],
            "audit": ["Audit Policies"],
            "user": ["User Account Control"],
            "network": ["Network Security"],
            "service": ["System Services"],
            "administrative": ["Administrative Templates"]
        }
        
        assigned_groups = []
        policy_text = f"{policy.policy_name} {policy.description or ''} {policy.category or ''}".lower()
        
        for keyword, group_names in category_mappings.items():
            if keyword in policy_text:
                for group_name in group_names:
                    for group in self.groups_cache.values():
                        if group.name == group_name:
                            assigned_groups.append(group.group_id)
                            break
        
        # If no specific group found, assign to "Uncategorized"
        if not assigned_groups:
            for group in self.groups_cache.values():
                if group.name == "Uncategorized":
                    assigned_groups.append(group.group_id)
                    break
        
        policy.group_ids = assigned_groups
    
    def _auto_assign_tags(self, policy: EnhancedPolicy):
        """Automatically assign tags based on policy content"""
        tag_mappings = {
            "firewall": ["Firewall"],
            "password": ["Password Policy"],
            "audit": ["Audit Policy"],
            "user": ["User Rights"],
            "network": ["Network Security"],
            "service": ["System Services"],
            "registry": ["Registry Settings"]
        }
        
        # Assign CIS level tags
        if policy.cis_level:
            level_tag = f"Level {policy.cis_level}" if "Level" not in policy.cis_level else policy.cis_level
            for tag in self.tags_cache.values():
                if tag.name == level_tag:
                    policy.tag_ids.append(tag.tag_id)
                    break
        
        # Assign content-based tags
        policy_text = f"{policy.policy_name} {policy.description or ''} {policy.category or ''}".lower()
        
        for keyword, tag_names in tag_mappings.items():
            if keyword in policy_text:
                for tag_name in tag_names:
                    for tag in self.tags_cache.values():
                        if tag.name == tag_name and tag.tag_id not in policy.tag_ids:
                            policy.tag_ids.append(tag.tag_id)
                            break
        
        # Remove duplicates
        policy.tag_ids = list(set(policy.tag_ids))
    
    def get_all_policies(self, include_metadata: bool = True) -> List[Dict[str, Any]]:
        """Get all policies with optional metadata"""
        policies = []
        for policy in self.policies_cache.values():
            policy_dict = policy.dict()
            
            if include_metadata:
                # Add group names
                policy_dict['groups'] = [
                    {"id": gid, "name": self.groups_cache[gid].name}
                    for gid in policy.group_ids if gid in self.groups_cache
                ]
                
                # Add tag names
                policy_dict['tags'] = [
                    {"id": tid, "name": self.tags_cache[tid].name, "color": self.tags_cache[tid].color}
                    for tid in policy.tag_ids if tid in self.tags_cache
                ]
                
                # Add documentation if exists
                if policy.policy_id in self.documentation_cache:
                    policy_dict['documentation'] = self.documentation_cache[policy.policy_id].dict()
            
            policies.append(policy_dict)
        
        return policies
    
    def search_policies(self, request: SearchRequest) -> Tuple[List[Dict[str, Any]], int]:
        """Advanced policy search with filtering and pagination"""
        policies = list(self.policies_cache.values())
        
        # Apply filters
        if request.status_filter:
            policies = [p for p in policies if p.status in request.status_filter]
        
        if request.priority_filter:
            policies = [p for p in policies if p.priority in request.priority_filter]
        
        if request.tag_filter:
            policies = [p for p in policies if any(tag_id in p.tag_ids for tag_id in request.tag_filter)]
        
        if request.group_filter:
            policies = [p for p in policies if any(group_id in p.group_ids for group_id in request.group_filter)]
        
        if request.category_filter:
            policies = [p for p in policies if p.category in request.category_filter]
        
        if request.cis_level_filter:
            policies = [p for p in policies if p.cis_level in request.cis_level_filter]
        
        # Text search
        if request.query:
            query = request.query.lower()
            filtered_policies = []
            for policy in policies:
                searchable_text = f"{policy.policy_name} {policy.description or ''} {policy.category or ''} {policy.registry_path or ''} {policy.gpo_path or ''}".lower()
                if query in searchable_text:
                    filtered_policies.append(policy)
            policies = filtered_policies
        
        # Date filtering
        if request.date_from or request.date_to:
            date_filtered = []
            for policy in policies:
                policy_date = policy.updated_at
                if request.date_from and policy_date < request.date_from:
                    continue
                if request.date_to and policy_date > request.date_to:
                    continue
                date_filtered.append(policy)
            policies = date_filtered
        
        total_count = len(policies)
        
        # Sorting
        reverse = request.sort_order.lower() == 'desc'
        if request.sort_by == 'policy_name':
            policies.sort(key=lambda p: p.policy_name.lower(), reverse=reverse)
        elif request.sort_by == 'status':
            policies.sort(key=lambda p: p.status.value, reverse=reverse)
        elif request.sort_by == 'priority':
            priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
            policies.sort(key=lambda p: priority_order.get(p.priority.value, 5), reverse=reverse)
        elif request.sort_by == 'updated_at':
            policies.sort(key=lambda p: p.updated_at, reverse=reverse)
        elif request.sort_by == 'category':
            policies.sort(key=lambda p: p.category or '', reverse=reverse)
        
        # Pagination
        start_idx = request.offset
        end_idx = start_idx + request.limit
        paginated_policies = policies[start_idx:end_idx]
        
        # Convert to dict with metadata
        result_policies = []
        for policy in paginated_policies:
            policy_dict = policy.dict()
            # Add metadata
            policy_dict['groups'] = [
                {"id": gid, "name": self.groups_cache[gid].name}
                for gid in policy.group_ids if gid in self.groups_cache
            ]
            policy_dict['tags'] = [
                {"id": tid, "name": self.tags_cache[tid].name, "color": self.tags_cache[tid].color}
                for tid in policy.tag_ids if tid in self.tags_cache
            ]
            result_policies.append(policy_dict)
        
        return result_policies, total_count
    
    def update_policy(self, policy_id: str, updates: PolicyUpdateRequest, user_id: str = "system") -> bool:
        """Update individual policy with history tracking"""
        if policy_id not in self.policies_cache:
            return False
        
        old_policy = self.policies_cache[policy_id]
        old_dict = old_policy.dict()
        
        # Apply updates
        updated_policy = old_policy.copy()
        changed_fields = []
        
        if updates.status is not None:
            updated_policy.status = updates.status
            changed_fields.append('status')
        
        if updates.priority is not None:
            updated_policy.priority = updates.priority
            changed_fields.append('priority')
        
        if updates.current_value is not None:
            updated_policy.current_value = updates.current_value
            changed_fields.append('current_value')
        
        if updates.tag_ids is not None:
            updated_policy.tag_ids = updates.tag_ids
            changed_fields.append('tag_ids')
        
        if updates.group_ids is not None:
            updated_policy.group_ids = updates.group_ids
            changed_fields.append('group_ids')
        
        if updates.custom_fields is not None:
            updated_policy.custom_fields.update(updates.custom_fields)
            changed_fields.append('custom_fields')
        
        updated_policy.updated_at = datetime.now()
        updated_policy.last_modified_by = user_id
        updated_policy.version += 1
        
        # Save updated policy
        self.policies_cache[policy_id] = updated_policy
        
        # Add history entry
        self._add_history_entry(
            policy_id=policy_id,
            change_type=ChangeType.UPDATED,
            old_value=old_dict,
            new_value=updated_policy.dict(),
            changed_fields=changed_fields,
            notes=updates.user_note,
            user_id=user_id
        )
        
        # Update tag usage
        self._update_tag_usage_counts()
        
        # Save data
        self._save_all_data()
        
        return True
    
    def bulk_update_policies(self, request: BulkUpdateRequest, user_id: str = "system") -> Dict[str, Any]:
        """Perform bulk updates on multiple policies"""
        batch_id = str(uuid.uuid4())
        updated_count = 0
        failed_policies = []
        
        for policy_id in request.policy_ids:
            if policy_id not in self.policies_cache:
                failed_policies.append({"policy_id": policy_id, "error": "Policy not found"})
                continue
            
            try:
                old_policy = self.policies_cache[policy_id]
                old_dict = old_policy.dict()
                
                # Apply updates
                updated_policy = old_policy.copy()
                changed_fields = []
                
                for field, value in request.updates.items():
                    if hasattr(updated_policy, field):
                        if field == 'tag_ids':
                            # Handle tag assignment
                            if isinstance(value, list):
                                updated_policy.tag_ids = value
                            elif isinstance(value, str) and value.startswith('+'):
                                # Add tag
                                tag_id = value[1:]
                                if tag_id not in updated_policy.tag_ids:
                                    updated_policy.tag_ids.append(tag_id)
                            elif isinstance(value, str) and value.startswith('-'):
                                # Remove tag
                                tag_id = value[1:]
                                if tag_id in updated_policy.tag_ids:
                                    updated_policy.tag_ids.remove(tag_id)
                        elif field == 'group_ids':
                            # Handle group assignment
                            if isinstance(value, list):
                                updated_policy.group_ids = value
                            elif isinstance(value, str) and value.startswith('+'):
                                # Add to group
                                group_id = value[1:]
                                if group_id not in updated_policy.group_ids:
                                    updated_policy.group_ids.append(group_id)
                            elif isinstance(value, str) and value.startswith('-'):
                                # Remove from group
                                group_id = value[1:]
                                if group_id in updated_policy.group_ids:
                                    updated_policy.group_ids.remove(group_id)
                        else:
                            setattr(updated_policy, field, value)
                        changed_fields.append(field)
                
                updated_policy.updated_at = datetime.now()
                updated_policy.last_modified_by = user_id
                updated_policy.version += 1
                
                # Save updated policy
                self.policies_cache[policy_id] = updated_policy
                
                # Add history entry
                self._add_history_entry(
                    policy_id=policy_id,
                    change_type=ChangeType.BULK_UPDATE,
                    old_value=old_dict,
                    new_value=updated_policy.dict(),
                    changed_fields=changed_fields,
                    notes=request.user_note,
                    user_id=user_id,
                    batch_id=batch_id
                )
                
                updated_count += 1
                
            except Exception as e:
                failed_policies.append({"policy_id": policy_id, "error": str(e)})
        
        # Update tag usage and save
        self._update_tag_usage_counts()
        self._save_all_data()
        
        return {
            "batch_id": batch_id,
            "updated_count": updated_count,
            "failed_count": len(failed_policies),
            "failed_policies": failed_policies,
            "total_requested": len(request.policy_ids)
        }
    
    # Group Management Methods
    
    def create_group(self, name: str, description: str = None, parent_group_id: str = None, user_id: str = "system") -> PolicyGroup:
        """Create new policy group"""
        group_id = str(uuid.uuid4())
        
        group = PolicyGroup(
            group_id=group_id,
            name=name,
            description=description,
            parent_group_id=parent_group_id,
            created_by=user_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.groups_cache[group_id] = group
        self._save_all_data()
        
        return group
    
    def get_all_groups(self, include_hierarchy: bool = True) -> List[Dict[str, Any]]:
        """Get all groups with optional hierarchy info"""
        groups = []
        for group in self.groups_cache.values():
            group_dict = group.dict()
            
            if include_hierarchy:
                # Add parent group info
                if group.parent_group_id and group.parent_group_id in self.groups_cache:
                    parent = self.groups_cache[group.parent_group_id]
                    group_dict['parent_group'] = {"id": parent.group_id, "name": parent.name}
                
                # Add child groups
                children = [
                    {"id": g.group_id, "name": g.name}
                    for g in self.groups_cache.values()
                    if g.parent_group_id == group.group_id
                ]
                group_dict['child_groups'] = children
                
                # Add policy count
                group_dict['policy_count'] = len(group.policy_ids)
            
            groups.append(group_dict)
        
        return groups
    
    def update_group(self, group_id: str, name: str = None, description: str = None, 
                    policy_ids: List[str] = None, user_id: str = "system") -> bool:
        """Update group information"""
        if group_id not in self.groups_cache:
            return False
        
        group = self.groups_cache[group_id]
        
        if name is not None:
            group.name = name
        if description is not None:
            group.description = description
        if policy_ids is not None:
            # Update group membership in policies
            old_policy_ids = set(group.policy_ids)
            new_policy_ids = set(policy_ids)
            
            # Remove group from policies no longer in group
            for policy_id in old_policy_ids - new_policy_ids:
                if policy_id in self.policies_cache:
                    policy = self.policies_cache[policy_id]
                    if group_id in policy.group_ids:
                        policy.group_ids.remove(group_id)
            
            # Add group to new policies
            for policy_id in new_policy_ids - old_policy_ids:
                if policy_id in self.policies_cache:
                    policy = self.policies_cache[policy_id]
                    if group_id not in policy.group_ids:
                        policy.group_ids.append(group_id)
            
            group.policy_ids = policy_ids
        
        group.updated_at = datetime.now()
        self._save_all_data()
        
        return True
    
    def delete_group(self, group_id: str) -> bool:
        """Delete group and remove from policies"""
        if group_id not in self.groups_cache:
            return False
        
        group = self.groups_cache[group_id]
        
        # Don't delete system groups
        if group.is_system_group:
            return False
        
        # Remove group from all policies
        for policy_id in group.policy_ids:
            if policy_id in self.policies_cache:
                policy = self.policies_cache[policy_id]
                if group_id in policy.group_ids:
                    policy.group_ids.remove(group_id)
        
        # Delete the group
        del self.groups_cache[group_id]
        self._save_all_data()
        
        return True
    
    # Tag Management Methods
    
    def create_tag(self, name: str, description: str = None, color: str = "#1976d2", user_id: str = "system") -> PolicyTag:
        """Create new policy tag"""
        tag_id = str(uuid.uuid4())
        
        tag = PolicyTag(
            tag_id=tag_id,
            name=name,
            description=description,
            color=color,
            created_by=user_id,
            created_at=datetime.now()
        )
        
        self.tags_cache[tag_id] = tag
        self._save_all_data()
        
        return tag
    
    def get_all_tags(self) -> List[Dict[str, Any]]:
        """Get all tags with usage statistics"""
        self._update_tag_usage_counts()
        return [tag.dict() for tag in self.tags_cache.values()]
    
    def update_tag(self, tag_id: str, name: str = None, description: str = None, color: str = None) -> bool:
        """Update tag information"""
        if tag_id not in self.tags_cache:
            return False
        
        tag = self.tags_cache[tag_id]
        
        if name is not None:
            tag.name = name
        if description is not None:
            tag.description = description
        if color is not None:
            tag.color = color
        
        self._save_all_data()
        return True
    
    def delete_tag(self, tag_id: str) -> bool:
        """Delete tag and remove from policies"""
        if tag_id not in self.tags_cache:
            return False
        
        # Remove tag from all policies
        for policy in self.policies_cache.values():
            if tag_id in policy.tag_ids:
                policy.tag_ids.remove(tag_id)
        
        # Delete the tag
        del self.tags_cache[tag_id]
        self._save_all_data()
        
        return True
    
    # History and Audit Methods
    
    def get_policy_history(self, policy_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history for specific policy"""
        policy_history = [
            h for h in self.history_cache 
            if h.policy_id == policy_id
        ]
        
        # Sort by timestamp descending
        policy_history.sort(key=lambda h: h.timestamp, reverse=True)
        
        return [h.dict() for h in policy_history[:limit]]
    
    def get_recent_changes(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent changes across all policies"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_changes = [
            h for h in self.history_cache
            if h.timestamp > cutoff
        ]
        
        # Sort by timestamp descending
        recent_changes.sort(key=lambda h: h.timestamp, reverse=True)
        
        return [h.dict() for h in recent_changes[:limit]]
    
    def get_batch_changes(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all changes from a specific batch operation"""
        batch_changes = [
            h for h in self.history_cache
            if h.batch_id == batch_id
        ]
        
        return [h.dict() for h in batch_changes]
    
    def revert_policy_change(self, history_id: str, user_id: str = "system") -> bool:
        """Revert a policy to a previous state"""
        history_entry = None
        for h in self.history_cache:
            if h.history_id == history_id:
                history_entry = h
                break
        
        if not history_entry or history_entry.policy_id not in self.policies_cache:
            return False
        
        # Can only revert certain change types
        if history_entry.change_type not in [ChangeType.UPDATED, ChangeType.STATUS_CHANGED, ChangeType.VALUE_CHANGED]:
            return False
        
        # Restore old values
        policy = self.policies_cache[history_entry.policy_id]
        old_dict = policy.dict()
        
        for field, value in history_entry.old_value.items():
            if hasattr(policy, field):
                setattr(policy, field, value)
        
        policy.updated_at = datetime.now()
        policy.last_modified_by = user_id
        policy.version += 1
        
        # Add revert history entry
        self._add_history_entry(
            policy_id=history_entry.policy_id,
            change_type=ChangeType.UPDATED,
            old_value=old_dict,
            new_value=policy.dict(),
            notes=f"Reverted change from {history_entry.timestamp}",
            user_id=user_id
        )
        
        self._save_all_data()
        return True
    
    # Statistics and Dashboard Methods
    
    def get_dashboard_statistics(self) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics"""
        stats = self._calculate_statistics()
        return stats.dict()
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get compliance summary by category and priority"""
        policies = list(self.policies_cache.values())
        
        # Category breakdown
        category_stats = {}
        for policy in policies:
            category = policy.category or "Uncategorized"
            if category not in category_stats:
                category_stats[category] = {
                    "total": 0,
                    "enabled": 0,
                    "disabled": 0,
                    "not_configured": 0
                }
            
            category_stats[category]["total"] += 1
            category_stats[category][policy.status.value] += 1
        
        # Priority breakdown
        priority_stats = {}
        for priority in PolicyPriority:
            priority_policies = [p for p in policies if p.priority == priority]
            priority_stats[priority.value] = {
                "total": len(priority_policies),
                "enabled": sum(1 for p in priority_policies if p.status == PolicyStatus.ENABLED),
                "disabled": sum(1 for p in priority_policies if p.status == PolicyStatus.DISABLED),
                "not_configured": sum(1 for p in priority_policies if p.status == PolicyStatus.NOT_CONFIGURED)
            }
        
        # Group statistics
        group_stats = {}
        for group in self.groups_cache.values():
            group_policies = [self.policies_cache[pid] for pid in group.policy_ids if pid in self.policies_cache]
            group_stats[group.name] = {
                "total": len(group_policies),
                "enabled": sum(1 for p in group_policies if p.status == PolicyStatus.ENABLED),
                "disabled": sum(1 for p in group_policies if p.status == PolicyStatus.DISABLED),
                "not_configured": sum(1 for p in group_policies if p.status == PolicyStatus.NOT_CONFIGURED)
            }
        
        return {
            "by_category": category_stats,
            "by_priority": priority_stats,
            "by_group": group_stats,
            "last_updated": datetime.now().isoformat()
        }
    
    # Export/Import Methods
    
    def export_dashboard_data(self, export_type: str = "full", policy_ids: List[str] = None) -> DashboardExport:
        """Export dashboard data for backup or sharing"""
        export_id = str(uuid.uuid4())
        
        # Select policies to export
        if export_type == "full":
            export_policies = list(self.policies_cache.values())
        elif export_type == "partial" and policy_ids:
            export_policies = [self.policies_cache[pid] for pid in policy_ids if pid in self.policies_cache]
        else:
            export_policies = []
        
        # Export related groups and tags
        used_group_ids = set()
        used_tag_ids = set()
        for policy in export_policies:
            used_group_ids.update(policy.group_ids)
            used_tag_ids.update(policy.tag_ids)
        
        export_groups = [self.groups_cache[gid] for gid in used_group_ids if gid in self.groups_cache]
        export_tags = [self.tags_cache[tid] for tid in used_tag_ids if tid in self.tags_cache]
        
        # Export related history and documentation
        policy_ids_set = {p.policy_id for p in export_policies}
        export_history = [h for h in self.history_cache if h.policy_id in policy_ids_set]
        export_docs = [self.documentation_cache[pid] for pid in policy_ids_set if pid in self.documentation_cache]
        
        export_data = DashboardExport(
            export_id=export_id,
            export_type=export_type,
            policies=export_policies,
            groups=export_groups,
            tags=export_tags,
            history=export_history[-1000:],  # Limit history to last 1000 entries
            documentation=export_docs,
            statistics=self._calculate_statistics() if export_type == "full" else None,
            created_at=datetime.now()
        )
        
        return export_data
    
    def import_dashboard_data(self, import_data: DashboardExport, merge: bool = True) -> Dict[str, Any]:
        """Import dashboard data from export"""
        imported_stats = {
            "policies": 0,
            "groups": 0,
            "tags": 0,
            "documentation": 0,
            "updated_policies": 0,
            "updated_groups": 0,
            "updated_tags": 0
        }
        
        batch_id = str(uuid.uuid4())
        
        # Import tags first
        for tag in import_data.tags:
            if tag.tag_id not in self.tags_cache:
                self.tags_cache[tag.tag_id] = tag
                imported_stats["tags"] += 1
            elif merge:
                self.tags_cache[tag.tag_id] = tag
                imported_stats["updated_tags"] += 1
        
        # Import groups
        for group in import_data.groups:
            if group.group_id not in self.groups_cache:
                self.groups_cache[group.group_id] = group
                imported_stats["groups"] += 1
            elif merge:
                self.groups_cache[group.group_id] = group
                imported_stats["updated_groups"] += 1
        
        # Import policies
        for policy in import_data.policies:
            if policy.policy_id not in self.policies_cache:
                self.policies_cache[policy.policy_id] = policy
                imported_stats["policies"] += 1
                
                self._add_history_entry(
                    policy_id=policy.policy_id,
                    change_type=ChangeType.IMPORTED,
                    new_value=policy.dict(),
                    notes="Policy imported from dashboard export",
                    batch_id=batch_id
                )
            elif merge:
                old_policy = self.policies_cache[policy.policy_id]
                self.policies_cache[policy.policy_id] = policy
                imported_stats["updated_policies"] += 1
                
                self._add_history_entry(
                    policy_id=policy.policy_id,
                    change_type=ChangeType.UPDATED,
                    old_value=old_policy.dict(),
                    new_value=policy.dict(),
                    notes="Policy updated from dashboard import",
                    batch_id=batch_id
                )
        
        # Import documentation
        for doc in import_data.documentation:
            self.documentation_cache[doc.policy_id] = doc
            imported_stats["documentation"] += 1
        
        # Import history (append only)
        self.history_cache.extend(import_data.history)
        
        # Update and save
        self._update_tag_usage_counts()
        self._save_all_data()
        
        return imported_stats
    
    # Documentation Methods
    
    def update_policy_documentation(self, policy_id: str, notes: str = None, 
                                  cis_reference: str = None, rationale: str = None,
                                  impact_assessment: str = None, remediation_steps: str = None,
                                  related_policies: List[str] = None, external_links: List[str] = None,
                                  user_id: str = "system") -> bool:
        """Update policy documentation"""
        if policy_id not in self.policies_cache:
            return False
        
        if policy_id not in self.documentation_cache:
            self.documentation_cache[policy_id] = PolicyDocumentation(
                policy_id=policy_id,
                last_updated=datetime.now(),
                updated_by=user_id
            )
        
        doc = self.documentation_cache[policy_id]
        
        if notes is not None:
            doc.notes = notes
        if cis_reference is not None:
            doc.cis_reference = cis_reference
        if rationale is not None:
            doc.rationale = rationale
        if impact_assessment is not None:
            doc.impact_assessment = impact_assessment
        if remediation_steps is not None:
            doc.remediation_steps = remediation_steps
        if related_policies is not None:
            doc.related_policies = related_policies
        if external_links is not None:
            doc.external_links = external_links
        
        doc.last_updated = datetime.now()
        doc.updated_by = user_id
        
        self._save_all_data()
        return True
    
    def get_policy_documentation(self, policy_id: str) -> Dict[str, Any]:
        """Get documentation for specific policy"""
        if policy_id not in self.documentation_cache:
            return {}
        
        return self.documentation_cache[policy_id].dict()