"""
Windows System Audit Engine - Step 6
Core engine for auditing Windows systems against CIS benchmark policies.
"""

import os
import json
import subprocess
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import platform
import socket
import uuid

from .models_audit import (
    AuditRun, AuditConfiguration, PolicyAuditResult, SystemInfo, AuditSummary,
    AuditStatus, ComplianceResult, AuditSeverity, AuditMethod, WindowsVersion,
    AuditScope, serialize_audit_run, serialize_policy_result, 
    generate_audit_summary, validate_audit_configuration
)

# =================================================================
# WINDOWS SYSTEM AUDIT ENGINE
# =================================================================

class WindowsAuditEngine:
    """
    Core Windows system audit engine for CIS benchmark compliance testing.
    Supports offline operation with PowerShell, registry, and WMI queries.
    """
    
    def __init__(self, data_dir: str = "audit_data"):
        """Initialize the audit engine with data storage directory"""
        self.data_dir = data_dir
        self.audit_cache = {}
        self.running_audits = {}
        
        # Create directories
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(data_dir, "results"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "reports"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "logs"), exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Initialize PowerShell session management
        self.powershell_available = self._check_powershell_availability()
        
        # Load audit rule definitions
        self.audit_rules = self._load_audit_rules()
        
        self.logger.info("WindowsAuditEngine initialized successfully")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for audit operations"""
        logger = logging.getLogger("WindowsAuditEngine")
        logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = os.path.join(self.data_dir, "logs", "audit_engine.log")
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        return logger
    
    def _check_powershell_availability(self) -> bool:
        """Check if PowerShell is available for audit operations"""
        try:
            if platform.system() != "Windows":
                self.logger.warning("Non-Windows system detected. PowerShell audits may be limited.")
                return False
            
            result = subprocess.run(
                ["powershell", "-Command", "Get-Host | Select-Object Version"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                self.logger.info("PowerShell detected and available for auditing")
                return True
            
        except Exception as e:
            self.logger.warning(f"PowerShell check failed: {e}")
        
        return False
    
    def _load_audit_rules(self) -> Dict[str, Dict]:
        """Load audit rule definitions from configuration files"""
        rules = {}
        
        # Default audit rules for common CIS policies
        default_rules = {
            "password_policy": {
                "registry_path": "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\Netlogon\\Parameters",
                "registry_key": "RequireSignOrSeal",
                "expected_value": "1",
                "audit_method": "registry",
                "description": "Ensure secure channel authentication is required"
            },
            "account_lockout": {
                "powershell_command": "Get-ADDefaultDomainPasswordPolicy | Select-Object LockoutThreshold",
                "expected_value": "5",
                "audit_method": "powershell",
                "description": "Check account lockout threshold"
            },
            "audit_policy": {
                "powershell_command": "auditpol /get /category:*",
                "audit_method": "powershell",
                "description": "Get current audit policy settings"
            },
            "firewall_status": {
                "powershell_command": "Get-NetFirewallProfile | Select-Object Name, Enabled",
                "audit_method": "powershell",
                "description": "Check Windows Firewall status for all profiles"
            },
            "windows_update": {
                "registry_path": "HKEY_LOCAL_MACHINE\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU",
                "registry_key": "AUOptions",
                "expected_value": "4",
                "audit_method": "registry",
                "description": "Check Windows Update automatic installation setting"
            }
        }
        
        rules.update(default_rules)
        
        # Try to load custom rules from file
        rules_file = os.path.join(self.data_dir, "audit_rules.json")
        if os.path.exists(rules_file):
            try:
                with open(rules_file, 'r') as f:
                    custom_rules = json.load(f)
                    rules.update(custom_rules)
                    self.logger.info(f"Loaded {len(custom_rules)} custom audit rules")
            except Exception as e:
                self.logger.warning(f"Failed to load custom audit rules: {e}")
        
        return rules
    
    def get_system_info(self) -> SystemInfo:
        """Collect comprehensive system information for audit context"""
        try:
            hostname = socket.gethostname()
            
            # Get OS information
            os_info = platform.uname()
            
            system_info = SystemInfo(
                hostname=hostname,
                os_version=f"{os_info.system} {os_info.release}",
                os_build=os_info.version,
                architecture=os_info.machine,
                scan_timestamp=datetime.now()
            )
            
            # Try to get additional Windows-specific information
            if platform.system() == "Windows":
                try:
                    # Get domain/workgroup information
                    domain_cmd = 'wmic computersystem get domain /value'
                    result = subprocess.run(
                        domain_cmd, shell=True, capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'Domain=' in line:
                                domain = line.split('=')[1].strip()
                                if domain and domain.lower() != hostname.lower():
                                    system_info.domain = domain
                                else:
                                    system_info.workgroup = domain
                    
                    # Get memory information
                    mem_cmd = 'wmic computersystem get TotalPhysicalMemory /value'
                    result = subprocess.run(
                        mem_cmd, shell=True, capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'TotalPhysicalMemory=' in line:
                                try:
                                    system_info.total_memory = int(line.split('=')[1].strip())
                                except:
                                    pass
                    
                    # Get CPU information
                    cpu_cmd = 'wmic cpu get name /value'
                    result = subprocess.run(
                        cpu_cmd, shell=True, capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'Name=' in line:
                                system_info.cpu_info = line.split('=')[1].strip()
                                break
                    
                    # Get last boot time
                    boot_cmd = 'wmic os get lastbootuptime /value'
                    result = subprocess.run(
                        boot_cmd, shell=True, capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'LastBootUpTime=' in line:
                                try:
                                    boot_time_str = line.split('=')[1].strip()[:14]
                                    system_info.last_boot = datetime.strptime(
                                        boot_time_str, '%Y%m%d%H%M%S'
                                    )
                                except:
                                    pass
                
                except Exception as e:
                    self.logger.warning(f"Failed to get extended system info: {e}")
            
            return system_info
            
        except Exception as e:
            self.logger.error(f"Failed to collect system information: {e}")
            # Return minimal system info
            return SystemInfo(
                hostname="unknown",
                os_version="unknown",
                os_build="unknown",
                architecture="unknown"
            )
    
    def audit_policy(self, policy: Dict[str, Any], audit_rules: Dict[str, Any]) -> PolicyAuditResult:
        """Audit a single policy against the system configuration"""
        start_time = time.time()
        
        try:
            policy_id = policy.get('id', policy.get('policy_id', 'unknown'))
            policy_name = policy.get('name', policy.get('policy_name', policy.get('title', 'Unknown Policy')))
            
            # Create initial result
            result = PolicyAuditResult(
                policy_id=policy_id,
                policy_name=policy_name,
                policy_title=policy.get('title', policy_name),
                category=policy.get('category', 'Uncategorized'),
                cis_level=policy.get('cis_level', 1),
                description=policy.get('description', 'No description available'),
                result=ComplianceResult.ERROR,
                severity=AuditSeverity.MEDIUM,
                audit_timestamp=datetime.now()
            )
            
            # Look for audit rule for this policy
            audit_rule = None
            
            # Try to find matching audit rule
            for rule_key, rule_data in audit_rules.items():
                if (rule_key in policy_id.lower() or 
                    rule_key in policy_name.lower() or
                    any(rule_key in tag.lower() for tag in policy.get('tags', []))):
                    audit_rule = rule_data
                    break
            
            if not audit_rule:
                # Try to infer audit method from policy data
                audit_rule = self._infer_audit_rule(policy)
            
            if not audit_rule:
                result.result = ComplianceResult.MANUAL_REVIEW
                result.error_message = "No automated audit rule available for this policy"
                self.logger.warning(f"No audit rule found for policy {policy_id}")
            else:
                # Perform the audit based on the rule
                result = self._execute_audit_rule(result, audit_rule)
            
        except Exception as e:
            result.result = ComplianceResult.ERROR
            result.error_message = str(e)
            self.logger.error(f"Error auditing policy {policy_id}: {e}")
        
        # Calculate execution time
        result.execution_time_ms = int((time.time() - start_time) * 1000)
        
        return result
    
    def _infer_audit_rule(self, policy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Attempt to infer audit rule from policy information"""
        try:
            policy_name = policy.get('name', '').lower()
            policy_desc = policy.get('description', '').lower()
            policy_text = f"{policy_name} {policy_desc}"
            
            # Registry-based policies
            if any(keyword in policy_text for keyword in ['registry', 'regkey', 'hkey']):
                # Try to extract registry information from policy text
                registry_info = self._extract_registry_info(policy)
                if registry_info:
                    return {
                        "audit_method": "registry",
                        "registry_path": registry_info.get('path'),
                        "registry_key": registry_info.get('key'),
                        "expected_value": registry_info.get('value')
                    }
            
            # Group Policy-based policies
            if any(keyword in policy_text for keyword in ['group policy', 'gpo', 'policy']):
                return {
                    "audit_method": "powershell",
                    "powershell_command": f"Get-GPRegistryValue -Name 'Default Domain Policy' | Where-Object {{$_.FullKeyPath -like '*{policy_name}*'}}",
                    "description": f"Group Policy audit for {policy.get('name', 'policy')}"
                }
            
            # Security policy-based
            if any(keyword in policy_text for keyword in ['password', 'account', 'lockout', 'audit']):
                return {
                    "audit_method": "powershell",
                    "powershell_command": "secedit /export /cfg temp_policy.inf && Get-Content temp_policy.inf",
                    "description": f"Security policy audit for {policy.get('name', 'policy')}"
                }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to infer audit rule: {e}")
            return None
    
    def _extract_registry_info(self, policy: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract registry information from policy text"""
        try:
            # This would implement registry path extraction from policy descriptions
            # For now, return None to indicate manual review needed
            return None
        except Exception:
            return None
    
    def _execute_audit_rule(self, result: PolicyAuditResult, audit_rule: Dict[str, Any]) -> PolicyAuditResult:
        """Execute a specific audit rule and update the result"""
        try:
            audit_method = audit_rule.get('audit_method', 'powershell')
            result.audit_method = AuditMethod(audit_method)
            
            if audit_method == 'registry':
                return self._audit_registry_value(result, audit_rule)
            elif audit_method == 'powershell':
                return self._audit_powershell_command(result, audit_rule)
            elif audit_method == 'wmi':
                return self._audit_wmi_query(result, audit_rule)
            else:
                result.result = ComplianceResult.ERROR
                result.error_message = f"Unsupported audit method: {audit_method}"
            
        except Exception as e:
            result.result = ComplianceResult.ERROR
            result.error_message = f"Audit rule execution failed: {e}"
            self.logger.error(f"Audit rule execution failed: {e}")
        
        return result
    
    def _audit_registry_value(self, result: PolicyAuditResult, audit_rule: Dict[str, Any]) -> PolicyAuditResult:
        """Audit a registry value"""
        try:
            registry_path = audit_rule.get('registry_path', '')
            registry_key = audit_rule.get('registry_key', '')
            expected_value = audit_rule.get('expected_value', '')
            
            result.registry_path = registry_path
            result.registry_key = registry_key
            result.expected_value = expected_value
            
            if platform.system() != "Windows":
                result.result = ComplianceResult.NOT_APPLICABLE
                result.error_message = "Registry audit not applicable on non-Windows systems"
                return result
            
            # Use PowerShell to read registry value
            ps_command = f"Get-ItemProperty -Path 'Registry::{registry_path}' -Name '{registry_key}' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty '{registry_key}'"
            
            cmd_result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True, text=True, timeout=30
            )
            
            if cmd_result.returncode == 0:
                current_value = cmd_result.stdout.strip()
                result.current_value = current_value
                
                if current_value == expected_value:
                    result.result = ComplianceResult.PASS
                else:
                    result.result = ComplianceResult.FAIL
                    result.remediation = f"Set registry value {registry_path}\\{registry_key} to {expected_value}"
            else:
                result.result = ComplianceResult.ERROR
                result.error_message = f"Failed to read registry value: {cmd_result.stderr}"
            
        except Exception as e:
            result.result = ComplianceResult.ERROR
            result.error_message = f"Registry audit failed: {e}"
        
        return result
    
    def _audit_powershell_command(self, result: PolicyAuditResult, audit_rule: Dict[str, Any]) -> PolicyAuditResult:
        """Audit using PowerShell command"""
        try:
            ps_command = audit_rule.get('powershell_command', '')
            expected_value = audit_rule.get('expected_value', '')
            
            if not ps_command:
                result.result = ComplianceResult.ERROR
                result.error_message = "No PowerShell command specified"
                return result
            
            if not self.powershell_available:
                result.result = ComplianceResult.NOT_APPLICABLE
                result.error_message = "PowerShell not available for audit"
                return result
            
            # Execute PowerShell command
            cmd_result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True, text=True, timeout=60
            )
            
            if cmd_result.returncode == 0:
                output = cmd_result.stdout.strip()
                result.current_value = output
                
                # Simple comparison for now - this could be enhanced with pattern matching
                if expected_value:
                    if expected_value.lower() in output.lower():
                        result.result = ComplianceResult.PASS
                    else:
                        result.result = ComplianceResult.FAIL
                        result.remediation = f"Expected output to contain: {expected_value}"
                else:
                    # If no expected value, just mark as informational
                    result.result = ComplianceResult.PASS
                    result.severity = AuditSeverity.INFORMATIONAL
            else:
                result.result = ComplianceResult.ERROR
                result.error_message = f"PowerShell command failed: {cmd_result.stderr}"
            
        except Exception as e:
            result.result = ComplianceResult.ERROR
            result.error_message = f"PowerShell audit failed: {e}"
        
        return result
    
    def _audit_wmi_query(self, result: PolicyAuditResult, audit_rule: Dict[str, Any]) -> PolicyAuditResult:
        """Audit using WMI query"""
        try:
            wmi_query = audit_rule.get('wmi_query', '')
            expected_value = audit_rule.get('expected_value', '')
            
            if not wmi_query:
                result.result = ComplianceResult.ERROR
                result.error_message = "No WMI query specified"
                return result
            
            # Use PowerShell to execute WMI query
            ps_command = f"Get-WmiObject -Query \"{wmi_query}\" | ConvertTo-Json"
            
            cmd_result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True, text=True, timeout=60
            )
            
            if cmd_result.returncode == 0:
                output = cmd_result.stdout.strip()
                result.current_value = output
                
                # Parse and evaluate the result
                if expected_value:
                    if expected_value.lower() in output.lower():
                        result.result = ComplianceResult.PASS
                    else:
                        result.result = ComplianceResult.FAIL
                else:
                    result.result = ComplianceResult.PASS
                    result.severity = AuditSeverity.INFORMATIONAL
            else:
                result.result = ComplianceResult.ERROR
                result.error_message = f"WMI query failed: {cmd_result.stderr}"
            
        except Exception as e:
            result.result = ComplianceResult.ERROR
            result.error_message = f"WMI audit failed: {e}"
        
        return result
    
    def start_audit(self, configuration: AuditConfiguration, policies: List[Dict[str, Any]]) -> str:
        """Start a new audit run with the given configuration and policies"""
        try:
            # Validate configuration
            errors = validate_audit_configuration(configuration)
            if errors:
                raise ValueError(f"Invalid configuration: {', '.join(errors)}")
            
            # Get system information
            system_info = self.get_system_info()
            
            # Create audit run
            audit_run = AuditRun(
                audit_id=configuration.audit_id,
                configuration=configuration,
                system_info=system_info,
                status=AuditStatus.PENDING,
                start_time=datetime.now()
            )
            
            # Store in running audits
            self.running_audits[configuration.audit_id] = audit_run
            
            # Start audit in background thread
            audit_thread = threading.Thread(
                target=self._execute_audit_run,
                args=(audit_run, policies),
                daemon=True
            )
            audit_thread.start()
            
            self.logger.info(f"Started audit run {configuration.audit_id}")
            return configuration.audit_id
            
        except Exception as e:
            self.logger.error(f"Failed to start audit: {e}")
            raise
    
    def _execute_audit_run(self, audit_run: AuditRun, policies: List[Dict[str, Any]]):
        """Execute the audit run in a separate thread"""
        try:
            audit_run.status = AuditStatus.RUNNING
            self.logger.info(f"Executing audit run {audit_run.audit_id}")
            
            # Filter policies based on configuration
            filtered_policies = self._filter_policies(policies, audit_run.configuration)
            total_policies = len(filtered_policies)
            
            if total_policies == 0:
                raise ValueError("No policies match the audit configuration")
            
            # Execute audits with parallel processing
            if audit_run.configuration.parallel_execution:
                audit_results = self._execute_parallel_audits(audit_run, filtered_policies)
            else:
                audit_results = self._execute_sequential_audits(audit_run, filtered_policies)
            
            # Update audit run with results
            audit_run.policy_results = audit_results
            audit_run.summary = generate_audit_summary(audit_results)
            audit_run.status = AuditStatus.COMPLETED
            audit_run.end_time = datetime.now()
            audit_run.duration_seconds = (audit_run.end_time - audit_run.start_time).total_seconds()
            audit_run.progress_percentage = 100
            
            # Save results
            self._save_audit_results(audit_run)
            
            # Generate reports if requested
            if audit_run.configuration.generate_report:
                self._generate_reports(audit_run)
            
            # Move to cache
            self.audit_cache[audit_run.audit_id] = audit_run
            
            self.logger.info(f"Completed audit run {audit_run.audit_id}: {audit_run.summary.compliance_percentage:.1f}% compliant")
            
        except Exception as e:
            audit_run.status = AuditStatus.FAILED
            audit_run.error_message = str(e)
            audit_run.end_time = datetime.now()
            if audit_run.start_time:
                audit_run.duration_seconds = (audit_run.end_time - audit_run.start_time).total_seconds()
            
            self.logger.error(f"Audit run {audit_run.audit_id} failed: {e}")
        
        finally:
            # Remove from running audits
            if audit_run.audit_id in self.running_audits:
                del self.running_audits[audit_run.audit_id]
    
    def _filter_policies(self, policies: List[Dict[str, Any]], config: AuditConfiguration) -> List[Dict[str, Any]]:
        """Filter policies based on audit configuration"""
        filtered = policies.copy()
        
        # Filter by scope
        if config.scope == AuditScope.SELECTED_POLICIES and config.policy_ids:
            filtered = [p for p in filtered if p.get('id', p.get('policy_id', '')) in config.policy_ids]
        elif config.scope == AuditScope.POLICY_GROUP and config.group_names:
            filtered = [p for p in filtered if any(group in p.get('group_names', []) for group in config.group_names)]
        elif config.scope == AuditScope.CIS_LEVEL and config.cis_levels:
            filtered = [p for p in filtered if p.get('cis_level', 1) in config.cis_levels]
        
        # Filter by categories
        if config.categories:
            filtered = [p for p in filtered if p.get('category', '') in config.categories]
        
        return filtered
    
    def _execute_parallel_audits(self, audit_run: AuditRun, policies: List[Dict[str, Any]]) -> List[PolicyAuditResult]:
        """Execute audits in parallel using thread pool"""
        results = []
        total_policies = len(policies)
        completed = 0
        
        with ThreadPoolExecutor(max_workers=audit_run.configuration.max_workers) as executor:
            # Submit all audit tasks
            future_to_policy = {
                executor.submit(self.audit_policy, policy, self.audit_rules): policy 
                for policy in policies
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_policy):
                policy = future_to_policy[future]
                try:
                    result = future.result(timeout=audit_run.configuration.timeout_seconds)
                    results.append(result)
                    completed += 1
                    
                    # Update progress
                    audit_run.progress_percentage = int((completed / total_policies) * 100)
                    audit_run.completed_policies = completed
                    audit_run.current_policy = result.policy_name
                    
                except Exception as e:
                    # Create error result for failed policy
                    policy_id = policy.get('id', policy.get('policy_id', 'unknown'))
                    error_result = PolicyAuditResult(
                        policy_id=policy_id,
                        policy_name=policy.get('name', 'Unknown'),
                        policy_title=policy.get('title', 'Unknown'),
                        category=policy.get('category', 'Uncategorized'),
                        cis_level=policy.get('cis_level', 1),
                        description=policy.get('description', ''),
                        result=ComplianceResult.ERROR,
                        severity=AuditSeverity.MEDIUM,
                        error_message=str(e)
                    )
                    results.append(error_result)
                    completed += 1
                    
                    self.logger.error(f"Policy audit failed: {policy_id} - {e}")
        
        return results
    
    def _execute_sequential_audits(self, audit_run: AuditRun, policies: List[Dict[str, Any]]) -> List[PolicyAuditResult]:
        """Execute audits sequentially"""
        results = []
        total_policies = len(policies)
        
        for i, policy in enumerate(policies):
            try:
                result = self.audit_policy(policy, self.audit_rules)
                results.append(result)
                
                # Update progress
                audit_run.progress_percentage = int(((i + 1) / total_policies) * 100)
                audit_run.completed_policies = i + 1
                audit_run.current_policy = result.policy_name
                
            except Exception as e:
                # Create error result
                policy_id = policy.get('id', policy.get('policy_id', 'unknown'))
                error_result = PolicyAuditResult(
                    policy_id=policy_id,
                    policy_name=policy.get('name', 'Unknown'),
                    policy_title=policy.get('title', 'Unknown'),
                    category=policy.get('category', 'Uncategorized'),
                    cis_level=policy.get('cis_level', 1),
                    description=policy.get('description', ''),
                    result=ComplianceResult.ERROR,
                    severity=AuditSeverity.MEDIUM,
                    error_message=str(e)
                )
                results.append(error_result)
                
                self.logger.error(f"Policy audit failed: {policy_id} - {e}")
        
        return results
    
    def _save_audit_results(self, audit_run: AuditRun):
        """Save audit results to persistent storage"""
        try:
            results_file = os.path.join(
                self.data_dir, "results", f"audit_{audit_run.audit_id}.json"
            )
            
            # Serialize audit run
            serialized_data = serialize_audit_run(audit_run)
            
            with open(results_file, 'w') as f:
                json.dump(serialized_data, f, indent=2, default=str)
            
            self.logger.info(f"Saved audit results to {results_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save audit results: {e}")
    
    def _generate_reports(self, audit_run: AuditRun):
        """Generate reports in requested formats"""
        try:
            # This would implement report generation
            # For now, just create a simple JSON report
            report_file = os.path.join(
                self.data_dir, "reports", f"report_{audit_run.audit_id}.json"
            )
            
            report_data = {
                "audit_id": audit_run.audit_id,
                "system_info": audit_run.system_info.__dict__,
                "summary": audit_run.summary.__dict__ if audit_run.summary else {},
                "results": [serialize_policy_result(r) for r in audit_run.policy_results],
                "generated_at": datetime.now().isoformat()
            }
            
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            audit_run.report_paths["json"] = report_file
            audit_run.report_generated = True
            
            self.logger.info(f"Generated audit report: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate reports: {e}")
    
    def get_audit_status(self, audit_id: str) -> Optional[AuditRun]:
        """Get the current status of an audit run"""
        if audit_id in self.running_audits:
            return self.running_audits[audit_id]
        elif audit_id in self.audit_cache:
            return self.audit_cache[audit_id]
        else:
            # Try to load from file
            return self._load_audit_results(audit_id)
    
    def _load_audit_results(self, audit_id: str) -> Optional[AuditRun]:
        """Load audit results from persistent storage"""
        try:
            results_file = os.path.join(
                self.data_dir, "results", f"audit_{audit_id}.json"
            )
            
            if not os.path.exists(results_file):
                return None
            
            with open(results_file, 'r') as f:
                data = json.load(f)
            
            # This would implement deserialization
            # For now, return None to indicate not implemented
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load audit results: {e}")
            return None
    
    def get_audit_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get history of completed audit runs"""
        try:
            history = []
            results_dir = os.path.join(self.data_dir, "results")
            
            if not os.path.exists(results_dir):
                return history
            
            # Get all result files
            result_files = [f for f in os.listdir(results_dir) if f.startswith("audit_") and f.endswith(".json")]
            result_files.sort(reverse=True)  # Most recent first
            
            for result_file in result_files[:limit]:
                try:
                    file_path = os.path.join(results_dir, result_file)
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    # Extract summary information
                    summary = {
                        "audit_id": data.get("audit_id"),
                        "audit_name": data.get("configuration", {}).get("name", "Unknown"),
                        "start_time": data.get("start_time"),
                        "end_time": data.get("end_time"),
                        "status": data.get("status"),
                        "compliance_percentage": data.get("summary", {}).get("compliance_percentage", 0),
                        "total_policies": data.get("summary", {}).get("total_policies", 0),
                        "failed_policies": data.get("summary", {}).get("failed_policies", 0)
                    }
                    
                    history.append(summary)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load audit summary from {result_file}: {e}")
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get audit history: {e}")
            return []
    
    def delete_audit_results(self, audit_id: str) -> bool:
        """Delete audit results and reports"""
        try:
            deleted_files = []
            
            # Delete results file
            results_file = os.path.join(self.data_dir, "results", f"audit_{audit_id}.json")
            if os.path.exists(results_file):
                os.remove(results_file)
                deleted_files.append(results_file)
            
            # Delete report files
            reports_dir = os.path.join(self.data_dir, "reports")
            if os.path.exists(reports_dir):
                for report_file in os.listdir(reports_dir):
                    if report_file.startswith(f"report_{audit_id}"):
                        report_path = os.path.join(reports_dir, report_file)
                        os.remove(report_path)
                        deleted_files.append(report_path)
            
            # Remove from cache
            if audit_id in self.audit_cache:
                del self.audit_cache[audit_id]
            
            if audit_id in self.running_audits:
                del self.running_audits[audit_id]
            
            self.logger.info(f"Deleted audit {audit_id}: {len(deleted_files)} files removed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete audit results: {e}")
            return False
    
    def cancel_audit(self, audit_id: str) -> bool:
        """Cancel a running audit"""
        try:
            if audit_id in self.running_audits:
                audit_run = self.running_audits[audit_id]
                audit_run.status = AuditStatus.CANCELLED
                audit_run.end_time = datetime.now()
                if audit_run.start_time:
                    audit_run.duration_seconds = (audit_run.end_time - audit_run.start_time).total_seconds()
                
                self.logger.info(f"Cancelled audit run {audit_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to cancel audit: {e}")
            return False