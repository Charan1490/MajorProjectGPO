import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  IconButton,
  Badge,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Alert,
  Tooltip,
  Button,
  CircularProgress
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Speed as MetricsIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Remove as NeutralIcon,
  Refresh as RefreshIcon,
  SignalCellularAlt as SignalIcon
} from '@mui/icons-material';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  Filler
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  ChartTooltip,
  Legend,
  Filler
);

const RealtimeMonitor = () => {
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [events, setEvents] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [complianceTrends, setComplianceTrends] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [error, setError] = useState(null);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // Connect to WebSocket
  const connectWebSocket = () => {
    if (connecting || connected) return;
    
    setConnecting(true);
    setError(null);

    try {
      const wsUrl = 'ws://localhost:8000/ws/realtime';
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('✅ WebSocket connected');
        setConnected(true);
        setConnecting(false);
        reconnectAttempts.current = 0;
        
        // Request initial statistics
        ws.send(JSON.stringify({ type: 'request_stats' }));
        
        // Setup ping interval to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000); // Ping every 30 seconds
        
        ws.pingInterval = pingInterval;
      };
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          switch (message.type) {
            case 'initial_state':
              handleInitialState(message.data);
              break;
            case 'event':
              handleEvent(message.data);
              break;
            case 'metrics':
              handleMetrics(message.data);
              break;
            case 'compliance_trend':
              handleComplianceTrend(message.data);
              break;
            case 'statistics':
              setStatistics(message.data);
              break;
            case 'pong':
              // Connection keepalive response
              break;
            default:
              console.log('Unknown message type:', message.type);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };
      
      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        setError('WebSocket connection error');
      };
      
      ws.onclose = () => {
        console.log('❌ WebSocket disconnected');
        setConnected(false);
        setConnecting(false);
        
        // Clear ping interval
        if (ws.pingInterval) {
          clearInterval(ws.pingInterval);
        }
        
        // Attempt reconnection
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, delay);
        } else {
          setError('Failed to connect after multiple attempts. Please refresh the page.');
        }
      };
      
      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setError('Failed to establish WebSocket connection');
      setConnecting(false);
    }
  };

  // Disconnect WebSocket
  const disconnectWebSocket = () => {
    if (wsRef.current) {
      if (wsRef.current.pingInterval) {
        clearInterval(wsRef.current.pingInterval);
      }
      wsRef.current.close();
      wsRef.current = null;
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    setConnected(false);
    reconnectAttempts.current = 0;
  };

  // Handle initial state
  const handleInitialState = (data) => {
    setStatistics(data);
    if (data.recent_metrics) {
      setMetrics(data.recent_metrics);
    }
    if (data.compliance_trend) {
      setComplianceTrends(data.compliance_trend);
    }
  };

  // Handle new event
  const handleEvent = (data) => {
    setEvents(prev => [data, ...prev].slice(0, 50)); // Keep last 50 events
  };

  // Handle metrics update
  const handleMetrics = (data) => {
    setMetrics(prev => [...prev, data].slice(-30)); // Keep last 30 data points
  };

  // Handle compliance trend update
  const handleComplianceTrend = (data) => {
    setComplianceTrends(prev => [...prev, data].slice(-30));
  };

  // Connect on mount
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      disconnectWebSocket();
    };
  }, []);

  // Get severity icon and color
  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'success':
        return <SuccessIcon color="success" />;
      case 'error':
        return <ErrorIcon color="error" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'info':
      default:
        return <InfoIcon color="info" />;
    }
  };

  // Get event type label
  const getEventTypeLabel = (eventType) => {
    const labels = {
      'policy_change': 'Policy',
      'deployment_status': 'Deployment',
      'audit_result': 'Audit',
      'system_alert': 'System'
    };
    return labels[eventType] || eventType;
  };

  // Prepare metrics chart data
  const metricsChartData = {
    labels: metrics.map(m => {
      const time = new Date(m.timestamp);
      return time.toLocaleTimeString();
    }),
    datasets: [
      {
        label: 'CPU Usage (%)',
        data: metrics.map(m => m.cpu_percent),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        fill: true,
        tension: 0.4
      },
      {
        label: 'Memory Usage (%)',
        data: metrics.map(m => m.memory_percent),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        fill: true,
        tension: 0.4
      }
    ]
  };

  const metricsChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'System Metrics (Real-Time)'
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100
      }
    }
  };

  // Prepare compliance trend chart data
  const complianceChartData = {
    labels: complianceTrends.map(c => {
      const time = new Date(c.timestamp);
      return time.toLocaleTimeString();
    }),
    datasets: [
      {
        label: 'Compliance Rate (%)',
        data: complianceTrends.map(c => c.compliance_rate),
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        fill: true,
        tension: 0.4
      }
    ]
  };

  const complianceChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Compliance Trend'
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100
      }
    }
  };

  return (
    <Box>
      {/* Connection Status */}
      <Paper sx={{ p: 2, mb: 2, bgcolor: connected ? 'success.main' : error ? 'error.main' : 'warning.main', color: 'white' }}>
        <Grid container alignItems="center" spacing={2}>
          <Grid item>
            <SignalIcon />
          </Grid>
          <Grid item xs>
            <Typography variant="body1">
              {connected ? '🟢 Connected to Real-Time Monitoring' :
               connecting ? '🟡 Connecting...' :
               error ? `🔴 ${error}` :
               '🔴 Disconnected'}
            </Typography>
          </Grid>
          <Grid item>
            {!connected && !connecting && (
              <Button 
                variant="contained" 
                color="inherit" 
                startIcon={<RefreshIcon />}
                onClick={connectWebSocket}
              >
                Reconnect
              </Button>
            )}
          </Grid>
        </Grid>
      </Paper>

      {/* Statistics Cards */}
      {statistics && (
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Active Connections
                </Typography>
                <Typography variant="h4">
                  {statistics.active_connections}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Events
                </Typography>
                <Typography variant="h4">
                  {statistics.total_events}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Policies Processed
                </Typography>
                <Typography variant="h4">
                  {statistics.policies_processed}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Active Deployments
                </Typography>
                <Typography variant="h4">
                  {statistics.active_deployments}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Charts */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: 300 }}>
            {metrics.length > 0 ? (
              <Line data={metricsChartData} options={metricsChartOptions} />
            ) : (
              <Box display="flex" alignItems="center" justifyContent="center" height="100%">
                <Typography color="textSecondary">Waiting for metrics data...</Typography>
              </Box>
            )}
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: 300 }}>
            {complianceTrends.length > 0 ? (
              <Line data={complianceChartData} options={complianceChartOptions} />
            ) : (
              <Box display="flex" alignItems="center" justifyContent="center" height="100%">
                <Typography color="textSecondary">Waiting for compliance data...</Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Event Feed */}
      <Paper sx={{ p: 2 }}>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Typography variant="h6">
            <Badge badgeContent={events.length} color="primary" max={999}>
              <NotificationsIcon sx={{ mr: 1 }} />
            </Badge>
            Live Event Feed
          </Typography>
        </Box>
        
        <Divider sx={{ mb: 2 }} />
        
        <List sx={{ maxHeight: 400, overflow: 'auto' }}>
          {events.length === 0 && (
            <ListItem>
              <ListItemText 
                primary={<Typography color="textSecondary" align="center">No events yet</Typography>}
              />
            </ListItem>
          )}
          
          {events.map((event, index) => (
            <React.Fragment key={event.event_id}>
              <ListItem alignItems="flex-start">
                <ListItemIcon>
                  {getSeverityIcon(event.severity)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="subtitle2">
                        {event.title}
                      </Typography>
                      <Chip 
                        label={getEventTypeLabel(event.event_type)}
                        size="small"
                        color={event.severity === 'error' ? 'error' : event.severity === 'warning' ? 'warning' : 'default'}
                      />
                      <Typography variant="caption" color="textSecondary">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </Typography>
                    </Box>
                  }
                  secondary={event.message}
                />
              </ListItem>
              {index < events.length - 1 && <Divider variant="inset" component="li" />}
            </React.Fragment>
          ))}
        </List>
      </Paper>
    </Box>
  );
};

export default RealtimeMonitor;
