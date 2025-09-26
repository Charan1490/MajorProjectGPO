# LGPO.exe Installation Instructions

## Overview
LGPO.exe is a free utility from Microsoft that enables local management of Group Policy Objects. It's essential for the full functionality of the CIS GPO Compliance Tool's deployment module.

## Download and Installation

### Step 1: Download LGPO.exe
1. Visit the official Microsoft download page:
   ```
   https://www.microsoft.com/en-us/download/details.aspx?id=55319
   ```

2. Click the "Download" button

3. Select "LGPO.zip" from the list and click "Next"

4. The download should start automatically

### Step 2: Extract and Install
1. Extract the downloaded `LGPO.zip` file
2. Copy `LGPO.exe` to one of these locations:
   - `backend/tools/LGPO.exe` (recommended)
   - `backend/LGPO.exe`
   - Any directory in your system PATH

### Step 3: Verify Installation
Run the installation helper script:
```batch
cd backend/tools
install_lgpo.bat
```

Or verify manually:
```batch
LGPO.exe /?
```

## Without LGPO.exe

The deployment tool will work without LGPO.exe but with reduced functionality:

### What Still Works:
- ✅ Registry file (.reg) generation
- ✅ PowerShell script generation  
- ✅ Batch script generation
- ✅ Documentation generation
- ✅ Package validation
- ✅ Deployment verification

### What's Limited:
- ❌ No .pol file generation (uses .reg instead)
- ❌ No LGPO-specific validation
- ❌ Manual registry import required

### Registry Import Process:
1. Double-click the generated `.reg` files
2. Confirm the registry import prompts
3. Reboot the system if required

## Usage in Deployment Tool

Once installed, LGPO.exe will be automatically detected and used for:
- Converting policies to `.pol` format
- Validating policy file structure  
- Creating Group Policy backups
- Applying policies via command line

## Troubleshooting

### LGPO.exe not recognized
- Ensure LGPO.exe is in the correct directory
- Check file permissions (should be executable)
- Verify Windows version compatibility

### Access Denied errors
- Run command prompt as Administrator
- Ensure proper NTFS permissions on LGPO.exe

### Validation failures
- Redownload LGPO.exe from Microsoft
- Check for antivirus interference
- Verify file integrity (not corrupted)

## Alternative Tools

While LGPO.exe is recommended, these alternatives can be used:
- **Group Policy Management Console** (GPMC) - For domain environments
- **Local Security Policy Editor** (secpol.msc) - For local security settings
- **Registry Editor** (regedit.exe) - For direct registry modification
- **PowerShell Group Policy Module** - For scripted policy management

However, these don't provide the same level of automation and offline capability as LGPO.exe.

## Legal and Licensing

LGPO.exe is provided by Microsoft as a free utility. By downloading and using LGPO.exe, you agree to Microsoft's licensing terms. The CIS GPO Compliance Tool does not redistribute LGPO.exe - users must download it directly from Microsoft.

## Support

For LGPO.exe-specific issues, consult:
- Microsoft's official documentation
- Windows Group Policy documentation  
- Microsoft TechNet forums

For integration issues with the CIS GPO Compliance Tool, check the tool's documentation and logs.