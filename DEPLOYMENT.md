# Deployment Module Documentation

## Overview

The Deployment Module (Step 4) of the CIS GPO Compliance Tool provides comprehensive offline deployment capabilities for Windows Group Policy Objects (GPO). This module packages finalized policy templates into portable, self-contained deployment packages that can be applied to standalone or air-gapped Windows systems without network connectivity.

## Key Features

### 🎯 Core Capabilities
- **Offline-First Design**: No network connectivity required for deployment
- **Multiple Export Formats**: LGPO .pol files, Registry .reg files, PowerShell scripts
- **Automated Scripts**: Self-executing deployment, verification, and rollback scripts
- **Cross-Platform Support**: Windows 10/11, Server 2019/2022 compatibility
- **Integrity Validation**: Checksums and validation for all package components

### 📦 Package Components
- **Policy Files**: LGPO-compatible .pol files and registry .reg files  
- **Deployment Scripts**: PowerShell and batch scripts for automated deployment
- **Verification Tools**: Scripts to validate applied policies
- **Rollback Support**: System backup and policy reversal capabilities
- **Documentation**: Complete deployment instructions and troubleshooting guides

## Architecture

### Backend Components

#### 1. Deployment Manager (`deployment_manager.py`)
- **Package Creation**: Converts dashboard policies to deployment packages
- **Format Conversion**: Generates LGPO, registry, and script formats
- **Validation Engine**: Ensures package integrity and completeness
- **Job Management**: Handles async package creation with progress tracking

#### 2. LGPO Utilities (`lgpo_utils.py`)
- **LGPO Integration**: Works with Microsoft's LGPO.exe tool
- **Policy Conversion**: Transforms policies to LGPO-compatible formats
- **Backup Management**: Creates and restores Group Policy backups
- **Format Validation**: Validates generated policy files

#### 3. Data Models (`models_deployment.py`)
- **Package Structures**: Comprehensive data models for deployment packages
- **Configuration Objects**: Export and script configuration management
- **Validation Results**: Detailed validation and error reporting
- **Job Tracking**: Progress monitoring for long-running operations

### Frontend Components

#### 1. Deployment Manager UI (`DeploymentManager.js`)
- **Package Creation Wizard**: Step-by-step package creation process
- **Status Dashboard**: Real-time monitoring of package status
- **Download Management**: Secure package download and validation
- **Progress Tracking**: Live updates during package creation

### CLI Interface

#### 1. Command Line Tool (`deployment_cli.py`)
- **Interactive Wizard**: Guided package creation process
- **Batch Operations**: Scriptable package management
- **Status Monitoring**: Real-time progress tracking
- **Package Management**: Create, list, delete, and validate packages

## Usage Guide

### Web Interface Usage

#### Creating a Deployment Package

1. **Access the Deployment Manager**
   - Navigate to the "Deployment Manager" tab in the web interface
   - Click "Create Package" to start the wizard

2. **Basic Configuration**
   - Enter package name and description
   - Select target Windows version
   - Choose deployment scope

3. **Policy Selection**
   - Select policies by:
     - All available policies
     - Specific policy groups
     - Policy tags
     - Individual policy IDs

4. **Export Format Configuration**
   - **LGPO .pol files**: For Group Policy import (recommended)
   - **Registry .reg files**: For direct registry import
   - **PowerShell scripts**: For automated deployment
   - **Batch files**: Simple wrapper scripts

5. **Script Configuration**
   - Enable PowerShell and batch script generation
   - Configure backup, verification, and rollback options
   - Set administrative privilege requirements

6. **Package Creation**
   - Review configuration and create package
   - Monitor build progress in real-time
   - Download completed package

### CLI Usage

#### Interactive Package Creation
```bash
cd backend
python deployment_cli.py create
```

#### List All Packages
```bash
python deployment_cli.py list
```

#### View Package Details
```bash
python deployment_cli.py show <package_id>
```

#### Check LGPO Status
```bash
python deployment_cli.py lgpo
```

### API Usage

#### Create Package via API
```bash
curl -X POST "http://localhost:8000/deployment/packages" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CIS Compliance Package",
    "description": "Windows 10 Enterprise compliance policies",
    "target_os": "windows_10_enterprise",
    "include_formats": ["lgpo_pol", "registry_reg", "powershell_ps1"],
    "include_scripts": true,
    "create_backup": true
  }'
```

#### Build Package
```bash
curl -X POST "http://localhost:8000/deployment/packages/{package_id}/build"
```

#### Download Package
```bash
curl -X POST "http://localhost:8000/deployment/packages/{package_id}/download" \
  --output deployment-package.zip
```

## Deployment Package Structure

### Package Contents

```
deployment-package/
├── README.txt                 # Deployment instructions
├── MANIFEST.json             # Package manifest and metadata
├── Deploy-CISCompliance.bat  # Batch wrapper script
├── Deploy-CISCompliance.ps1  # Main PowerShell deployment script
├── Verify-CISCompliance.ps1  # Verification script
├── Rollback-CISCompliance.ps1 # Rollback script
├── Machine.pol               # Computer configuration policies
├── User.pol                  # User configuration policies
├── CISCompliance.reg         # Registry import file
└── CISCompliance.inf         # Security template file
```

### Target Machine Deployment

#### Prerequisites on Target Machine
- Windows Administrator privileges
- PowerShell 3.0 or later (for automated deployment)
- No external network connectivity required

#### Deployment Options

##### Option 1: Automated Deployment (Recommended)
1. Extract deployment package to local directory
2. Right-click `Deploy-CISCompliance.bat` and select "Run as administrator"
3. Follow on-screen prompts
4. Review deployment log for any issues
5. Reboot system when prompted

##### Option 2: PowerShell Deployment
```powershell
# Open PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\Deploy-CISCompliance.ps1

# With options
.\Deploy-CISCompliance.ps1 -WhatIf  # Preview changes
.\Deploy-CISCompliance.ps1 -Force   # Skip confirmations
```

##### Option 3: Manual Registry Import
```cmd
# Import registry settings
regedit /s CISCompliance.reg

# Apply LGPO files (if LGPO.exe available)
LGPO.exe /m Machine.pol
LGPO.exe /u User.pol
```

#### Post-Deployment Verification
```powershell
# Run verification script
.\Verify-CISCompliance.ps1

# Check specific settings
gpresult /r
```

#### Rollback Process
```powershell
# Locate backup directory created during deployment
.\Rollback-CISCompliance.ps1 -BackupPath "C:\Temp\CIS-Backup-YYYYMMDD-HHMMSS"
```

## LGPO.exe Integration

### About LGPO.exe
LGPO.exe is a free utility from Microsoft for managing Local Group Policy Objects. It's essential for full deployment functionality.

### Installation
1. Download from: https://www.microsoft.com/en-us/download/details.aspx?id=55319
2. Extract LGPO.exe to the `tools/` directory
3. Verify installation: `LGPO.exe /?`

### Without LGPO.exe
The tool gracefully degrades functionality when LGPO.exe is unavailable:
- Generates registry (.reg) files instead of policy (.pol) files
- Provides manual import instructions
- Maintains full script generation capabilities

## Configuration Options

### Export Formats

#### LGPO Policy Files (.pol)
- **Purpose**: Group Policy import using LGPO.exe
- **Scope**: Separate files for Computer and User configurations
- **Advantages**: Native Group Policy format, reversible
- **Requirements**: LGPO.exe on target machine

#### Registry Files (.reg)
- **Purpose**: Direct registry import
- **Scope**: Combined Computer and User settings
- **Advantages**: No additional tools required
- **Limitations**: Manual rollback required

#### PowerShell Scripts (.ps1)
- **Purpose**: Automated policy application
- **Features**: Logging, backup, verification, error handling
- **Advantages**: Full automation, detailed logging
- **Requirements**: PowerShell 3.0+, Administrator privileges

#### Security Templates (.inf)
- **Purpose**: Security policy configuration
- **Scope**: Security-related settings only
- **Usage**: Import via Security Configuration Manager
- **Format**: Standard Windows security template format

### Script Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `use_powershell` | Generate PowerShell deployment scripts | `true` |
| `use_batch` | Generate batch wrapper scripts | `true` |
| `require_admin` | Require administrator privileges | `true` |
| `create_backup` | Create system backup before deployment | `true` |
| `verify_before_apply` | Verify settings before applying | `true` |
| `log_changes` | Log all policy changes | `true` |
| `rollback_support` | Include rollback capabilities | `true` |

## Error Handling and Troubleshooting

### Common Issues

#### Package Creation Fails
```
Error: No policies found for deployment
Solution: Ensure policies exist in dashboard and selection criteria are correct
```

#### LGPO.exe Not Found
```
Warning: LGPO.exe not available. Registry files will be generated instead.
Solution: Download and install LGPO.exe from Microsoft
```

#### Deployment Script Fails
```
Error: Access denied
Solution: Ensure script is run as Administrator
```

#### Policy Validation Errors
```
Error: Invalid policy file format
Solution: Recreate package with fresh policy data
```

### Validation Checks

The deployment manager performs comprehensive validation:
- **Policy Integrity**: Ensures all selected policies are valid
- **Format Compatibility**: Validates export format requirements
- **Script Syntax**: Checks generated script syntax
- **File Checksums**: Verifies package file integrity
- **Configuration Completeness**: Ensures all required fields are present

### Logging and Diagnostics

#### Backend Logging
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### PowerShell Script Logging
```powershell
# Logs are automatically created at:
C:\Temp\CIS-Deployment-YYYYMMDD-HHMMSS.log
```

#### Deployment Status Tracking
- Real-time progress monitoring via web interface
- Detailed job status via API endpoints
- Comprehensive error messages with suggested solutions

## Best Practices

### Package Creation
1. **Test in Development**: Always test packages in non-production environments
2. **Use Descriptive Names**: Include OS version and purpose in package names
3. **Document Changes**: Provide detailed descriptions for all packages
4. **Regular Validation**: Validate packages before deployment

### Deployment Process
1. **Create Backups**: Always create system backups before deployment
2. **Staged Deployment**: Deploy to small groups before organization-wide rollout
3. **Monitor Systems**: Check system behavior after deployment
4. **Keep Rollback Ready**: Maintain access to rollback procedures

### Security Considerations
1. **Administrative Access**: Ensure deployment scripts run with appropriate privileges
2. **Package Integrity**: Verify package checksums before deployment
3. **Audit Trail**: Maintain logs of all deployment activities
4. **Access Control**: Restrict access to deployment packages and tools

## API Reference

### Endpoints

#### Package Management
- `GET /deployment/packages` - List all packages
- `POST /deployment/packages` - Create new package
- `GET /deployment/packages/{id}` - Get package details
- `DELETE /deployment/packages/{id}` - Delete package
- `POST /deployment/packages/{id}/build` - Build package
- `POST /deployment/packages/{id}/download` - Download package
- `POST /deployment/packages/{id}/validate` - Validate package

#### System Information
- `GET /deployment/statistics` - Get deployment statistics
- `GET /deployment/windows-versions` - List supported OS versions
- `GET /deployment/package-formats` - List available export formats
- `GET /deployment/lgpo/status` - Check LGPO.exe availability

#### Job Management
- `GET /deployment/jobs/{id}` - Get job status and progress

### Response Format
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    "package_id": "uuid",
    "status": "completed",
    "additional_data": {}
  }
}
```

## Integration Points

### Dashboard Integration
- **Policy Selection**: Leverages dashboard policy grouping and tagging
- **Status Synchronization**: Updates deployment status in dashboard
- **History Tracking**: Records deployment activities in policy history

### Template System Integration
- **Policy Source**: Uses templates as source for deployment policies
- **Validation**: Ensures deployed policies match template definitions
- **Version Control**: Tracks template versions in deployment packages

## Future Enhancements

### Planned Features
1. **Compliance Testing**: Automated compliance verification after deployment
2. **Remediation Scripts**: Automated policy correction capabilities
3. **Centralized Management**: Multi-machine deployment coordination
4. **Advanced Scheduling**: Time-based and condition-based deployment
5. **Reporting Dashboard**: Comprehensive deployment analytics

### Extension Points
- **Custom Export Formats**: Plugin system for additional export formats
- **Third-party Tools**: Integration with other policy management tools
- **Cloud Connectors**: Secure cloud-based package distribution
- **Mobile Management**: Integration with mobile device management

## Support and Maintenance

### Regular Maintenance
- Monitor package storage space usage
- Clean up old/unused deployment packages
- Update LGPO.exe when Microsoft releases new versions
- Review and update deployment documentation

### Troubleshooting Resources
- Built-in validation and error reporting
- Comprehensive logging at all levels
- CLI tools for package inspection and repair
- Web interface for real-time monitoring

### Getting Help
- Check validation results for specific error messages
- Review deployment logs for detailed error information
- Use CLI tools for debugging package issues
- Consult Microsoft LGPO documentation for advanced scenarios

## Conclusion

The Deployment Module provides a complete solution for offline GPO deployment, enabling organizations to maintain CIS compliance in air-gapped environments. With support for multiple export formats, comprehensive automation, and robust error handling, it serves as the final step in the CIS GPO Compliance Tool workflow, delivering policies from analysis through deployment to Windows endpoints.