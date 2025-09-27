"""
Audit Manager - Step 6
High-level manager that coordinates audit operations, integrates with other modules,
and provides a unified interface for audit functionality.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor

from .models_audit import (
    AuditRun, AuditConfiguration, PolicyAuditResult, AuditSummary, AuditTrend,
    ReportTemplate, AuditStatus, ComplianceResult, AuditScope, ReportFormat,
    serialize_audit_run, generate_audit_summary
)
from .audit_engine import WindowsAuditEngine
from .report_generator import ReportGenerator

# =================================================================
# MAIN AUDIT MANAGER
# =================================================================

class AuditManager:
    """
    High-level audit manager that coordinates all audit operations.
    Integrates with dashboard, template, and policy systems.
    """
    
    def __init__(self, data_dir: str = "audit_data"):
        """Initialize audit manager with data storage directory"""
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize components
        self.audit_engine = WindowsAuditEngine(data_dir)
        self.report_generator = ReportGenerator(os.path.join(data_dir, "reports"))
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Initialize caches
        self.audit_cache = {}
        self.trend_cache = {}
        self.configuration_cache = {}
        
        # Load historical data
        self._load_audit_history()
        
        self.logger.info("AuditManager initialized successfully")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for audit manager"""
        logger = logging.getLogger("AuditManager")
        logger.setLevel(logging.INFO)
        
        # Create file handler if not already exists
        if not logger.handlers:
            log_file = os.path.join(self.data_dir, "logs", "audit_manager.log")
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            handler = logging.FileHandler(log_file)
            handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            
            logger.addHandler(handler)
        
        return logger
    
    def _load_audit_history(self):
        """Load historical audit data from storage"""
        try:
            # Load audit configurations
            configs_file = os.path.join(self.data_dir, "configurations.json")
            if os.path.exists(configs_file):
                with open(configs_file, 'r') as f:
                    config_data = json.load(f)
                    # Convert to AuditConfiguration objects
                    # For now, just store the raw data
                    self.configuration_cache.update(config_data)
            
            # Load trend data
            trends_file = os.path.join(self.data_dir, "trends.json")
            if os.path.exists(trends_file):
                with open(trends_file, 'r') as f:
                    trend_data = json.load(f)
                    # Convert to AuditTrend objects
                    # For now, just store the raw data
                    self.trend_cache.update(trend_data)
            
            self.logger.info(f"Loaded {len(self.configuration_cache)} configurations and {len(self.trend_cache)} trend datasets")
            
        except Exception as e:
            self.logger.warning(f"Failed to load audit history: {e}")
    
    def create_audit_configuration(self, name: str, description: str = "",
                                 scope: AuditScope = AuditScope.FULL_SYSTEM,
                                 **kwargs) -> AuditConfiguration:
        """Create a new audit configuration"""
        try:
            config = AuditConfiguration(
                name=name,
                description=description,
                scope=scope,
                **kwargs
            )
            
            # Store configuration
            self.configuration_cache[config.audit_id] = config
            self._save_configurations()
            
            self.logger.info(f"Created audit configuration: {config.audit_id}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to create audit configuration: {e}")
            raise
    
    def start_audit(self, config: AuditConfiguration, 
                   policies_source: str = "dashboard") -> str:
        """Start a new audit run"""
        try:
            # Get policies from the specified source
            policies = self._get_policies_for_audit(policies_source, config)
            
            if not policies:
                raise ValueError("No policies available for audit")
            
            # Start the audit
            audit_id = self.audit_engine.start_audit(config, policies)
            
            self.logger.info(f"Started audit {audit_id} with {len(policies)} policies")
            return audit_id
            
        except Exception as e:
            self.logger.error(f"Failed to start audit: {e}")
            raise
    
    def _get_policies_for_audit(self, source: str, config: AuditConfiguration) -> List[Dict[str, Any]]:
        """Get policies from the specified source for auditing"""
        try:
            policies = []
            
            if source == "dashboard":
                # Try to get policies from dashboard manager
                policies = self._get_dashboard_policies(config)
            elif source == "templates":
                # Try to get policies from template manager
                policies = self._get_template_policies(config)
            elif source == "file":
                # Load policies from file
                policies = self._load_policies_from_file(config)
            else:
                raise ValueError(f"Unknown policies source: {source}")
            
            return policies
            
        except Exception as e:
            self.logger.error(f"Failed to get policies from {source}: {e}")
            return []
    
    def _get_dashboard_policies(self, config: AuditConfiguration) -> List[Dict[str, Any]]:
        """Get policies from dashboard manager"""
        try:
            # This would integrate with the dashboard manager
            # For now, return sample policies
            sample_policies = [
                {
                    "id": "policy_001",
                    "policy_id": "policy_001",
                    "name": "Account Lockout Threshold",
                    "title": "Set account lockout threshold",
                    "category": "Account Policies",
                    "cis_level": 1,
                    "description": "Configure account lockout threshold to enhance security",
                    "tags": ["account", "security", "lockout"]
                },
                {
                    "id": "policy_002",
                    "policy_id": "policy_002",
                    "name": "Windows Firewall Domain Profile",
                    "title": "Enable Windows Firewall for Domain Profile",
                    "category": "Windows Firewall",
                    "cis_level": 1,
                    "description": "Ensure Windows Firewall is enabled for domain profile",
                    "tags": ["firewall", "network", "security"]
                },
                {
                    "id": "policy_003",
                    "policy_id": "policy_003",
                    "name": "Password History",
                    "title": "Enforce password history",
                    "category": "Account Policies",
                    "cis_level": 1,
                    "description": "Remember password history to prevent reuse",
                    "tags": ["password", "security", "history"]
                }
            ]
            
            return sample_policies
            
        except Exception as e:
            self.logger.error(f"Failed to get dashboard policies: {e}")
            return []
    
    def _get_template_policies(self, config: AuditConfiguration) -> List[Dict[str, Any]]:
        """Get policies from template manager"""
        try:
            # This would integrate with the template manager
            # For now, return empty list
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get template policies: {e}")
            return []
    
    def _load_policies_from_file(self, config: AuditConfiguration) -> List[Dict[str, Any]]:
        """Load policies from file"""
        try:
            # This would load policies from a specified file
            # For now, return empty list
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to load policies from file: {e}")
            return []
    
    def get_audit_status(self, audit_id: str) -> Optional[AuditRun]:
        """Get current status of an audit run"""
        return self.audit_engine.get_audit_status(audit_id)
    
    def cancel_audit(self, audit_id: str) -> bool:
        """Cancel a running audit"""
        return self.audit_engine.cancel_audit(audit_id)
    
    def delete_audit(self, audit_id: str) -> bool:
        """Delete audit results and associated data"""
        return self.audit_engine.delete_audit_results(audit_id)
    
    def generate_report(self, audit_id: str, format: ReportFormat = ReportFormat.HTML,
                       template_name: str = "standard") -> str:
        """Generate a report for completed audit"""
        try:
            # Get audit run
            audit_run = self.get_audit_status(audit_id)
            if not audit_run:
                raise ValueError(f"Audit {audit_id} not found")
            
            if audit_run.status != AuditStatus.COMPLETED:
                raise ValueError(f"Audit {audit_id} is not completed")
            
            # Generate report
            report_path = self.report_generator.generate_report(
                audit_run, format, template_name
            )
            
            self.logger.info(f"Generated {format.value} report for audit {audit_id}: {report_path}")
            return report_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate report: {e}")
            raise
    
    def get_audit_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get audit history with summary information"""
        return self.audit_engine.get_audit_history(limit)
    
    def get_compliance_trends(self, system_id: Optional[str] = None,
                            days: int = 30) -> Dict[str, Any]:
        """Get compliance trends over time"""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get audit history
            history = self.get_audit_history(100)  # Get more data for trend analysis
            
            # Filter by date range
            filtered_history = []
            for audit_summary in history:
                if audit_summary.get('end_time'):
                    try:
                        audit_date = datetime.fromisoformat(audit_summary['end_time'].replace('Z', '+00:00'))
                        if start_date <= audit_date <= end_date:
                            filtered_history.append(audit_summary)
                    except:
                        continue
            
            # Sort by date
            filtered_history.sort(key=lambda x: x.get('end_time', ''), reverse=False)
            
            # Calculate trends
            trend_data = {
                "period": f"{days} days",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "audit_count": len(filtered_history),
                "compliance_scores": [h.get('compliance_percentage', 0) for h in filtered_history],
                "audit_dates": [h.get('end_time', '') for h in filtered_history],
                "failed_policies_trend": [h.get('failed_policies', 0) for h in filtered_history],
                "total_policies_trend": [h.get('total_policies', 0) for h in filtered_history]
            }
            
            # Calculate trend direction
            if len(trend_data['compliance_scores']) >= 2:
                recent_scores = trend_data['compliance_scores'][-3:]  # Last 3 audits
                older_scores = trend_data['compliance_scores'][:-3] if len(trend_data['compliance_scores']) > 3 else []
                
                if older_scores:
                    recent_avg = sum(recent_scores) / len(recent_scores)
                    older_avg = sum(older_scores) / len(older_scores)
                    
                    if recent_avg > older_avg + 5:
                        trend_data['trend_direction'] = 'improving'
                    elif recent_avg < older_avg - 5:
                        trend_data['trend_direction'] = 'declining'
                    else:
                        trend_data['trend_direction'] = 'stable'
                else:
                    trend_data['trend_direction'] = 'insufficient_data'
            else:
                trend_data['trend_direction'] = 'insufficient_data'
            
            return trend_data
            
        except Exception as e:
            self.logger.error(f"Failed to get compliance trends: {e}")
            return {
                "error": str(e),
                "audit_count": 0,
                "trend_direction": "error"
            }
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get comprehensive audit statistics"""
        try:
            history = self.get_audit_history(100)
            
            if not history:
                return {
                    "total_audits": 0,
                    "average_compliance": 0.0,
                    "best_compliance": 0.0,
                    "worst_compliance": 0.0,
                    "total_policies_audited": 0,
                    "most_common_failures": []
                }
            
            # Calculate statistics
            compliance_scores = [h.get('compliance_percentage', 0) for h in history if h.get('compliance_percentage') is not None]
            total_policies = [h.get('total_policies', 0) for h in history if h.get('total_policies') is not None]
            
            stats = {
                "total_audits": len(history),
                "average_compliance": sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0.0,
                "best_compliance": max(compliance_scores) if compliance_scores else 0.0,
                "worst_compliance": min(compliance_scores) if compliance_scores else 0.0,
                "total_policies_audited": sum(total_policies),
                "last_audit_date": history[0].get('end_time', '') if history else '',
                "audits_this_month": len([h for h in history if self._is_this_month(h.get('end_time', ''))]),
                "trend_direction": self.get_compliance_trends(days=30).get('trend_direction', 'unknown')
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get audit statistics: {e}")
            return {"error": str(e)}
    
    def _is_this_month(self, date_str: str) -> bool:
        """Check if date string is in current month"""
        try:
            if not date_str:
                return False
            
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            now = datetime.now()
            
            return date.year == now.year and date.month == now.month
            
        except:
            return False
    
    def search_audit_results(self, query: str, audit_ids: Optional[List[str]] = None,
                           result_types: Optional[List[ComplianceResult]] = None) -> List[Dict[str, Any]]:
        """Search audit results across multiple audits"""
        try:
            results = []
            
            # Get audit IDs to search
            search_ids = audit_ids or [h['audit_id'] for h in self.get_audit_history(50)]
            
            for audit_id in search_ids:
                audit_run = self.get_audit_status(audit_id)
                if not audit_run or not audit_run.policy_results:
                    continue
                
                # Search through policy results
                for policy_result in audit_run.policy_results:
                    if self._matches_search_query(policy_result, query, result_types):
                        results.append({
                            "audit_id": audit_id,
                            "audit_name": audit_run.configuration.name,
                            "audit_date": audit_run.end_time.isoformat() if audit_run.end_time else '',
                            "policy_id": policy_result.policy_id,
                            "policy_name": policy_result.policy_name,
                            "category": policy_result.category,
                            "result": policy_result.result.value,
                            "severity": policy_result.severity.value,
                            "error_message": policy_result.error_message,
                            "remediation": policy_result.remediation
                        })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search audit results: {e}")
            return []
    
    def _matches_search_query(self, policy_result: PolicyAuditResult, query: str,
                            result_types: Optional[List[ComplianceResult]]) -> bool:
        """Check if policy result matches search criteria"""
        try:
            # Filter by result type
            if result_types and policy_result.result not in result_types:
                return False
            
            # Search in text fields
            query_lower = query.lower()
            search_fields = [
                policy_result.policy_name.lower(),
                policy_result.policy_title.lower(),
                policy_result.category.lower(),
                (policy_result.description or '').lower(),
                (policy_result.error_message or '').lower(),
                (policy_result.remediation or '').lower()
            ]
            
            return any(query_lower in field for field in search_fields)
            
        except Exception as e:
            self.logger.warning(f"Error in search matching: {e}")
            return False
    
    def compare_audits(self, audit_id1: str, audit_id2: str) -> Dict[str, Any]:
        """Compare results between two audit runs"""
        try:
            audit1 = self.get_audit_status(audit_id1)
            audit2 = self.get_audit_status(audit_id2)
            
            if not audit1 or not audit2:
                raise ValueError("One or both audits not found")
            
            # Create policy maps for comparison
            policies1 = {r.policy_id: r for r in audit1.policy_results}
            policies2 = {r.policy_id: r for r in audit2.policy_results}
            
            # Find common policies
            common_policies = set(policies1.keys()) & set(policies2.keys())
            
            # Analyze changes
            improved = []
            degraded = []
            unchanged = []
            
            for policy_id in common_policies:
                result1 = policies1[policy_id]
                result2 = policies2[policy_id]
                
                if result1.result == ComplianceResult.FAIL and result2.result == ComplianceResult.PASS:
                    improved.append({
                        "policy_id": policy_id,
                        "policy_name": result1.policy_name,
                        "previous": result1.result.value,
                        "current": result2.result.value
                    })
                elif result1.result == ComplianceResult.PASS and result2.result == ComplianceResult.FAIL:
                    degraded.append({
                        "policy_id": policy_id,
                        "policy_name": result1.policy_name,
                        "previous": result1.result.value,
                        "current": result2.result.value
                    })
                else:
                    unchanged.append({
                        "policy_id": policy_id,
                        "policy_name": result1.policy_name,
                        "result": result1.result.value
                    })
            
            comparison = {
                "audit1": {
                    "id": audit_id1,
                    "name": audit1.configuration.name,
                    "date": audit1.end_time.isoformat() if audit1.end_time else '',
                    "compliance": audit1.summary.compliance_percentage if audit1.summary else 0
                },
                "audit2": {
                    "id": audit_id2,
                    "name": audit2.configuration.name,
                    "date": audit2.end_time.isoformat() if audit2.end_time else '',
                    "compliance": audit2.summary.compliance_percentage if audit2.summary else 0
                },
                "comparison": {
                    "common_policies": len(common_policies),
                    "improved_policies": len(improved),
                    "degraded_policies": len(degraded),
                    "unchanged_policies": len(unchanged),
                    "compliance_change": (audit2.summary.compliance_percentage - audit1.summary.compliance_percentage) if (audit1.summary and audit2.summary) else 0
                },
                "details": {
                    "improved": improved[:10],  # Limit for API response
                    "degraded": degraded[:10],
                    "unchanged": unchanged[:10] if len(unchanged) <= 20 else []  # Only show if reasonable number
                }
            }
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Failed to compare audits: {e}")
            return {"error": str(e)}
    
    def _save_configurations(self):
        """Save audit configurations to persistent storage"""
        try:
            configs_file = os.path.join(self.data_dir, "configurations.json")
            
            # Convert configurations to serializable format
            config_data = {}
            for config_id, config in self.configuration_cache.items():
                if hasattr(config, '__dict__'):
                    config_data[config_id] = config.__dict__
                else:
                    config_data[config_id] = config
            
            with open(configs_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
        except Exception as e:
            self.logger.error(f"Failed to save configurations: {e}")
    
    def get_remediation_summary(self, audit_id: str) -> Dict[str, Any]:
        """Get summary of remediation actions needed"""
        try:
            audit_run = self.get_audit_status(audit_id)
            if not audit_run:
                raise ValueError(f"Audit {audit_id} not found")
            
            # Get failed policies with remediation
            failed_with_remediation = [
                r for r in audit_run.policy_results 
                if r.result == ComplianceResult.FAIL and r.remediation
            ]
            
            # Group by category and severity
            by_category = {}
            by_severity = {}
            
            for result in failed_with_remediation:
                # By category
                if result.category not in by_category:
                    by_category[result.category] = []
                by_category[result.category].append({
                    "policy_name": result.policy_name,
                    "severity": result.severity.value,
                    "remediation": result.remediation
                })
                
                # By severity
                severity = result.severity.value
                if severity not in by_severity:
                    by_severity[severity] = []
                by_severity[severity].append({
                    "policy_name": result.policy_name,
                    "category": result.category,
                    "remediation": result.remediation
                })
            
            summary = {
                "audit_id": audit_id,
                "total_failed_policies": len([r for r in audit_run.policy_results if r.result == ComplianceResult.FAIL]),
                "policies_with_remediation": len(failed_with_remediation),
                "by_category": by_category,
                "by_severity": by_severity,
                "priority_actions": by_severity.get('critical', [])[:5] + by_severity.get('high', [])[:5]  # Top priority items
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get remediation summary: {e}")
            return {"error": str(e)}
    
    def export_audit_data(self, audit_ids: Optional[List[str]] = None) -> str:
        """Export audit data for backup or analysis"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = os.path.join(self.data_dir, f"audit_export_{timestamp}.json")
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "export_version": "1.0",
                "configurations": self.configuration_cache,
                "audits": []
            }
            
            # Export specific audits or all recent ones
            ids_to_export = audit_ids or [h['audit_id'] for h in self.get_audit_history(20)]
            
            for audit_id in ids_to_export:
                audit_run = self.get_audit_status(audit_id)
                if audit_run:
                    export_data["audits"].append(serialize_audit_run(audit_run))
            
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            self.logger.info(f"Exported audit data to {export_file}")
            return export_file
            
        except Exception as e:
            self.logger.error(f"Failed to export audit data: {e}")
            raise
    
    def cleanup_old_audits(self, days_to_keep: int = 90) -> int:
        """Clean up old audit results to save storage space"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            history = self.get_audit_history(200)  # Get more history for cleanup
            
            deleted_count = 0
            for audit_summary in history:
                if audit_summary.get('end_time'):
                    try:
                        audit_date = datetime.fromisoformat(audit_summary['end_time'].replace('Z', '+00:00'))
                        if audit_date < cutoff_date:
                            if self.delete_audit(audit_summary['audit_id']):
                                deleted_count += 1
                    except:
                        continue
            
            self.logger.info(f"Cleaned up {deleted_count} old audit results")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old audits: {e}")
            return 0