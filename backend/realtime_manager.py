"""
Real-Time Monitoring Manager for Module 3 Dashboard
Provides WebSocket support for live updates of:
- Policy changes
- Deployment status
- Audit results
- System metrics
- Compliance trends
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
from collections import deque
import psutil
import time

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_connections: int
    policies_processed: int
    deployments_active: int
    
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class RealtimeEvent:
    """Real-time event notification"""
    event_id: str
    event_type: str  # policy_change, deployment_status, audit_result, system_alert
    timestamp: str
    severity: str  # info, warning, error, success
    title: str
    message: str
    data: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class ComplianceTrend:
    """Compliance trend data point"""
    timestamp: str
    total_policies: int
    compliant: int
    non_compliant: int
    pending: int
    compliance_rate: float
    
    def to_dict(self) -> dict:
        return asdict(self)

class RealtimeMonitoringManager:
    """Manages real-time monitoring and WebSocket connections"""
    
    def __init__(self, max_history: int = 100):
        """Initialize real-time monitoring manager"""
        self.active_connections: Set = set()
        self.event_history: deque = deque(maxlen=max_history)
        self.metrics_history: deque = deque(maxlen=100)
        self.compliance_history: deque = deque(maxlen=50)
        
        # Counters for statistics
        self.total_policies_processed = 0
        self.active_deployments = 0
        self.total_events = 0
        
        # Background task references
        self.metrics_task = None
        self.monitoring_active = False
    
    async def connect_client(self, websocket):
        """Register a new WebSocket client"""
        self.active_connections.add(websocket)
        
        # Send initial state to new client
        await self.send_initial_state(websocket)
        
        # Send recent events
        for event in list(self.event_history):
            await websocket.send_json({
                "type": "event",
                "data": event.to_dict()
            })
    
    def disconnect_client(self, websocket):
        """Unregister a WebSocket client"""
        self.active_connections.discard(websocket)
    
    async def send_initial_state(self, websocket):
        """Send initial state to newly connected client"""
        initial_state = {
            "type": "initial_state",
            "data": {
                "active_connections": len(self.active_connections),
                "total_events": self.total_events,
                "policies_processed": self.total_policies_processed,
                "active_deployments": self.active_deployments,
                "recent_metrics": [m.to_dict() for m in list(self.metrics_history)[-10:]],
                "compliance_trend": [c.to_dict() for c in list(self.compliance_history)[-10:]]
            }
        }
        await websocket.send_json(initial_state)
    
    async def broadcast_event(self, event: RealtimeEvent):
        """Broadcast event to all connected clients"""
        self.event_history.append(event)
        self.total_events += 1
        
        message = {
            "type": "event",
            "data": event.to_dict()
        }
        
        # Send to all connected clients
        disconnected = set()
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.active_connections -= disconnected
    
    async def broadcast_metrics(self, metrics: SystemMetrics):
        """Broadcast system metrics to all connected clients"""
        self.metrics_history.append(metrics)
        
        message = {
            "type": "metrics",
            "data": metrics.to_dict()
        }
        
        disconnected = set()
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.add(websocket)
        
        self.active_connections -= disconnected
    
    async def broadcast_compliance_trend(self, trend: ComplianceTrend):
        """Broadcast compliance trend to all connected clients"""
        self.compliance_history.append(trend)
        
        message = {
            "type": "compliance_trend",
            "data": trend.to_dict()
        }
        
        disconnected = set()
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.add(websocket)
        
        self.active_connections -= disconnected
    
    def get_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                active_connections=len(self.active_connections),
                policies_processed=self.total_policies_processed,
                deployments_active=self.active_deployments
            )
        except Exception as e:
            print(f"Error collecting metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                active_connections=len(self.active_connections),
                policies_processed=self.total_policies_processed,
                deployments_active=self.active_deployments
            )
    
    async def start_monitoring(self):
        """Start background monitoring tasks"""
        self.monitoring_active = True
        
        # Start metrics collection
        asyncio.create_task(self._collect_metrics_loop())
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks"""
        self.monitoring_active = False
    
    async def _collect_metrics_loop(self):
        """Background loop to collect and broadcast metrics"""
        while self.monitoring_active:
            try:
                metrics = self.get_system_metrics()
                await self.broadcast_metrics(metrics)
                await asyncio.sleep(5)  # Collect metrics every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in metrics loop: {e}")
                await asyncio.sleep(5)
    
    async def notify_policy_change(
        self, 
        policy_id: str, 
        policy_name: str, 
        change_type: str,
        user: str = "system"
    ):
        """Notify about policy changes"""
        event = RealtimeEvent(
            event_id=f"policy_{policy_id}_{int(time.time())}",
            event_type="policy_change",
            timestamp=datetime.now().isoformat(),
            severity="info",
            title=f"Policy {change_type.title()}",
            message=f"Policy '{policy_name}' was {change_type} by {user}",
            data={
                "policy_id": policy_id,
                "policy_name": policy_name,
                "change_type": change_type,
                "user": user
            }
        )
        
        self.total_policies_processed += 1
        await self.broadcast_event(event)
    
    async def notify_deployment_status(
        self, 
        deployment_id: str, 
        status: str,
        package_name: str,
        details: Optional[str] = None
    ):
        """Notify about deployment status changes"""
        severity_map = {
            "pending": "info",
            "running": "info",
            "completed": "success",
            "failed": "error",
            "cancelled": "warning"
        }
        
        event = RealtimeEvent(
            event_id=f"deploy_{deployment_id}_{int(time.time())}",
            event_type="deployment_status",
            timestamp=datetime.now().isoformat(),
            severity=severity_map.get(status, "info"),
            title=f"Deployment {status.title()}",
            message=f"Deployment '{package_name}' is {status}" + (f": {details}" if details else ""),
            data={
                "deployment_id": deployment_id,
                "status": status,
                "package_name": package_name,
                "details": details
            }
        )
        
        if status in ["running", "pending"]:
            self.active_deployments += 1
        elif status in ["completed", "failed", "cancelled"]:
            self.active_deployments = max(0, self.active_deployments - 1)
        
        await self.broadcast_event(event)
    
    async def notify_audit_result(
        self, 
        audit_id: str, 
        compliant_count: int,
        non_compliant_count: int,
        total_count: int
    ):
        """Notify about audit completion"""
        compliance_rate = (compliant_count / total_count * 100) if total_count > 0 else 0
        
        event = RealtimeEvent(
            event_id=f"audit_{audit_id}_{int(time.time())}",
            event_type="audit_result",
            timestamp=datetime.now().isoformat(),
            severity="success" if compliance_rate >= 80 else "warning" if compliance_rate >= 50 else "error",
            title="Audit Completed",
            message=f"Compliance: {compliance_rate:.1f}% ({compliant_count}/{total_count} policies)",
            data={
                "audit_id": audit_id,
                "compliant": compliant_count,
                "non_compliant": non_compliant_count,
                "total": total_count,
                "compliance_rate": compliance_rate
            }
        )
        
        await self.broadcast_event(event)
    
    async def notify_system_alert(
        self, 
        severity: str,
        title: str,
        message: str,
        data: Optional[Dict] = None
    ):
        """Send system alert"""
        event = RealtimeEvent(
            event_id=f"alert_{int(time.time())}",
            event_type="system_alert",
            timestamp=datetime.now().isoformat(),
            severity=severity,
            title=title,
            message=message,
            data=data or {}
        )
        
        await self.broadcast_event(event)
    
    async def update_compliance_trend(
        self,
        total_policies: int,
        compliant: int,
        non_compliant: int,
        pending: int
    ):
        """Update compliance trend data"""
        compliance_rate = (compliant / total_policies * 100) if total_policies > 0 else 0
        
        trend = ComplianceTrend(
            timestamp=datetime.now().isoformat(),
            total_policies=total_policies,
            compliant=compliant,
            non_compliant=non_compliant,
            pending=pending,
            compliance_rate=compliance_rate
        )
        
        await self.broadcast_compliance_trend(trend)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current monitoring statistics"""
        recent_metrics = list(self.metrics_history)[-10:] if self.metrics_history else []
        recent_events = list(self.event_history)[-20:] if self.event_history else []
        recent_compliance = list(self.compliance_history)[-10:] if self.compliance_history else []
        
        return {
            "active_connections": len(self.active_connections),
            "total_events": self.total_events,
            "policies_processed": self.total_policies_processed,
            "active_deployments": self.active_deployments,
            "metrics_history_count": len(self.metrics_history),
            "events_history_count": len(self.event_history),
            "compliance_history_count": len(self.compliance_history),
            "recent_metrics": [m.to_dict() for m in recent_metrics],
            "recent_events": [e.to_dict() for e in recent_events],
            "recent_compliance": [c.to_dict() for c in recent_compliance],
            "monitoring_active": self.monitoring_active
        }

# Global instance
realtime_manager = RealtimeMonitoringManager()
