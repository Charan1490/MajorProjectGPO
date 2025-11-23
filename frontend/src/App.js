import React, { useState, useEffect, useMemo } from 'react';
import {
  Container,
  Box,
  Typography,
  Paper,
  LinearProgress,
  Alert,
  Grid,
  Button,
  Tabs,
  Tab,
  TextField,
  CircularProgress,
  Chip,
  AppBar,
  Toolbar,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  FormControlLabel,
  Switch,
  Menu,
  MenuItem,
  ThemeProvider,
  createTheme,
  CssBaseline,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Checkbox,
  FormControl,
  InputLabel,
  Select,
  Card,
  CardContent,
  CardActions,
  ButtonGroup,
  Stack
} from '@mui/material';
import {
  Upload as UploadIcon,
  Search as SearchIcon,
  Download as DownloadIcon,
  FilterList as FilterListIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Menu as MenuIcon,
  DarkMode as DarkModeIcon,
  LightMode as LightModeIcon,
  Info as InfoIcon,
  Help as HelpIcon,
  Settings as SettingsIcon,
  History as HistoryIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Check as CheckIcon,
  ContentCopy as CopyIcon,
  Dashboard as DashboardIcon,
  CloudUpload as DeploymentIcon,
  Assessment as AuditIcon,
  Build as RemediationIcon,
  Assignment as TemplateIcon
} from '@mui/icons-material';
import axios from 'axios';
import { saveAs } from 'file-saver';
import FileUploader from './components/FileUploader';
import PolicyTable from './components/PolicyTable';
import DashboardStatistics from './components/DashboardStatistics';
import AdvancedPolicyTable from './components/AdvancedPolicyTable';
import PolicyHistoryDialog from './components/PolicyHistoryDialog';
import DeploymentManager from './components/DeploymentManager';
import AuditScanner from './components/AuditScanner';
import ChatbotWidget from './components/ChatbotWidget';

const API_BASE_URL = 'http://localhost:8000';

// Theme configuration
const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    success: {
      main: '#2e7d32',
    },
    error: {
      main: '#d32f2f',
    },
    warning: {
      main: '#ed6c02',
    },
    info: {
      main: '#0288d1',
    },
  },
});

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#f48fb1',
    },
    success: {
      main: '#66bb6a',
    },
    error: {
      main: '#f44336',
    },
    warning: {
      main: '#ffa726',
    },
    info: {
      main: '#29b6f6',
    },
  },
});

function App() {
  // State for theme
  const [darkMode, setDarkMode] = useState(false);
  
  // Ensure theme is always valid with all required colors
  const theme = useMemo(() => {
    const baseTheme = darkMode ? darkTheme : lightTheme;
    return createTheme({
      ...baseTheme,
      palette: {
        ...baseTheme.palette,
        // Ensure all color variants exist
        primary: baseTheme.palette.primary || { main: '#1976d2' },
        secondary: baseTheme.palette.secondary || { main: '#dc004e' },
        error: baseTheme.palette.error || { main: '#d32f2f' },
        warning: baseTheme.palette.warning || { main: '#ed6c02' },
        info: baseTheme.palette.info || { main: '#0288d1' },
        success: baseTheme.palette.success || { main: '#2e7d32' },
      }
    });
  }, [darkMode]);

  // State for drawer
  const [drawerOpen, setDrawerOpen] = useState(false);

  // State for file upload
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [taskId, setTaskId] = useState('');
  const [extractionStatus, setExtractionStatus] = useState(null);

  // State for policy data
  const [policies, setPolicies] = useState([]);
  const [isLoadingPolicies, setIsLoadingPolicies] = useState(false);
  const [loadError, setLoadError] = useState('');
  
  // State for completed tasks
  const [completedTasks, setCompletedTasks] = useState([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);

  // State for Step 2: Template Management
  const [templatePolicies, setTemplatePolicies] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);
  const [isLoadingTemplatePolicies, setIsLoadingTemplatePolicies] = useState(false);
  
  // Template Manager specific state
  const [showCreateTemplate, setShowCreateTemplate] = useState(false);
  const [selectedPolicies, setSelectedPolicies] = useState([]);
  const [newTemplate, setNewTemplate] = useState({ name: '', description: '', cis_level: 'Level 1' });
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Filter template policies
  const templateFilteredPolicies = useMemo(() => {
    if (!Array.isArray(templatePolicies)) return [];
    
    try {
      return templatePolicies.filter(policy => {
        if (!policy) return false;
        
        const matchesSearch = searchQuery === '' || 
          (policy.policy_name && policy.policy_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
          (policy.policy_id && policy.policy_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
          (policy.category && policy.category.toLowerCase().includes(searchQuery.toLowerCase()));
        
        const matchesStatus = statusFilter === 'all' || policy.status === statusFilter;
        
        return matchesSearch && matchesStatus;
      });
    } catch (error) {
      console.error('Error filtering template policies:', error);
      return [];
    }
  }, [templatePolicies, searchQuery, statusFilter]);

  // State for UI
  const [currentTab, setCurrentTab] = useState(0);
  const [filterMenuAnchor, setFilterMenuAnchor] = useState(null);
  const [statusExpanded, setStatusExpanded] = useState(true); // Control status section visibility

  // Step 3: Dashboard state
  const [dashboardPolicies, setDashboardPolicies] = useState([]);
  const [dashboardStatistics, setDashboardStatistics] = useState(null);
  const [dashboardGroups, setDashboardGroups] = useState([]);
  const [dashboardTags, setDashboardTags] = useState([]);
  const [isDashboardLoading, setIsDashboardLoading] = useState(false);
  const [selectedDashboardPolicies, setSelectedDashboardPolicies] = useState([]);
  const [historyDialog, setHistoryDialog] = useState({ open: false, policyId: null, policyName: '' });
  const [dashboardSearchQuery, setDashboardSearchQuery] = useState('');

  // Status polling interval
  const POLLING_INTERVAL = 2000; // 2 seconds

  // Effect to load dashboard data when switching to Dashboard tab
  useEffect(() => {
    if (currentTab === 4) { // Dashboard tab
      fetchDashboardData();
    }
  }, [currentTab]);

  // Effect to load template data when switching to Template Manager tab
  useEffect(() => {
    if (currentTab === 3) {
      fetchTemplates();
      fetchTemplatePolicies();
    }
  }, [currentTab]);

  // Effect to poll status if task is in progress
  useEffect(() => {
    const fetchStatus = async (id) => {
      try {
        const response = await axios.get(`${API_BASE_URL}/status/${id}`);
        setExtractionStatus(response.data);

        // If completed, fetch the results
        if (response.data.status === 'completed') {
          fetchResults(id);
        }
      } catch (error) {
        console.error('Error fetching task status:', error);
        
        // If task status is not found (404), try to fetch results directly
        if (error.response?.status === 404) {
          console.log('Task status not found, trying to fetch results directly...');
          try {
            await fetchResults(id);
            // If results exist, create a mock status
            setExtractionStatus({
              task_id: id,
              status: 'completed',
              message: 'Results found',
              progress: 100,
              details: 'Task status was recovered from saved results'
            });
            return;
          } catch (resultsError) {
            console.error('No results found either:', resultsError);
          }
        }
        
        setUploadError(error.response?.data?.detail || 'Error checking task status');
      }
    };

    let interval;
    if (taskId && extractionStatus && extractionStatus.status === 'processing') {
      interval = setInterval(() => {
        fetchStatus(taskId);
      }, POLLING_INTERVAL);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [taskId, extractionStatus, POLLING_INTERVAL]);

  // Load completed tasks when component mounts
  useEffect(() => {
    fetchCompletedTasks();
  }, []);

  // Handle file upload
  const handleFileUpload = async () => {
    if (!file) {
      setUploadError('Please select a file first');
      return;
    }

    setIsUploading(true);
    setUploadError('');
    setTaskId('');
    setExtractionStatus(null);
    setPolicies([]);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload-pdf/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setTaskId(response.data.task_id);
      
      // Initialize status for immediate UI feedback
      setExtractionStatus({
        task_id: response.data.task_id,
        status: 'processing',
        message: 'Starting PDF extraction...',
        progress: 0,
        details: 'Upload completed, initializing extraction process'
      });
      
      // Start polling for status immediately
      setTimeout(() => {
        fetchTaskStatus(response.data.task_id);
      }, 1000); // Wait 1 second before first poll
    } catch (error) {
      console.error('Error uploading file:', error);
      let errorMessage = 'Error connecting to the server. Please try again later.';
      if (error.response) {
        errorMessage = error.response.data?.detail || 'Server error occurred';
      } else if (error.request) {
        errorMessage = 'Could not connect to the server. Is the backend running?';
      }
      setUploadError(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  // Fetch task status
  const fetchTaskStatus = async (id) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/status/${id}`);
      setExtractionStatus(response.data);

      // If completed, fetch the results
      if (response.data.status === 'completed') {
        fetchResults(id);
      }
    } catch (error) {
      console.error('Error fetching task status:', error);
      
      // If task status is not found (404), try to fetch results directly
      // This handles the case where the task status was lost but results exist
      if (error.response?.status === 404) {
        console.log('Task status not found, trying to fetch results directly...');
        try {
          await fetchResults(id);
          // If results exist, create a mock status
          setExtractionStatus({
            task_id: id,
            status: 'completed',
            message: 'Results found',
            progress: 100,
            details: 'Task status was recovered from saved results'
          });
          return;
        } catch (resultsError) {
          console.error('No results found either:', resultsError);
        }
      }
      
      setUploadError(error.response?.data?.detail || 'Error checking task status');
    }
  };

  // Fetch extraction results
  const fetchResults = async (id) => {
    setIsLoadingPolicies(true);
    setLoadError('');

    try {
      const response = await axios.get(`${API_BASE_URL}/results/${id}`);
      setPolicies(response.data.policies);
    } catch (error) {
      console.error('Error fetching results:', error);
      setLoadError(error.response?.data?.detail || 'Error loading extraction results');
    } finally {
      setIsLoadingPolicies(false);
    }
  };

  // Fetch completed tasks
  const fetchCompletedTasks = async () => {
    setIsLoadingTasks(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/completed-tasks`);
      setCompletedTasks(response.data.completed_tasks || []);
    } catch (error) {
      console.error('Error fetching completed tasks:', error);
    } finally {
      setIsLoadingTasks(false);
    }
  };

  // Load a specific completed task
  const loadCompletedTask = async (taskId) => {
    setTaskId(taskId);
    
    // Try to fetch the status first
    try {
      await fetchTaskStatus(taskId);
    } catch (error) {
      // If status fails, try to fetch results directly
      await fetchResults(taskId);
      setExtractionStatus({
        task_id: taskId,
        status: 'completed',
        message: 'Results loaded from saved file',
        progress: 100,
        details: 'Previously completed extraction loaded successfully'
      });
    }
  };

  // Handle file download
  const handleDownload = async (format) => {
    if (!taskId) {
      return;
    }

    try {
      if (format === 'json') {
        // Create a JSON blob from the policies
        const jsonStr = JSON.stringify(policies, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        saveAs(blob, 'cis_policies.json');
      } else if (format === 'csv') {
        // Convert to CSV format
        let csvContent = 'Category,Subcategory,Policy Name,Description,Rationale,Registry Path,GPO Path,Required Value,CIS Level\n';
        
        policies.forEach(p => {
          const row = [
            p.category || '',
            p.subcategory || '',
            p.policy_name || '',
            (p.description || '').replace(/,/g, ';'),
            (p.rationale || '').replace(/,/g, ';'),
            p.registry_path || '',
            p.gpo_path || '',
            p.required_value || '',
            p.cis_level || ''
          ];
          csvContent += row.map(field => `"${field}"`).join(',') + '\n';
        });
        
        const blob = new Blob([csvContent], { type: 'text/csv' });
        saveAs(blob, 'cis_policies.csv');
      }
    } catch (error) {
      console.error('Error downloading file:', error);
    }
  };

  // Filter policies based on search query
  const filteredPolicies = policies.filter(policy => {
    if (!searchQuery) return true;
    
    const query = searchQuery.toLowerCase();
    return (
      (policy.policy_name && policy.policy_name.toLowerCase().includes(query)) ||
      (policy.category && policy.category.toLowerCase().includes(query)) ||
      (policy.subcategory && policy.subcategory.toLowerCase().includes(query)) ||
      (policy.description && policy.description.toLowerCase().includes(query)) ||
      (policy.gpo_path && policy.gpo_path.toLowerCase().includes(query)) ||
      (policy.registry_path && policy.registry_path.toLowerCase().includes(query))
    );
  });

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
    
    // If switching to View Policies tab (index 1) and no policies are loaded,
    // but there are completed tasks, load the most recent one
    if (newValue === 1 && policies.length === 0 && completedTasks.length > 0) {
      const mostRecentTask = completedTasks[0]; // Assuming they're sorted by recency
      loadCompletedTask(mostRecentTask.task_id);
    }
    
    // If switching to Template Manager tab (index 3), load templates and policies
    if (newValue === 3) {
      fetchTemplates();
      fetchTemplatePolicies();
    }
    
    // If switching to Dashboard tab (index 4), load dashboard data
    if (newValue === 4) {
      fetchDashboardData();
    }
  };

  // Step 2: Template Management Functions
  const fetchTemplates = async () => {
    setIsLoadingTemplates(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/templates/`);
      // Backend returns {templates: [...], total_count: N}, so we need response.data.templates
      const templates = response.data.templates || [];
      setTemplates(Array.isArray(templates) ? templates : []);
    } catch (error) {
      console.error('Error fetching templates:', error);
      // Set empty array on error
      setTemplates([]);
    } finally {
      setIsLoadingTemplates(false);
    }
  };

  const fetchTemplatePolicies = async () => {
    setIsLoadingTemplatePolicies(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/template-policies/`);
      // Backend returns {policies: [...], total_count: N}, so we need response.data.policies
      const policies = response.data.policies || [];
      setTemplatePolicies(Array.isArray(policies) ? policies : []);
    } catch (error) {
      console.error('Error fetching template policies:', error);
      // Set empty array on error
      setTemplatePolicies([]);
    } finally {
      setIsLoadingTemplatePolicies(false);
    }
  };

  const importCisPolicies = async () => {
    if (!taskId) {
      alert('No CIS policies to import. Please upload and process a benchmark first.');
      return;
    }
    
    try {
      const response = await axios.post(`${API_BASE_URL}/import-cis-policies/${taskId}`);
      const importedCount = Object.keys(response.data.imported_policies || {}).length;
      alert(`Successfully imported ${importedCount} CIS policies to template system`);
      fetchTemplatePolicies(); // Refresh the policies list
    } catch (error) {
      console.error('Error importing CIS policies:', error);
      alert('Error importing CIS policies: ' + (error.response?.data?.detail || error.message));
    }
  };

  const createTemplate = async (templateData) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/templates/`, templateData);
      alert('Template created successfully');
      fetchTemplates(); // Refresh templates list
      return response.data;
    } catch (error) {
      console.error('Error creating template:', error);
      alert('Error creating template');
    }
  };

  const exportTemplate = async (templateId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/templates/${templateId}/export`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/json' });
      saveAs(blob, `template-${templateId}.json`);
    } catch (error) {
      console.error('Error exporting template:', error);
      alert('Error exporting template');
    }
  };

  // Template Management Functions
  const handleCreateTemplate = async () => {
    if (!newTemplate.name.trim()) {
      alert('Template name is required');
      return;
    }
    
    const currentSelection = selectedPolicies || [];
    if (currentSelection.length === 0) {
      alert('Please select at least one policy for the template');
      return;
    }
    
    try {
      const templateData = {
        ...newTemplate,
        policy_ids: currentSelection,
        tags: []
      };
      
      await createTemplate(templateData);
      setShowCreateTemplate(false);
      setNewTemplate({ name: '', description: '', cis_level: 'Level 1' });
      setSelectedPolicies([]);
    } catch (error) {
      console.error('Error creating template:', error);
    }
  };

  const handlePolicySelection = (policyId) => {
    if (!policyId) return;
    
    setSelectedPolicies(prev => {
      const currentSelection = prev || [];
      return currentSelection.includes(policyId)
        ? currentSelection.filter(id => id !== policyId)
        : [...currentSelection, policyId];
    });
  };

  const handleSelectAllPolicies = () => {
    if (!Array.isArray(templateFilteredPolicies) || templateFilteredPolicies.length === 0) {
      return;
    }
    
    const currentSelection = selectedPolicies || [];
    const filteredPolicyIds = templateFilteredPolicies.map(p => p.policy_id).filter(Boolean);
    const allSelected = filteredPolicyIds.every(id => currentSelection.includes(id));
    
    if (allSelected) {
      setSelectedPolicies(prev => (prev || []).filter(id => !filteredPolicyIds.includes(id)));
    } else {
      const newSelections = filteredPolicyIds.filter(id => !currentSelection.includes(id));
      setSelectedPolicies(prev => [...(prev || []), ...newSelections]);
    }
  };

  const updatePolicyStatus = async (policyId, newStatus) => {
    try {
      await axios.put(`${API_BASE_URL}/template-policies/${policyId}`, {
        status: newStatus
      });
      fetchTemplatePolicies(); // Refresh the policies
    } catch (error) {
      console.error('Error updating policy status:', error);
      alert('Error updating policy status');
    }
  };

  const handleBulkStatusUpdate = async (status) => {
    const currentSelection = selectedPolicies || [];
    if (currentSelection.length === 0) {
      alert('No policies selected');
      return;
    }

    try {
      await axios.post(`${API_BASE_URL}/template-policies/bulk-update`, {
        policy_ids: currentSelection,
        changes: { status }
      });
      
      fetchTemplatePolicies();
      setSelectedPolicies([]);
      alert(`Updated ${currentSelection.length} policies to ${status}`);
    } catch (error) {
      console.error('Error bulk updating policies:', error);
      alert('Error updating policies');
    }
  };

  const duplicateTemplate = async (templateId) => {
    try {
      const newName = prompt('Enter name for duplicated template:');
      if (!newName) return;
      
      await axios.post(`${API_BASE_URL}/templates/${templateId}/duplicate`, {
        new_name: newName
      });
      
      fetchTemplates();
      alert('Template duplicated successfully');
    } catch (error) {
      console.error('Error duplicating template:', error);
      alert('Error duplicating template');
    }
  };

  const deleteTemplate = async (templateId) => {
    if (!window.confirm('Are you sure you want to delete this template?')) return;
    
    try {
      await axios.delete(`${API_BASE_URL}/templates/${templateId}`);
      fetchTemplates();
      alert('Template deleted successfully');
    } catch (error) {
      console.error('Error deleting template:', error);
      alert('Error deleting template');
    }
  };

  // Step 3: Dashboard Functions
  
  const fetchDashboardData = async () => {
    setIsDashboardLoading(true);
    try {
      // Fetch statistics first
      const statsResponse = await axios.get(`${API_BASE_URL}/dashboard/statistics`);
      if (statsResponse.data.success) {
        setDashboardStatistics(statsResponse.data.data);
      }

      // Fetch policies
      const policiesResponse = await axios.get(`${API_BASE_URL}/dashboard/policies`);
      if (policiesResponse.data.success) {
        setDashboardPolicies(policiesResponse.data.data.policies || []);
      }

      // Fetch groups
      const groupsResponse = await axios.get(`${API_BASE_URL}/dashboard/groups`);
      if (groupsResponse.data.success) {
        setDashboardGroups(groupsResponse.data.data.groups || []);
      }

      // Fetch tags
      const tagsResponse = await axios.get(`${API_BASE_URL}/dashboard/tags`);
      if (tagsResponse.data.success) {
        setDashboardTags(tagsResponse.data.data.tags || []);
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      alert('Error loading dashboard data');
    } finally {
      setIsDashboardLoading(false);
    }
  };

  const importToDashboard = async () => {
    try {
      setIsDashboardLoading(true);
      const response = await axios.post(`${API_BASE_URL}/dashboard/import-from-templates`);
      
      if (response.data.success) {
        alert(response.data.message);
        // Refresh dashboard data
        await fetchDashboardData();
      } else {
        alert('Failed to import policies: ' + response.data.error);
      }
    } catch (error) {
      console.error('Error importing to dashboard:', error);
      alert('Error importing policies to dashboard');
    } finally {
      setIsDashboardLoading(false);
    }
  };

  const handleDashboardPolicySelect = (policyId) => {
    setSelectedDashboardPolicies(prev => 
      prev.includes(policyId) 
        ? prev.filter(id => id !== policyId)
        : [...prev, policyId]
    );
  };

  const handleDashboardSelectAll = () => {
    if (selectedDashboardPolicies.length === dashboardPolicies.length) {
      setSelectedDashboardPolicies([]);
    } else {
      setSelectedDashboardPolicies(dashboardPolicies.map(p => p.policy_id));
    }
  };

  const handleDashboardBulkUpdate = async (updates) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/dashboard/policies/bulk-update`, {
        policy_ids: selectedDashboardPolicies,
        updates: updates,
        user_note: `Bulk update: ${Object.keys(updates).join(', ')}`
      });

      if (response.data.success) {
        alert(response.data.message);
        setSelectedDashboardPolicies([]);
        await fetchDashboardData();
      } else {
        alert('Bulk update failed: ' + response.data.error);
      }
    } catch (error) {
      console.error('Error in bulk update:', error);
      alert('Error performing bulk update');
    }
  };

  const handleViewHistory = (policyId) => {
    const policy = dashboardPolicies.find(p => p.policy_id === policyId);
    setHistoryDialog({
      open: true,
      policyId: policyId,
      policyName: policy ? policy.policy_name : 'Unknown Policy'
    });
  };

  const handleViewDocumentation = async (policyId) => {
    // For now, just show an alert. This could open a documentation dialog
    try {
      const response = await axios.get(`${API_BASE_URL}/dashboard/policies/${policyId}/documentation`);
      if (response.data.success) {
        const doc = response.data.data.documentation;
        alert(`Documentation for policy ${policyId}:\n\nNotes: ${doc?.notes || 'No notes'}\nRationale: ${doc?.rationale || 'No rationale'}`);
      } else {
        alert('No documentation available for this policy');
      }
    } catch (error) {
      console.error('Error fetching documentation:', error);
      alert('Error fetching documentation');
    }
  };

  const handleUpdateDashboardPolicy = async (policyId, updates) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/dashboard/policies/${policyId}`, {
        ...updates,
        user_note: 'Updated via dashboard interface'
      });

      if (response.data.success) {
        // Refresh the policies list
        await fetchDashboardData();
      } else {
        alert('Failed to update policy: ' + response.data.error);
      }
    } catch (error) {
      console.error('Error updating policy:', error);
      alert('Error updating policy');
    }
  };

  const searchDashboardPolicies = useMemo(() => {
    if (!dashboardSearchQuery.trim()) return dashboardPolicies;
    
    const query = dashboardSearchQuery.toLowerCase();
    return dashboardPolicies.filter(policy => 
      policy.policy_name?.toLowerCase().includes(query) ||
      policy.category?.toLowerCase().includes(query) ||
      policy.description?.toLowerCase().includes(query) ||
      policy.policy_id?.toLowerCase().includes(query)
    );
  }, [dashboardPolicies, dashboardSearchQuery]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <IconButton
              edge="start"
              color="inherit"
              aria-label="menu"
              onClick={() => setDrawerOpen(true)}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              CIS Benchmark Parser
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={darkMode}
                  onChange={(e) => setDarkMode(e.target.checked)}
                  icon={<LightModeIcon />}
                  checkedIcon={<DarkModeIcon />}
                />
              }
              label=""
            />
          </Toolbar>
        </AppBar>

        {/* Side Drawer */}
        <Drawer
          anchor="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        >
          <Box
            sx={{ width: 250 }}
            role="presentation"
            onClick={() => setDrawerOpen(false)}
            onKeyDown={() => setDrawerOpen(false)}
          >
            <List>
              <ListItem button onClick={() => setCurrentTab(0)}>
                <ListItemIcon>
                  <UploadIcon />
                </ListItemIcon>
                <ListItemText primary="Upload PDF" />
              </ListItem>
              <ListItem button onClick={() => setCurrentTab(1)} disabled={policies.length === 0}>
                <ListItemIcon>
                  <SearchIcon />
                </ListItemIcon>
                <ListItemText primary="View Policies" />
              </ListItem>
              <ListItem button onClick={() => setCurrentTab(2)}>
                <ListItemIcon>
                  <HistoryIcon />
                </ListItemIcon>
                <ListItemText primary="Previous Extractions" />
              </ListItem>
              <ListItem button onClick={() => setCurrentTab(3)}>
                <ListItemIcon>
                  <TemplateIcon />
                </ListItemIcon>
                <ListItemText primary="Template Manager" />
              </ListItem>
              <ListItem button onClick={() => setCurrentTab(4)}>
                <ListItemIcon>
                  <DashboardIcon />
                </ListItemIcon>
                <ListItemText primary="Policy Dashboard" />
              </ListItem>
              <ListItem button onClick={() => setCurrentTab(5)}>
                <ListItemIcon>
                  <DeploymentIcon />
                </ListItemIcon>
                <ListItemText primary="Deployment Manager" />
              </ListItem>
              <ListItem button onClick={() => setCurrentTab(6)}>
                <ListItemIcon>
                  <AuditIcon />
                </ListItemIcon>
                <ListItemText primary="Audit Manager" />
              </ListItem>
              <ListItem button onClick={() => setCurrentTab(7)}>
                <ListItemIcon>
                  <RemediationIcon />
                </ListItemIcon>
                <ListItemText primary="Remediation Manager" />
              </ListItem>
            </List>
            <Divider />
            <List>
              <ListItem button>
                <ListItemIcon>
                  <InfoIcon />
                </ListItemIcon>
                <ListItemText primary="About" />
              </ListItem>
              <ListItem button>
                <ListItemIcon>
                  <HelpIcon />
                </ListItemIcon>
                <ListItemText primary="Help" />
              </ListItem>
              <ListItem button>
                <ListItemIcon>
                  <SettingsIcon />
                </ListItemIcon>
                <ListItemText primary="Settings" />
              </ListItem>
            </List>
          </Box>
        </Drawer>

        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
          <Tabs 
            value={currentTab} 
            onChange={handleTabChange} 
            variant="scrollable"
            scrollButtons="auto"
            allowScrollButtonsMobile
            sx={{
              '& .MuiTabs-scrollButtons': {
                '&.Mui-disabled': { opacity: 0.3 }
              }
            }}
          >
            <Tab label="Upload Benchmark" />
            <Tab label="View Policies" disabled={policies.length === 0 && completedTasks.length === 0} />
            <Tab label="Previous Extractions" />
            <Tab label="Template Manager" />
            <Tab label="Policy Dashboard" />
            <Tab label="Deployment Manager" />
            <Tab label="Audit Manager" />
            <Tab label="Remediation Manager" />
          </Tabs>

          {/* Upload Tab */}
          {currentTab === 0 && (
            <Paper sx={{ p: 3, mt: 3 }}>
              <Typography variant="h5" gutterBottom>
                Upload CIS Benchmark PDF
              </Typography>
              
              <FileUploader 
                onFileChange={(selectedFile) => {
                  setFile(selectedFile);
                  setUploadError('');
                }} 
              />
              
              <Box sx={{ mt: 2 }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleFileUpload}
                  disabled={!file || isUploading}
                  startIcon={isUploading ? <CircularProgress size={20} /> : <UploadIcon />}
                >
                  {isUploading ? 'Processing...' : 'Extract Policies'}
                </Button>
              </Box>

              {uploadError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {uploadError}
                </Alert>
              )}

              {/* Status Section */}
              {(extractionStatus || taskId) && (
                <Paper sx={{ 
                  mt: 3, 
                  p: 2, 
                  border: extractionStatus?.status === 'failed' ? '2px solid #f44336' : '2px solid #1976d2',
                  backgroundColor: extractionStatus?.status === 'failed' ? '#ffebee' : '#e3f2fd'
                }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="h6" sx={{ color: extractionStatus?.status === 'failed' ? '#d32f2f' : '#1976d2', fontWeight: 'bold' }}>
                      Processing Status
                    </Typography>
                    <Button
                      variant="outlined"
                      size="small"
                      color="primary"
                      onClick={() => setStatusExpanded(!statusExpanded)}
                      endIcon={statusExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      sx={{ 
                        borderColor: extractionStatus?.status === 'failed' ? 'error.main' : 'primary.main',
                        color: extractionStatus?.status === 'failed' ? 'error.main' : 'primary.main',
                        fontWeight: 'bold'
                      }}
                    >
                      {statusExpanded ? 'Hide Details' : 'Show Details'}
                    </Button>
                  </Box>
                  
                  {extractionStatus && (
                    <>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Box sx={{ width: '100%', mr: 1 }}>
                          <LinearProgress 
                            variant="determinate" 
                            value={extractionStatus.progress} 
                            sx={{ height: 8, borderRadius: 4 }}
                            color={extractionStatus.status === 'failed' ? 'error' : 'primary'}
                          />
                        </Box>
                        <Box sx={{ minWidth: 35 }}>
                          <Typography variant="body2" color="text.secondary">
                            {extractionStatus.progress}%
                          </Typography>
                        </Box>
                      </Box>
                      
                      <Typography variant="body1" sx={{ mb: 1, fontWeight: 'medium' }}>
                        {extractionStatus.message}
                      </Typography>
                      
                      {statusExpanded && (
                        <>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            Task ID: {extractionStatus.task_id}
                          </Typography>
                          
                          {extractionStatus.details && (
                            <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                              {extractionStatus.details}
                            </Typography>
                          )}
                          
                          <Box sx={{ mt: 2 }}>
                            <Chip 
                              label={extractionStatus.status.toUpperCase()} 
                              color={
                                extractionStatus.status === 'completed' ? 'success' : 
                                extractionStatus.status === 'failed' ? 'error' : 
                                'primary'
                              }
                              variant="filled"
                            />
                          </Box>
                        </>
                      )}
                    </>
                  )}
                </Paper>
              )}
            </Paper>
          )}

          {/* View Policies Tab */}
          {currentTab === 1 && (
            <Paper sx={{ p: 3, mt: 3 }}>
              {isLoadingPolicies ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
                  <CircularProgress size={40} />
                  <Typography variant="body1" sx={{ ml: 2 }}>
                    Loading policies...
                  </Typography>
                </Box>
              ) : policies.length === 0 && completedTasks.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant="body1" color="text.secondary">
                    No policies extracted yet. Upload and process a CIS Benchmark PDF first.
                  </Typography>
                </Box>
              ) : policies.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant="body1" color="text.secondary">
                    Loading the most recent extraction...
                  </Typography>
                  <CircularProgress size={24} sx={{ mt: 2 }} />
                </Box>
              ) : (
                <>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h5">
                  Extracted Policies ({policies.length})
                </Typography>
                <Box>
                  <Button
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    onClick={() => handleDownload('json')}
                    sx={{ mr: 1 }}
                  >
                    Download JSON
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    onClick={() => handleDownload('csv')}
                  >
                    Download CSV
                  </Button>
                </Box>
              </Box>

              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} md={8}>
                  <TextField
                    fullWidth
                    label="Search policies"
                    variant="outlined"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by policy name, category, description..."
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<FilterListIcon />}
                    onClick={(e) => setFilterMenuAnchor(e.currentTarget)}
                    sx={{ height: '56px' }}
                  >
                    Filters
                  </Button>
                </Grid>
              </Grid>

              <Menu
                anchorEl={filterMenuAnchor}
                open={Boolean(filterMenuAnchor)}
                onClose={() => setFilterMenuAnchor(null)}
              >
                <MenuItem onClick={() => setFilterMenuAnchor(null)}>All Categories</MenuItem>
                <MenuItem onClick={() => setFilterMenuAnchor(null)}>Level 1 Only</MenuItem>
                <MenuItem onClick={() => setFilterMenuAnchor(null)}>Level 2 Only</MenuItem>
              </Menu>

              {isLoadingPolicies ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                  <CircularProgress />
                </Box>
              ) : loadError ? (
                <Alert severity="error">{loadError}</Alert>
              ) : (
                <PolicyTable policies={filteredPolicies} />
              )}
                </>
              )}
            </Paper>
          )}

          {/* Previous Extractions Tab */}
          {currentTab === 2 && (
            <Paper sx={{ p: 3, mt: 3 }}>
              <Typography variant="h5" gutterBottom>
                Previous Extractions
              </Typography>
              
              {isLoadingTasks ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                  <CircularProgress />
                </Box>
              ) : completedTasks.length === 0 ? (
                <Typography variant="body1" color="text.secondary">
                  No previous extractions found.
                </Typography>
              ) : (
                <List>
                  {completedTasks.map((task, index) => (
                    <ListItem key={task.task_id} button onClick={() => loadCompletedTask(task.task_id)}>
                      <ListItemIcon>
                        <HistoryIcon />
                      </ListItemIcon>
                      <ListItemText
                        primary={task.file_name || `Extraction ${index + 1}`}
                        secondary={task.message}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </Paper>
          )}

          {/* Template Manager Tab */}
          {currentTab === 3 && (
            <Paper sx={{ p: 3, mt: 3 }}>
              <Typography variant="h4" gutterBottom>
                GPO Template Manager
              </Typography>
              
              {/* Import CIS Policies Section */}
              <Paper sx={{ p: 2, mb: 3, bgcolor: 'background.default' }}>
                <Typography variant="h6" gutterBottom>
                  Import CIS Policies
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Import policies from the current CIS benchmark extraction into the template system.
                </Typography>
                <Button
                  variant="contained"
                  onClick={importCisPolicies}
                  disabled={!taskId}
                  startIcon={<UploadIcon />}
                >
                  Import Current CIS Policies
                </Button>
                {!taskId && (
                  <Typography variant="body2" color="warning.main" sx={{ mt: 1 }}>
                    Please upload and process a benchmark first to import policies.
                  </Typography>
                )}
              </Paper>

              {/* Template Policies Section */}
              <Paper sx={{ p: 2, mb: 3, bgcolor: 'background.default' }}>
                <Typography variant="h6" gutterBottom>
                  Template Policies ({Array.isArray(templatePolicies) ? templatePolicies.length : 0})
                </Typography>
                
                {isLoadingTemplatePolicies ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                    <CircularProgress />
                  </Box>
                ) : !Array.isArray(templatePolicies) || templatePolicies.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No policies in template system. Import CIS policies to get started.
                  </Typography>
                ) : (
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Showing first 5 policies. Total: {templatePolicies.length}
                    </Typography>
                    <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                      {templatePolicies.slice(0, 5).map((policy, index) => (
                        <Card key={policy.policy_id || index} sx={{ mb: 1, p: 1 }}>
                          <Typography variant="body2" fontWeight="bold">
                            {policy.policy_name || policy.policy_id || 'Unnamed Policy'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Status: {policy.status || 'not_configured'} | Level: {policy.cis_level || 'N/A'}
                          </Typography>
                        </Card>
                      ))}
                      {templatePolicies.length > 5 && (
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          ...and {templatePolicies.length - 5} more policies
                        </Typography>
                      )}
                    </Box>
                  </Box>
                )}
              </Paper>

              {/* Action Bar */}
              <Paper sx={{ p: 2, mb: 3, bgcolor: 'background.default' }}>
                <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <Button
                      variant="contained"
                      onClick={() => setShowCreateTemplate(true)}
                      disabled={!selectedPolicies || selectedPolicies.length === 0}
                      startIcon={<AddIcon />}
                    >
                      Create Template ({(selectedPolicies || []).length})
                    </Button>
                  </Box>
                  
                    {selectedPolicies && selectedPolicies.length > 0 ? (
                      <ButtonGroup variant="outlined" size="small">
                        <Button 
                          onClick={() => handleBulkStatusUpdate('enabled')}
                          color="primary"
                        >
                          Enable Selected
                        </Button>
                        <Button 
                          onClick={() => handleBulkStatusUpdate('disabled')}
                          color="primary"
                        >
                          Disable Selected
                        </Button>
                        <Button 
                          onClick={() => setSelectedPolicies([])}
                          color="primary"
                        >
                          Clear Selection
                        </Button>
                      </ButtonGroup>
                    ) : null}
                </Stack>
              </Paper>

              {/* Search and Filter Bar */}
              <Paper sx={{ p: 2, mb: 3 }}>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      variant="outlined"
                      placeholder="Search policies..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      InputProps={{
                        startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
                      }}
                    />
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <FormControl fullWidth>
                      <InputLabel>Status Filter</InputLabel>
                      <Select
                        value={statusFilter}
                        label="Status Filter"
                        onChange={(e) => setStatusFilter(e.target.value)}
                      >
                        <MenuItem value="all">All Statuses</MenuItem>
                        <MenuItem value="enabled">Enabled</MenuItem>
                        <MenuItem value="disabled">Disabled</MenuItem>
                        <MenuItem value="not_configured">Not Configured</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Button
                      fullWidth
                      variant="outlined"
                      onClick={handleSelectAllPolicies}
                      startIcon={<CheckIcon />}
                    >
                      {Array.isArray(templateFilteredPolicies) && templateFilteredPolicies.length > 0 && templateFilteredPolicies.every(p => (selectedPolicies || []).includes(p.policy_id)) ? 'Deselect All' : 'Select All'}
                    </Button>
                  </Grid>
                </Grid>
              </Paper>

              {/* Policy List */}
              <Paper sx={{ mb: 3 }}>
                <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                  <Typography variant="h6">
                    Template Policies ({templateFilteredPolicies.length} of {Array.isArray(templatePolicies) ? templatePolicies.length : 0})
                  </Typography>
                </Box>
                
                {isLoadingTemplatePolicies ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                    <CircularProgress />
                  </Box>
                ) : !Array.isArray(templatePolicies) || templatePolicies.length === 0 ? (
                  <Box sx={{ p: 3, textAlign: 'center' }}>
                    <Typography variant="body1" color="text.secondary" gutterBottom>
                      No policies in template system
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Import CIS policies to get started with template management
                    </Typography>
                    <Button
                      variant="contained"
                      onClick={importCisPolicies}
                      disabled={!taskId}
                      startIcon={<UploadIcon />}
                      sx={{ mt: 2 }}
                    >
                      Import CIS Policies
                    </Button>
                  </Box>
                ) : templateFilteredPolicies.length === 0 ? (
                  <Box sx={{ p: 3, textAlign: 'center' }}>
                    <Typography variant="body1" color="text.secondary">
                      No policies match your current filters
                    </Typography>
                  </Box>
                ) : (
                  <List sx={{ maxHeight: 600, overflow: 'auto' }}>
                    {templateFilteredPolicies.map((policy) => (
                      <ListItem
                        key={policy.policy_id}
                        sx={{
                          borderBottom: 1,
                          borderColor: 'divider',
                          '&:hover': { bgcolor: 'action.hover' }
                        }}
                      >
                        <Checkbox
                          checked={(selectedPolicies || []).includes(policy.policy_id)}
                          onChange={() => handlePolicySelection(policy.policy_id)}
                          sx={{ mr: 2 }}
                        />
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant="subtitle1" component="span">
                                {policy.policy_name || policy.title}
                              </Typography>
                              <Chip 
                                label={policy.status || 'not_configured'} 
                                size="small"
                                color={
                                  policy.status === 'enabled' ? 'success' :
                                  policy.status === 'disabled' ? 'error' : 'default'
                                }
                                variant="filled"
                              />
                              {policy.cis_level && (
                                <Chip 
                                  label={`Level ${policy.cis_level}`} 
                                  size="small" 
                                  variant="outlined"
                                />
                              )}
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="body2" color="text.secondary">
                                ID: {policy.policy_id} • Category: {policy.category || 'N/A'}
                              </Typography>
                              {policy.description && (
                                <Typography variant="body2" sx={{ mt: 0.5 }}>
                                  {policy.description.length > 100 
                                    ? `${policy.description.substring(0, 100)}...` 
                                    : policy.description}
                                </Typography>
                              )}
                            </Box>
                          }
                          primaryTypographyProps={{ component: 'div' }}
                          secondaryTypographyProps={{ component: 'div' }}
                        />
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <ButtonGroup size="small" variant="outlined">
                            <Button
                              onClick={() => updatePolicyStatus(policy.policy_id, 'enabled')}
                              color={policy.status === 'enabled' ? 'success' : 'primary'}
                            >
                              Enable
                            </Button>
                            <Button
                              onClick={() => updatePolicyStatus(policy.policy_id, 'disabled')}
                              color={policy.status === 'disabled' ? 'error' : 'primary'}
                            >
                              Disable
                            </Button>
                          </ButtonGroup>
                        </Box>
                      </ListItem>
                    ))}
                  </List>
                )}
              </Paper>

              {/* Templates Section */}
              <Paper sx={{ p: 2 }}>
                <Box sx={{ p: 1, borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                  <Typography variant="h6">
                    Saved Templates ({Array.isArray(templates) ? templates.length : 0})
                  </Typography>
                </Box>
                
                {isLoadingTemplates ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                    <CircularProgress />
                  </Box>
                ) : !Array.isArray(templates) || templates.length === 0 ? (
                  <Box sx={{ p: 3, textAlign: 'center' }}>
                    <Typography variant="body1" color="text.secondary" gutterBottom>
                      No saved templates yet
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Select policies above and create your first template
                    </Typography>
                  </Box>
                ) : (
                  <Grid container spacing={2}>
                    {templates.map((template) => (
                      <Grid item xs={12} md={6} lg={4} key={template.template_id}>
                        <Card>
                          <CardContent>
                            <Typography variant="h6" gutterBottom>
                              {template.name}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                              {template.description || 'No description provided'}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                              <Chip 
                                label={`${template.policy_ids?.length || 0} policies`} 
                                size="small" 
                              />
                              {template.cis_level && (
                                <Chip 
                                  label={`CIS ${template.cis_level}`} 
                                  size="small" 
                                  variant="outlined" 
                                />
                              )}
                            </Box>
                            <Typography variant="caption" color="text.secondary">
                              Created: {new Date(template.created_at).toLocaleDateString()}
                            </Typography>
                          </CardContent>
                          <CardActions>
                            <Button
                              size="small"
                              onClick={() => exportTemplate(template.template_id)}
                              startIcon={<DownloadIcon />}
                            >
                              Export
                            </Button>
                            <Button
                              size="small"
                              onClick={() => duplicateTemplate(template.template_id)}
                              startIcon={<CopyIcon />}
                            >
                              Duplicate
                            </Button>
                            <Button
                              size="small"
                              color="error"
                              onClick={() => deleteTemplate(template.template_id)}
                              startIcon={<DeleteIcon />}
                            >
                              Delete
                            </Button>
                          </CardActions>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>
                )}
              </Paper>
            </Paper>
          )}

          {/* Policy Dashboard Tab */}
          {currentTab === 4 && (
            <Paper sx={{ p: 3, mt: 3 }}>
              <Typography variant="h4" gutterBottom>
                Policy Dashboard
              </Typography>
              
              {/* Import Section */}
              <Paper sx={{ p: 2, mb: 3, bgcolor: 'background.default' }}>
                <Typography variant="h6" gutterBottom>
                  Dashboard Setup
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Import policies from the template system to enable advanced dashboard features.
                </Typography>
                <Button
                  variant="contained"
                  onClick={importToDashboard}
                  disabled={isDashboardLoading}
                  startIcon={<UploadIcon />}
                  sx={{ mr: 2 }}
                >
                  Import Template Policies
                </Button>
                <Button
                  variant="outlined"
                  onClick={fetchDashboardData}
                  disabled={isDashboardLoading}
                  startIcon={<SearchIcon />}
                >
                  Refresh Dashboard
                </Button>
              </Paper>

              {/* Statistics Section */}
              <Paper sx={{ p: 2, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Compliance Overview
                </Typography>
                <DashboardStatistics 
                  statistics={dashboardStatistics} 
                  isLoading={isDashboardLoading} 
                />
              </Paper>

              {/* Search and Filter */}
              <Paper sx={{ p: 2, mb: 3 }}>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      variant="outlined"
                      placeholder="Search policies..."
                      value={dashboardSearchQuery}
                      onChange={(e) => setDashboardSearchQuery(e.target.value)}
                      InputProps={{
                        startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
                      }}
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">
                      {searchDashboardPolicies.length} of {dashboardPolicies.length} policies shown
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>

              {/* Advanced Policy Table */}
              <AdvancedPolicyTable
                policies={searchDashboardPolicies}
                selectedPolicies={selectedDashboardPolicies}
                onSelectPolicy={handleDashboardPolicySelect}
                onSelectAll={handleDashboardSelectAll}
                onBulkUpdate={handleDashboardBulkUpdate}
                onViewHistory={handleViewHistory}
                onViewDocumentation={handleViewDocumentation}
                onUpdatePolicy={handleUpdateDashboardPolicy}
                isLoading={isDashboardLoading}
              />
            </Paper>
          )}

          {/* Deployment Manager Tab */}
          {currentTab === 5 && (
            <Paper sx={{ p: 3, mt: 3 }}>
              <DeploymentManager />
            </Paper>
          )}

          {/* Audit Scanner Tab */}
          {currentTab === 6 && (
            <AuditScanner />
          )}

          {/* Remediation Manager Tab */}
          {currentTab === 7 && (
            <Paper sx={{ p: 3, mt: 3 }}>
              <Typography variant="h5" gutterBottom>
                Automated Remediation & Rollback Manager
              </Typography>
              <Typography variant="body1" color="text.secondary" paragraph>
                Step 7: Automatically fix compliance issues and safely rollback changes when needed.
              </Typography>
              
              <Alert severity="success" sx={{ mb: 3 }}>
                <Typography variant="body2">
                  <strong>Remediation System Features:</strong>
                  <br />• Automated policy remediation with risk assessment
                  <br />• Comprehensive system backups before changes
                  <br />• Safe rollback to previous configuration states
                  <br />• Real-time remediation progress monitoring
                  <br />• Detailed remediation logs and reporting
                </Typography>
              </Alert>

              <Grid container spacing={3}>
                <Grid item xs={12} md={4}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom color="primary">
                        Create Remediation Plan
                      </Typography>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        Generate automated fix plan from audit results
                      </Typography>
                      <Button variant="contained" startIcon={<AddIcon />} fullWidth>
                        Create Plan
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom color="secondary">
                        System Backups
                      </Typography>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        Create and manage system configuration backups
                      </Typography>
                      <Button variant="contained" color="secondary" startIcon={<CopyIcon />} fullWidth>
                        Manage Backups
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} md={4}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom color="warning">
                        Rollback Plans
                      </Typography>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        Safely restore previous system configurations
                      </Typography>
                      <Button variant="contained" color="warning" startIcon={<HistoryIcon />} fullWidth>
                        Create Rollback
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Active Remediation Sessions
                      </Typography>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        Monitor ongoing remediation executions
                      </Typography>
                      <Button variant="outlined" startIcon={<CircularProgress size={20} />} fullWidth>
                        View Active Sessions
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Remediation Statistics
                      </Typography>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        View comprehensive remediation metrics
                      </Typography>
                      <Button variant="outlined" startIcon={<InfoIcon />} fullWidth>
                        View Statistics
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              <Alert severity="error" sx={{ mt: 3 }}>
                <Typography variant="body2">
                  <strong>⚠️ Critical:</strong> Remediation actions modify system configurations and require administrator privileges. Always create backups before remediation and verify rollback capabilities.
                </Typography>
              </Alert>
            </Paper>
          )}

          {/* Policy History Dialog */}
          <PolicyHistoryDialog
            open={historyDialog.open}
            onClose={() => setHistoryDialog({ open: false, policyId: null, policyName: '' })}
            policyId={historyDialog.policyId}
            policyName={historyDialog.policyName}
          />

          {/* Create Template Dialog */}
          <Dialog 
            open={showCreateTemplate} 
            onClose={() => setShowCreateTemplate(false)}
            maxWidth="sm"
            fullWidth
          >
            <DialogTitle>Create New Template</DialogTitle>
            <DialogContent>
              <TextField
                autoFocus
                margin="dense"
                label="Template Name"
                fullWidth
                variant="outlined"
                value={newTemplate.name}
                onChange={(e) => setNewTemplate(prev => ({ ...prev, name: e.target.value }))}
                sx={{ mb: 2 }}
              />
              <TextField
                margin="dense"
                label="Description"
                fullWidth
                multiline
                rows={3}
                variant="outlined"
                value={newTemplate.description}
                onChange={(e) => setNewTemplate(prev => ({ ...prev, description: e.target.value }))}
                sx={{ mb: 2 }}
              />
              <FormControl fullWidth>
                <InputLabel>CIS Level</InputLabel>
                <Select
                  value={newTemplate.cis_level}
                  label="CIS Level"
                  onChange={(e) => setNewTemplate(prev => ({ ...prev, cis_level: e.target.value }))}
                >
                  <MenuItem value="Level 1">Level 1</MenuItem>
                  <MenuItem value="Level 2">Level 2</MenuItem>
                </Select>
              </FormControl>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Selected policies: {(selectedPolicies || []).length}
              </Typography>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setShowCreateTemplate(false)}>Cancel</Button>
              <Button onClick={handleCreateTemplate} variant="contained">Create Template</Button>
            </DialogActions>
          </Dialog>
        </Container>
      </Box>
      
      {/* Global Chatbot Widget - appears on all pages */}
      <ChatbotWidget />
    </ThemeProvider>
  );
}

export default App;
