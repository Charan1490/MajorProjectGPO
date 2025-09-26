/**
 * Advanced Policy Table Component
 * Enhanced table with sorting, filtering, bulk operations, and inline editing
 */

import React, { useState, useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  Checkbox,
  IconButton,
  Menu,
  MenuItem,
  Chip,
  TextField,
  Select,
  FormControl,
  InputLabel,
  Box,
  Typography,
  Button,
  ButtonGroup,
  Collapse,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Badge
} from '@mui/material';
import {
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  History as HistoryIcon,
  Description as DescriptionIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon
} from '@mui/icons-material';

const statusColors = {
  enabled: 'success',
  disabled: 'error',
  not_configured: 'default',
  pending: 'warning',
  error: 'error'
};

const priorityColors = {
  critical: '#d32f2f',
  high: '#f57c00',
  medium: '#1976d2',
  low: '#388e3c',
  info: '#607d8b'
};

const PolicyRow = ({ 
  policy, 
  isSelected, 
  onSelect, 
  onUpdate, 
  onViewHistory, 
  onViewDocumentation,
  expandedRows,
  setExpandedRows,
  editingRow,
  setEditingRow
}) => {
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [editValues, setEditValues] = useState({});
  
  const isExpanded = expandedRows.includes(policy.policy_id);
  const isEditing = editingRow === policy.policy_id;
  
  const handleEdit = () => {
    setEditingRow(policy.policy_id);
    setEditValues({
      status: policy.status,
      priority: policy.priority,
      current_value: policy.current_value || '',
      notes: policy.notes || ''
    });
    setMenuAnchor(null);
  };
  
  const handleSave = () => {
    onUpdate(policy.policy_id, editValues);
    setEditingRow(null);
    setEditValues({});
  };
  
  const handleCancel = () => {
    setEditingRow(null);
    setEditValues({});
  };
  
  const toggleExpanded = () => {
    if (isExpanded) {
      setExpandedRows(prev => prev.filter(id => id !== policy.policy_id));
    } else {
      setExpandedRows(prev => [...prev, policy.policy_id]);
    }
  };

  return (
    <>
      <TableRow hover selected={isSelected}>
        <TableCell padding="checkbox">
          <Checkbox checked={isSelected} onChange={() => onSelect(policy.policy_id)} />
        </TableCell>
        
        <TableCell>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <IconButton size="small" onClick={toggleExpanded}>
              {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
            <Box sx={{ ml: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                {policy.policy_name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                ID: {policy.policy_id}
              </Typography>
            </Box>
          </Box>
        </TableCell>
        
        <TableCell>
          <Typography variant="body2">{policy.category || 'N/A'}</Typography>
        </TableCell>
        
        <TableCell>
          {isEditing ? (
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <Select
                value={editValues.status}
                onChange={(e) => setEditValues({...editValues, status: e.target.value})}
              >
                <MenuItem value="enabled">Enabled</MenuItem>
                <MenuItem value="disabled">Disabled</MenuItem>
                <MenuItem value="not_configured">Not Configured</MenuItem>
                <MenuItem value="pending">Pending</MenuItem>
              </Select>
            </FormControl>
          ) : (
            <Chip
              label={policy.status?.replace('_', ' ').toUpperCase()}
              color={statusColors[policy.status] || 'default'}
              size="small"
            />
          )}
        </TableCell>
        
        <TableCell>
          {isEditing ? (
            <FormControl size="small" sx={{ minWidth: 100 }}>
              <Select
                value={editValues.priority}
                onChange={(e) => setEditValues({...editValues, priority: e.target.value})}
              >
                <MenuItem value="critical">Critical</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="info">Info</MenuItem>
              </Select>
            </FormControl>
          ) : (
            <Chip
              label={policy.priority?.toUpperCase()}
              size="small"
              sx={{
                backgroundColor: priorityColors[policy.priority] || '#607d8b',
                color: 'white',
                fontWeight: 'bold'
              }}
            />
          )}
        </TableCell>
        
        <TableCell>
          {isEditing ? (
            <TextField
              size="small"
              value={editValues.current_value}
              onChange={(e) => setEditValues({...editValues, current_value: e.target.value})}
              placeholder="Enter value"
              sx={{ minWidth: 150 }}
            />
          ) : (
            <Typography variant="body2" sx={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {policy.current_value || policy.required_value || 'N/A'}
            </Typography>
          )}
        </TableCell>
        
        <TableCell>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {(policy.tags || []).slice(0, 2).map((tag) => (
              <Chip
                key={tag.id}
                label={tag.name}
                size="small"
                sx={{
                  backgroundColor: tag.color,
                  color: 'white',
                  fontSize: '0.75rem'
                }}
              />
            ))}
            {(policy.tags || []).length > 2 && (
              <Chip
                label={`+${(policy.tags || []).length - 2}`}
                size="small"
                variant="outlined"
              />
            )}
          </Box>
        </TableCell>
        
        <TableCell>
          <Typography variant="caption" color="text.secondary">
            {policy.updated_at ? new Date(policy.updated_at).toLocaleDateString() : 'N/A'}
          </Typography>
        </TableCell>
        
        <TableCell>
          {isEditing ? (
            <ButtonGroup size="small">
              <IconButton onClick={handleSave} color="primary">
                <SaveIcon />
              </IconButton>
              <IconButton onClick={handleCancel} color="secondary">
                <CancelIcon />
              </IconButton>
            </ButtonGroup>
          ) : (
            <>
              <IconButton
                size="small"
                onClick={(e) => setMenuAnchor(e.currentTarget)}
              >
                <MoreVertIcon />
              </IconButton>
              <Menu
                anchorEl={menuAnchor}
                open={Boolean(menuAnchor)}
                onClose={() => setMenuAnchor(null)}
              >
                <MenuItem onClick={handleEdit}>
                  <EditIcon sx={{ mr: 1 }} fontSize="small" />
                  Edit
                </MenuItem>
                <MenuItem onClick={() => { onViewHistory(policy.policy_id); setMenuAnchor(null); }}>
                  <HistoryIcon sx={{ mr: 1 }} fontSize="small" />
                  View History
                </MenuItem>
                <MenuItem onClick={() => { onViewDocumentation(policy.policy_id); setMenuAnchor(null); }}>
                  <DescriptionIcon sx={{ mr: 1 }} fontSize="small" />
                  Documentation
                </MenuItem>
              </Menu>
            </>
          )}
        </TableCell>
      </TableRow>
      
      {/* Expanded Row */}
      <TableRow>
        <TableCell colSpan={9} sx={{ py: 0 }}>
          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
            <Box sx={{ p: 2, backgroundColor: 'rgba(0, 0, 0, 0.02)' }}>
              <Typography variant="subtitle2" gutterBottom>
                Policy Details
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2, mb: 2 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Description</Typography>
                  <Typography variant="body2">
                    {policy.description || 'No description available'}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Registry Path</Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                    {policy.registry_path || 'N/A'}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">GPO Path</Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                    {policy.gpo_path || 'N/A'}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">CIS Level</Typography>
                  <Typography variant="body2">
                    {policy.cis_level || 'N/A'}
                  </Typography>
                </Box>
              </Box>
              
              {/* Groups */}
              {(policy.groups || []).length > 0 && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="caption" color="text.secondary">Groups: </Typography>
                  {policy.groups.map((group) => (
                    <Chip
                      key={group.id}
                      label={group.name}
                      size="small"
                      variant="outlined"
                      sx={{ mr: 1, mb: 0.5 }}
                    />
                  ))}
                </Box>
              )}
              
              {/* All Tags */}
              {(policy.tags || []).length > 0 && (
                <Box>
                  <Typography variant="caption" color="text.secondary">All Tags: </Typography>
                  {policy.tags.map((tag) => (
                    <Chip
                      key={tag.id}
                      label={tag.name}
                      size="small"
                      sx={{
                        backgroundColor: tag.color,
                        color: 'white',
                        mr: 1,
                        mb: 0.5,
                        fontSize: '0.75rem'
                      }}
                    />
                  ))}
                </Box>
              )}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
};

const AdvancedPolicyTable = ({ 
  policies, 
  selectedPolicies, 
  onSelectPolicy, 
  onSelectAll,
  onBulkUpdate,
  onViewHistory,
  onViewDocumentation,
  onUpdatePolicy,
  isLoading = false
}) => {
  const [orderBy, setOrderBy] = useState('policy_name');
  const [order, setOrder] = useState('asc');
  const [expandedRows, setExpandedRows] = useState([]);
  const [editingRow, setEditingRow] = useState(null);
  const [visibleColumns, setVisibleColumns] = useState({
    policy_name: true,
    category: true,
    status: true,
    priority: true,
    value: true,
    tags: true,
    updated: true,
    actions: true
  });
  const [columnMenuAnchor, setColumnMenuAnchor] = useState(null);
  
  const handleRequestSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };
  
  const sortedPolicies = useMemo(() => {
    if (!policies) return [];
    
    return [...policies].sort((a, b) => {
      let aValue = a[orderBy] || '';
      let bValue = b[orderBy] || '';
      
      if (typeof aValue === 'string') aValue = aValue.toLowerCase();
      if (typeof bValue === 'string') bValue = bValue.toLowerCase();
      
      if (aValue < bValue) return order === 'asc' ? -1 : 1;
      if (aValue > bValue) return order === 'asc' ? 1 : -1;
      return 0;
    });
  }, [policies, orderBy, order]);
  
  const isAllSelected = selectedPolicies.length > 0 && selectedPolicies.length === policies?.length;
  const isIndeterminate = selectedPolicies.length > 0 && selectedPolicies.length < policies?.length;
  
  const toggleColumnVisibility = (column) => {
    setVisibleColumns(prev => ({ ...prev, [column]: !prev[column] }));
  };
  
  if (isLoading) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography>Loading policies...</Typography>
      </Paper>
    );
  }
  
  if (!policies || policies.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No policies found
        </Typography>
      </Paper>
    );
  }
  
  return (
    <Paper sx={{ width: '100%', overflow: 'hidden' }}>
      {/* Bulk Actions Bar */}
      {selectedPolicies.length > 0 && (
        <Box sx={{ p: 2, backgroundColor: 'primary.light', color: 'primary.contrastText' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="subtitle1">
              {selectedPolicies.length} policies selected
            </Typography>
            <ButtonGroup variant="contained" size="small">
              <Button onClick={() => onBulkUpdate({ status: 'enabled' })}>
                Enable All
              </Button>
              <Button onClick={() => onBulkUpdate({ status: 'disabled' })}>
                Disable All
              </Button>
              <Button onClick={() => onBulkUpdate({ priority: 'high' })}>
                Set High Priority
              </Button>
            </ButtonGroup>
          </Box>
        </Box>
      )}
      
      {/* Table */}
      <TableContainer sx={{ maxHeight: '70vh' }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  indeterminate={isIndeterminate}
                  checked={isAllSelected}
                  onChange={onSelectAll}
                />
              </TableCell>
              
              {visibleColumns.policy_name && (
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'policy_name'}
                    direction={orderBy === 'policy_name' ? order : 'asc'}
                    onClick={() => handleRequestSort('policy_name')}
                  >
                    Policy Name
                  </TableSortLabel>
                </TableCell>
              )}
              
              {visibleColumns.category && (
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'category'}
                    direction={orderBy === 'category' ? order : 'asc'}
                    onClick={() => handleRequestSort('category')}
                  >
                    Category
                  </TableSortLabel>
                </TableCell>
              )}
              
              {visibleColumns.status && (
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'status'}
                    direction={orderBy === 'status' ? order : 'asc'}
                    onClick={() => handleRequestSort('status')}
                  >
                    Status
                  </TableSortLabel>
                </TableCell>
              )}
              
              {visibleColumns.priority && (
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'priority'}
                    direction={orderBy === 'priority' ? order : 'asc'}
                    onClick={() => handleRequestSort('priority')}
                  >
                    Priority
                  </TableSortLabel>
                </TableCell>
              )}
              
              {visibleColumns.value && (
                <TableCell>Configuration Value</TableCell>
              )}
              
              {visibleColumns.tags && (
                <TableCell>Tags</TableCell>
              )}
              
              {visibleColumns.updated && (
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'updated_at'}
                    direction={orderBy === 'updated_at' ? order : 'asc'}
                    onClick={() => handleRequestSort('updated_at')}
                  >
                    Last Updated
                  </TableSortLabel>
                </TableCell>
              )}
              
              {visibleColumns.actions && (
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    Actions
                    <IconButton
                      size="small"
                      onClick={(e) => setColumnMenuAnchor(e.currentTarget)}
                      sx={{ ml: 1 }}
                    >
                      <VisibilityIcon />
                    </IconButton>
                  </Box>
                  <Menu
                    anchorEl={columnMenuAnchor}
                    open={Boolean(columnMenuAnchor)}
                    onClose={() => setColumnMenuAnchor(null)}
                  >
                    <MenuItem>
                      <Typography variant="subtitle2">Show/Hide Columns</Typography>
                    </MenuItem>
                    {Object.entries(visibleColumns).map(([column, visible]) => (
                      <MenuItem key={column} onClick={() => toggleColumnVisibility(column)}>
                        <Checkbox checked={visible} size="small" />
                        {column.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </MenuItem>
                    ))}
                  </Menu>
                </TableCell>
              )}
            </TableRow>
          </TableHead>
          
          <TableBody>
            {sortedPolicies.map((policy) => (
              <PolicyRow
                key={policy.policy_id}
                policy={policy}
                isSelected={selectedPolicies.includes(policy.policy_id)}
                onSelect={onSelectPolicy}
                onUpdate={onUpdatePolicy}
                onViewHistory={onViewHistory}
                onViewDocumentation={onViewDocumentation}
                expandedRows={expandedRows}
                setExpandedRows={setExpandedRows}
                editingRow={editingRow}
                setEditingRow={setEditingRow}
              />
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default AdvancedPolicyTable;