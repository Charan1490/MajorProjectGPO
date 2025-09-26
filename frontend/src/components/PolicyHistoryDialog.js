/**
 * Policy History Dialog Component
 * Displays change history with diff view and revert capabilities
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Paper,
  Chip,
  Divider,
  IconButton,
  Collapse,
  Alert,
  CircularProgress,
  Tooltip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import {
  History as HistoryIcon,
  Edit as EditIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  RestoreFromTrash as RestoreIcon,
  FiberManualRecord as DotIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const changeTypeIcons = {
  created: AddIcon,
  updated: EditIcon,
  deleted: DeleteIcon,
  status_changed: EditIcon,
  value_changed: EditIcon,
  tagged: AddIcon,
  untagged: DeleteIcon,
  grouped: AddIcon,
  ungrouped: DeleteIcon,
  bulk_update: EditIcon,
  imported: AddIcon,
  exported: HistoryIcon
};

const changeTypeColors = {
  created: 'success',
  updated: 'primary',
  deleted: 'error',
  status_changed: 'warning',
  value_changed: 'info',
  tagged: 'success',
  untagged: 'error',
  grouped: 'success',
  ungrouped: 'error',
  bulk_update: 'secondary',
  imported: 'primary',
  exported: 'default'
};

const ChangeDetails = ({ change, onRevert }) => {
  const [expanded, setExpanded] = useState(false);
  
  const formatValue = (value) => {
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value || 'N/A');
  };
  
  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };
  
  const canRevert = ['updated', 'status_changed', 'value_changed'].includes(change.change_type);
  
  return (
    <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Chip
              label={change.change_type.replace('_', ' ').toUpperCase()}
              color={changeTypeColors[change.change_type] || 'default'}
              size="small"
              sx={{ mr: 2 }}
            />
            <Typography variant="body2" color="text.secondary">
              {formatTimestamp(change.timestamp)}
            </Typography>
          </Box>
          
          <Typography variant="body2" sx={{ mb: 1 }}>
            Changed by: <strong>{change.user_id}</strong>
          </Typography>
          
          {change.notes && (
            <Typography variant="body2" sx={{ mb: 1, fontStyle: 'italic' }}>
              Notes: {change.notes}
            </Typography>
          )}
          
          {change.batch_id && (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
              Batch ID: {change.batch_id}
            </Typography>
          )}
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          {canRevert && (
            <Tooltip title="Revert this change">
              <IconButton
                size="small"
                onClick={() => onRevert(change.history_id)}
                color="primary"
              >
                <RestoreIcon />
              </IconButton>
            </Tooltip>
          )}
          <IconButton
            size="small"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
      </Box>
      
      <Collapse in={expanded}>
        <Divider sx={{ mb: 2 }} />
        
        {change.changed_fields && change.changed_fields.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Changed Fields:
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {change.changed_fields.map((field) => (
                <Chip key={field} label={field} size="small" variant="outlined" />
              ))}
            </Box>
          </Box>
        )}
        
        {(change.old_value || change.new_value) && (
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Value Changes:
            </Typography>
            
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              {change.old_value && (
                <Box>
                  <Typography variant="caption" color="error.main" sx={{ fontWeight: 'bold' }}>
                    Before:
                  </Typography>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 1,
                      backgroundColor: 'error.light',
                      opacity: 0.1,
                      maxHeight: 200,
                      overflow: 'auto'
                    }}
                  >
                    <pre style={{ margin: 0, fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
                      {formatValue(change.old_value)}
                    </pre>
                  </Paper>
                </Box>
              )}
              
              {change.new_value && (
                <Box>
                  <Typography variant="caption" color="success.main" sx={{ fontWeight: 'bold' }}>
                    After:
                  </Typography>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 1,
                      backgroundColor: 'success.light',
                      opacity: 0.1,
                      maxHeight: 200,
                      overflow: 'auto'
                    }}
                  >
                    <pre style={{ margin: 0, fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
                      {formatValue(change.new_value)}
                    </pre>
                  </Paper>
                </Box>
              )}
            </Box>
          </Box>
        )}
      </Collapse>
    </Paper>
  );
};

const PolicyHistoryDialog = ({ open, onClose, policyId, policyName }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  useEffect(() => {
    if (open && policyId) {
      fetchHistory();
    }
  }, [open, policyId]);
  
  const canRevert = (change) => {
    return ['status_changed', 'value_changed', 'tagged', 'untagged', 'updated'].includes(change.change_type);
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };
  
  const fetchHistory = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await axios.get(`${API_BASE_URL}/dashboard/policies/${policyId}/history`);
      if (response.data.success) {
        setHistory(response.data.data.history || []);
      } else {
        setError(response.data.error || 'Failed to fetch history');
      }
    } catch (err) {
      setError('Error fetching policy history');
      console.error('Error fetching history:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const handleRevert = async (historyId) => {
    if (!window.confirm('Are you sure you want to revert this change? This action cannot be undone.')) {
      return;
    }
    
    try {
      const response = await axios.post(`${API_BASE_URL}/dashboard/history/${historyId}/revert`);
      if (response.data.success) {
        // Refresh history to show the revert
        await fetchHistory();
        alert('Change reverted successfully');
      } else {
        alert('Failed to revert change: ' + response.data.error);
      }
    } catch (err) {
      alert('Error reverting change');
      console.error('Error reverting change:', err);
    }
  };
  
  const groupHistoryByDate = (history) => {
    const groups = {};
    history.forEach((change) => {
      const date = new Date(change.timestamp).toDateString();
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(change);
    });
    return groups;
  };
  
  const historyGroups = groupHistoryByDate(history);
  
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <HistoryIcon sx={{ mr: 1 }} />
            <Box>
              <Typography variant="h6">Policy History</Typography>
              <Typography variant="subtitle2" color="text.secondary">
                {policyName}
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={fetchHistory} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        )}
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        {!loading && !error && history.length === 0 && (
          <Typography variant="body1" color="text.secondary" sx={{ textAlign: 'center', p: 3 }}>
            No history found for this policy
          </Typography>
        )}
        
        {!loading && !error && history.length > 0 && (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Found {history.length} changes
            </Typography>
            
            {Object.entries(historyGroups).map(([date, changes]) => (
              <Box key={date} sx={{ mb: 3 }}>
                <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold', color: 'primary.main' }}>
                  {date}
                </Typography>
                
                <List dense>
                  {changes.map((change, index) => {
                    const IconComponent = changeTypeIcons[change.change_type] || EditIcon;
                    return (
                      <Box key={change.history_id} sx={{ mb: 1 }}>
                        <ListItem 
                          sx={{ 
                            backgroundColor: 'background.paper',
                            borderLeft: `4px solid ${changeTypeColors[change.change_type] === 'primary' ? '#1976d2' : 
                              changeTypeColors[change.change_type] === 'success' ? '#4caf50' :
                              changeTypeColors[change.change_type] === 'error' ? '#f44336' :
                              changeTypeColors[change.change_type] === 'warning' ? '#ff9800' : '#9e9e9e'}`,
                            borderRadius: 1,
                            mb: 1
                          }}
                        >
                          <ListItemIcon>
                            <IconComponent 
                              color={changeTypeColors[change.change_type] || 'default'} 
                              fontSize="small" 
                            />
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Chip
                                  label={change.change_type.replace('_', ' ').toUpperCase()}
                                  color={changeTypeColors[change.change_type] || 'default'}
                                  size="small"
                                />
                                <Typography variant="body2" color="text.secondary">
                                  {formatTimestamp(change.timestamp)}
                                </Typography>
                              </Box>
                            }
                            secondary={
                              <Box>
                                <Typography variant="body2" sx={{ mt: 0.5 }}>
                                  Changed by: <strong>{change.user_id}</strong>
                                </Typography>
                                {change.notes && (
                                  <Typography variant="body2" sx={{ fontStyle: 'italic', mt: 0.5 }}>
                                    Notes: {change.notes}
                                  </Typography>
                                )}
                              </Box>
                            }
                          />
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {canRevert(change) && (
                              <Tooltip title="Revert this change">
                                <IconButton
                                  size="small"
                                  onClick={() => handleRevert(change.history_id)}
                                  color="primary"
                                >
                                  <RestoreIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Box>
                        </ListItem>
                        <ChangeDetails
                          change={change}
                          onRevert={handleRevert}
                        />
                      </Box>
                    );
                  })}
                </List>
              </Box>
            ))}
          </Box>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default PolicyHistoryDialog;