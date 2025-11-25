import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Grid, Card, CardContent, Button, Chip, 
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, LinearProgress, IconButton, Tooltip, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Select, MenuItem, FormControl,
  InputLabel, Divider, Alert, Badge, Avatar, Stack
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Computer as ComputerIcon,
  CloudDone as CloudDoneIcon,
  CloudOff as CloudOffIcon,
  Error as ErrorIcon,
  CloudUpload as DeployIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Schedule as ScheduleIcon,
  Speed as SpeedIcon,
  Security as SecurityIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const FleetDashboard = () => {
  // State management
  const [machines, setMachines] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [selectedMachine, setSelectedMachine] = useState(null);
  const [deploymentDialogOpen, setDeploymentDialogOpen] = useState(false);
  
  // WebSocket connection
  const [ws, setWs] = useState(null);

  // Initialize WebSocket connection
  useEffect(() => {
    const websocket = new WebSocket(`ws://localhost:8000/ws/fleet?client_id=dashboard_${Date.now()}`);
    
    websocket.onopen = () => {
      console.log('✅ WebSocket connected');
      setWsConnected(true);
      
      // Subscribe to channels
      websocket.send(JSON.stringify({
        type: 'subscribe',
        channels: ['fleet_status', 'machine_updates', 'deployments']
      }));
    };
    
    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      console.log('📩 WebSocket message:', message);
      
      handleWebSocketMessage(message);
    };
    
    websocket.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      setWsConnected(false);
    };
    
    websocket.onclose = () => {
      console.log('🔌 WebSocket disconnected');
      setWsConnected(false);
    };
    
    setWs(websocket);
    
    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message) => {
    switch (message.message_type) {
      case 'machine_status':
        // Update single machine in the list
        setMachines(prev => {
          const index = prev.findIndex(m => m.machine_id === message.data.machine_id);
          if (index >= 0) {
            const updated = [...prev];
            updated[index] = message.data;
            return updated;
          } else {
            return [...prev, message.data];
          }
        });
        break;
      
      case 'fleet_statistics':
        setStatistics(message.data);
        break;
      
      case 'deployment_update':
        // Update deployment in the list
        setDeployments(prev => {
          const index = prev.findIndex(d => d.deployment_id === message.data.deployment_id);
          if (index >= 0) {
            const updated = [...prev];
            updated[index] = message.data;
            return updated;
          } else {
            return [...prev, message.data];
          }
        });
        break;
      
      case 'deployment_progress':
        // Real-time progress updates
        console.log('📈 Deployment progress:', message.data);
        break;
      
      default:
        console.log('Unknown message type:', message.message_type);
    }
  }, []);

  // Fetch fleet data
  const fetchFleetData = async () => {
    setLoading(true);
    try {
      const [machinesRes, statsRes, deploymentsRes] = await Promise.all([
        axios.get(`${API_BASE}/api/fleet/machines`),
        axios.get(`${API_BASE}/api/fleet/statistics`),
        axios.get(`${API_BASE}/api/fleet/deployments?limit=10`)
      ]);
      
      setMachines(machinesRes.data);
      setStatistics(statsRes.data);
      setDeployments(deploymentsRes.data);
    } catch (error) {
      console.error('Error fetching fleet data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Initial data load
  useEffect(() => {
    fetchFleetData();
  }, []);

  // Get status color and icon
  const getStatusDisplay = (status) => {
    const displays = {
      online: { color: 'success', icon: <CloudDoneIcon />, label: 'Online' },
      offline: { color: 'default', icon: <CloudOffIcon />, label: 'Offline' },
      deploying: { color: 'info', icon: <DeployIcon />, label: 'Deploying' },
      error: { color: 'error', icon: <ErrorIcon />, label: 'Error' }
    };
    return displays[status] || displays.offline;
  };

  // Get compliance color
  const getComplianceColor = (score) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>
            Fleet Management
          </Typography>
          <Badge
            color={wsConnected ? 'success' : 'error'}
            variant="dot"
            sx={{ ml: 1 }}
          >
            <Chip
              label={wsConnected ? 'Live Updates' : 'Disconnected'}
              size="small"
              color={wsConnected ? 'success' : 'default'}
            />
          </Badge>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchFleetData}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<DeployIcon />}
            onClick={() => setDeploymentDialogOpen(true)}
          >
            New Deployment
          </Button>
        </Box>
      </Box>

      {/* Statistics Cards */}
      {statistics && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <ComputerIcon color="primary" />
                  <Typography variant="h6" color="text.secondary">
                    Total Machines
                  </Typography>
                </Box>
                <Typography variant="h3" sx={{ fontWeight: 700 }}>
                  {statistics.total_machines}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {statistics.online_machines} online • {statistics.offline_machines} offline
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <SecurityIcon color="success" />
                  <Typography variant="h6" color="text.secondary">
                    Avg Compliance
                  </Typography>
                </Box>
                <Typography variant="h3" sx={{ fontWeight: 700, color: 'success.main' }}>
                  {statistics.average_compliance_score}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {statistics.compliant_machines} compliant • {statistics.non_compliant_machines} non-compliant
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <DeployIcon color="info" />
                  <Typography variant="h6" color="text.secondary">
                    Active Deployments
                  </Typography>
                </Box>
                <Typography variant="h3" sx={{ fontWeight: 700, color: 'info.main' }}>
                  {statistics.active_deployments}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {statistics.completed_deployments_today} completed today
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <ErrorIcon color="error" />
                  <Typography variant="h6" color="text.secondary">
                    Needs Attention
                  </Typography>
                </Box>
                <Typography variant="h3" sx={{ fontWeight: 700, color: 'error.main' }}>
                  {statistics.machines_needing_attention.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {statistics.error_machines} errors • {statistics.deploying_machines} deploying
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Machines Table */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Fleet Machines
          </Typography>
          
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Hostname</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>OS Version</TableCell>
                  <TableCell>IP Address</TableCell>
                  <TableCell>Compliance</TableCell>
                  <TableCell>CPU</TableCell>
                  <TableCell>Memory</TableCell>
                  <TableCell>Last Seen</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {machines.map((machine) => {
                  const statusDisplay = getStatusDisplay(machine.status);
                  
                  return (
                    <TableRow
                      key={machine.machine_id}
                      hover
                      sx={{ cursor: 'pointer' }}
                      onClick={() => setSelectedMachine(machine)}
                    >
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
                            {machine.hostname.charAt(0).toUpperCase()}
                          </Avatar>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {machine.hostname}
                          </Typography>
                        </Box>
                      </TableCell>
                      
                      <TableCell>
                        <Chip
                          icon={statusDisplay.icon}
                          label={statusDisplay.label}
                          color={statusDisplay.color}
                          size="small"
                        />
                      </TableCell>
                      
                      <TableCell>
                        <Typography variant="body2">
                          {machine.os_version}
                        </Typography>
                      </TableCell>
                      
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {machine.ip_address}
                        </Typography>
                      </TableCell>
                      
                      <TableCell>
                        {machine.compliance_score !== null ? (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <LinearProgress
                              variant="determinate"
                              value={machine.compliance_score}
                              color={getComplianceColor(machine.compliance_score)}
                              sx={{ width: 80, height: 8, borderRadius: 1 }}
                            />
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {machine.compliance_score}%
                            </Typography>
                          </Box>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            N/A
                          </Typography>
                        )}
                      </TableCell>
                      
                      <TableCell>
                        {machine.cpu_usage !== null ? (
                          <Typography variant="body2">
                            {machine.cpu_usage}%
                          </Typography>
                        ) : (
                          <Typography variant="body2" color="text.secondary">N/A</Typography>
                        )}
                      </TableCell>
                      
                      <TableCell>
                        {machine.memory_used !== null ? (
                          <Typography variant="body2">
                            {Math.round(machine.memory_used / 1024)} GB
                          </Typography>
                        ) : (
                          <Typography variant="body2" color="text.secondary">N/A</Typography>
                        )}
                      </TableCell>
                      
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {new Date(machine.last_seen).toLocaleString()}
                        </Typography>
                      </TableCell>
                      
                      <TableCell>
                        <Tooltip title="View Details">
                          <IconButton size="small" color="primary">
                            <InfoIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
          
          {machines.length === 0 && !loading && (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No machines registered yet
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Recent Deployments */}
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Recent Deployments
          </Typography>
          
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Progress</TableCell>
                  <TableCell>Succeeded</TableCell>
                  <TableCell>Failed</TableCell>
                  <TableCell>Started</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {deployments.map((deployment) => (
                  <TableRow key={deployment.deployment_id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {deployment.name}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Chip
                        label={deployment.status}
                        color={
                          deployment.status === 'completed' ? 'success' :
                          deployment.status === 'failed' ? 'error' :
                          'info'
                        }
                        size="small"
                      />
                    </TableCell>
                    
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={
                            (deployment.succeeded / deployment.total_machines) * 100
                          }
                          sx={{ width: 100, height: 8, borderRadius: 1 }}
                        />
                        <Typography variant="body2">
                          {deployment.succeeded}/{deployment.total_machines}
                        </Typography>
                      </Box>
                    </TableCell>
                    
                    <TableCell>
                      <Chip
                        icon={<CheckCircleIcon />}
                        label={deployment.succeeded}
                        color="success"
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    
                    <TableCell>
                      <Chip
                        icon={<CancelIcon />}
                        label={deployment.failed}
                        color="error"
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {new Date(deployment.started_at).toLocaleString()}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          
          {deployments.length === 0 && !loading && (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No deployments yet
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Loading overlay */}
      {loading && (
        <Box sx={{ width: '100%', mt: 2 }}>
          <LinearProgress />
        </Box>
      )}
    </Box>
  );
};

export default FleetDashboard;
