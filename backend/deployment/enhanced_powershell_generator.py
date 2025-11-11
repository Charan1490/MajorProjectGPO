"""
Enhanced PowerShell Script Generator
Creates comprehensive PowerShell scripts that actually apply CIS policies
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

try:
    from .policy_path_researcher import PolicyPathResearcher, PolicyPath
except ImportError:
    # Fallback for testing
    from policy_path_researcher import PolicyPathResearcher, PolicyPath

logger = logging.getLogger(__name__)

class EnhancedPowerShellGenerator:
    """Generate comprehensive PowerShell scripts for CIS policy deployment"""
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """Initialize the PowerShell generator"""
        self.researcher = PolicyPathResearcher(gemini_api_key)
        
    def generate_deployment_script(self, policies: List[Dict[str, Any]], 
                                 target_os: str = "Windows 11",
                                 include_backup: bool = True,
                                 include_verification: bool = True,
                                 include_rollback: bool = True) -> str:
        """Generate comprehensive PowerShell deployment script"""
        
        logger.info(f"Generating PowerShell script for {len(policies)} policies")
        
        # Research policy paths
        research_results = self.researcher.research_bulk_policies(policies)
        
        # Generate script sections
        script_header = self._generate_script_header(target_os)
        script_functions = self._generate_utility_functions()
        script_backup = self._generate_backup_section() if include_backup else ""
        script_policies = self._generate_policy_application_section(research_results)
        script_verification = self._generate_verification_section(research_results) if include_verification else ""
        script_rollback = self._generate_rollback_section() if include_rollback else ""
        script_footer = self._generate_script_footer()
        
        # Combine all sections
        full_script = "\n".join([
            script_header,
            script_functions,
            script_backup,
            script_policies,
            script_verification,
            script_rollback,
            script_footer
        ])
        
        return full_script
    
    def _generate_script_header(self, target_os: str) -> str:
        """Generate PowerShell script header"""
        
        return f'''#Requires -RunAsAdministrator
<#
.SYNOPSIS
    CIS Benchmark Compliance Deployment Script

.DESCRIPTION
    Applies CIS benchmark policies to {target_os} systems.
    This script implements actual registry changes, Group Policy modifications,
    and security settings to achieve CIS compliance.

.PARAMETER WhatIf
    Preview changes without applying them

.PARAMETER CreateBackup
    Create system backup before applying changes (default: true)

.PARAMETER BackupPath
    Path to store backup files (default: C:\\CIS-Backup)

.PARAMETER LogPath
    Path to log file (default: C:\\CIS-Deployment.log)

.PARAMETER SkipVerification
    Skip policy verification after application

.PARAMETER ForceReboot
    Force system reboot if required by policies

.EXAMPLE
    .\\Deploy-CISCompliance.ps1
    .\\Deploy-CISCompliance.ps1 -WhatIf
    .\\Deploy-CISCompliance.ps1 -BackupPath "D:\\Backups"

.NOTES
    Generated: {datetime.now().isoformat()}
    Target OS: {target_os}
    
    REQUIREMENTS:
    - PowerShell 5.1 or later
    - Administrator privileges
    - Windows Management Framework
    
    WARNINGS:
    - This script modifies system settings
    - Always test in a non-production environment first
    - System reboot may be required
    
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory=$false)]
    [switch]$WhatIf,
    
    [Parameter(Mandatory=$false)]
    [switch]$CreateBackup = $true,
    
    [Parameter(Mandatory=$false)]
    [string]$BackupPath = "C:\\CIS-Backup",
    
    [Parameter(Mandatory=$false)]
    [string]$LogPath = "C:\\CIS-Deployment.log",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipVerification = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$ForceReboot = $false
)

# Script configuration
$ErrorActionPreference = "Stop"
$script:SuccessCount = 0
$script:FailureCount = 0
$script:WarningCount = 0
$script:RebootRequired = $false
$script:StartTime = Get-Date

Write-Host "=== CIS Benchmark Compliance Deployment ===" -ForegroundColor Cyan
Write-Host "Started: $($script:StartTime)" -ForegroundColor Green
Write-Host "Target OS: {target_os}" -ForegroundColor Yellow
if ($WhatIf) {{
    Write-Host "MODE: PREVIEW ONLY (WhatIf)" -ForegroundColor Magenta
}}
Write-Host ""'''
    
    def _generate_utility_functions(self) -> str:
        """Generate utility functions for the script"""
        
        return '''
# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

function Write-Log {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("INFO", "WARNING", "ERROR", "SUCCESS")]
        [string]$Level = "INFO",
        
        [Parameter(Mandatory=$false)]
        [switch]$NoConsole
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    if (-not $NoConsole) {
        switch ($Level) {
            "INFO"    { Write-Host $logEntry -ForegroundColor White }
            "WARNING" { Write-Host $logEntry -ForegroundColor Yellow }
            "ERROR"   { Write-Host $logEntry -ForegroundColor Red }
            "SUCCESS" { Write-Host $logEntry -ForegroundColor Green }
        }
    }
    
    if ($LogPath) {
        try {
            $logDir = Split-Path $LogPath -Parent
            if (-not (Test-Path $logDir)) {
                New-Item -ItemType Directory -Path $logDir -Force | Out-Null
            }
            $logEntry | Out-File -FilePath $LogPath -Append -Encoding UTF8
        } catch {
            Write-Warning "Failed to write to log file: $_"
        }
    }
}

function Set-RegistryValue {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory=$true)]
        [string]$RegistryPath,
        
        [Parameter(Mandatory=$true)]
        [string]$ValueName,
        
        [Parameter(Mandatory=$true)]
        [object]$ValueData,
        
        [Parameter(Mandatory=$true)]
        [ValidateSet("REG_DWORD","REG_SZ","REG_MULTI_SZ","REG_EXPAND_SZ","REG_BINARY")]
        [string]$ValueType,
        
        [Parameter(Mandatory=$false)]
        [string]$PolicyName = "Unknown Policy"
    )
    
    # Ensure provider-qualified path (HKLM:\\)
    if ($RegistryPath -notmatch '^[A-Za-z]{2,4}:\\') {
        $RegistryPath = $RegistryPath -replace '^([A-Za-z]{2,4})\\\\', '$1:\\\\'
    }
    
    try {
        # Ensure registry path exists
        if (-not (Test-Path $RegistryPath)) {
            if ($PSCmdlet.ShouldProcess($RegistryPath, "Create Registry Key")) {
                Write-Log "Creating registry key: $RegistryPath"
                New-Item -Path $RegistryPath -Force | Out-Null
            }
        }
        
        # Map REG_* types to PowerShell PropertyType values
        $propType = switch ($ValueType) {
            "REG_DWORD"     { "DWord" }
            "REG_SZ"        { "String" }
            "REG_EXPAND_SZ" { "ExpandString" }
            "REG_MULTI_SZ"  { "MultiString" }
            "REG_BINARY"    { "Binary" }
            default         { "String" }
        }
        
        # Apply the setting using create-or-update pattern
        if ($PSCmdlet.ShouldProcess("$RegistryPath\\$ValueName", "Set Registry Value to $ValueData")) {
            # Check if value exists
            $valueExists = Get-ItemProperty -Path $RegistryPath -Name $ValueName -ErrorAction SilentlyContinue
            
            if ($valueExists) {
                # Value exists - update it (no -Type parameter)
                Set-ItemProperty -Path $RegistryPath -Name $ValueName -Value $ValueData -Force
            } else {
                # Value doesn't exist - create with PropertyType
                New-ItemProperty -Path $RegistryPath -Name $ValueName -Value $ValueData -PropertyType $propType -Force | Out-Null
            }
            
            # Verify the change
            $newValue = Get-ItemPropertyValue -Path $RegistryPath -Name $ValueName -ErrorAction Stop
            if ($newValue -eq $ValueData) {
                Write-Log "✓ Successfully applied: $PolicyName" -Level SUCCESS
                $script:SuccessCount++
                return $true
            } else {
                Write-Log "✗ Verification failed for: $PolicyName (Expected: $ValueData, Got: $newValue)" -Level ERROR
                $script:FailureCount++
                return $false
            }
        } else {
            Write-Log "Would set $RegistryPath\\$ValueName = $ValueData ($ValueType)" -Level INFO
            return $true
        }
        
    } catch {
        Write-Log "✗ Failed to apply $PolicyName - $_" -Level ERROR
        $script:FailureCount++
        return $false
    }
}

function Test-RegistryValue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$RegistryPath,
        
        [Parameter(Mandatory=$true)]
        [string]$ValueName,
        
        [Parameter(Mandatory=$true)]
        [object]$ExpectedValue,
        
        [Parameter(Mandatory=$false)]
        [string]$PolicyName = "Unknown Policy"
    )
    
    try {
        if (-not (Test-Path $RegistryPath)) {
            Write-Log "✗ Registry path does not exist: $RegistryPath" -Level WARNING
            return $false
        }
        
        $currentValue = Get-ItemPropertyValue -Path $RegistryPath -Name $ValueName -ErrorAction SilentlyContinue
        
        if ($currentValue -eq $ExpectedValue) {
            Write-Log "✓ Verified: $PolicyName" -Level SUCCESS
            return $true
        } else {
            Write-Log "✗ Verification failed: $PolicyName (Expected: $ExpectedValue, Current: $currentValue)" -Level WARNING
            return $false
        }
        
    } catch {
        Write-Log "✗ Error verifying $PolicyName: $_" -Level ERROR
        return $false
    }
}

function Invoke-SecurityPolicy {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory=$true)]
        [string]$Section,
        
        [Parameter(Mandatory=$true)]
        [string]$Setting,
        
        [Parameter(Mandatory=$true)]
        [string]$Value,
        
        [Parameter(Mandatory=$false)]
        [string]$PolicyName = "Unknown Policy"
    )
    
    try {
        $randomId = Get-Random
        $secEditFile = "$env:TEMP\\CIS-SecEdit-$randomId.inf"
        $secEditDb = "$env:TEMP\\CIS-SecEdit-$randomId.sdb"
        
        # Create security template
        $secTemplate = @"
[Unicode]
Unicode=yes
[Version]
signature="`$CHICAGO`$"
Revision=1
[System Access]
[Event Audit]
[Registry Values]
[$Section]
$Setting = $Value
"@
        
        if ($PSCmdlet.ShouldProcess($PolicyName, "Apply Security Policy")) {
            $secTemplate | Out-File -FilePath $secEditFile -Encoding Unicode
            
            # Apply security policy with unique DB file
            $result = & secedit.exe /configure /db $secEditDb /cfg $secEditFile /quiet 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                Write-Log "✓ Applied security policy: $PolicyName" -Level SUCCESS
                $script:SuccessCount++
                return $true
            } else {
                Write-Log "✗ Failed to apply security policy: $PolicyName (Exit code: $LASTEXITCODE)" -Level ERROR
                if ($result) {
                    Write-Log "secedit output: $result" -Level ERROR
                }
                $script:FailureCount++
                return $false
            }
        } else {
            Write-Log "Would apply security policy: $PolicyName" -Level INFO
            return $true
        }
        
    } catch {
        Write-Log "✗ Error applying security policy $PolicyName - $_" -Level ERROR
        $script:FailureCount++
        return $false
    } finally {
        if (Test-Path $secEditFile) {
            Remove-Item $secEditFile -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path $secEditDb) {
            Remove-Item $secEditDb -Force -ErrorAction SilentlyContinue
        }
    }
}

function Set-GroupPolicy {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory=$true)]
        [string]$Path,
        
        [Parameter(Mandatory=$true)]
        [string]$Setting,
        
        [Parameter(Mandatory=$true)]
        [string]$Value,
        
        [Parameter(Mandatory=$false)]
        [string]$PolicyName = "Unknown Policy"
    )
    
    # This would use LGPO.exe if available, otherwise fall back to registry
    $lgpoPath = Get-Command "lgpo.exe" -ErrorAction SilentlyContinue
    
    if ($lgpoPath) {
        try {
            if ($PSCmdlet.ShouldProcess($PolicyName, "Apply Group Policy")) {
                # Use LGPO tool
                $tempFile = "$env:TEMP\\gpo-$(Get-Random).txt"
                "$Path\\$Setting`n$Value" | Out-File -FilePath $tempFile
                
                $result = & lgpo.exe /t $tempFile
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Log "✓ Applied group policy: $PolicyName" -Level SUCCESS
                    $script:SuccessCount++
                    return $true
                } else {
                    Write-Log "✗ Failed to apply group policy: $PolicyName" -Level ERROR
                    $script:FailureCount++
                    return $false
                }
            }
        } catch {
            Write-Log "✗ Error applying group policy $PolicyName: $_" -Level ERROR
            $script:FailureCount++
            return $false
        } finally {
            if (Test-Path $tempFile) {
                Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
            }
        }
    } else {
        Write-Log "LGPO.exe not found, skipping group policy: $PolicyName" -Level WARNING
        $script:WarningCount++
        return $false
    }
}'''
    
    def _generate_backup_section(self) -> str:
        """Generate backup section of the script"""
        
        return '''
# ============================================================================
# SYSTEM BACKUP
# ============================================================================

function New-SystemBackup {
    [CmdletBinding(SupportsShouldProcess)]
    param()
    
    if (-not $CreateBackup) {
        Write-Log "Backup creation skipped by user" -Level INFO
        return $true
    }
    
    Write-Log "Creating system backup..." -Level INFO
    
    try {
        # Create backup directory
        if (-not (Test-Path $BackupPath)) {
            if ($PSCmdlet.ShouldProcess($BackupPath, "Create Backup Directory")) {
                New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
                Write-Log "Created backup directory: $BackupPath" -Level INFO
            }
        }
        
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $registryBackup = Join-Path $BackupPath "Registry-Backup-$timestamp.reg"
        $gpoBackup = Join-Path $BackupPath "GPO-Backup-$timestamp"
        $securityBackup = Join-Path $BackupPath "Security-Backup-$timestamp.inf"
        
        # Backup registry
        if ($PSCmdlet.ShouldProcess($registryBackup, "Export Registry")) {
            Write-Log "Backing up registry to: $registryBackup"
            $result = & reg.exe export HKLM $registryBackup /y
            if ($LASTEXITCODE -eq 0) {
                Write-Log "✓ Registry backup completed" -Level SUCCESS
            } else {
                Write-Log "✗ Registry backup failed" -Level ERROR
                return $false
            }
        }
        
        # Backup group policies
        if ($PSCmdlet.ShouldProcess($gpoBackup, "Backup Group Policies")) {
            Write-Log "Backing up group policies to: $gpoBackup"
            try {
                $lgpoPath = Get-Command "lgpo.exe" -ErrorAction SilentlyContinue
                if ($lgpoPath) {
                    & lgpo.exe /b $gpoBackup
                    if ($LASTEXITCODE -eq 0) {
                        Write-Log "✓ Group Policy backup completed" -Level SUCCESS
                    }
                } else {
                    Write-Log "LGPO.exe not found, copying policy files manually" -Level WARNING
                    $policyPath = "$env:SystemRoot\\System32\\GroupPolicy"
                    if (Test-Path $policyPath) {
                        Copy-Item -Path $policyPath -Destination $gpoBackup -Recurse -Force
                        Write-Log "✓ Group Policy files copied" -Level SUCCESS
                    }
                }
            } catch {
                Write-Log "✗ Group Policy backup failed: $_" -Level ERROR
            }
        }
        
        # Backup security settings
        if ($PSCmdlet.ShouldProcess($securityBackup, "Export Security Settings")) {
            Write-Log "Backing up security settings to: $securityBackup"
            try {
                & secedit.exe /export /cfg $securityBackup
                if ($LASTEXITCODE -eq 0) {
                    Write-Log "✓ Security settings backup completed" -Level SUCCESS
                } else {
                    Write-Log "✗ Security settings backup failed" -Level ERROR
                }
            } catch {
                Write-Log "✗ Security settings backup error: $_" -Level ERROR
            }
        }
        
        # Create backup manifest
        $manifest = @{
            "BackupDate" = $timestamp
            "RegistryBackup" = $registryBackup
            "GPOBackup" = $gpoBackup
            "SecurityBackup" = $securityBackup
            "SystemInfo" = @{
                "ComputerName" = $env:COMPUTERNAME
                "OSVersion" = (Get-CimInstance -ClassName Win32_OperatingSystem).Caption
                "PowerShellVersion" = $PSVersionTable.PSVersion.ToString()
            }
        }
        
        $manifestPath = Join-Path $BackupPath "Backup-Manifest-$timestamp.json"
        $manifest | ConvertTo-Json -Depth 3 | Out-File -FilePath $manifestPath -Encoding UTF8
        Write-Log "✓ Backup manifest created: $manifestPath" -Level SUCCESS
        
        Write-Log "System backup completed successfully" -Level SUCCESS
        return $true
        
    } catch {
        Write-Log "✗ System backup failed: $_" -Level ERROR
        return $false
    }
}

# Create system backup before proceeding
if (-not (New-SystemBackup)) {
    Write-Log "Backup creation failed. Stopping deployment for safety." -Level ERROR
    exit 1
}'''
    
    def _generate_policy_application_section(self, research_results: Dict[str, Any]) -> str:
        """Generate policy application section"""
        
        lines = [
            "",
            "# ============================================================================",
            "# POLICY APPLICATION",
            "# ============================================================================",
            "",
            "Write-Log \"Starting CIS policy application...\" -Level INFO",
            ""
        ]
        
        successful_policies = [r for r in research_results.values() if r.success]
        failed_policies = [r for r in research_results.values() if not r.success]
        
        lines.append(f"# Found {len(successful_policies)} policies with implementation details")
        lines.append(f"# {len(failed_policies)} policies require manual research")
        lines.append("")
        
        for policy_id, result in research_results.items():
            if not result.success:
                lines.extend([
                    f"# SKIPPED: {policy_id} - {result.error_message}",
                    ""
                ])
                continue
            
            policy_path = result.policy_path
            lines.extend(self._generate_single_policy_implementation(policy_path))
        
        return "\n".join(lines)
    
    def _generate_single_policy_implementation(self, policy_path: PolicyPath) -> List[str]:
        """Generate implementation for a single policy"""
        
        lines = [
            f"# ----------------------------------------",
            f"# Policy: {policy_path.policy_name}",
            f"# ID: {policy_path.policy_id}",
            f"# Risk Level: {policy_path.risk_level}",
            f"# ----------------------------------------"
        ]
        
        if policy_path.remediation_notes:
            lines.extend([
                f"# Notes: {policy_path.remediation_notes}",
                ""
            ])
        
        # Registry-based implementation
        if policy_path.registry_key and policy_path.registry_value_name:
            lines.extend([
                f"Write-Log \"Applying policy: {policy_path.policy_name}\"",
                f"try {{",
                f"    $success = Set-RegistryValue \\",
                f"        -RegistryPath \"{policy_path.registry_path}\" \\",
                f"        -ValueName \"{policy_path.registry_value_name}\" \\",
                f"        -ValueData {policy_path.enabled_value} \\",
                f"        -ValueType \"{policy_path.registry_value_type}\" \\",
                f"        -PolicyName \"{policy_path.policy_name}\"",
                f"    ",
                f"    if ($success -and {str(policy_path.requires_reboot).lower()}) {{",
                f"        $script:RebootRequired = $true",
                f"        Write-Log \"Policy {policy_path.policy_name} requires system reboot\" -Level WARNING",
                f"    }}",
                f"}} catch {{",
                f"    Write-Log \"Failed to apply {policy_path.policy_name}: $_\" -Level ERROR",
                f"    $script:FailureCount++",
                f"}}",
                ""
            ])
        
        # Security policy implementation
        if policy_path.secedit_section and policy_path.secedit_setting:
            lines.extend([
                f"try {{",
                f"    Invoke-SecurityPolicy \\",
                f"        -Section \"{policy_path.secedit_section}\" \\",
                f"        -Setting \"{policy_path.secedit_setting}\" \\",
                f"        -Value \"{policy_path.enabled_value}\" \\",
                f"        -PolicyName \"{policy_path.policy_name}\"",
                f"}} catch {{",
                f"    Write-Log \"Failed to apply security policy {policy_path.policy_name}: $_\" -Level ERROR",
                f"}}",
                ""
            ])
        
        # Group policy implementation
        if policy_path.gpo_path and policy_path.gpo_setting:
            lines.extend([
                f"try {{",
                f"    Set-GroupPolicy \\",
                f"        -Path \"{policy_path.gpo_path}\" \\",
                f"        -Setting \"{policy_path.gpo_setting}\" \\",
                f"        -Value \"{policy_path.enabled_value}\" \\",
                f"        -PolicyName \"{policy_path.policy_name}\"",
                f"}} catch {{",
                f"    Write-Log \"Failed to apply group policy {policy_path.policy_name}: $_\" -Level ERROR",
                f"}}",
                ""
            ])
        
        # Custom PowerShell command
        if policy_path.powershell_command:
            lines.extend([
                f"try {{",
                f"    Write-Log \"Executing custom command for: {policy_path.policy_name}\"",
                f"    {policy_path.powershell_command}",
                f"    Write-Log \"✓ Custom command completed: {policy_path.policy_name}\" -Level SUCCESS",
                f"}} catch {{",
                f"    Write-Log \"✗ Custom command failed for {policy_path.policy_name}: $_\" -Level ERROR",
                f"}}",
                ""
            ])
        
        return lines
    
    def _generate_verification_section(self, research_results: Dict[str, Any]) -> str:
        """Generate verification section"""
        
        lines = [
            "",
            "# ============================================================================",
            "# POLICY VERIFICATION",
            "# ============================================================================",
            "",
            "if (-not $SkipVerification) {",
            "    Write-Log \"Starting policy verification...\" -Level INFO",
            "    $script:VerificationPassed = 0",
            "    $script:VerificationFailed = 0",
            ""
        ]
        
        for policy_id, result in research_results.items():
            if not result.success:
                continue
            
            policy_path = result.policy_path
            
            if policy_path.verification_command:
                lines.extend([
                    f"    # Verify: {policy_path.policy_name}",
                    f"    try {{",
                    f"        {policy_path.verification_command}",
                    f"        $script:VerificationPassed++",
                    f"    }} catch {{",
                    f"        Write-Log \"Verification failed for {policy_path.policy_name}: $_\" -Level WARNING",
                    f"        $script:VerificationFailed++",
                    f"    }}",
                    ""
                ])
            elif policy_path.registry_key and policy_path.registry_value_name:
                lines.extend([
                    f"    # Verify: {policy_path.policy_name}",
                    f"    $verified = Test-RegistryValue \\",
                    f"        -RegistryPath \"{policy_path.registry_path}\" \\",
                    f"        -ValueName \"{policy_path.registry_value_name}\" \\",
                    f"        -ExpectedValue {policy_path.enabled_value} \\",
                    f"        -PolicyName \"{policy_path.policy_name}\"",
                    f"    ",
                    f"    if ($verified) {{",
                    f"        $script:VerificationPassed++",
                    f"    }} else {{",
                    f"        $script:VerificationFailed++",
                    f"    }}",
                    ""
                ])
        
        lines.extend([
            "    Write-Log \"Verification completed: $script:VerificationPassed passed, $script:VerificationFailed failed\" -Level INFO",
            "} else {",
            "    Write-Log \"Policy verification skipped by user\" -Level INFO",
            "}"
        ])
        
        return "\n".join(lines)
    
    def _generate_rollback_section(self) -> str:
        """Generate rollback section"""
        
        return '''
# ============================================================================
# ROLLBACK FUNCTIONALITY
# ============================================================================

function New-RollbackScript {
    [CmdletBinding()]
    param()
    
    $rollbackScript = @'
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    CIS Policy Rollback Script
    
.DESCRIPTION
    Rolls back CIS policy changes using system backup
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupManifestPath
)

try {
    $manifest = Get-Content $BackupManifestPath | ConvertFrom-Json
    
    Write-Host "Rolling back CIS policy changes..." -ForegroundColor Yellow
    
    # Restore registry
    if (Test-Path $manifest.RegistryBackup) {
        Write-Host "Restoring registry..." -ForegroundColor Cyan
        & reg.exe import $manifest.RegistryBackup
        Write-Host "Registry restored successfully" -ForegroundColor Green
    }
    
    # Restore security settings
    if (Test-Path $manifest.SecurityBackup) {
        Write-Host "Restoring security settings..." -ForegroundColor Cyan
        & secedit.exe /configure /db "$env:TEMP\\rollback.sdb" /cfg $manifest.SecurityBackup /quiet
        Write-Host "Security settings restored successfully" -ForegroundColor Green
    }
    
    Write-Host "Rollback completed successfully" -ForegroundColor Green
    Write-Host "System reboot recommended" -ForegroundColor Yellow
    
} catch {
    Write-Error "Rollback failed: $_"
    exit 1
}
'@
    
    $rollbackPath = Join-Path $BackupPath "Rollback-CISPolicies.ps1"
    $rollbackScript | Out-File -FilePath $rollbackPath -Encoding UTF8
    Write-Log "Rollback script created: $rollbackPath" -Level INFO
}

# Create rollback script
New-RollbackScript'''
    
    def _generate_script_footer(self) -> str:
        """Generate script footer with summary and completion"""
        
        return '''
# ============================================================================
# DEPLOYMENT SUMMARY
# ============================================================================

$script:EndTime = Get-Date
$script:Duration = $script:EndTime - $script:StartTime

Write-Host ""
Write-Host "=== CIS Benchmark Deployment Summary ===" -ForegroundColor Cyan
Write-Host "Started: $($script:StartTime)" -ForegroundColor White
Write-Host "Completed: $($script:EndTime)" -ForegroundColor White
Write-Host "Duration: $($script:Duration.ToString('hh\\:mm\\:ss'))" -ForegroundColor White
Write-Host ""
Write-Host "Results:" -ForegroundColor Yellow
Write-Host "  ✓ Successful: $script:SuccessCount" -ForegroundColor Green
Write-Host "  ✗ Failed: $script:FailureCount" -ForegroundColor Red
Write-Host "  ⚠ Warnings: $script:WarningCount" -ForegroundColor Yellow
Write-Host ""

if ($script:RebootRequired) {
    Write-Host "⚠ SYSTEM REBOOT REQUIRED ⚠" -ForegroundColor Red -BackgroundColor Yellow
    Write-Host "Some policies require a system restart to take effect." -ForegroundColor Yellow
    
    if ($ForceReboot) {
        Write-Host "Initiating system reboot in 30 seconds..." -ForegroundColor Red
        Write-Host "Press Ctrl+C to cancel" -ForegroundColor Yellow
        Start-Sleep -Seconds 30
        Restart-Computer -Force
    } else {
        Write-Host "Please restart the system manually when convenient." -ForegroundColor Yellow
    }
}

# Final status
if ($script:FailureCount -eq 0) {
    Write-Log "CIS Benchmark deployment completed successfully" -Level SUCCESS
    exit 0
} else {
    Write-Log "CIS Benchmark deployment completed with $script:FailureCount failures" -Level ERROR
    exit 1
}'''