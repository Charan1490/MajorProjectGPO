"""
Policy Path Research Service
Uses Gemini API to research Windows registry paths and GPO settings for CIS policies
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from google import genai
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class PolicyPath:
    """Windows policy implementation details"""
    policy_id: str
    policy_name: str
    registry_path: str
    registry_hive: str  # HKLM, HKCU, etc.
    registry_key: str
    registry_value_name: str
    registry_value_type: str  # REG_DWORD, REG_SZ, etc.
    enabled_value: Any
    disabled_value: Any
    gpo_path: Optional[str] = None
    gpo_setting: Optional[str] = None
    secedit_section: Optional[str] = None
    secedit_setting: Optional[str] = None
    powershell_command: Optional[str] = None
    verification_command: Optional[str] = None
    remediation_notes: Optional[str] = None
    requires_reboot: bool = False
    risk_level: str = "Medium"  # Low, Medium, High, Critical

@dataclass
class PolicyResearchResult:
    """Result of policy path research"""
    success: bool
    policy_path: Optional[PolicyPath]
    error_message: Optional[str]
    confidence_score: float = 0.0
    sources: List[str] = None

class PolicyPathResearcher:
    """Research Windows policy implementation paths using Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the policy path researcher"""
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            logger.warning("No Gemini API key provided. Using fallback database only.")
            self.client = None
        else:
            # Use the new Google GenAI SDK client
            self.client = genai.Client(api_key=self.api_key)
            # Use gemini-2.5-flash which is the latest stable model
            self.model_name = 'gemini-2.5-flash'
        
        # Load existing policy database
        self.policy_database = self._load_policy_database()
        
    def _load_policy_database(self) -> Dict[str, PolicyPath]:
        """Load existing policy database from file"""
        db_path = Path(__file__).parent / "policy_paths_database.json"
        
        if db_path.exists():
            try:
                with open(db_path, 'r') as f:
                    data = json.load(f)
                    return {k: PolicyPath(**v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading policy database: {e}")
        
        return {}
    
    def _save_policy_database(self):
        """Save policy database to file"""
        db_path = Path(__file__).parent / "policy_paths_database.json"
        
        try:
            data = {k: v.__dict__ for k, v in self.policy_database.items()}
            with open(db_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving policy database: {e}")
    
    def research_policy_path(self, policy: Dict[str, Any]) -> PolicyResearchResult:
        """Research implementation path for a CIS policy"""
        
        policy_id = policy.get('id', '')
        policy_name = policy.get('name', '')
        
        # Check if we already have this policy in database
        if policy_id in self.policy_database:
            logger.info(f"Found policy {policy_id} in database")
            return PolicyResearchResult(
                success=True,
                policy_path=self.policy_database[policy_id],
                error_message=None,
                confidence_score=1.0,
                sources=["Local Database"]
            )
        
        # Research using Gemini API
        if self.client:
            result = self._research_with_gemini(policy)
            if result.success:
                # Save to database
                self.policy_database[policy_id] = result.policy_path
                self._save_policy_database()
                return result
        
        # Fallback to heuristic research
        return self._research_with_heuristics(policy)
    
    def _research_with_gemini(self, policy: Dict[str, Any]) -> PolicyResearchResult:
        """Research policy path using Gemini API with fallback"""
        
        try:
            prompt = self._create_research_prompt(policy)
            
            # Use the new Google GenAI SDK API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            if response.text:
                return self._parse_gemini_response(policy, response.text)
            else:
                return PolicyResearchResult(
                    success=False,
                    policy_path=None,
                    error_message="Empty response from Gemini API"
                )
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error with Gemini API: {error_msg}")
            
            # If API is overloaded (503) or rate limited, use heuristics as fallback
            if '503' in error_msg or 'overloaded' in error_msg.lower() or 'rate' in error_msg.lower():
                logger.warning(f"API overloaded/rate limited, using heuristics fallback for {policy.get('id', 'unknown')}")
                return self._research_with_heuristics(policy)
            
            return PolicyResearchResult(
                success=False,
                policy_path=None,
                error_message=error_msg
            )
    
    def _get_category_specific_hint(self, policy_name_lower: str) -> str:
        """Provide category-specific implementation hints based on policy name"""
        
        # Category 1: Password Policies
        if any(kw in policy_name_lower for kw in ['password history', 'minimum password age', 'maximum password age', 
                                                     'minimum password length', 'password complexity', 'reversible encryption']):
            return """

**CATEGORY: PASSWORD POLICY**
- Implementation Method: secedit (Security Template) + net accounts
- Registry: NOT APPLICABLE (use 'N/A' for all registry fields)
- secedit_section: "[System Access]"
- Common Settings: PasswordHistorySize, MinimumPasswordAge, MaximumPasswordAge, MinimumPasswordLength, PasswordComplexity
- PowerShell Commands: Use `net accounts` commands (e.g., /uniquepw:24, /minpwage:1, /maxpwage:365, /minpwlen:14)
- Verification: Use `net accounts` command and parse output
- CRITICAL: Do NOT use HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System registry paths
"""
        
        # Category 2: Account Lockout Policies
        elif any(kw in policy_name_lower for kw in ['account lockout', 'lockout threshold', 'lockout duration', 
                                                      'reset lockout counter', 'administrator account lockout']):
            return """

**CATEGORY: ACCOUNT LOCKOUT POLICY**
- Implementation Method: secedit (Security Template) + net accounts
- Registry: May use HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa for some settings
- secedit_section: "[System Access]" or "[Security Options]"
- Common Settings: LockoutBadCount, LockoutDuration, ResetLockoutCount, AllowAdministratorLockout
- PowerShell Commands: Use `net accounts` (e.g., /lockoutthreshold:10, /lockoutduration:15, /lockoutreset:15)
- Verification: Use `net accounts` or check registry value
- Note: Administrator lockout requires KB5020282 patch
"""
        
        # Category 3: User Rights Assignment (Privileges)
        elif any(kw in policy_name_lower for kw in ['user right', 'privilege', 'log on', 'logon', 'shut down system',
                                                      'access this computer', 'deny', 'impersonate', 'create token',
                                                      'backup files', 'restore files', 'debug programs']):
            return """

**CATEGORY: USER RIGHTS ASSIGNMENT**
- Implementation Method: secedit (Security Template) ONLY
- Registry: NOT APPLICABLE (use 'N/A')
- secedit_section: "[Privilege Rights]"
- Common Settings: SeNetworkLogonRight, SeInteractiveLogonRight, SeRemoteShutdownPrivilege, SeDebugPrivilege, SeBackupPrivilege
- Value Format: Comma-separated SIDs or well-known names (e.g., "*S-1-5-32-544,*S-1-5-32-545" or "Administrators,Users")
- PowerShell: Use secedit.exe with INF file (ALWAYS use @' ... '@ single-quoted here-strings for $CHICAGO$)
- Verification: Export security policy with `secedit /export` and check [Privilege Rights] section
- CRITICAL: These are NOT registry-based
"""
        
        # Category 4: Security Options (mixed implementations)
        elif any(kw in policy_name_lower for kw in ['security option', 'interactive logon', 'network access', 
                                                      'network security', 'microsoft network', 'accounts:', 'audit:',
                                                      'devices:', 'domain controller:', 'domain member:']):
            return """

**CATEGORY: SECURITY OPTIONS**
- Implementation Method: MIXED (Registry + secedit)
- Registry: Often uses HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa or HKLM\\SYSTEM\\CurrentControlSet\\Services\\LanmanWorkstation\\Parameters
- secedit_section: "[Registry Values]" or "[Security Options]"
- PowerShell: May combine registry + secedit methods
- Verification: Check registry value or use secedit export
- Examples:
  * Interactive logon: HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System
  * Network security: HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa
  * SMB settings: HKLM\\SYSTEM\\CurrentControlSet\\Services\\LanmanServer\\Parameters
"""
        
        # Category 5: Audit Policies
        elif any(kw in policy_name_lower for kw in ['audit', 'auditing', 'audit policy', 'failure', 'success']):
            return """

**CATEGORY: AUDIT POLICY**
- Implementation Method: auditpol.exe (PRIMARY) or secedit
- Registry: NOT APPLICABLE (use 'N/A')
- secedit_section: "[Event Audit]" (legacy) or use auditpol for advanced audit
- PowerShell Commands: Use `auditpol /set` commands (e.g., auditpol /set /subcategory:"Logon" /success:enable /failure:enable)
- Verification: Use `auditpol /get` commands
- Format: Enable both Success and Failure for most policies
- CRITICAL: Advanced Audit Policies require auditpol, not secedit
"""
        
        # Category 6: Windows Firewall
        elif any(kw in policy_name_lower for kw in ['firewall', 'domain profile', 'private profile', 'public profile']):
            return """

**CATEGORY: WINDOWS FIREWALL**
- Implementation Method: netsh advfirewall or PowerShell NetSecurity cmdlets
- Registry: HKLM\\SOFTWARE\\Policies\\Microsoft\\WindowsFirewall (for GPO settings)
- PowerShell Commands: 
  * Use `Set-NetFirewallProfile` cmdlets (e.g., Set-NetFirewallProfile -Profile Domain -Enabled True)
  * Or `netsh advfirewall set` commands
- Verification: Use `Get-NetFirewallProfile` or `netsh advfirewall show allprofiles`
- Profiles: Domain, Private, Public
- Settings: Firewall state, inbound/outbound rules, logging
"""
        
        # Category 7: Windows Defender / Microsoft Defender
        elif any(kw in policy_name_lower for kw in ['defender', 'windows defender', 'antivirus', 'real-time protection',
                                                      'exploit protection', 'attack surface reduction']):
            return """

**CATEGORY: WINDOWS DEFENDER / SECURITY**
- Implementation Method: Registry (Primary) + PowerShell cmdlets
- Registry: HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender
- PowerShell Commands: 
  * Use `Set-MpPreference` cmdlets (e.g., Set-MpPreference -DisableRealtimeMonitoring $false)
  * Use `Set-ProcessMitigation` for exploit protection
- Verification: Use `Get-MpPreference` or check registry
- CRITICAL: Requires Windows Defender service to be running
"""
        
        # Category 8: Remote Desktop / Terminal Services
        elif any(kw in policy_name_lower for kw in ['remote desktop', 'terminal services', 'rdp', 'remote assistance']):
            return """

**CATEGORY: REMOTE DESKTOP SERVICES**
- Implementation Method: Registry
- Registry: 
  * HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server
  * HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows NT\\Terminal Services
- PowerShell: Registry modification or WMI
- Verification: Check registry values or use `Get-ItemProperty`
- Settings: fDenyTSConnections, SecurityLayer, UserAuthentication, MinEncryptionLevel
"""
        
        # Category 9: BitLocker Drive Encryption
        elif any(kw in policy_name_lower for kw in ['bitlocker', 'drive encryption', 'encryption method']):
            return """

**CATEGORY: BITLOCKER DRIVE ENCRYPTION**
- Implementation Method: Registry + manage-bde command
- Registry: HKLM\\SOFTWARE\\Policies\\Microsoft\\FVE (Full Volume Encryption)
- PowerShell Commands: Use `manage-bde` or `Enable-BitLocker` cmdlets
- Verification: Use `Get-BitLockerVolume` or `manage-bde -status`
- CRITICAL: Requires TPM hardware support
"""
        
        # Category 10: AppLocker / Application Control
        elif any(kw in policy_name_lower for kw in ['applocker', 'application control', 'software restriction']):
            return """

**CATEGORY: APPLOCKER / APPLICATION CONTROL**
- Implementation Method: PowerShell AppLocker cmdlets + Group Policy
- Registry: HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\SrpV2
- PowerShell Commands: Use `Set-AppLockerPolicy`, `Get-AppLockerPolicy` cmdlets
- Verification: Check AppLocker event logs or Get-AppLockerPolicy
- CRITICAL: Requires Windows Enterprise/Education editions
"""
        
        # Default: Generic guidance
        return """

**GENERAL POLICY IMPLEMENTATION**
- Research the correct implementation method for this specific policy
- Check if it requires registry, secedit, auditpol, or specialized cmdlets
- Provide accurate registry paths with proper hive (HKLM or HKCU)
- For secedit-based policies, specify the correct section name
- Always provide working verification commands
"""
    
    def _create_research_prompt(self, policy: Dict[str, Any]) -> str:
        """Create research prompt for Gemini API with category-specific guidance"""
        
        policy_name = policy.get('name', 'Unknown')
        policy_lower = policy_name.lower()
        
        # Detect policy category and provide specific implementation guidance
        category_hint = self._get_category_specific_hint(policy_lower)
        
        secedit_hint = category_hint if category_hint else ""
        
        return f"""
As a Windows security expert, research the implementation details for this CIS policy:

Policy ID: {policy.get('id', 'Unknown')}
Policy Name: {policy_name}
Description: {policy.get('description', 'No description')}
Category: {policy.get('category', 'Unknown')}
CIS Level: {policy.get('cis_level', 'Unknown')}
{secedit_hint}

Please provide the following information in JSON format:

{{
    "registry_hive": "HKLM or HKCU (use 'N/A' if not registry-based)",
    "registry_key": "Full registry key path (use 'N/A' if secedit-based)",
    "registry_value_name": "Registry value name (use 'N/A' if secedit-based)",
    "registry_value_type": "REG_DWORD, REG_SZ, REG_BINARY, etc. (use 'N/A' if secedit-based)",
    "enabled_value": "Value when policy is enabled (e.g., '24' for password history)",
    "disabled_value": "Value when policy is disabled",
    "gpo_path": "Group Policy path if applicable",
    "gpo_setting": "GPO setting name",
    "secedit_section": "Security template section (e.g., 'System Access', '[Account Lockout]')",
    "secedit_setting": "Security template setting (e.g., 'PasswordHistorySize', 'MinimumPasswordAge')",
    "powershell_command": "PowerShell command to apply this policy (e.g., 'net accounts /uniquepw:24')",
    "verification_command": "PowerShell command to verify the policy",
    "remediation_notes": "Important notes for remediation",
    "requires_reboot": true/false,
    "risk_level": "Low/Medium/High/Critical",
    "confidence_score": 0.0-1.0
}}

**Implementation Priority**:
1. For Password/Account policies: Use secedit_section + secedit_setting (PRIMARY METHOD)
2. For Registry-based policies: Use registry_hive + registry_key + registry_value_name
3. For Group Policy: Use gpo_path + gpo_setting
4. Always provide powershell_command and verification_command

**Common secedit settings**:
- Password policies: PasswordHistorySize, MinimumPasswordAge, MaximumPasswordAge, MinimumPasswordLength, PasswordComplexity
- Account lockout: LockoutBadCount, ResetLockoutCount, LockoutDuration
- Section: [System Access] for password and lockout policies

**CRITICAL PowerShell Syntax Rules for powershell_command**:
When generating PowerShell commands that create .inf files or use here-strings:
- ALWAYS use SINGLE-QUOTED here-strings: @' ... '@ (NOT @" ... "@)
- Single quotes prevent variable interpolation and keep $CHICAGO$ as literal text
- Example CORRECT syntax:
  $infContent = @'
  [Unicode]
  Unicode=yes
  [Version]
  signature="$CHICAGO$"
  '@
- Example WRONG syntax (causes parse errors):
  $infContent = "@
  signature=\\"$CHICAGO$\\"
  @"
- Use proper indentation (4 spaces) inside try/catch blocks
- Add comments to explain what the code does

Provide accurate, tested information for Windows 10/11 standalone systems.
"""
    
    def _parse_gemini_response(self, policy: Dict[str, Any], response_text: str) -> PolicyResearchResult:
        """Parse Gemini API response into PolicyPath"""
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                return PolicyResearchResult(
                    success=False,
                    policy_path=None,
                    error_message="No JSON found in response"
                )
            
            data = json.loads(json_match.group())
            
            # Create PolicyPath object
            policy_path = PolicyPath(
                policy_id=policy.get('id', ''),
                policy_name=policy.get('name', ''),
                registry_path=f"{data.get('registry_hive', 'HKLM')}:\\{data.get('registry_key', '')}",
                registry_hive=data.get('registry_hive', 'HKLM'),
                registry_key=data.get('registry_key', ''),
                registry_value_name=data.get('registry_value_name', ''),
                registry_value_type=data.get('registry_value_type', 'REG_DWORD'),
                enabled_value=data.get('enabled_value'),
                disabled_value=data.get('disabled_value'),
                gpo_path=data.get('gpo_path'),
                gpo_setting=data.get('gpo_setting'),
                secedit_section=data.get('secedit_section'),
                secedit_setting=data.get('secedit_setting'),
                powershell_command=data.get('powershell_command'),
                verification_command=data.get('verification_command'),
                remediation_notes=data.get('remediation_notes'),
                requires_reboot=data.get('requires_reboot', False),
                risk_level=data.get('risk_level', 'Medium')
            )
            
            return PolicyResearchResult(
                success=True,
                policy_path=policy_path,
                error_message=None,
                confidence_score=data.get('confidence_score', 0.8),
                sources=["Gemini AI Research"]
            )
            
        except json.JSONDecodeError as e:
            return PolicyResearchResult(
                success=False,
                policy_path=None,
                error_message=f"JSON parsing error: {e}"
            )
        except Exception as e:
            return PolicyResearchResult(
                success=False,
                policy_path=None,
                error_message=f"Response parsing error: {e}"
            )
    
    def _research_with_heuristics(self, policy: Dict[str, Any]) -> PolicyResearchResult:
        """Fallback research using heuristics and known patterns"""
        
        policy_name = policy.get('name', '').lower()
        category = policy.get('category', '').lower()
        
        # Check if this is a password/account policy (requires secedit, not registry)
        password_policy_keywords = ['password history', 'minimum password age', 'maximum password age', 
                                    'minimum password length', 'password complexity', 'reversible encryption',
                                    'account lockout', 'lockout threshold', 'lockout duration', 'reset account lockout']
        
        is_password_policy = any(keyword in policy_name for keyword in password_policy_keywords)
        
        # Password policy mappings (secedit-based)
        if is_password_policy:
            secedit_mappings = {
                'password history': {'section': 'System Access', 'setting': 'PasswordHistorySize', 'value': '24'},
                'minimum password age': {'section': 'System Access', 'setting': 'MinimumPasswordAge', 'value': '1'},
                'maximum password age': {'section': 'System Access', 'setting': 'MaximumPasswordAge', 'value': '365'},
                'minimum password length': {'section': 'System Access', 'setting': 'MinimumPasswordLength', 'value': '14'},
                'password complexity': {'section': 'System Access', 'setting': 'PasswordComplexity', 'value': '1'},
                'reversible encryption': {'section': 'System Access', 'setting': 'ClearTextPassword', 'value': '0'},
                'account lockout': {'section': 'System Access', 'setting': 'LockoutBadCount', 'value': '10'},
                'lockout threshold': {'section': 'System Access', 'setting': 'LockoutBadCount', 'value': '10'},
                'lockout duration': {'section': 'System Access', 'setting': 'LockoutDuration', 'value': '15'},
                'reset account lockout': {'section': 'System Access', 'setting': 'ResetLockoutCount', 'value': '15'}
            }
            
            # Find best match
            secedit_config = None
            for keyword, config in secedit_mappings.items():
                if keyword in policy_name:
                    secedit_config = config
                    break
            
            if secedit_config:
                # Return secedit-based policy (no registry)
                policy_path = PolicyPath(
                    policy_id=policy.get('id', ''),
                    policy_name=policy.get('name', ''),
                    registry_path='N/A',
                    registry_hive='N/A',
                    registry_key='N/A',
                    registry_value_name='N/A',
                    registry_value_type='N/A',
                    enabled_value=secedit_config['value'],
                    disabled_value='0',
                    secedit_section=secedit_config['section'],
                    secedit_setting=secedit_config['setting'],
                    powershell_command=self._generate_password_policy_command(secedit_config),
                    verification_command=f"net accounts",
                    remediation_notes=f"This password policy must be set via secedit or net accounts command. Registry modification is not supported.",
                    requires_reboot=False,
                    risk_level='Medium'
                )
                
                return PolicyResearchResult(
                    success=True,
                    policy_path=policy_path,
                    error_message=None,
                    confidence_score=0.7
                )
        
        # Common CIS policy patterns (registry-based)
        registry_mappings = {
            # Account Policies (non-password/lockout)
            'password': {
                'hive': 'N/A',
                'key': 'N/A',
                'type': 'N/A'
            },
            'lockout': {
                'hive': 'N/A', 
                'key': 'N/A',
                'type': 'N/A'
            },
            # Local Policies
            'audit': {
                'hive': 'HKLM',
                'key': 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\\Audit',
                'type': 'REG_DWORD'
            },
            'user rights': {
                'hive': 'HKLM',
                'key': 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',
                'type': 'REG_SZ'
            },
            # Security Options
            'network security': {
                'hive': 'HKLM',
                'key': 'SYSTEM\\CurrentControlSet\\Control\\Lsa',
                'type': 'REG_DWORD'
            },
            'interactive logon': {
                'hive': 'HKLM',
                'key': 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',
                'type': 'REG_DWORD'
            }
        }
        
        # Find best match
        best_match = None
        for pattern, config in registry_mappings.items():
            if pattern in policy_name or pattern in category:
                best_match = config
                break
        
        if not best_match:
            # Default fallback
            best_match = {
                'hive': 'HKLM',
                'key': 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',
                'type': 'REG_DWORD'
            }
        
        # Generate policy path
        policy_path = PolicyPath(
            policy_id=policy.get('id', ''),
            policy_name=policy.get('name', ''),
            registry_path=f"{best_match['hive']}:\\{best_match['key']}",
            registry_hive=best_match['hive'],
            registry_key=best_match['key'],
            registry_value_name=self._generate_value_name(policy),
            registry_value_type=best_match['type'],
            enabled_value=1 if best_match['type'] == 'REG_DWORD' else 'Enabled',
            disabled_value=0 if best_match['type'] == 'REG_DWORD' else 'Disabled',
            remediation_notes="Generated using heuristic analysis - verify manually",
            requires_reboot=False,
            risk_level="Medium"
        )
        
        return PolicyResearchResult(
            success=True,
            policy_path=policy_path,
            error_message=None,
            confidence_score=0.3,  # Low confidence for heuristic
            sources=["Heuristic Analysis"]
        )
    
    def _generate_password_policy_command(self, config: Dict[str, str]) -> str:
        """Generate PowerShell command for password policy"""
        setting = config['setting']
        value = config['value']
        
        # Map secedit settings to net accounts parameters
        net_accounts_map = {
            'PasswordHistorySize': f'net accounts /uniquepw:{value}',
            'MinimumPasswordAge': f'net accounts /minpwage:{value}',
            'MaximumPasswordAge': f'net accounts /maxpwage:{value}',
            'MinimumPasswordLength': f'net accounts /minpwlen:{value}',
            'LockoutBadCount': f'net accounts /lockoutthreshold:{value}',
            'LockoutDuration': f'net accounts /lockoutduration:{value}',
            'ResetLockoutCount': f'net accounts /lockoutwindow:{value}'
        }
        
        return net_accounts_map.get(setting, f'# Manual secedit required for {setting}')
    
    def _generate_value_name(self, policy: Dict[str, Any]) -> str:
        """Generate registry value name from policy information"""
        
        name = policy.get('name', '')
        
        # Clean up name for registry value
        value_name = re.sub(r'[^\w\s]', '', name)
        value_name = re.sub(r'\s+', '_', value_name.strip())
        
        # Truncate if too long
        if len(value_name) > 50:
            value_name = value_name[:50]
        
        return value_name or "Policy_Setting"
    
    def research_bulk_policies(self, policies: List[Dict[str, Any]]) -> Dict[str, PolicyResearchResult]:
        """Research multiple policies in bulk with rate limiting"""
        
        import time
        
        results = {}
        api_calls_made = 0
        max_api_calls = 10  # Limit API calls to avoid overload
        
        for i, policy in enumerate(policies):
            policy_id = policy.get('id', f'policy_{i}')
            logger.info(f"Researching policy {i+1}/{len(policies)}: {policy_id}")
            
            try:
                # Check database first (this is fast and doesn't use API)
                if policy_id in self.policy_database:
                    logger.info(f"Found policy {policy_id} in database")
                    results[policy_id] = PolicyResearchResult(
                        success=True,
                        policy_path=self.policy_database[policy_id],
                        error_message=None,
                        confidence_score=1.0,
                        sources=["Local Database"]
                    )
                    continue
                
                # Only use API if we haven't hit the limit
                if api_calls_made >= max_api_calls:
                    logger.warning(f"API call limit reached ({max_api_calls}), using fallback for {policy_id}")
                    result = self._research_with_heuristics(policy)
                else:
                    # Make API call with retry logic
                    result = self.research_policy_path(policy)
                    
                    # If we made an API call (not from cache), increment counter and add delay
                    if self.client and '503' not in str(result.error_message or ''):
                        api_calls_made += 1
                        # Add delay between API calls to avoid rate limiting
                        if i < len(policies) - 1:  # Don't delay after last policy
                            time.sleep(2)  # 2 second delay between API calls
                
                results[policy_id] = result
                
                if result.success:
                    logger.info(f"Successfully researched {policy_id}")
                else:
                    logger.warning(f"Failed to research {policy_id}: {result.error_message}")
                    
            except Exception as e:
                logger.error(f"Error researching {policy_id}: {e}")
                results[policy_id] = PolicyResearchResult(
                    success=False,
                    policy_path=None,
                    error_message=str(e)
                )
        
        logger.info(f"Bulk research completed. Made {api_calls_made} API calls out of {len(policies)} policies")
        return results
    
    def get_policy_statistics(self) -> Dict[str, Any]:
        """Get statistics about the policy database"""
        
        total_policies = len(self.policy_database)
        
        risk_levels = {}
        registry_hives = {}
        requires_reboot = 0
        
        for policy_path in self.policy_database.values():
            # Risk level stats
            risk_levels[policy_path.risk_level] = risk_levels.get(policy_path.risk_level, 0) + 1
            
            # Registry hive stats
            registry_hives[policy_path.registry_hive] = registry_hives.get(policy_path.registry_hive, 0) + 1
            
            # Reboot requirement stats
            if policy_path.requires_reboot:
                requires_reboot += 1
        
        return {
            "total_policies": total_policies,
            "risk_levels": risk_levels,
            "registry_hives": registry_hives,
            "requires_reboot": requires_reboot,
            "reboot_percentage": (requires_reboot / total_policies * 100) if total_policies > 0 else 0
        }