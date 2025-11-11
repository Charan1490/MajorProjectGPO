#Requires -RunAsAdministrator
<#
.SYNOPSIS
    CIS Benchmark Compliance Deployment Script

.DESCRIPTION
    Applies CIS benchmark policies to Windows 11 systems.
    This script implements actual registry changes, Group Policy modifications,
    and security settings to achieve CIS compliance.

.PARAMETER WhatIf
    Preview changes without applying them

.PARAMETER CreateBackup
    Create system backup before applying changes (default: true)

.PARAMETER BackupPath
    Path to store backup files (default: C:\CIS-Backup)

.PARAMETER LogPath
    Path to log file (default: C:\CIS-Deployment.log)

.PARAMETER SkipVerification
    Skip policy verification after application

.PARAMETER ForceReboot
    Force system reboot if required by policies

.EXAMPLE
    .\Deploy-CISCompliance.ps1
    .\Deploy-CISCompliance.ps1 -WhatIf
    .\Deploy-CISCompliance.ps1 -BackupPath "D:\Backups"

.NOTES
    Generated: 2025-11-11T12:37:29.619406
    Target OS: Windows 11
    
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
    [string]$BackupPath = "C:\CIS-Backup",
    
    [Parameter(Mandatory=$false)]
    [string]$LogPath = "C:\CIS-Deployment.log",
    
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
Write-Host "Target OS: Windows 11" -ForegroundColor Yellow
if ($WhatIf) {
    Write-Host "MODE: PREVIEW ONLY (WhatIf)" -ForegroundColor Magenta
}
Write-Host ""

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
    
    # Ensure provider-qualified path (examples: HKLM:\ or HKEY_LOCAL_MACHINE:\)
    if ($RegistryPath -notmatch '^[A-Za-z0-9_]+:\\') {
        # convert e.g. "HKLM\SOFTWARE\..." or "HKEY_LOCAL_MACHINE\SOFTWARE\..." -> "HKLM:\SOFTWARE\..."
        $RegistryPath = $RegistryPath -replace '^([A-Za-z0-9_]+)\\', '$1:\\'
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
        if ($PSCmdlet.ShouldProcess("$RegistryPath\$ValueName", "Set Registry Value to $ValueData")) {
            # Check if value exists (explicit property presence test)
            $valueObj = Get-ItemProperty -Path $RegistryPath -ErrorAction SilentlyContinue
            $valueExists = $false
            if ($null -ne $valueObj) {
                $valueExists = $valueObj.PSObject.Properties.Name -contains $ValueName
            }
            
            if ($valueExists) {
                # Value exists - update it (no -Type parameter)
                Set-ItemProperty -Path $RegistryPath -Name $ValueName -Value $ValueData -Force
            } else {
                # Value doesn't exist - create with PropertyType
                New-ItemProperty -Path $RegistryPath -Name $ValueName -Value $ValueData -PropertyType $propType -Force | Out-Null
            }
            
            # Verify the change
            $newValue = Get-ItemPropertyValue -Path $RegistryPath -Name $ValueName -ErrorAction Stop
            
            # Coerce types for comparison (handle DWORD vs string)
            switch ($propType) {
                "DWord" {
                    $compareOK = ([int]$newValue -eq [int]$ValueData)
                }
                "ExpandString" { $compareOK = ($newValue -eq $ValueData) }
                "MultiString" {
                    # normalize both sides to arrays of strings for comparison
                    $left = if ($newValue -is [System.Array]) { $newValue } elseif ($null -eq $newValue) { @() } else { @([string]$newValue) }
                    $right = if ($ValueData -is [System.Array]) { $ValueData } elseif ($null -eq $ValueData) { @() } else { @([string]$ValueData) }

                    # compare lengths and elements (order-sensitive)
                    $compareOK = ($left.Length -eq $right.Length) -and (($left -join ",") -eq ($right -join ","))
                }
                default { $compareOK = ($newValue -eq $ValueData) }
            }
            
            if ($compareOK) {
                Write-Log "✓ Successfully applied: $PolicyName" -Level SUCCESS
                $script:SuccessCount++
                return $true
            } else {
                Write-Log "✗ Verification failed for: $PolicyName (Expected: $ValueData, Got: $newValue)" -Level ERROR
                $script:FailureCount++
                return $false
            }
        } else {
            Write-Log "Would set $RegistryPath\$ValueName = $ValueData ($ValueType)" -Level INFO
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
        $secEditFile = "$env:TEMP\CIS-SecEdit-$randomId.inf"
        $secEditDb = "$env:TEMP\CIS-SecEdit-$randomId.sdb"
        
        # Create security template with proper ordering
        # ensure value is quoted if it contains spaces or is not purely numeric
        $infValue = if ($Value -match '^\d+$') { $Value } else { '"' + ($Value -replace '"','\"') + '"' }
        $secTemplate = @'
[Unicode]
Unicode=yes
[Version]
signature="$CHICAGO$"
Revision=1
'@ + "`n[$Section]`n$Setting = $infValue`n"
        
        if ($PSCmdlet.ShouldProcess($PolicyName, "Apply Security Policy")) {
            $secTemplate | Out-File -FilePath $secEditFile -Encoding Unicode
            
            # Apply security policy with unique DB file
            $result = & secedit.exe /configure /db $secEditDb /cfg $secEditFile /quiet 2>&1
            
            # Always log exit code for troubleshooting
            Write-Log "secedit exit code: $LASTEXITCODE" -Level INFO -NoConsole
            if ($result) {
                Write-Log "secedit output: $result" -Level INFO -NoConsole
            }
            
            if ($LASTEXITCODE -eq 0) {
                Write-Log "✓ Applied security policy: $PolicyName" -Level SUCCESS
                $script:SuccessCount++
                return $true
            } else {
                Write-Log "✗ Failed to apply security policy: $PolicyName (Exit code: $LASTEXITCODE)" -Level ERROR
                if ($result) {
                    Write-Log "secedit error: $result" -Level ERROR
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
    
    # Note: LGPO.exe requires specific import formats (PolicyDefinitions XML or Registry.pol)
    # For standalone Pro machines, registry-based policy application is more reliable
    # Most policies are already applied via Set-RegistryValue
    
    $lgpoPath = Get-Command "lgpo.exe" -ErrorAction SilentlyContinue
    
    if ($lgpoPath) {
        Write-Log "LGPO.exe found but requires proper policy template format - skipping direct LGPO call" -Level INFO -NoConsole
        Write-Log "Policy '$PolicyName' should be applied via registry (already handled)" -Level INFO -NoConsole
        # Don't increment warning count as this is expected behavior
        return $true
    } else {
        Write-Log "LGPO.exe not found - using registry-based policy application (standard)" -Level INFO -NoConsole
        # This is the expected path for most deployments
        return $true
    }
}

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
        
        # Backup registry (specific keys we'll modify)
        if ($PSCmdlet.ShouldProcess($registryBackup, "Export Registry")) {
            Write-Log "Backing up registry keys to: $registryBackup"
            
            # Create a combined registry export of all keys we'll modify
            $keysToBackup = @(
                "HKLM\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters",
                "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                "HKLM\SOFTWARE\Policies\Microsoft\Windows\Personalization"
            )
            
            $backupSuccess = $true
            $registryFiles = @()
            foreach ($key in $keysToBackup) {
                $safeKeyName = ($key -replace '\\|:','_')
                $keyFile = $registryBackup -replace '\.reg$', "-$safeKeyName.reg"
                $result = & reg.exe export $key $keyFile /y 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Log "✓ Backed up: $key" -Level INFO -NoConsole
                    $registryFiles += $keyFile
                } else {
                    Write-Log "⚠ Could not backup: $key (may not exist yet or permission issue). reg.exe output: $result" -Level WARNING -NoConsole
                    $backupSuccess = $false
                }
            }
            
            if (-not $backupSuccess) {
                Write-Log "✗ One or more registry key backups failed." -Level ERROR
                # Decide: abort deployment or continue. To abort, uncomment next line:
                # return $false
                # Continue anyway as keys may not exist yet (will be created by script)
            } else {
                Write-Log "✓ Registry backup completed" -Level SUCCESS
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
                    $policyPath = "$env:SystemRoot\System32\GroupPolicy"
                    if (Test-Path $policyPath) {
                        if (-not (Test-Path $gpoBackup)) {
                            New-Item -ItemType Directory -Path $gpoBackup -Force | Out-Null
                        }
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
            "RegistryBackups" = $registryFiles
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
}

# ============================================================================
# POLICY APPLICATION
# ============================================================================

Write-Log "Starting CIS policy application..." -Level INFO

# Found 3 policies with implementation details
# 0 policies require manual research

# ----------------------------------------
# Policy: Ensure 'Minimum password age' is set to '1 or more day(s)'
# ID: 1.1.1
# Risk Level: Low
# ----------------------------------------
# Notes: Affects password policy domain-wide if system is domain controller

Write-Log "Applying policy: Ensure 'Minimum password age' is set to '1 or more day(s)'"
try {
    $success = Set-RegistryValue \
        -RegistryPath "HKLM:\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters" \
        -ValueName "MinimumPasswordAge" \
        -ValueData 1 \
        -ValueType "REG_DWORD" \
        -PolicyName "Ensure 'Minimum password age' is set to '1 or more day(s)'"
    
    # Set this per-policy depending on whether it actually needs a reboot
    $policyRequiresReboot = $false  # This policy does not require reboot
    
    if ($success -and $policyRequiresReboot) {
        $script:RebootRequired = $true
        Write-Log "Policy Ensure 'Minimum password age' is set to '1 or more day(s)' requires system reboot" -Level WARNING
    }
} catch {
    Write-Log "Failed to apply Ensure 'Minimum password age' is set to '1 or more day(s)': $_" -Level ERROR
    $script:FailureCount++
}

try {
    Invoke-SecurityPolicy \
        -Section "System Access" \
        -Setting "MinimumPasswordAge" \
        -Value "1" \
        -PolicyName "Ensure 'Minimum password age' is set to '1 or more day(s)'"
} catch {
    Write-Log "Failed to apply security policy Ensure 'Minimum password age' is set to '1 or more day(s)': $_" -Level ERROR
}

try {
    Set-GroupPolicy \
        -Path "Computer Configuration\Policies\Windows Settings\Security Settings\Account Policies\Password Policy" \
        -Setting "Minimum password age" \
        -Value "1" \
        -PolicyName "Ensure 'Minimum password age' is set to '1 or more day(s)'"
} catch {
    Write-Log "Failed to apply group policy Ensure 'Minimum password age' is set to '1 or more day(s)': $_" -Level ERROR
}

# ----------------------------------------
# Policy: Ensure 'Accounts: Block Microsoft accounts' is set to 'Users can't add or log on with Microsoft accounts'
# ID: 2.3.1.1
# Risk Level: Medium
# ----------------------------------------
# Notes: Prevents users from adding Microsoft accounts for authentication

Write-Log "Applying policy: Ensure 'Accounts: Block Microsoft accounts' is set to 'Users can't add or log on with Microsoft accounts'"
try {
    $success = Set-RegistryValue \
        -RegistryPath "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" \
        -ValueName "NoConnectedUser" \
        -ValueData 3 \
        -ValueType "REG_DWORD" \
        -PolicyName "Ensure 'Accounts: Block Microsoft accounts' is set to 'Users can't add or log on with Microsoft accounts'"
    
    # Set this per-policy depending on whether it actually needs a reboot
    $policyRequiresReboot = $false  # This policy does not require reboot
    
    if ($success -and $policyRequiresReboot) {
        $script:RebootRequired = $true
        Write-Log "Policy Ensure 'Accounts: Block Microsoft accounts' is set to 'Users can't add or log on with Microsoft accounts' requires system reboot" -Level WARNING
    }
} catch {
    Write-Log "Failed to apply Ensure 'Accounts: Block Microsoft accounts' is set to 'Users can't add or log on with Microsoft accounts': $_" -Level ERROR
    $script:FailureCount++
}

try {
    Set-GroupPolicy \
        -Path "Computer Configuration\Policies\Windows Settings\Security Settings\Local Policies\Security Options" \
        -Setting "Accounts: Block Microsoft accounts" \
        -Value "3" \
        -PolicyName "Ensure 'Accounts: Block Microsoft accounts' is set to 'Users can't add or log on with Microsoft accounts'"
} catch {
    Write-Log "Failed to apply group policy Ensure 'Accounts: Block Microsoft accounts' is set to 'Users can't add or log on with Microsoft accounts': $_" -Level ERROR
}

# ----------------------------------------
# Policy: Ensure 'Prevent enabling lock screen camera' is set to 'Enabled'
# ID: 18.1.1.1
# Risk Level: Medium
# ----------------------------------------
# Notes: Prevents camera access from lock screen for privacy

Write-Log "Applying policy: Ensure 'Prevent enabling lock screen camera' is set to 'Enabled'"
try {
    $success = Set-RegistryValue \
        -RegistryPath "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization" \
        -ValueName "NoLockScreenCamera" \
        -ValueData 1 \
        -ValueType "REG_DWORD" \
        -PolicyName "Ensure 'Prevent enabling lock screen camera' is set to 'Enabled'"
    
    # Set this per-policy depending on whether it actually needs a reboot
    $policyRequiresReboot = $false  # This policy does not require reboot
    
    if ($success -and $policyRequiresReboot) {
        $script:RebootRequired = $true
        Write-Log "Policy Ensure 'Prevent enabling lock screen camera' is set to 'Enabled' requires system reboot" -Level WARNING
    }
} catch {
    Write-Log "Failed to apply Ensure 'Prevent enabling lock screen camera' is set to 'Enabled': $_" -Level ERROR
    $script:FailureCount++
}

try {
    Set-GroupPolicy \
        -Path "Computer Configuration\Administrative Templates\Control Panel\Personalization" \
        -Setting "Prevent enabling lock screen camera" \
        -Value "1" \
        -PolicyName "Ensure 'Prevent enabling lock screen camera' is set to 'Enabled'"
} catch {
    Write-Log "Failed to apply group policy Ensure 'Prevent enabling lock screen camera' is set to 'Enabled': $_" -Level ERROR
}


# ============================================================================
# POLICY VERIFICATION
# ============================================================================

if (-not $SkipVerification) {
    Write-Log "Starting policy verification..." -Level INFO
    $script:VerificationPassed = 0
    $script:VerificationFailed = 0

    # Verify: Ensure 'Minimum password age' is set to '1 or more day(s)'
    try {
        $value = Get-ItemPropertyValue -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters' -Name 'MinimumPasswordAge' -ErrorAction SilentlyContinue
        if ($value -ge 1) { Write-Log "✓ Minimum password age verified" -Level SUCCESS; $script:VerificationPassed++; } else { Write-Log "✗ Minimum password age verification failed" -Level ERROR; $script:VerificationFailed++; }
    } catch {
        Write-Log "Verification failed for Ensure 'Minimum password age' is set to '1 or more day(s)': $_" -Level WARNING
        $script:VerificationFailed++
    }

    # Verify: Ensure 'Accounts: Block Microsoft accounts' is set to 'Users can't add or log on with Microsoft accounts'
    try {
        $value = Get-ItemPropertyValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -Name 'NoConnectedUser' -ErrorAction SilentlyContinue
        if ($value -eq 3) { Write-Log "✓ Microsoft accounts properly blocked" -Level SUCCESS; $script:VerificationPassed++; } else { Write-Log "✗ Microsoft accounts blocking verification failed" -Level ERROR; $script:VerificationFailed++; }
    } catch {
        Write-Log "Verification failed for Ensure 'Accounts: Block Microsoft accounts' is set to 'Users can't add or log on with Microsoft accounts': $_" -Level WARNING
        $script:VerificationFailed++
    }

    # Verify: Ensure 'Prevent enabling lock screen camera' is set to 'Enabled'
    try {
        $value = Get-ItemPropertyValue -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization' -Name 'NoLockScreenCamera' -ErrorAction SilentlyContinue
        if ($value -eq 1) { Write-Log "✓ Lock screen camera prevention verified" -Level SUCCESS; $script:VerificationPassed++; } else { Write-Log "✗ Lock screen camera prevention verification failed" -Level ERROR; $script:VerificationFailed++; }
    } catch {
        Write-Log "Verification failed for Ensure 'Prevent enabling lock screen camera' is set to 'Enabled': $_" -Level WARNING
        $script:VerificationFailed++
    }

    Write-Log "Verification completed: $script:VerificationPassed passed, $script:VerificationFailed failed" -Level INFO
} else {
    Write-Log "Policy verification skipped by user" -Level INFO
}

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
    
    # Restore registry (handle both single file and array of files)
    $registryBackups = $manifest.RegistryBackups
    if ($null -eq $registryBackups) {
        $registryBackups = @($manifest.RegistryBackup)  # Fallback for old format
    }
    
    foreach ($backupFile in $registryBackups) {
        if (Test-Path $backupFile) {
            Write-Host "Restoring registry from: $backupFile" -ForegroundColor Cyan
            & reg.exe import $backupFile
        }
    }
    Write-Host "Registry restored successfully" -ForegroundColor Green
    
    # Restore security settings
    if (Test-Path $manifest.SecurityBackup) {
        Write-Host "Restoring security settings..." -ForegroundColor Cyan
        & secedit.exe /configure /db "$env:TEMP\rollback.sdb" /cfg $manifest.SecurityBackup /quiet
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
New-RollbackScript

# ============================================================================
# DEPLOYMENT SUMMARY
# ============================================================================

$script:EndTime = Get-Date
$script:Duration = $script:EndTime - $script:StartTime

Write-Host ""
Write-Host "=== CIS Benchmark Deployment Summary ===" -ForegroundColor Cyan
Write-Host "Started: $($script:StartTime)" -ForegroundColor White
Write-Host "Completed: $($script:EndTime)" -ForegroundColor White
Write-Host "Duration: $($script:Duration.ToString('hh\:mm\:ss'))" -ForegroundColor White
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
}