"""
System Backup Manager for Remediation and Rollback
Handles creation, validation, and restoration of system backups
"""

import os
import json
import shutil
import subprocess
import hashlib
import zipfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

# Windows-specific imports with fallback
try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False
    # Create mock winreg for non-Windows platforms
    class MockWinreg:
        HKEY_LOCAL_MACHINE = "HKEY_LOCAL_MACHINE"
        HKEY_CURRENT_USER = "HKEY_CURRENT_USER"
        REG_SZ = "REG_SZ"
        REG_DWORD = "REG_DWORD"
        
        @staticmethod
        def OpenKey(*args, **kwargs):
            raise OSError("Registry operations not supported on this platform")
        
        @staticmethod
        def QueryValueEx(*args, **kwargs):
            raise OSError("Registry operations not supported on this platform")
        
        @staticmethod
        def EnumKey(*args, **kwargs):
            raise OSError("Registry operations not supported on this platform")
        
        @staticmethod
        def EnumValue(*args, **kwargs):
            raise OSError("Registry operations not supported on this platform")
    
    winreg = MockWinreg()

from .models_remediation import (
    SystemBackup, BackupType, RollbackStatus, RemediationType,
    serialize_system_backup, deserialize_system_backup
)

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages system backups for safe remediation and rollback"""
    
    def __init__(self, backup_path: str = "data/backups"):
        """Initialize backup manager"""
        self.backup_path = Path(backup_path)
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        self.active_backups: Dict[str, SystemBackup] = {}
        self.backup_index_file = self.backup_path / "backup_index.json"
        
        # Load existing backups
        self._load_backup_index()
    
    def _load_backup_index(self):
        """Load backup index from storage"""
        try:
            if self.backup_index_file.exists():
                with open(self.backup_index_file, 'r') as f:
                    data = json.load(f)
                    for backup_data in data.get('backups', []):
                        backup = deserialize_system_backup(backup_data)
                        self.active_backups[backup.backup_id] = backup
                        
                        # Validate backup still exists
                        if not Path(backup.backup_path).exists():
                            backup.status = RollbackStatus.CORRUPTED
                            logger.warning(f"Backup file missing: {backup.backup_path}")
        except Exception as e:
            logger.error(f"Error loading backup index: {e}")
    
    def _save_backup_index(self):
        """Save backup index to storage"""
        try:
            data = {
                'backups': [serialize_system_backup(backup) for backup in self.active_backups.values()],
                'last_updated': datetime.now().isoformat()
            }
            with open(self.backup_index_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving backup index: {e}")
    
    def create_system_backup(
        self,
        name: str,
        description: str,
        backup_type: BackupType,
        created_by: str,
        policies: List[str] = None,
        registry_keys: List[str] = None,
        gpos: List[str] = None
    ) -> str:
        """Create a system backup"""
        import uuid
        
        backup_id = str(uuid.uuid4())
        backup_dir = self.backup_path / backup_id
        backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"Creating backup: {name} ({backup_type.value})")
        
        try:
            # Collect system information
            system_info = self._collect_system_info()
            
            # Create backup based on type
            backup_files = []
            size_bytes = 0
            
            if backup_type == BackupType.FULL_SYSTEM:
                backup_files, size_bytes = self._backup_full_system(backup_dir)
            elif backup_type == BackupType.REGISTRY_ONLY:
                backup_files, size_bytes = self._backup_registry(backup_dir, registry_keys)
            elif backup_type == BackupType.GROUP_POLICY:
                backup_files, size_bytes = self._backup_group_policies(backup_dir, gpos)
            elif backup_type == BackupType.SECURITY_SETTINGS:
                backup_files, size_bytes = self._backup_security_settings(backup_dir)
            elif backup_type == BackupType.SELECTIVE:
                backup_files, size_bytes = self._backup_selective(backup_dir, policies, registry_keys, gpos)
            
            # Create backup archive
            backup_archive = self._create_backup_archive(backup_dir, backup_files)
            
            # Calculate checksum
            checksum = self._calculate_checksum(backup_archive)
            
            # Create backup record
            backup = SystemBackup(
                backup_id=backup_id,
                name=name,
                description=description,
                backup_type=backup_type,
                created_at=datetime.now(),
                created_by=created_by,
                size_bytes=size_bytes,
                backup_path=str(backup_archive),
                affected_policies=policies or [],
                affected_registry_keys=registry_keys or [],
                affected_gpos=gpos or [],
                system_info=system_info,
                checksum=checksum,
                compression_used=True,
                encryption_used=False,
                status=RollbackStatus.AVAILABLE,
                expiry_date=datetime.now() + timedelta(days=90)
            )
            
            # Validate backup
            validation_results = self._validate_backup(backup)
            backup.validation_results = validation_results
            
            self.active_backups[backup_id] = backup
            self._save_backup_index()
            
            logger.info(f"Backup created successfully: {backup_id}")
            return backup_id
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            # Cleanup on failure
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)
            raise
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect current system information"""
        system_info = {
            'timestamp': datetime.now().isoformat(),
            'hostname': os.environ.get('COMPUTERNAME', 'Unknown'),
            'username': os.environ.get('USERNAME', 'Unknown'),
            'os_version': 'Windows',
            'backup_tool_version': '1.0.0'
        }
        
        try:
            # Get Windows version
            result = subprocess.run(['ver'], shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                system_info['os_version'] = result.stdout.strip()
        except Exception:
            pass
        
        try:
            # Get system uptime
            result = subprocess.run(['systeminfo'], shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'System Boot Time:' in line:
                        system_info['last_boot'] = line.split(':', 1)[1].strip()
                        break
        except Exception:
            pass
        
        return system_info
    
    def _backup_full_system(self, backup_dir: Path) -> Tuple[List[str], int]:
        """Create full system backup"""
        backup_files = []
        total_size = 0
        
        # Export entire registry
        registry_file = backup_dir / "full_registry.reg"
        self._export_registry_hive(None, str(registry_file))
        backup_files.append(str(registry_file))
        total_size += registry_file.stat().st_size if registry_file.exists() else 0
        
        # Backup group policies
        gpo_files, gpo_size = self._backup_group_policies(backup_dir)
        backup_files.extend(gpo_files)
        total_size += gpo_size
        
        # Backup security settings
        sec_files, sec_size = self._backup_security_settings(backup_dir)
        backup_files.extend(sec_files)
        total_size += sec_size
        
        return backup_files, total_size
    
    def _backup_registry(self, backup_dir: Path, registry_keys: List[str] = None) -> Tuple[List[str], int]:
        """Backup registry keys"""
        backup_files = []
        total_size = 0
        
        if registry_keys:
            for i, key in enumerate(registry_keys):
                try:
                    reg_file = backup_dir / f"registry_{i+1}.reg"
                    self._export_registry_key(key, str(reg_file))
                    backup_files.append(str(reg_file))
                    total_size += reg_file.stat().st_size if reg_file.exists() else 0
                except Exception as e:
                    logger.warning(f"Failed to backup registry key {key}: {e}")
        else:
            # Full registry backup
            registry_file = backup_dir / "full_registry.reg"
            self._export_registry_hive(None, str(registry_file))
            backup_files.append(str(registry_file))
            total_size += registry_file.stat().st_size if registry_file.exists() else 0
        
        return backup_files, total_size
    
    def _backup_group_policies(self, backup_dir: Path, gpo_names: List[str] = None) -> Tuple[List[str], int]:
        """Backup group policies"""
        backup_files = []
        total_size = 0
        
        # Create GPO backup directory
        gpo_dir = backup_dir / "group_policies"
        gpo_dir.mkdir(exist_ok=True)
        
        try:
            # Export local group policy
            lgpo_file = gpo_dir / "local_policy.pol"
            self._export_local_group_policy(str(lgpo_file))
            if lgpo_file.exists():
                backup_files.append(str(lgpo_file))
                total_size += lgpo_file.stat().st_size
            
            # Export security templates
            secedit_file = gpo_dir / "security_config.inf"
            self._export_security_config(str(secedit_file))
            if secedit_file.exists():
                backup_files.append(str(secedit_file))
                total_size += secedit_file.stat().st_size
                
        except Exception as e:
            logger.error(f"Failed to backup group policies: {e}")
        
        return backup_files, total_size
    
    def _backup_security_settings(self, backup_dir: Path) -> Tuple[List[str], int]:
        """Backup security settings"""
        backup_files = []
        total_size = 0
        
        security_dir = backup_dir / "security"
        security_dir.mkdir(exist_ok=True)
        
        try:
            # Export security configuration
            sec_file = security_dir / "security_config.cfg"
            cmd = f'secedit /export /cfg "{sec_file}" /areas SECURITYPOLICY,USER_RIGHTS,REGKEYS'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and sec_file.exists():
                backup_files.append(str(sec_file))
                total_size += sec_file.stat().st_size
            
            # Export audit policy
            audit_file = security_dir / "audit_policy.txt"
            cmd = 'auditpol /get /category:* /r'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                with open(audit_file, 'w') as f:
                    f.write(result.stdout)
                backup_files.append(str(audit_file))
                total_size += audit_file.stat().st_size
                
        except Exception as e:
            logger.error(f"Failed to backup security settings: {e}")
        
        return backup_files, total_size
    
    def _backup_selective(
        self, 
        backup_dir: Path, 
        policies: List[str] = None,
        registry_keys: List[str] = None,
        gpos: List[str] = None
    ) -> Tuple[List[str], int]:
        """Create selective backup"""
        backup_files = []
        total_size = 0
        
        # Backup specified registry keys
        if registry_keys:
            reg_files, reg_size = self._backup_registry(backup_dir, registry_keys)
            backup_files.extend(reg_files)
            total_size += reg_size
        
        # Backup specified group policies
        if gpos:
            gpo_files, gpo_size = self._backup_group_policies(backup_dir, gpos)
            backup_files.extend(gpo_files)
            total_size += gpo_size
        
        # If policies specified, try to map to registry keys/GPOs
        if policies:
            # This would be expanded based on policy definitions
            # For now, include basic security settings
            sec_files, sec_size = self._backup_security_settings(backup_dir)
            backup_files.extend(sec_files)
            total_size += sec_size
        
        return backup_files, total_size
    
    def _export_registry_key(self, key_path: str, output_file: str):
        """Export specific registry key"""
        if not HAS_WINREG:
            logger.warning(f"Registry operations not supported on {os.name} platform")
            # Create empty file for cross-platform compatibility
            Path(output_file).write_text(f"# Registry export not supported on {os.name}\n# Key: {key_path}\n")
            return
            
        try:
            cmd = f'reg export "{key_path}" "{output_file}" /y'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Failed to export registry key {key_path}: {result.stderr}")
        except Exception as e:
            logger.error(f"Error exporting registry key {key_path}: {e}")
    
    def _export_registry_hive(self, hive: str = None, output_file: str = None):
        """Export registry hive or entire registry"""
        if not HAS_WINREG:
            logger.warning(f"Registry operations not supported on {os.name} platform")
            # Create empty file for cross-platform compatibility
            Path(output_file).write_text(f"# Registry hive export not supported on {os.name}\n# Hive: {hive or 'ALL'}\n")
            return
            
        try:
            if hive:
                cmd = f'reg export "{hive}" "{output_file}" /y'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            else:
                # Export all hives to single file is not directly supported
                # Export major hives separately and combine
                hives = [
                    "HKEY_LOCAL_MACHINE\\SOFTWARE",
                    "HKEY_LOCAL_MACHINE\\SYSTEM", 
                    "HKEY_CURRENT_USER",
                    "HKEY_LOCAL_MACHINE\\SECURITY"
                ]
                
                combined_content = []
                for i, hive_key in enumerate(hives):
                    temp_file = f"{output_file}.temp_{i}"
                    cmd = f'reg export "{hive_key}" "{temp_file}" /y'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0 and os.path.exists(temp_file):
                        with open(temp_file, 'r', encoding='utf-16-le') as f:
                            content = f.read()
                            combined_content.append(content)
                        os.remove(temp_file)
                
                # Write combined content
                if combined_content:
                    with open(output_file, 'w', encoding='utf-16-le') as f:
                        f.write('\n\n'.join(combined_content))
                        
        except Exception as e:
            logger.error(f"Error exporting registry: {e}")
    
    def _export_local_group_policy(self, output_file: str):
        """Export local group policy"""
        if not HAS_WINREG:
            logger.warning(f"Group policy operations not supported on {os.name} platform")
            # Create empty file for cross-platform compatibility
            Path(output_file).write_text(f"# Group policy export not supported on {os.name}\n")
            return
            
        try:
            # Try to use LGPO if available
            lgpo_path = shutil.which("lgpo.exe")
            if lgpo_path:
                cmd = f'"{lgpo_path}" /b "{os.path.dirname(output_file)}"'
                subprocess.run(cmd, shell=True, capture_output=True)
            else:
                # Fallback: copy policy files directly
                policy_dirs = [
                    r"C:\Windows\System32\GroupPolicy",
                    r"C:\Windows\System32\GroupPolicyUsers"
                ]
                
                for policy_dir in policy_dirs:
                    if os.path.exists(policy_dir):
                        backup_dir = os.path.dirname(output_file)
                        shutil.copytree(policy_dir, os.path.join(backup_dir, os.path.basename(policy_dir)), dirs_exist_ok=True)
                        
        except Exception as e:
            logger.error(f"Error exporting local group policy: {e}")
    
    def _export_security_config(self, output_file: str):
        """Export security configuration"""
        if not HAS_WINREG:
            logger.warning(f"Security configuration export not supported on {os.name} platform")
            # Create empty file for cross-platform compatibility
            Path(output_file).write_text(f"# Security config export not supported on {os.name}\n")
            return
            
        try:
            cmd = f'secedit /export /cfg "{output_file}"'
            subprocess.run(cmd, shell=True, capture_output=True)
        except Exception as e:
            logger.error(f"Error exporting security config: {e}")
    
    def _create_backup_archive(self, backup_dir: Path, backup_files: List[str]) -> Path:
        """Create compressed backup archive"""
        archive_path = backup_dir.parent / f"{backup_dir.name}.zip"
        
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in backup_files:
                    if os.path.exists(file_path):
                        # Add file to archive with relative path
                        rel_path = os.path.relpath(file_path, backup_dir)
                        zipf.write(file_path, rel_path)
            
            # Clean up temporary directory
            shutil.rmtree(backup_dir, ignore_errors=True)
            
            return archive_path
            
        except Exception as e:
            logger.error(f"Error creating backup archive: {e}")
            raise
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of backup file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating checksum: {e}")
            return ""
    
    def _validate_backup(self, backup: SystemBackup) -> Dict[str, Any]:
        """Validate backup integrity and completeness"""
        results = {
            'is_valid': True,
            'checks': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check if backup file exists
            if not Path(backup.backup_path).exists():
                results['is_valid'] = False
                results['errors'].append("Backup file does not exist")
                return results
            
            results['checks']['file_exists'] = True
            
            # Verify file size
            actual_size = Path(backup.backup_path).stat().st_size
            if abs(actual_size - backup.size_bytes) > 1024:  # Allow 1KB difference
                results['warnings'].append(f"File size mismatch: expected {backup.size_bytes}, got {actual_size}")
            
            results['checks']['size_valid'] = True
            
            # Verify checksum
            if backup.checksum:
                calculated_checksum = self._calculate_checksum(Path(backup.backup_path))
                if calculated_checksum != backup.checksum:
                    results['is_valid'] = False
                    results['errors'].append("Checksum verification failed")
                else:
                    results['checks']['checksum_valid'] = True
            
            # Test archive integrity
            try:
                with zipfile.ZipFile(backup.backup_path, 'r') as zipf:
                    test_result = zipf.testzip()
                    if test_result:
                        results['is_valid'] = False
                        results['errors'].append(f"Archive corruption detected: {test_result}")
                    else:
                        results['checks']['archive_valid'] = True
            except Exception as e:
                results['is_valid'] = False
                results['errors'].append(f"Archive validation failed: {e}")
            
        except Exception as e:
            results['is_valid'] = False
            results['errors'].append(f"Validation error: {e}")
        
        return results
    
    def get_backup(self, backup_id: str) -> Optional[SystemBackup]:
        """Get backup by ID"""
        return self.active_backups.get(backup_id)
    
    def list_backups(self, backup_type: BackupType = None, created_by: str = None) -> List[SystemBackup]:
        """List available backups with optional filtering"""
        backups = list(self.active_backups.values())
        
        if backup_type:
            backups = [b for b in backups if b.backup_type == backup_type]
        
        if created_by:
            backups = [b for b in backups if b.created_by == created_by]
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x.created_at, reverse=True)
        
        return backups
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup"""
        try:
            backup = self.active_backups.get(backup_id)
            if not backup:
                return False
            
            # Delete backup file
            backup_file = Path(backup.backup_path)
            if backup_file.exists():
                backup_file.unlink()
            
            # Remove from index
            del self.active_backups[backup_id]
            self._save_backup_index()
            
            logger.info(f"Deleted backup: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting backup {backup_id}: {e}")
            return False
    
    def cleanup_expired_backups(self):
        """Clean up expired backups"""
        now = datetime.now()
        expired_backups = []
        
        for backup_id, backup in self.active_backups.items():
            if backup.expiry_date and now > backup.expiry_date:
                expired_backups.append(backup_id)
        
        for backup_id in expired_backups:
            self.delete_backup(backup_id)
        
        logger.info(f"Cleaned up {len(expired_backups)} expired backups")
        return len(expired_backups)
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics"""
        backups = list(self.active_backups.values())
        
        stats = {
            'total_backups': len(backups),
            'total_size_bytes': sum(b.size_bytes for b in backups),
            'by_type': {},
            'by_status': {},
            'oldest_backup': None,
            'newest_backup': None
        }
        
        if backups:
            # Group by type
            for backup in backups:
                backup_type = backup.backup_type.value
                if backup_type not in stats['by_type']:
                    stats['by_type'][backup_type] = 0
                stats['by_type'][backup_type] += 1
            
            # Group by status
            for backup in backups:
                status = backup.status.value
                if status not in stats['by_status']:
                    stats['by_status'][status] = 0
                stats['by_status'][status] += 1
            
            # Find oldest and newest
            sorted_backups = sorted(backups, key=lambda x: x.created_at)
            stats['oldest_backup'] = {
                'id': sorted_backups[0].backup_id,
                'name': sorted_backups[0].name,
                'created_at': sorted_backups[0].created_at.isoformat()
            }
            stats['newest_backup'] = {
                'id': sorted_backups[-1].backup_id,
                'name': sorted_backups[-1].name,
                'created_at': sorted_backups[-1].created_at.isoformat()
            }
        
        return stats