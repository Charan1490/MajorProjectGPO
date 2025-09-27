"""
Main Remediation Manager for CIS GPO Compliance Tool
Coordinates automated remediation, backup, and rollback operations
"""

import os
import json
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import logging
import uuid

from .models_remediation import (
    RemediationPlan, RemediationSession, RemediationStatus, RemediationSeverity,
    SystemBackup, RollbackPlan, BackupType, RemediationType,
    serialize_remediation_plan, serialize_system_backup
)
from .backup_manager import BackupManager
from .remediation_engine import RemediationEngine
from .rollback_manager import RollbackManager

logger = logging.getLogger(__name__)


class RemediationManager:
    """Main manager for remediation and rollback operations"""
    
    def __init__(self, data_path: str = "data/remediation"):
        """Initialize remediation manager"""
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        backup_path = self.data_path / "backups"
        self.backup_manager = BackupManager(str(backup_path))
        
        self.remediation_engine = RemediationEngine(self.backup_manager)
        self.rollback_manager = RollbackManager(self.backup_manager)
        
        # Storage for remediation plans
        self.remediation_plans: Dict[str, RemediationPlan] = {}
        self.plans_file = self.data_path / "remediation_plans.json"
        
        # Load existing data
        self._load_remediation_plans()
        
        # Set up progress monitoring
        self.remediation_engine.add_progress_callback(self._on_remediation_progress)
    
    def _load_remediation_plans(self):
        """Load saved remediation plans"""
        try:
            if self.plans_file.exists():
                with open(self.plans_file, 'r') as f:
                    data = json.load(f)
                    for plan_data in data.get('plans', []):
                        try:
                            plan = self._deserialize_remediation_plan(plan_data)
                            self.remediation_plans[plan.plan_id] = plan
                        except Exception as e:
                            logger.error(f"Error loading remediation plan: {e}")
        except Exception as e:
            logger.error(f"Error loading remediation plans: {e}")
    
    def _save_remediation_plans(self):
        """Save remediation plans to storage"""
        try:
            data = {
                'plans': [serialize_remediation_plan(plan) for plan in self.remediation_plans.values()],
                'last_updated': datetime.now().isoformat()
            }
            with open(self.plans_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving remediation plans: {e}")
    
    def _deserialize_remediation_plan(self, data: Dict[str, Any]) -> RemediationPlan:
        """Deserialize remediation plan from JSON"""
        from .models_remediation import RemediationAction, deserialize_system_backup
        
        actions = []
        for action_data in data.get('actions', []):
            action = RemediationAction(
                action_id=action_data['action_id'],
                policy_id=action_data['policy_id'],
                policy_title=action_data['policy_title'],
                remediation_type=RemediationType(action_data['remediation_type']),
                severity=RemediationSeverity(action_data['severity']),
                current_value=action_data.get('current_value'),
                target_value=action_data.get('target_value'),
                registry_key=action_data.get('registry_key'),
                registry_value=action_data.get('registry_value'),
                description=action_data.get('description', ''),
                command=action_data.get('command'),
                script_content=action_data.get('script_content'),
                requires_reboot=action_data.get('requires_reboot', False),
                risk_level=action_data.get('risk_level', 'medium'),
                impact_description=action_data.get('impact_description', ''),
                reversible=action_data.get('reversible', True),
                status=RemediationStatus(action_data.get('status', 'pending')),
                error_message=action_data.get('error_message'),
                executed_at=datetime.fromisoformat(action_data['executed_at']) if action_data.get('executed_at') else None,
                execution_time_seconds=action_data.get('execution_time_seconds')
            )
            actions.append(action)
        
        return RemediationPlan(
            plan_id=data['plan_id'],
            name=data['name'],
            description=data['description'],
            created_at=datetime.fromisoformat(data['created_at']),
            created_by=data['created_by'],
            source_audit_id=data['source_audit_id'],
            target_system=data['target_system'],
            actions=actions,
            create_backup=data.get('create_backup', True),
            backup_type=BackupType(data.get('backup_type', 'selective')),
            require_confirmation=data.get('require_confirmation', True),
            continue_on_error=data.get('continue_on_error', False),
            max_parallel_actions=data.get('max_parallel_actions', 3),
            timeout_minutes=data.get('timeout_minutes', 60),
            retry_failed_actions=data.get('retry_failed_actions', True),
            max_retries=data.get('max_retries', 3),
            status=RemediationStatus(data.get('status', 'pending')),
            progress_percentage=data.get('progress_percentage', 0),
            current_action=data.get('current_action'),
            total_actions=data.get('total_actions', 0),
            successful_actions=data.get('successful_actions', 0),
            failed_actions=data.get('failed_actions', 0),
            skipped_actions=data.get('skipped_actions', 0),
            start_time=datetime.fromisoformat(data['start_time']) if data.get('start_time') else None,
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            estimated_completion=datetime.fromisoformat(data['estimated_completion']) if data.get('estimated_completion') else None,
            backup_id=data.get('backup_id')
        )
    
    def _on_remediation_progress(self, session: RemediationSession):
        """Handle remediation progress updates"""
        # Update the corresponding plan
        plan = self.remediation_plans.get(session.plan_id)
        if plan:
            plan.progress_percentage = session.progress_percentage
            plan.status = session.status
            self._save_remediation_plans()
    
    # Remediation Plan Management
    def create_remediation_plan_from_audit(
        self,
        name: str,
        description: str,
        audit_id: str,
        audit_results: List[Dict[str, Any]],
        created_by: str,
        **kwargs
    ) -> str:
        """Create remediation plan from audit results"""
        
        # Filter for failed policies only
        failed_policies = [
            policy for policy in audit_results 
            if policy.get('result', '').lower() in ['fail', 'failed', 'non-compliant']
        ]
        
        if not failed_policies:
            raise ValueError("No failed policies found in audit results")
        
        # Create plan using remediation engine
        plan_id = self.remediation_engine.create_remediation_plan(
            name=name,
            description=description,
            source_audit_id=audit_id,
            target_system=kwargs.get('target_system', 'localhost'),
            failed_policies=failed_policies,
            created_by=created_by,
            selective_policies=kwargs.get('selective_policies'),
            severity_filter=kwargs.get('severity_filter')
        )
        
        # The plan is created in the engine but we need to store it
        # For now, create a basic plan record
        plan = RemediationPlan(
            plan_id=plan_id,
            name=name,
            description=description,
            created_at=datetime.now(),
            created_by=created_by,
            source_audit_id=audit_id,
            target_system=kwargs.get('target_system', 'localhost'),
            total_actions=len(failed_policies)
        )
        
        self.remediation_plans[plan_id] = plan
        self._save_remediation_plans()
        
        logger.info(f"Created remediation plan: {plan_id} with {len(failed_policies)} failed policies")
        return plan_id
    
    def get_remediation_plan(self, plan_id: str) -> Optional[RemediationPlan]:
        """Get remediation plan by ID"""
        return self.remediation_plans.get(plan_id)
    
    def list_remediation_plans(
        self,
        created_by: str = None,
        status: RemediationStatus = None,
        limit: int = 50
    ) -> List[RemediationPlan]:
        """List remediation plans with optional filtering"""
        plans = list(self.remediation_plans.values())
        
        if created_by:
            plans = [p for p in plans if p.created_by == created_by]
        
        if status:
            plans = [p for p in plans if p.status == status]
        
        # Sort by creation date (newest first)
        plans.sort(key=lambda x: x.created_at, reverse=True)
        
        return plans[:limit]
    
    def delete_remediation_plan(self, plan_id: str) -> bool:
        """Delete remediation plan"""
        if plan_id in self.remediation_plans:
            plan = self.remediation_plans[plan_id]
            
            # Can't delete running plans
            if plan.status == RemediationStatus.RUNNING:
                return False
            
            del self.remediation_plans[plan_id]
            self._save_remediation_plans()
            
            logger.info(f"Deleted remediation plan: {plan_id}")
            return True
        return False
    
    # Remediation Execution
    def execute_remediation_plan(
        self,
        plan_id: str,
        operator: str,
        confirm_high_risk: bool = False,
        dry_run: bool = False
    ) -> str:
        """Execute remediation plan"""
        
        plan = self.remediation_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Remediation plan not found: {plan_id}")
        
        if plan.status != RemediationStatus.PENDING:
            raise ValueError(f"Plan is not in pending status: {plan.status.value}")
        
        if dry_run:
            return self._simulate_remediation_execution(plan, operator)
        
        # Execute using remediation engine
        session_id = self.remediation_engine.execute_remediation_plan(
            plan=plan,
            operator=operator,
            confirm_high_risk=confirm_high_risk
        )
        
        logger.info(f"Started remediation execution: plan={plan_id}, session={session_id}")
        return session_id
    
    def _simulate_remediation_execution(self, plan: RemediationPlan, operator: str) -> str:
        """Simulate remediation execution (dry run)"""
        session_id = str(uuid.uuid4())
        
        # Create mock session for dry run
        mock_session = RemediationSession(
            session_id=session_id,
            plan_id=plan.plan_id,
            operator=operator,
            start_time=datetime.now(),
            current_phase="dry_run_simulation",
            progress_percentage=100,
            status=RemediationStatus.COMPLETED
        )
        
        # Add simulation results
        mock_session.log_messages = [
            f"DRY RUN: Would execute {len(plan.actions)} remediation actions",
            f"DRY RUN: Backup would be created: {plan.create_backup}",
            f"DRY RUN: Estimated execution time: {len(plan.actions) * 2} minutes"
        ]
        
        for i, action in enumerate(plan.actions):
            mock_session.log_messages.append(f"DRY RUN: Action {i+1}: {action.policy_title} ({action.remediation_type.value})")
        
        return session_id
    
    def get_remediation_session(self, session_id: str) -> Optional[RemediationSession]:
        """Get remediation session status"""
        return self.remediation_engine.get_session_status(session_id)
    
    def cancel_remediation_session(self, session_id: str) -> bool:
        """Cancel active remediation session"""
        return self.remediation_engine.cancel_session(session_id)
    
    def get_remediation_results(self, plan_id: str) -> List[Dict[str, Any]]:
        """Get remediation results for a plan"""
        results = self.remediation_engine.get_session_results(plan_id)
        
        # Convert to serializable format
        serialized_results = []
        for result in results:
            serialized_results.append({
                'result_id': result.result_id,
                'action_id': result.action_id,
                'executed_at': result.executed_at.isoformat(),
                'executed_by': result.executed_by,
                'execution_time_seconds': result.execution_time_seconds,
                'success': result.success,
                'status_before': result.status_before,
                'status_after': result.status_after,
                'changes_made': result.changes_made,
                'error_message': result.error_message,
                'verification_passed': result.verification_passed
            })
        
        return serialized_results
    
    # Backup Management
    def create_system_backup(
        self,
        name: str,
        description: str,
        backup_type: BackupType,
        created_by: str,
        **kwargs
    ) -> str:
        """Create system backup"""
        return self.backup_manager.create_system_backup(
            name=name,
            description=description,
            backup_type=backup_type,
            created_by=created_by,
            policies=kwargs.get('policies'),
            registry_keys=kwargs.get('registry_keys'),
            gpos=kwargs.get('gpos')
        )
    
    def list_system_backups(
        self,
        backup_type: BackupType = None,
        created_by: str = None
    ) -> List[Dict[str, Any]]:
        """List system backups"""
        backups = self.backup_manager.list_backups(backup_type, created_by)
        
        # Convert to serializable format
        serialized_backups = []
        for backup in backups:
            serialized_backups.append(serialize_system_backup(backup))
        
        return serialized_backups
    
    def get_system_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get system backup by ID"""
        backup = self.backup_manager.get_backup(backup_id)
        if backup:
            return serialize_system_backup(backup)
        return None
    
    def delete_system_backup(self, backup_id: str) -> bool:
        """Delete system backup"""
        return self.backup_manager.delete_backup(backup_id)
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics"""
        return self.backup_manager.get_backup_statistics()
    
    # Rollback Management
    def create_rollback_plan(
        self,
        name: str,
        description: str,
        backup_id: str,
        created_by: str,
        selective_rollback: bool = False,
        selected_policies: List[str] = None
    ) -> str:
        """Create rollback plan"""
        return self.rollback_manager.create_rollback_plan(
            name=name,
            description=description,
            backup_id=backup_id,
            created_by=created_by,
            selective_rollback=selective_rollback,
            selected_policies=selected_policies
        )
    
    def execute_rollback_plan(
        self,
        rollback_id: str,
        operator: str,
        force_execution: bool = False
    ) -> bool:
        """Execute rollback plan"""
        return self.rollback_manager.execute_rollback_plan(
            rollback_id=rollback_id,
            operator=operator,
            force_execution=force_execution
        )
    
    def get_rollback_plan(self, rollback_id: str) -> Optional[RollbackPlan]:
        """Get rollback plan by ID"""
        return self.rollback_manager.get_rollback_plan(rollback_id)
    
    def list_rollback_plans(self, active_only: bool = True) -> List[RollbackPlan]:
        """List rollback plans"""
        return self.rollback_manager.list_rollback_plans(active_only)
    
    def cancel_rollback_plan(self, rollback_id: str) -> bool:
        """Cancel rollback plan"""
        return self.rollback_manager.cancel_rollback(rollback_id)
    
    def get_rollback_history(self, limit: int = 50) -> List[RollbackPlan]:
        """Get rollback history"""
        return self.rollback_manager.get_rollback_history(limit)
    
    # Analysis and Reporting
    def get_remediation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive remediation statistics"""
        plans = list(self.remediation_plans.values())
        
        stats = {
            'total_plans': len(plans),
            'by_status': {},
            'by_created_by': {},
            'total_actions': sum(p.total_actions for p in plans),
            'successful_actions': sum(p.successful_actions for p in plans),
            'failed_actions': sum(p.failed_actions for p in plans),
            'success_rate': 0,
            'average_execution_time': 0,
            'plans_with_backups': 0
        }
        
        # Group by status
        for plan in plans:
            status = plan.status.value
            if status not in stats['by_status']:
                stats['by_status'][status] = 0
            stats['by_status'][status] += 1
        
        # Group by creator
        for plan in plans:
            creator = plan.created_by
            if creator not in stats['by_created_by']:
                stats['by_created_by'][creator] = 0
            stats['by_created_by'][creator] += 1
        
        # Calculate success rate
        total_completed_actions = stats['successful_actions'] + stats['failed_actions']
        if total_completed_actions > 0:
            stats['success_rate'] = (stats['successful_actions'] / total_completed_actions) * 100
        
        # Calculate average execution time
        completed_plans = [p for p in plans if p.start_time and p.end_time]
        if completed_plans:
            total_time = sum((p.end_time - p.start_time).total_seconds() for p in completed_plans)
            stats['average_execution_time'] = total_time / len(completed_plans)
        
        # Count plans with backups
        stats['plans_with_backups'] = sum(1 for p in plans if p.backup_id)
        
        return stats
    
    def generate_remediation_report(
        self,
        plan_id: str,
        include_detailed_results: bool = True
    ) -> Dict[str, Any]:
        """Generate comprehensive remediation report"""
        plan = self.remediation_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Remediation plan not found: {plan_id}")
        
        report = {
            'plan_summary': serialize_remediation_plan(plan),
            'execution_summary': {
                'total_actions': plan.total_actions,
                'successful_actions': plan.successful_actions,
                'failed_actions': plan.failed_actions,
                'skipped_actions': plan.skipped_actions,
                'success_rate': (plan.successful_actions / plan.total_actions * 100) if plan.total_actions > 0 else 0,
                'execution_time_seconds': (plan.end_time - plan.start_time).total_seconds() if plan.start_time and plan.end_time else None
            },
            'backup_info': None,
            'detailed_results': [],
            'generated_at': datetime.now().isoformat()
        }
        
        # Add backup information
        if plan.backup_id:
            backup = self.backup_manager.get_backup(plan.backup_id)
            if backup:
                report['backup_info'] = serialize_system_backup(backup)
        
        # Add detailed results
        if include_detailed_results:
            report['detailed_results'] = self.get_remediation_results(plan_id)
        
        return report
    
    def export_remediation_logs(
        self,
        plan_id: str = None,
        date_range: tuple = None,
        output_format: str = "json"
    ) -> str:
        """Export remediation logs"""
        
        # Filter plans based on criteria
        plans = list(self.remediation_plans.values())
        
        if plan_id:
            plans = [p for p in plans if p.plan_id == plan_id]
        
        if date_range:
            start_date, end_date = date_range
            plans = [p for p in plans if start_date <= p.created_at <= end_date]
        
        # Generate export data
        export_data = {
            'export_metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_plans': len(plans),
                'date_range': [d.isoformat() for d in date_range] if date_range else None,
                'plan_filter': plan_id
            },
            'plans': [serialize_remediation_plan(plan) for plan in plans],
            'results': {}
        }
        
        # Add detailed results for each plan
        for plan in plans:
            export_data['results'][plan.plan_id] = self.get_remediation_results(plan.plan_id)
        
        # Save to file
        export_filename = f"remediation_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"
        export_path = self.data_path / "exports" / export_filename
        export_path.parent.mkdir(exist_ok=True)
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported remediation logs to: {export_path}")
        return str(export_path)
    
    # Maintenance
    def cleanup_old_data(self, max_age_days: int = 90):
        """Clean up old remediation data"""
        cleanup_stats = {
            'expired_backups': 0,
            'old_plans': 0,
            'old_sessions': 0,
            'old_rollbacks': 0
        }
        
        # Clean up expired backups
        cleanup_stats['expired_backups'] = self.backup_manager.cleanup_expired_backups()
        
        # Clean up old completed remediation sessions
        cleanup_stats['old_sessions'] = self.remediation_engine.cleanup_completed_sessions(max_age_days * 24)
        
        # Clean up old rollback records
        cleanup_stats['old_rollbacks'] = self.rollback_manager.cleanup_old_rollbacks(max_age_days)
        
        # Clean up old completed plans
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        old_plans = []
        
        for plan_id, plan in self.remediation_plans.items():
            if (plan.status in [RemediationStatus.COMPLETED, RemediationStatus.FAILED] and
                plan.created_at < cutoff_date):
                old_plans.append(plan_id)
        
        for plan_id in old_plans:
            del self.remediation_plans[plan_id]
        
        if old_plans:
            self._save_remediation_plans()
        
        cleanup_stats['old_plans'] = len(old_plans)
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats
    
    def get_system_health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        health = {
            'overall_status': 'healthy',
            'checks': {},
            'issues': [],
            'recommendations': [],
            'last_checked': datetime.now().isoformat()
        }
        
        try:
            # Check backup system
            backup_stats = self.backup_manager.get_backup_statistics()
            health['checks']['backup_system'] = {
                'status': 'healthy' if backup_stats['total_backups'] > 0 else 'warning',
                'total_backups': backup_stats['total_backups'],
                'total_size_gb': backup_stats['total_size_bytes'] / (1024**3)
            }
            
            if backup_stats['total_backups'] == 0:
                health['issues'].append("No system backups available")
                health['recommendations'].append("Create at least one system backup before performing remediation")
            
            # Check remediation plans
            plan_stats = self.get_remediation_statistics()
            health['checks']['remediation_plans'] = {
                'status': 'healthy',
                'total_plans': plan_stats['total_plans'],
                'success_rate': plan_stats['success_rate']
            }
            
            if plan_stats['success_rate'] < 80 and plan_stats['total_plans'] > 0:
                health['checks']['remediation_plans']['status'] = 'warning'
                health['issues'].append(f"Low remediation success rate: {plan_stats['success_rate']:.1f}%")
                health['recommendations'].append("Review failed remediation actions and improve action definitions")
            
            # Check disk space
            disk_usage = shutil.disk_usage(self.data_path)
            free_gb = disk_usage.free / (1024**3)
            health['checks']['disk_space'] = {
                'status': 'healthy' if free_gb > 5 else 'warning',
                'free_space_gb': free_gb
            }
            
            if free_gb < 5:
                health['issues'].append(f"Low disk space: {free_gb:.1f}GB remaining")
                health['recommendations'].append("Clean up old backups and logs to free disk space")
            
            # Overall status
            if health['issues']:
                health['overall_status'] = 'warning' if len(health['issues']) < 3 else 'critical'
            
        except Exception as e:
            health['overall_status'] = 'error'
            health['issues'].append(f"Health check error: {e}")
        
        return health