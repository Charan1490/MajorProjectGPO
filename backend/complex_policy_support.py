"""
Complex Policy Support for ADMX Generation
Handles advanced Windows policy types including:
- User Rights Assignments
- Security Options
- Audit Policies
- Privilege Escalation Controls
- Advanced Security Settings
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re

# ============================================================================
# COMPLEX POLICY TYPE DEFINITIONS
# ============================================================================

class ComplexPolicyType(str, Enum):
    """Types of complex policies requiring special handling"""
    USER_RIGHTS = "user_rights"
    AUDIT_POLICY = "audit_policy"
    SECURITY_OPTION = "security_option"
    PRIVILEGE = "privilege"
    RESTRICTED_GROUP = "restricted_group"
    SERVICE_CONTROL = "service_control"
    REGISTRY_ACL = "registry_acl"
    FILE_SYSTEM_ACL = "file_system_acl"

@dataclass
class UserRightsPolicy:
    """User Rights Assignment policy"""
    right_name: str
    display_name: str
    description: str
    recommended_principals: List[str]
    registry_key: str = "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa"
    
@dataclass
class AuditPolicy:
    """Audit Policy configuration"""
    category: str
    subcategory: str
    display_name: str
    description: str
    recommended_setting: str  # Success, Failure, Success and Failure, No Auditing
    guid: Optional[str] = None

@dataclass
class SecurityOption:
    """Security Options policy"""
    option_name: str
    display_name: str
    description: str
    registry_path: str
    value_type: str
    recommended_value: Any
    possible_values: Optional[List[Any]] = None


# ============================================================================
# USER RIGHTS ASSIGNMENTS
# ============================================================================

class UserRightsDatabase:
    """
    Database of Windows User Rights Assignments
    """
    
    USER_RIGHTS = {
        "SeNetworkLogonRight": UserRightsPolicy(
            right_name="SeNetworkLogonRight",
            display_name="Access this computer from the network",
            description="Determines which users and groups can connect to the computer over the network",
            recommended_principals=["Administrators", "Authenticated Users"],
            registry_key="HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa"
        ),
        "SeTcbPrivilege": UserRightsPolicy(
            right_name="SeTcbPrivilege",
            display_name="Act as part of the operating system",
            description="Allows a process to impersonate any user without authentication",
            recommended_principals=[],  # Should be empty for security
        ),
        "SeMachineAccountPrivilege": UserRightsPolicy(
            right_name="SeMachineAccountPrivilege",
            display_name="Add workstations to domain",
            description="Allows users to add computer accounts to the domain",
            recommended_principals=["Administrators"],
        ),
        "SeIncreaseQuotaPrivilege": UserRightsPolicy(
            right_name="SeIncreaseQuotaPrivilege",
            display_name="Adjust memory quotas for a process",
            description="Determines which users can adjust maximum memory available to a process",
            recommended_principals=["Administrators", "LOCAL SERVICE", "NETWORK SERVICE"],
        ),
        "SeInteractiveLogonRight": UserRightsPolicy(
            right_name="SeInteractiveLogonRight",
            display_name="Allow log on locally",
            description="Determines which users can log on locally to the computer",
            recommended_principals=["Administrators", "Users"],
        ),
        "SeRemoteInteractiveLogonRight": UserRightsPolicy(
            right_name="SeRemoteInteractiveLogonRight",
            display_name="Allow log on through Remote Desktop Services",
            description="Determines which users or groups can access the logon screen of a remote device through a Remote Desktop Services connection",
            recommended_principals=["Administrators"],
        ),
        "SeBackupPrivilege": UserRightsPolicy(
            right_name="SeBackupPrivilege",
            display_name="Back up files and directories",
            description="Allows users to circumvent file and directory permissions to back up the system",
            recommended_principals=["Administrators"],
        ),
        "SeChangeNotifyPrivilege": UserRightsPolicy(
            right_name="SeChangeNotifyPrivilege",
            display_name="Bypass traverse checking",
            description="Allows users to pass through directories to which they otherwise have no access",
            recommended_principals=["Administrators", "Backup Operators", "Users", "LOCAL SERVICE", "NETWORK SERVICE"],
        ),
        "SeSystemtimePrivilege": UserRightsPolicy(
            right_name="SeSystemtimePrivilege",
            display_name="Change the system time",
            description="Determines which users and groups can change the time and date on the internal clock",
            recommended_principals=["Administrators", "LOCAL SERVICE"],
        ),
        "SeCreatePagefilePrivilege": UserRightsPolicy(
            right_name="SeCreatePagefilePrivilege",
            display_name="Create a pagefile",
            description="Determines which users and groups can call an internal API to create a pagefile",
            recommended_principals=["Administrators"],
        ),
        "SeCreateTokenPrivilege": UserRightsPolicy(
            right_name="SeCreateTokenPrivilege",
            display_name="Create a token object",
            description="Allows a process to create an access token",
            recommended_principals=[],  # Should be empty for security
        ),
        "SeCreateGlobalPrivilege": UserRightsPolicy(
            right_name="SeCreateGlobalPrivilege",
            display_name="Create global objects",
            description="Determines which accounts can be used by processes to create global objects",
            recommended_principals=["Administrators", "LOCAL SERVICE", "NETWORK SERVICE", "SERVICE"],
        ),
        "SeCreatePermanentPrivilege": UserRightsPolicy(
            right_name="SeCreatePermanentPrivilege",
            display_name="Create permanent shared objects",
            description="Determines which accounts can be used by processes to create directory objects",
            recommended_principals=[],  # Should be empty for security
        ),
        "SeDebugPrivilege": UserRightsPolicy(
            right_name="SeDebugPrivilege",
            display_name="Debug programs",
            description="Determines which users can attach a debugger to any process or to the kernel",
            recommended_principals=["Administrators"],
        ),
        "SeDenyNetworkLogonRight": UserRightsPolicy(
            right_name="SeDenyNetworkLogonRight",
            display_name="Deny access to this computer from the network",
            description="Determines which users are prevented from accessing a computer over the network",
            recommended_principals=["Guests", "Local account"],
        ),
        "SeDenyBatchLogonRight": UserRightsPolicy(
            right_name="SeDenyBatchLogonRight",
            display_name="Deny log on as a batch job",
            description="Determines which accounts cannot log on using a batch-queue facility",
            recommended_principals=["Guests"],
        ),
        "SeDenyServiceLogonRight": UserRightsPolicy(
            right_name="SeDenyServiceLogonRight",
            display_name="Deny log on as a service",
            description="Determines which service accounts are prevented from registering a process as a service",
            recommended_principals=["Guests"],
        ),
        "SeDenyInteractiveLogonRight": UserRightsPolicy(
            right_name="SeDenyInteractiveLogonRight",
            display_name="Deny log on locally",
            description="Determines which users are prevented from logging on at the computer",
            recommended_principals=["Guests"],
        ),
        "SeDenyRemoteInteractiveLogonRight": UserRightsPolicy(
            right_name="SeDenyRemoteInteractiveLogonRight",
            display_name="Deny log on through Remote Desktop Services",
            description="Determines which users and groups are prohibited from logging on as a Remote Desktop Services client",
            recommended_principals=["Guests", "Local account"],
        ),
        "SeEnableDelegationPrivilege": UserRightsPolicy(
            right_name="SeEnableDelegationPrivilege",
            display_name="Enable computer and user accounts to be trusted for delegation",
            description="Allows users to change the Trusted for Delegation setting on a computer object",
            recommended_principals=[],  # Should be empty for workstations
        ),
        "SeRemoteShutdownPrivilege": UserRightsPolicy(
            right_name="SeRemoteShutdownPrivilege",
            display_name="Force shutdown from a remote system",
            description="Determines which users can shut down a computer from a remote location on the network",
            recommended_principals=["Administrators"],
        ),
        "SeImpersonatePrivilege": UserRightsPolicy(
            right_name="SeImpersonatePrivilege",
            display_name="Impersonate a client after authentication",
            description="Allows programs that run on behalf of a user to impersonate a client",
            recommended_principals=["Administrators", "LOCAL SERVICE", "NETWORK SERVICE", "SERVICE"],
        ),
        "SeLoadDriverPrivilege": UserRightsPolicy(
            right_name="SeLoadDriverPrivilege",
            display_name="Load and unload device drivers",
            description="Determines which users can dynamically load and unload device drivers",
            recommended_principals=["Administrators"],
        ),
        "SeTakeOwnershipPrivilege": UserRightsPolicy(
            right_name="SeTakeOwnershipPrivilege",
            display_name="Take ownership of files or other objects",
            description="Allows a user to take ownership of any securable object in the system",
            recommended_principals=["Administrators"],
        ),
    }
    
    @classmethod
    def get_user_right(cls, right_name: str) -> Optional[UserRightsPolicy]:
        """Get user right by name"""
        return cls.USER_RIGHTS.get(right_name)
    
    @classmethod
    def identify_user_right(cls, policy_text: str) -> Optional[str]:
        """Identify user right from policy description"""
        policy_lower = policy_text.lower()
        
        for right_name, right_policy in cls.USER_RIGHTS.items():
            display_lower = right_policy.display_name.lower()
            if display_lower in policy_lower or right_name.lower() in policy_lower:
                return right_name
        
        return None


# ============================================================================
# AUDIT POLICY DEFINITIONS
# ============================================================================

class AuditPolicyDatabase:
    """
    Database of Windows Audit Policies
    """
    
    AUDIT_POLICIES = {
        "Account Logon": {
            "Credential Validation": AuditPolicy(
                category="Account Logon",
                subcategory="Credential Validation",
                display_name="Audit Credential Validation",
                description="Determines whether the OS audits credential validation attempts",
                recommended_setting="Success and Failure",
                guid="{0cce923f-69ae-11d9-bed3-505054503030}"
            ),
        },
        "Account Management": {
            "Security Group Management": AuditPolicy(
                category="Account Management",
                subcategory="Security Group Management",
                display_name="Audit Security Group Management",
                description="Determines whether the OS audits security group management events",
                recommended_setting="Success",
                guid="{0cce9237-69ae-11d9-bed3-505054503030}"
            ),
            "User Account Management": AuditPolicy(
                category="Account Management",
                subcategory="User Account Management",
                display_name="Audit User Account Management",
                description="Determines whether the OS audits user account management events",
                recommended_setting="Success and Failure",
                guid="{0cce9235-69ae-11d9-bed3-505054503030}"
            ),
        },
        "Logon/Logoff": {
            "Logon": AuditPolicy(
                category="Logon/Logoff",
                subcategory="Logon",
                display_name="Audit Logon",
                description="Determines whether the OS audits user logon attempts",
                recommended_setting="Success and Failure",
                guid="{0cce9215-69ae-11d9-bed3-505054503030}"
            ),
            "Logoff": AuditPolicy(
                category="Logon/Logoff",
                subcategory="Logoff",
                display_name="Audit Logoff",
                description="Determines whether the OS audits user logoff events",
                recommended_setting="Success",
                guid="{0cce9216-69ae-11d9-bed3-505054503030}"
            ),
            "Account Lockout": AuditPolicy(
                category="Logon/Logoff",
                subcategory="Account Lockout",
                display_name="Audit Account Lockout",
                description="Determines whether the OS audits account lockout events",
                recommended_setting="Failure",
                guid="{0cce9217-69ae-11d9-bed3-505054503030}"
            ),
        },
        "Policy Change": {
            "Audit Policy Change": AuditPolicy(
                category="Policy Change",
                subcategory="Audit Policy Change",
                display_name="Audit Audit Policy Change",
                description="Determines whether the OS audits changes to audit policy",
                recommended_setting="Success",
                guid="{0cce922f-69ae-11d9-bed3-505054503030}"
            ),
            "Authentication Policy Change": AuditPolicy(
                category="Policy Change",
                subcategory="Authentication Policy Change",
                display_name="Audit Authentication Policy Change",
                description="Determines whether the OS audits changes to authentication policy",
                recommended_setting="Success",
                guid="{0cce9230-69ae-11d9-bed3-505054503030}"
            ),
        },
        "Privilege Use": {
            "Sensitive Privilege Use": AuditPolicy(
                category="Privilege Use",
                subcategory="Sensitive Privilege Use",
                display_name="Audit Sensitive Privilege Use",
                description="Determines whether the OS audits sensitive privilege usage",
                recommended_setting="Success and Failure",
                guid="{0cce9228-69ae-11d9-bed3-505054503030}"
            ),
        },
        "System": {
            "Security State Change": AuditPolicy(
                category="System",
                subcategory="Security State Change",
                display_name="Audit Security State Change",
                description="Determines whether the OS audits changes to the security state",
                recommended_setting="Success",
                guid="{0cce9210-69ae-11d9-bed3-505054503030}"
            ),
            "Security System Extension": AuditPolicy(
                category="System",
                subcategory="Security System Extension",
                display_name="Audit Security System Extension",
                description="Determines whether the OS audits security system extensions",
                recommended_setting="Success",
                guid="{0cce9211-69ae-11d9-bed3-505054503030}"
            ),
            "System Integrity": AuditPolicy(
                category="System",
                subcategory="System Integrity",
                display_name="Audit System Integrity",
                description="Determines whether the OS audits system integrity violations",
                recommended_setting="Success and Failure",
                guid="{0cce9212-69ae-11d9-bed3-505054503030}"
            ),
        },
    }
    
    @classmethod
    def get_audit_policy(cls, category: str, subcategory: str) -> Optional[AuditPolicy]:
        """Get audit policy by category and subcategory"""
        if category in cls.AUDIT_POLICIES:
            return cls.AUDIT_POLICIES[category].get(subcategory)
        return None
    
    @classmethod
    def identify_audit_policy(cls, policy_text: str) -> Optional[Tuple[str, str]]:
        """Identify audit policy from text"""
        policy_lower = policy_text.lower()
        
        for category, subcategories in cls.AUDIT_POLICIES.items():
            for subcategory, audit_policy in subcategories.items():
                if (subcategory.lower() in policy_lower or 
                    audit_policy.display_name.lower() in policy_lower):
                    return (category, subcategory)
        
        return None


# ============================================================================
# SECURITY OPTIONS
# ============================================================================

class SecurityOptionsDatabase:
    """
    Database of Windows Security Options
    """
    
    SECURITY_OPTIONS = {
        "Interactive logon: Machine inactivity limit": SecurityOption(
            option_name="Interactive logon: Machine inactivity limit",
            display_name="Interactive logon: Machine inactivity limit",
            description="Windows notices inactivity of a logon session, and if the amount of inactive time exceeds the inactivity limit, then the screen saver will run, locking the session",
            registry_path="HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System:InactivityTimeoutSecs",
            value_type="REG_DWORD",
            recommended_value=900,
            possible_values=None
        ),
        "Network security: LAN Manager authentication level": SecurityOption(
            option_name="Network security: LAN Manager authentication level",
            display_name="Network security: LAN Manager authentication level",
            description="Determines which challenge/response authentication protocol is used for network logons",
            registry_path="HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa:LmCompatibilityLevel",
            value_type="REG_DWORD",
            recommended_value=5,
            possible_values=[0, 1, 2, 3, 4, 5]
        ),
        "User Account Control: Admin Approval Mode for the built-in Administrator account": SecurityOption(
            option_name="User Account Control: Admin Approval Mode for the built-in Administrator account",
            display_name="User Account Control: Admin Approval Mode for Administrator",
            description="Determines whether the built-in Administrator account uses Admin Approval Mode",
            registry_path="HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System:FilterAdministratorToken",
            value_type="REG_DWORD",
            recommended_value=1,
            possible_values=[0, 1]
        ),
        "User Account Control: Run all administrators in Admin Approval Mode": SecurityOption(
            option_name="User Account Control: Run all administrators in Admin Approval Mode",
            display_name="User Account Control: Run all administrators in Admin Approval Mode",
            description="Determines the behavior of all User Account Control (UAC) policy settings for the computer",
            registry_path="HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System:EnableLUA",
            value_type="REG_DWORD",
            recommended_value=1,
            possible_values=[0, 1]
        ),
    }
    
    @classmethod
    def get_security_option(cls, option_name: str) -> Optional[SecurityOption]:
        """Get security option by name"""
        return cls.SECURITY_OPTIONS.get(option_name)
    
    @classmethod
    def identify_security_option(cls, policy_text: str) -> Optional[str]:
        """Identify security option from text"""
        policy_lower = policy_text.lower()
        
        for option_name, security_option in cls.SECURITY_OPTIONS.items():
            if option_name.lower() in policy_lower:
                return option_name
        
        return None


# ============================================================================
# COMPLEX POLICY ANALYZER
# ============================================================================

class ComplexPolicyAnalyzer:
    """
    Analyzes policies to identify complex types and provide appropriate handling
    """
    
    @staticmethod
    def identify_policy_type(policy_data: Dict[str, Any]) -> ComplexPolicyType:
        """
        Identify the complex policy type
        
        Args:
            policy_data: Policy information dictionary
            
        Returns:
            ComplexPolicyType enum value
        """
        policy_text = (
            str(policy_data.get('policy_name', '')) + " " +
            str(policy_data.get('description', '')) + " " +
            str(policy_data.get('gpo_path', ''))
        ).lower()
        
        # Check for user rights
        if any(keyword in policy_text for keyword in ['user right', 'log on', 'privilege', 'impersonate']):
            if UserRightsDatabase.identify_user_right(policy_text):
                return ComplexPolicyType.USER_RIGHTS
        
        # Check for audit policies
        if any(keyword in policy_text for keyword in ['audit', 'auditing']):
            if AuditPolicyDatabase.identify_audit_policy(policy_text):
                return ComplexPolicyType.AUDIT_POLICY
        
        # Check for security options
        if 'security option' in policy_text or 'interactive logon' in policy_text or 'user account control' in policy_text:
            if SecurityOptionsDatabase.identify_security_option(policy_text):
                return ComplexPolicyType.SECURITY_OPTION
        
        # Check for service control
        if any(keyword in policy_text for keyword in ['service', 'startup type']):
            return ComplexPolicyType.SERVICE_CONTROL
        
        # Check for group membership
        if 'restricted group' in policy_text or 'group membership' in policy_text:
            return ComplexPolicyType.RESTRICTED_GROUP
        
        # Default to security option
        return ComplexPolicyType.SECURITY_OPTION
    
    @staticmethod
    def enhance_policy_with_complex_data(policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance policy data with complex policy-specific information
        
        Args:
            policy_data: Policy information dictionary
            
        Returns:
            Enhanced policy data dictionary
        """
        enhanced = policy_data.copy()
        policy_type = ComplexPolicyAnalyzer.identify_policy_type(policy_data)
        
        enhanced['complex_type'] = policy_type.value
        
        policy_text = str(policy_data.get('policy_name', '')) + " " + str(policy_data.get('description', ''))
        
        if policy_type == ComplexPolicyType.USER_RIGHTS:
            right_name = UserRightsDatabase.identify_user_right(policy_text)
            if right_name:
                user_right = UserRightsDatabase.get_user_right(right_name)
                if user_right:
                    enhanced['user_right_name'] = user_right.right_name
                    enhanced['recommended_principals'] = user_right.recommended_principals
                    if not enhanced.get('registry_path'):
                        enhanced['registry_path'] = user_right.registry_key
        
        elif policy_type == ComplexPolicyType.AUDIT_POLICY:
            audit_info = AuditPolicyDatabase.identify_audit_policy(policy_text)
            if audit_info:
                category, subcategory = audit_info
                audit_policy = AuditPolicyDatabase.get_audit_policy(category, subcategory)
                if audit_policy:
                    enhanced['audit_category'] = audit_policy.category
                    enhanced['audit_subcategory'] = audit_policy.subcategory
                    enhanced['audit_guid'] = audit_policy.guid
                    enhanced['recommended_setting'] = audit_policy.recommended_setting
        
        elif policy_type == ComplexPolicyType.SECURITY_OPTION:
            option_name = SecurityOptionsDatabase.identify_security_option(policy_text)
            if option_name:
                security_option = SecurityOptionsDatabase.get_security_option(option_name)
                if security_option:
                    if not enhanced.get('registry_path'):
                        enhanced['registry_path'] = security_option.registry_path
                    if not enhanced.get('required_value'):
                        enhanced['required_value'] = security_option.recommended_value
                    enhanced['value_type'] = security_option.value_type
                    if security_option.possible_values:
                        enhanced['possible_values'] = security_option.possible_values
        
        return enhanced
