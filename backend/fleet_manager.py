"""
Fleet Manager - Phase 1: Central Deployment Server
Manages fleet of machines, deployment orchestration, and real-time updates
"""

import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from pathlib import Path
import logging

from models_fleet import (
    Machine, MachineRegistration, MachineHeartbeat, MachineStatus,
    RemoteDeployment, DeploymentProgress, DeploymentSummary, DeploymentPhase,
    FleetStatistics, AgentCommand, AgentCommandResult, RollbackRequest,
    MachineGroupRequest, AgentCapability
)

logger = logging.getLogger(__name__)


class FleetManager:
    """
    Manages fleet of Windows machines with central deployment orchestration
    """
    
    def __init__(self, data_dir: str = "fleet_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Storage files
        self.machines_file = self.data_dir / "machines.json"
        self.deployments_file = self.data_dir / "deployments.json"
        self.deployment_logs_file = self.data_dir / "deployment_logs.json"
        
        # In-memory caches
        self.machines: Dict[str, Machine] = {}
        self.deployments: Dict[str, RemoteDeployment] = {}
        self.deployment_progress: Dict[str, Dict[str, DeploymentProgress]] = {}
        self.command_queue: Dict[str, List[AgentCommand]] = {}
        
        # WebSocket connections for real-time updates
        self.websocket_connections: Set = set()
        
        # Load existing data
        self._load_data()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _load_data(self):
        """Load machines and deployments from disk"""
        try:
            if self.machines_file.exists():
                with open(self.machines_file, 'r') as f:
                    data = json.load(f)
                    self.machines = {
                        k: Machine(**v) for k, v in data.items()
                    }
                logger.info(f"Loaded {len(self.machines)} machines")
            
            if self.deployments_file.exists():
                with open(self.deployments_file, 'r') as f:
                    data = json.load(f)
                    self.deployments = {
                        k: RemoteDeployment(**v) for k, v in data.items()
                    }
                logger.info(f"Loaded {len(self.deployments)} deployments")
        
        except Exception as e:
            logger.error(f"Error loading fleet data: {e}")
    
    def _save_machines(self):
        """Persist machines to disk"""
        try:
            data = {k: v.dict() for k, v in self.machines.items()}
            with open(self.machines_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving machines: {e}")
    
    def _save_deployments(self):
        """Persist deployments to disk"""
        try:
            data = {k: v.dict() for k, v in self.deployments.items()}
            with open(self.deployments_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving deployments: {e}")
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        # Note: These will be started by FastAPI lifespan events
        pass
    
    # ============================================================================
    # MACHINE MANAGEMENT
    # ============================================================================
    
    def register_machine(self, registration: MachineRegistration) -> Machine:
        """Register a new machine or update existing"""
        # Check if machine exists (by hostname)
        existing = self.get_machine_by_hostname(registration.hostname)
        
        if existing:
            # Update existing machine
            machine_id = existing.machine_id
            machine = Machine(
                machine_id=machine_id,
                **registration.dict(),
                status=MachineStatus.ONLINE,
                last_seen=datetime.now(),
                registered_at=existing.registered_at
            )
        else:
            # Create new machine
            machine = Machine(
                **registration.dict(),
                status=MachineStatus.ONLINE,
                last_seen=datetime.now()
            )
        
        self.machines[machine.machine_id] = machine
        self._save_machines()
        
        logger.info(f"Registered machine: {machine.hostname} ({machine.machine_id})")
        
        # Broadcast update via WebSocket
        asyncio.create_task(self._broadcast_machine_update(machine))
        
        return machine
    
    def update_machine_heartbeat(self, heartbeat: MachineHeartbeat) -> bool:
        """Update machine status from heartbeat"""
        machine = self.machines.get(heartbeat.machine_id)
        if not machine:
            logger.warning(f"Heartbeat from unknown machine: {heartbeat.machine_id}")
            return False
        
        # Update status
        machine.status = heartbeat.status
        machine.last_seen = datetime.now()
        
        # Update metrics if provided
        if heartbeat.cpu_usage is not None:
            machine.cpu_usage = heartbeat.cpu_usage
        if heartbeat.memory_used is not None:
            machine.memory_used = heartbeat.memory_used
        if heartbeat.disk_free is not None:
            machine.disk_free = heartbeat.disk_free
        if heartbeat.compliance_score is not None:
            machine.compliance_score = heartbeat.compliance_score
        if heartbeat.policies_applied is not None:
            machine.policies_applied = heartbeat.policies_applied
        if heartbeat.policies_failed is not None:
            machine.policies_failed = heartbeat.policies_failed
        
        self._save_machines()
        
        # Broadcast update
        asyncio.create_task(self._broadcast_machine_update(machine))
        
        return True
    
    def get_machine(self, machine_id: str) -> Optional[Machine]:
        """Get machine by ID"""
        return self.machines.get(machine_id)
    
    def get_machine_by_hostname(self, hostname: str) -> Optional[Machine]:
        """Get machine by hostname"""
        for machine in self.machines.values():
            if machine.hostname.lower() == hostname.lower():
                return machine
        return None
    
    def list_machines(
        self,
        status: Optional[MachineStatus] = None,
        groups: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[Machine]:
        """List machines with optional filters"""
        machines = list(self.machines.values())
        
        if status:
            machines = [m for m in machines if m.status == status]
        
        if groups:
            machines = [m for m in machines if any(g in m.groups for g in groups)]
        
        if tags:
            machines = [m for m in machines if any(t in m.tags for t in tags)]
        
        return machines
    
    def update_machine_groups_tags(self, request: MachineGroupRequest) -> int:
        """Bulk update machine groups and tags"""
        updated_count = 0
        
        for machine_id in request.machine_ids:
            machine = self.machines.get(machine_id)
            if not machine:
                continue
            
            # Update groups
            if request.groups_to_add:
                machine.groups.extend(
                    [g for g in request.groups_to_add if g not in machine.groups]
                )
            if request.groups_to_remove:
                machine.groups = [
                    g for g in machine.groups if g not in request.groups_to_remove
                ]
            
            # Update tags
            if request.tags_to_add:
                machine.tags.extend(
                    [t for t in request.tags_to_add if t not in machine.tags]
                )
            if request.tags_to_remove:
                machine.tags = [
                    t for t in machine.tags if t not in request.tags_to_remove
                ]
            
            updated_count += 1
        
        self._save_machines()
        return updated_count
    
    def delete_machine(self, machine_id: str) -> bool:
        """Remove machine from fleet"""
        if machine_id in self.machines:
            machine = self.machines[machine_id]
            del self.machines[machine_id]
            self._save_machines()
            logger.info(f"Deleted machine: {machine.hostname}")
            return True
        return False
    
    # ============================================================================
    # DEPLOYMENT ORCHESTRATION
    # ============================================================================
    
    def create_deployment(self, deployment: RemoteDeployment) -> RemoteDeployment:
        """Create a new remote deployment"""
        # Resolve target machines
        target_machine_ids = self._resolve_target_machines(deployment)
        deployment.target_machines = target_machine_ids
        
        # Update metadata
        deployment.status = DeploymentPhase.PENDING
        deployment.created_at = datetime.now()
        
        # Store deployment
        self.deployments[deployment.deployment_id] = deployment
        self._save_deployments()
        
        # Initialize progress tracking
        self.deployment_progress[deployment.deployment_id] = {}
        
        logger.info(
            f"Created deployment {deployment.deployment_id}: "
            f"{deployment.name} targeting {len(target_machine_ids)} machines"
        )
        
        # Execute if immediate
        if deployment.execute_immediately:
            asyncio.create_task(self._execute_deployment(deployment.deployment_id))
        
        return deployment
    
    def _resolve_target_machines(self, deployment: RemoteDeployment) -> List[str]:
        """Resolve deployment targets to machine IDs"""
        target_ids = set()
        
        # Explicit machine IDs
        if deployment.target_machines:
            target_ids.update(deployment.target_machines)
        
        # By groups
        if deployment.target_groups:
            for machine in self.machines.values():
                if any(g in machine.groups for g in deployment.target_groups):
                    target_ids.add(machine.machine_id)
        
        # By tags
        if deployment.target_tags:
            for machine in self.machines.values():
                if any(t in machine.tags for t in deployment.target_tags):
                    target_ids.add(machine.machine_id)
        
        # All machines
        if deployment.target_all:
            target_ids.update(self.machines.keys())
        
        # Only return online machines
        online_ids = [
            mid for mid in target_ids
            if self.machines.get(mid) and self.machines[mid].status == MachineStatus.ONLINE
        ]
        
        return list(online_ids)
    
    async def _execute_deployment(self, deployment_id: str):
        """Execute deployment asynchronously"""
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            logger.error(f"Deployment not found: {deployment_id}")
            return
        
        deployment.status = DeploymentPhase.VALIDATING
        self._save_deployments()
        
        target_machines = deployment.target_machines or []
        
        try:
            if deployment.parallel_execution:
                # Execute in parallel batches
                batch_size = deployment.max_parallel
                for i in range(0, len(target_machines), batch_size):
                    batch = target_machines[i:i + batch_size]
                    tasks = [
                        self._deploy_to_machine(deployment_id, machine_id)
                        for machine_id in batch
                    ]
                    await asyncio.gather(*tasks)
            else:
                # Sequential execution
                for machine_id in target_machines:
                    await self._deploy_to_machine(deployment_id, machine_id)
            
            # Mark as completed
            deployment.status = DeploymentPhase.COMPLETED
            
        except Exception as e:
            logger.error(f"Deployment {deployment_id} failed: {e}")
            deployment.status = DeploymentPhase.FAILED
        
        finally:
            self._save_deployments()
            await self._broadcast_deployment_update(deployment_id)
    
    async def _deploy_to_machine(self, deployment_id: str, machine_id: str):
        """Deploy to a single machine"""
        machine = self.machines.get(machine_id)
        if not machine:
            logger.warning(f"Machine not found: {machine_id}")
            return
        
        # Create progress tracker
        progress = DeploymentProgress(
            deployment_id=deployment_id,
            machine_id=machine_id,
            hostname=machine.hostname,
            phase=DeploymentPhase.PENDING,
            started_at=datetime.now()
        )
        
        self.deployment_progress[deployment_id][machine_id] = progress
        
        try:
            # Update machine status
            machine.status = MachineStatus.DEPLOYING
            self._save_machines()
            
            # Create command for agent
            command = self._create_deployment_command(deployment_id, machine_id)
            await self._send_command_to_agent(machine_id, command)
            
            # Command execution and progress updates will come from agent
            # via update_deployment_progress()
            
        except Exception as e:
            logger.error(f"Failed to deploy to {machine.hostname}: {e}")
            progress.phase = DeploymentPhase.FAILED
            progress.errors.append(str(e))
            progress.completed_at = datetime.now()
            
            machine.status = MachineStatus.ERROR
            self._save_machines()
            
            await self._broadcast_deployment_progress(progress)
    
    def _create_deployment_command(
        self, deployment_id: str, machine_id: str
    ) -> AgentCommand:
        """Create deployment command for agent"""
        deployment = self.deployments[deployment_id]
        
        return AgentCommand(
            command_type="deploy",
            payload={
                "deployment_id": deployment_id,
                "policy_package_id": deployment.policy_package_id,
                "policy_ids": deployment.policy_ids,
                "create_backup": deployment.create_backup,
                "verify_before_apply": deployment.verify_before_apply,
                "rollback_on_failure": deployment.rollback_on_failure
            },
            timeout_seconds=3600
        )
    
    async def _send_command_to_agent(self, machine_id: str, command: AgentCommand):
        """Queue command for agent to pick up"""
        if machine_id not in self.command_queue:
            self.command_queue[machine_id] = []
        
        self.command_queue[machine_id].append(command)
        logger.info(f"Queued command {command.command_id} for machine {machine_id}")
    
    def get_pending_commands(self, machine_id: str) -> List[AgentCommand]:
        """Get pending commands for an agent"""
        commands = self.command_queue.get(machine_id, [])
        
        # Clear the queue
        self.command_queue[machine_id] = []
        
        return commands
    
    def update_deployment_progress(self, progress: DeploymentProgress):
        """Update deployment progress from agent"""
        deployment_id = progress.deployment_id
        machine_id = progress.machine_id
        
        if deployment_id not in self.deployment_progress:
            self.deployment_progress[deployment_id] = {}
        
        self.deployment_progress[deployment_id][machine_id] = progress
        
        # Update machine status
        machine = self.machines.get(machine_id)
        if machine:
            if progress.phase == DeploymentPhase.COMPLETED:
                machine.status = MachineStatus.ONLINE
                machine.policies_applied = progress.policies_applied
                machine.policies_failed = progress.policies_failed
            elif progress.phase == DeploymentPhase.FAILED:
                machine.status = MachineStatus.ERROR
            else:
                machine.status = MachineStatus.DEPLOYING
            
            self._save_machines()
        
        # Broadcast update
        asyncio.create_task(self._broadcast_deployment_progress(progress))
    
    def get_deployment_summary(self, deployment_id: str) -> Optional[DeploymentSummary]:
        """Get overall deployment status"""
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            return None
        
        progress_dict = self.deployment_progress.get(deployment_id, {})
        progress_list = list(progress_dict.values())
        
        # Count statuses
        succeeded = sum(1 for p in progress_list if p.phase == DeploymentPhase.COMPLETED)
        failed = sum(1 for p in progress_list if p.phase == DeploymentPhase.FAILED)
        in_progress = sum(
            1 for p in progress_list
            if p.phase not in [DeploymentPhase.COMPLETED, DeploymentPhase.FAILED, DeploymentPhase.PENDING]
        )
        pending = sum(1 for p in progress_list if p.phase == DeploymentPhase.PENDING)
        
        return DeploymentSummary(
            deployment_id=deployment_id,
            name=deployment.name,
            status=deployment.status,
            total_machines=len(deployment.target_machines or []),
            succeeded=succeeded,
            failed=failed,
            in_progress=in_progress,
            pending=pending,
            started_at=deployment.created_at,
            machine_results=progress_list
        )
    
    def list_deployments(
        self,
        status: Optional[DeploymentPhase] = None,
        limit: int = 50
    ) -> List[RemoteDeployment]:
        """List deployments with optional filter"""
        deployments = list(self.deployments.values())
        
        if status:
            deployments = [d for d in deployments if d.status == status]
        
        # Sort by created_at descending
        deployments.sort(key=lambda d: d.created_at, reverse=True)
        
        return deployments[:limit]
    
    # ============================================================================
    # FLEET STATISTICS
    # ============================================================================
    
    def get_fleet_statistics(self) -> FleetStatistics:
        """Calculate fleet-wide statistics"""
        machines = list(self.machines.values())
        
        # Count by status
        online = sum(1 for m in machines if m.status == MachineStatus.ONLINE)
        offline = sum(1 for m in machines if m.status == MachineStatus.OFFLINE)
        deploying = sum(1 for m in machines if m.status == MachineStatus.DEPLOYING)
        error = sum(1 for m in machines if m.status == MachineStatus.ERROR)
        
        # Compliance
        compliance_scores = [m.compliance_score for m in machines if m.compliance_score is not None]
        avg_compliance = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0.0
        compliant = sum(1 for score in compliance_scores if score >= 80)
        non_compliant = sum(1 for score in compliance_scores if score < 80)
        
        # Deployments
        active = sum(
            1 for d in self.deployments.values()
            if d.status in [DeploymentPhase.PENDING, DeploymentPhase.VALIDATING, DeploymentPhase.APPLYING]
        )
        
        today = datetime.now().date()
        completed_today = sum(
            1 for d in self.deployments.values()
            if d.status == DeploymentPhase.COMPLETED and d.created_at.date() == today
        )
        failed_today = sum(
            1 for d in self.deployments.values()
            if d.status == DeploymentPhase.FAILED and d.created_at.date() == today
        )
        
        # Machines needing attention
        needing_attention = [
            m.hostname for m in machines
            if m.status == MachineStatus.ERROR or
            (m.compliance_score is not None and m.compliance_score < 60)
        ]
        
        return FleetStatistics(
            total_machines=len(machines),
            online_machines=online,
            offline_machines=offline,
            deploying_machines=deploying,
            error_machines=error,
            average_compliance_score=round(avg_compliance, 2),
            compliant_machines=compliant,
            non_compliant_machines=non_compliant,
            active_deployments=active,
            completed_deployments_today=completed_today,
            failed_deployments_today=failed_today,
            machines_needing_attention=needing_attention
        )
    
    # ============================================================================
    # WEBSOCKET BROADCASTING
    # ============================================================================
    
    async def _broadcast_machine_update(self, machine: Machine):
        """Broadcast machine status update via WebSocket"""
        message = {
            "message_type": "machine_status",
            "timestamp": datetime.now().isoformat(),
            "data": machine.dict()
        }
        await self._broadcast_to_websockets(message)
    
    async def _broadcast_deployment_update(self, deployment_id: str):
        """Broadcast deployment status update"""
        summary = self.get_deployment_summary(deployment_id)
        if summary:
            message = {
                "message_type": "deployment_update",
                "timestamp": datetime.now().isoformat(),
                "data": summary.dict()
            }
            await self._broadcast_to_websockets(message)
    
    async def _broadcast_deployment_progress(self, progress: DeploymentProgress):
        """Broadcast individual machine progress"""
        message = {
            "message_type": "deployment_progress",
            "timestamp": datetime.now().isoformat(),
            "data": progress.dict()
        }
        await self._broadcast_to_websockets(message)
    
    async def _broadcast_to_websockets(self, message: dict):
        """Send message to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
        
        disconnected = set()
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.websocket_connections -= disconnected
    
    def add_websocket(self, websocket):
        """Register a WebSocket connection"""
        self.websocket_connections.add(websocket)
        logger.info("WebSocket connected")
    
    def remove_websocket(self, websocket):
        """Unregister a WebSocket connection"""
        self.websocket_connections.discard(websocket)
        logger.info("WebSocket disconnected")
    
    # ============================================================================
    # BACKGROUND TASKS
    # ============================================================================
    
    async def check_offline_machines(self):
        """Mark machines offline if no heartbeat received"""
        timeout_minutes = 5
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        
        for machine in self.machines.values():
            if machine.last_seen < cutoff_time and machine.status == MachineStatus.ONLINE:
                machine.status = MachineStatus.OFFLINE
                logger.warning(f"Machine went offline: {machine.hostname}")
                await self._broadcast_machine_update(machine)
        
        self._save_machines()
