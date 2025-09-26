"""
LGPO Utilities for CIS GPO Compliance Tool
Handles Local Group Policy Object operations using Microsoft LGPO.exe
"""

import os
import subprocess
import tempfile
import shutil
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LGPOResult:
    """Result from LGPO operation"""
    success: bool
    output: str
    error: str
    return_code: int


class LGPOManager:
    """Manager for LGPO.exe operations"""
    
    def __init__(self, lgpo_path: Optional[str] = None):
        """Initialize LGPO manager"""
        self.lgpo_path = self._find_lgpo_executable(lgpo_path)
        self.temp_dir = tempfile.mkdtemp(prefix="lgpo_")
        
        logger.info(f"LGPO manager initialized with executable: {self.lgpo_path}")
    
    def _find_lgpo_executable(self, provided_path: Optional[str] = None) -> Optional[str]:
        """Find LGPO.exe executable"""
        
        if provided_path and os.path.isfile(provided_path):
            return provided_path
        
        # Common locations to search for LGPO.exe
        search_paths = [
            # Current directory
            os.path.join(os.getcwd(), "LGPO.exe"),
            # Tools directory
            os.path.join(os.getcwd(), "tools", "LGPO.exe"),
            # Backend directory
            os.path.join(os.path.dirname(__file__), "LGPO.exe"),
            os.path.join(os.path.dirname(__file__), "..", "tools", "LGPO.exe"),
            # System PATH
            shutil.which("LGPO.exe") or ""
        ]
        
        for path in search_paths:
            if path and os.path.isfile(path):
                logger.info(f"Found LGPO.exe at: {path}")
                return path
        
        logger.warning("LGPO.exe not found. Download from Microsoft and place in tools directory")
        return None
    
    def is_available(self) -> bool:
        """Check if LGPO.exe is available"""
        return self.lgpo_path is not None and os.path.isfile(self.lgpo_path)
    
    def get_version(self) -> Optional[str]:
        """Get LGPO version"""
        if not self.is_available():
            return None
        
        try:
            result = subprocess.run(
                [self.lgpo_path, "/?"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse version from output
            for line in result.stdout.split('\n'):
                if 'version' in line.lower():
                    return line.strip()
                    
            return "Unknown version"
            
        except Exception as e:
            logger.error(f"Error getting LGPO version: {e}")
            return None
    
    def apply_policy_file(self, pol_file_path: str, scope: str = "machine") -> LGPOResult:
        """Apply policy file using LGPO"""
        
        if not self.is_available():
            return LGPOResult(
                success=False,
                output="",
                error="LGPO.exe not available",
                return_code=-1
            )
        
        if not os.path.isfile(pol_file_path):
            return LGPOResult(
                success=False,
                output="",
                error=f"Policy file not found: {pol_file_path}",
                return_code=-1
            )
        
        # Build command
        scope_flag = "/m" if scope.lower() == "machine" else "/u"
        cmd = [self.lgpo_path, scope_flag, pol_file_path]
        
        try:
            logger.info(f"Executing LGPO command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=os.path.dirname(self.lgpo_path)
            )
            
            success = result.returncode == 0
            
            return LGPOResult(
                success=success,
                output=result.stdout,
                error=result.stderr,
                return_code=result.returncode
            )
            
        except subprocess.TimeoutExpired:
            return LGPOResult(
                success=False,
                output="",
                error="LGPO operation timed out",
                return_code=-2
            )
        except Exception as e:
            return LGPOResult(
                success=False,
                output="",
                error=str(e),
                return_code=-3
            )
    
    def parse_policy_file(self, pol_file_path: str) -> LGPOResult:
        """Parse policy file to text using LGPO"""
        
        if not self.is_available():
            return LGPOResult(
                success=False,
                output="",
                error="LGPO.exe not available",
                return_code=-1
            )
        
        if not os.path.isfile(pol_file_path):
            return LGPOResult(
                success=False,
                output="",
                error=f"Policy file not found: {pol_file_path}",
                return_code=-1
            )
        
        # Create temporary output file
        output_file = os.path.join(self.temp_dir, "parsed_policy.txt")
        
        try:
            # Build command to parse policy file
            cmd = [self.lgpo_path, "/parse", "/m", pol_file_path, "/v"]
            
            logger.info(f"Parsing policy file: {pol_file_path}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.path.dirname(self.lgpo_path)
            )
            
            success = result.returncode == 0
            
            return LGPOResult(
                success=success,
                output=result.stdout,
                error=result.stderr,
                return_code=result.returncode
            )
            
        except Exception as e:
            return LGPOResult(
                success=False,
                output="",
                error=str(e),
                return_code=-3
            )
    
    def backup_current_policy(self, backup_path: str, scope: str = "both") -> LGPOResult:
        """Backup current local group policy"""
        
        if not self.is_available():
            return LGPOResult(
                success=False,
                output="",
                error="LGPO.exe not available",
                return_code=-1
            )
        
        # Ensure backup directory exists
        os.makedirs(backup_path, exist_ok=True)
        
        try:
            results = []
            
            # Backup machine policy
            if scope.lower() in ["machine", "both"]:
                machine_backup = os.path.join(backup_path, "Machine-Backup.pol")
                cmd = [self.lgpo_path, "/b", "/m", machine_backup]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                results.append(result)
            
            # Backup user policy
            if scope.lower() in ["user", "both"]:
                user_backup = os.path.join(backup_path, "User-Backup.pol")
                cmd = [self.lgpo_path, "/b", "/u", user_backup]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                results.append(result)
            
            # Check if all operations succeeded
            all_success = all(r.returncode == 0 for r in results)
            combined_output = "\n".join(r.stdout for r in results)
            combined_error = "\n".join(r.stderr for r in results)
            
            return LGPOResult(
                success=all_success,
                output=combined_output,
                error=combined_error,
                return_code=0 if all_success else results[-1].returncode
            )
            
        except Exception as e:
            return LGPOResult(
                success=False,
                output="",
                error=str(e),
                return_code=-3
            )
    
    def create_policy_from_registry(self, registry_entries: List[Dict[str, Any]], 
                                  output_path: str, scope: str = "machine") -> LGPOResult:
        """Create policy file from registry entries"""
        
        try:
            # Create temporary registry file
            reg_file = os.path.join(self.temp_dir, f"{scope}_policy.reg")
            
            with open(reg_file, 'w', encoding='utf-8') as f:
                f.write("Windows Registry Editor Version 5.00\n\n")
                
                for entry in registry_entries:
                    hive = entry.get('hive', 'HKLM')
                    key_path = entry.get('key_path', '')
                    value_name = entry.get('value_name', '')
                    value_type = entry.get('value_type', 'REG_DWORD')
                    value_data = entry.get('value_data', '')
                    
                    # Write registry key
                    full_path = f"{hive}\\{key_path}"
                    f.write(f"[{full_path}]\n")
                    
                    # Write registry value
                    if value_type == 'REG_DWORD':
                        try:
                            dword_val = int(value_data)
                            f.write(f'"{value_name}"=dword:{dword_val:08x}\n')
                        except (ValueError, TypeError):
                            f.write(f'"{value_name}"=dword:00000000\n')
                    else:
                        f.write(f'"{value_name}"="{value_data}"\n')
                    
                    f.write("\n")
            
            # Convert registry file to policy using LGPO if available
            if self.is_available():
                scope_flag = "/m" if scope.lower() == "machine" else "/u"
                cmd = [self.lgpo_path, "/r", reg_file, scope_flag, output_path]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                return LGPOResult(
                    success=result.returncode == 0,
                    output=result.stdout,
                    error=result.stderr,
                    return_code=result.returncode
                )
            else:
                # If LGPO not available, just copy the registry file
                shutil.copy(reg_file, output_path)
                
                return LGPOResult(
                    success=True,
                    output=f"Registry file created: {output_path}",
                    error="",
                    return_code=0
                )
            
        except Exception as e:
            return LGPOResult(
                success=False,
                output="",
                error=str(e),
                return_code=-3
            )
    
    def validate_policy_file(self, pol_file_path: str) -> LGPOResult:
        """Validate policy file format"""
        
        if not os.path.isfile(pol_file_path):
            return LGPOResult(
                success=False,
                output="",
                error=f"Policy file not found: {pol_file_path}",
                return_code=-1
            )
        
        try:
            # Basic file validation
            file_size = os.path.getsize(pol_file_path)
            
            if file_size == 0:
                return LGPOResult(
                    success=False,
                    output="",
                    error="Policy file is empty",
                    return_code=-1
                )
            
            # If LGPO is available, use it for validation
            if self.is_available():
                return self.parse_policy_file(pol_file_path)
            else:
                # Basic validation without LGPO
                with open(pol_file_path, 'rb') as f:
                    header = f.read(16)
                    
                # Check for basic policy file structure
                if len(header) < 8:
                    return LGPOResult(
                        success=False,
                        output="",
                        error="Invalid policy file format - file too short",
                        return_code=-1
                    )
                
                return LGPOResult(
                    success=True,
                    output=f"Policy file appears valid (size: {file_size} bytes)",
                    error="",
                    return_code=0
                )
                
        except Exception as e:
            return LGPOResult(
                success=False,
                output="",
                error=str(e),
                return_code=-3
            )
    
    def get_installation_instructions(self) -> str:
        """Get LGPO.exe installation instructions"""
        
        return """
Microsoft LGPO.exe Installation Instructions
==========================================

LGPO.exe is a free utility from Microsoft for managing Local Group Policy.

Download and Installation:
1. Visit: https://www.microsoft.com/en-us/download/details.aspx?id=55319
2. Download "LGPO.zip"
3. Extract LGPO.exe to one of these locations:
   - Current directory: ./LGPO.exe
   - Tools directory: ./tools/LGPO.exe
   - System PATH location

Verification:
Run 'LGPO.exe /?' to verify installation and view help.

Alternative Installation:
The tool will work without LGPO.exe but with reduced functionality:
- Registry files (.reg) will be generated instead of policy files
- Manual import required using regedit
- No policy parsing or validation features

For full offline deployment capabilities, LGPO.exe is recommended.
"""
    
    def cleanup(self):
        """Cleanup temporary files"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.warning(f"Error cleaning up LGPO temp directory: {e}")
    
    def __del__(self):
        """Destructor to cleanup resources"""
        self.cleanup()


class LGPOPolicyParser:
    """Parser for LGPO policy definitions"""
    
    @staticmethod
    def parse_admx_references(policy_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Parse ADMX template references from policy data"""
        
        references = []
        
        # Look for ADMX references in policy metadata
        if 'admx_reference' in policy_data:
            admx_ref = policy_data['admx_reference']
            references.append({
                'template': admx_ref.get('template', ''),
                'namespace': admx_ref.get('namespace', ''),
                'policy_name': admx_ref.get('policy_name', ''),
                'category': admx_ref.get('category', '')
            })
        
        return references
    
    @staticmethod
    def extract_registry_settings(policy_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract registry settings from policy data"""
        
        registry_settings = []
        
        # Direct registry settings
        if 'registry_settings' in policy_data:
            for setting in policy_data['registry_settings']:
                registry_settings.append({
                    'hive': setting.get('hive', 'HKLM'),
                    'key_path': setting.get('key_path', ''),
                    'value_name': setting.get('value_name', ''),
                    'value_type': setting.get('value_type', 'REG_DWORD'),
                    'value_data': setting.get('value_data', ''),
                    'description': setting.get('description', '')
                })
        
        # Inferred registry settings from policy details
        if 'current_value' in policy_data and 'registry_path' in policy_data:
            registry_settings.append({
                'hive': 'HKLM',
                'key_path': policy_data.get('registry_path', ''),
                'value_name': policy_data.get('registry_value', 'Enabled'),
                'value_type': 'REG_DWORD',
                'value_data': 1 if policy_data.get('current_value') == 'enabled' else 0,
                'description': policy_data.get('description', '')
            })
        
        return registry_settings
    
    @staticmethod 
    def categorize_policies(policies: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize policies by type/scope"""
        
        categories = {
            'computer_configuration': [],
            'user_configuration': [],
            'security_settings': [],
            'administrative_templates': [],
            'unknown': []
        }
        
        for policy in policies:
            category = policy.get('category', '').lower()
            scope = policy.get('scope', '').lower()
            
            if scope == 'user':
                categories['user_configuration'].append(policy)
            elif scope == 'computer' or scope == 'machine':
                categories['computer_configuration'].append(policy)
            elif 'security' in category:
                categories['security_settings'].append(policy)
            elif 'administrative' in category or 'template' in category:
                categories['administrative_templates'].append(policy)
            else:
                categories['unknown'].append(policy)
        
        return categories
    
    @staticmethod
    def validate_policy_compatibility(policy_data: Dict[str, Any], 
                                    target_os: str) -> Tuple[bool, List[str]]:
        """Validate policy compatibility with target OS"""
        
        warnings = []
        is_compatible = True
        
        # Check OS version requirements
        if 'min_os_version' in policy_data:
            min_version = policy_data['min_os_version']
            # Add OS version checking logic here
            warnings.append(f"Policy requires minimum OS version: {min_version}")
        
        # Check for deprecated policies
        if policy_data.get('deprecated', False):
            warnings.append("Policy is marked as deprecated")
        
        # Check for Windows edition requirements
        required_edition = policy_data.get('required_edition', '')
        if required_edition:
            warnings.append(f"Policy may require Windows edition: {required_edition}")
        
        return is_compatible, warnings


def download_lgpo_tool(destination_dir: str) -> Tuple[bool, str]:
    """
    Provide instructions for downloading LGPO.exe
    Note: Actual download would require user action due to Microsoft's download page
    """
    
    instructions = f"""
To download LGPO.exe automatically is not possible due to Microsoft's download restrictions.
Please follow these manual steps:

1. Open a web browser and navigate to:
   https://www.microsoft.com/en-us/download/details.aspx?id=55319

2. Click "Download" and select "LGPO.zip"

3. Extract the downloaded ZIP file

4. Copy LGPO.exe to: {destination_dir}

5. Verify installation by running: LGPO.exe /?

Alternative: The deployment tool will work without LGPO.exe but will generate
registry files (.reg) instead of policy files (.pol) for manual import.
"""
    
    return False, instructions


def create_lgpo_installation_script() -> str:
    """Create a script to help with LGPO installation"""
    
    script_content = '''
@echo off
REM LGPO.exe Installation Helper Script

echo ========================================
echo LGPO.exe Installation Helper
echo ========================================
echo.

echo Checking for LGPO.exe...
if exist "LGPO.exe" (
    echo LGPO.exe found in current directory!
    LGPO.exe /?
    echo.
    echo Installation verified successfully.
    pause
    exit /b 0
)

if exist "tools\\LGPO.exe" (
    echo LGPO.exe found in tools directory!
    tools\\LGPO.exe /?
    echo.
    echo Installation verified successfully.
    pause
    exit /b 0
)

echo LGPO.exe not found. Please download it manually.
echo.
echo Download Instructions:
echo 1. Visit: https://www.microsoft.com/en-us/download/details.aspx?id=55319
echo 2. Download LGPO.zip
echo 3. Extract LGPO.exe to current directory or tools\\ directory
echo 4. Run this script again to verify
echo.
echo Without LGPO.exe, the tool will generate registry files instead.
echo.
pause
'''
    
    return script_content