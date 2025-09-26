import React, { useState, useEffect } from 'react';
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
  Card,
  CardContent
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
  History as HistoryIcon
} from '@mui/icons-material';
import axios from 'axios';
import { saveAs } from 'file-saver';
import FileUploader from './components/FileUploader';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  // Theme and UI state
  const [darkMode, setDarkMode] = useState(false);

  const theme = createTheme({
    palette: {
      mode: darkMode ? 'dark' : 'light',
    },
  });

  const [drawerOpen, setDrawerOpen] = useState(false);

  // File upload and processing state
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [taskId, setTaskId] = useState('');
  const [extractionStatus, setExtractionStatus] = useState(null);

  // Policy viewing state
  const [policies, setPolicies] = useState([]);
  const [isLoadingPolicies, setIsLoadingPolicies] = useState(false);
  const [loadError, setLoadError] = useState('');

  // Tasks state
  const [completedTasks, setCompletedTasks] = useState([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);

  // Template Manager state
  const [templatePolicies, setTemplatePolicies] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);
  const [isLoadingTemplatePolicies, setIsLoadingTemplatePolicies] = useState(false);

  // State for UI
  const [currentTab, setCurrentTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMenuAnchor, setFilterMenuAnchor] = useState(null);
  const [statusExpanded, setStatusExpanded] = useState(true);

  // Status polling interval
  const POLLING_INTERVAL = 2000; // 2 seconds

  // Effect to load template data when switching to Template Manager tab
  useEffect(() => {
    if (currentTab === 3) {
      fetchTemplates();
      fetchTemplatePolicies();
    }
  }, [currentTab]);

  // Effect to poll status if task is in progress
  useEffect(() => {
    let interval;

    if (taskId && extractionStatus && extractionStatus.status === 'processing') {
      interval = setInterval(() => {
        fetchTaskStatus(taskId);
      }, POLLING_INTERVAL);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [taskId, extractionStatus]);

  // Fetch task status
  const fetchTaskStatus = async (id) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/status/${id}`);
      setExtractionStatus(response.data);
    } catch (error) {
      console.error('Error fetching status:', error);
    }
  };

  // Fetch completed tasks
  const fetchCompletedTasks = async () => {
    setIsLoadingTasks(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/completed-tasks`);
      setCompletedTasks(response.data.tasks);
    } catch (error) {
      console.error('Error fetching completed tasks:', error);
      setCompletedTasks([]);
    } finally {
      setIsLoadingTasks(false);
    }
  };

  // Fetch policies for a task
  const fetchPolicies = async (id) => {
    setIsLoadingPolicies(true);
    setLoadError('');
    try {
      const response = await axios.get(`${API_BASE_URL}/results/${id}`);
      setPolicies(response.data.policies || []);
    } catch (error) {
      console.error('Error fetching policies:', error);
      setLoadError('Failed to load policies. Please try again.');
      setPolicies([]);
    } finally {
      setIsLoadingPolicies(false);
    }
  };

  const handleFileUpload = async () => {
    if (!file) {
      setUploadError('Please select a file first');
      return;
    }

    setIsUploading(true);
    setUploadError('');
    
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE_URL}/upload-pdf/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setTaskId(response.data.task_id);
      setExtractionStatus({ status: 'processing' });
      
      // Start polling for status
      fetchTaskStatus(response.data.task_id);
    } catch (error) {
      console.error('Upload error:', error);
      setUploadError(error.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleTaskSwitch = (id) => {
    setTaskId(id);
    fetchTaskStatus(id);
    fetchPolicies(id);
  };

  const handleDownload = async (id) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/download/${id}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/json' });
      saveAs(blob, `cis-policies-${id}.json`);
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

  // Load completed tasks on component mount
  useEffect(() => {
    fetchCompletedTasks();
  }, []);

  // If switching to Template Manager tab (index 3), load templates and policies
  useEffect(() => {
    if (currentTab === 3) {
      fetchTemplates();
      fetchTemplatePolicies();
    }
  }, [currentTab]);

  const fetchTemplates = async () => {
    setIsLoadingTemplates(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/templates/`);
      const templates = response.data.templates || [];
      setTemplates(Array.isArray(templates) ? templates : []);
    } catch (error) {
      console.error('Error fetching templates:', error);
      setTemplates([]);
    } finally {
      setIsLoadingTemplates(false);
    }
  };

  const fetchTemplatePolicies = async () => {
    setIsLoadingTemplatePolicies(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/template-policies/`);
      const policies = response.data.policies || [];
      setTemplatePolicies(Array.isArray(policies) ? policies : []);
    } catch (error) {
      console.error('Error fetching template policies:', error);
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
      fetchTemplatePolicies();
    } catch (error) {
      console.error('Error importing CIS policies:', error);
      alert('Error importing CIS policies: ' + (error.response?.data?.detail || error.message));
    }
  };

  const createTemplate = async (templateData) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/templates/`, templateData);
      alert('Template created successfully');
      fetchTemplates();
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
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              CIS Benchmark Parser
            </Typography>
            <IconButton
              color="inherit"
              onClick={() => setDarkMode(!darkMode)}
            >
              {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>
          </Toolbar>
        </AppBar>

        <Drawer
          anchor="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        >
          <Box sx={{ width: 250 }}>
            <List>
              <ListItem button onClick={() => { setCurrentTab(0); setDrawerOpen(false); }}>
                <ListItemIcon><UploadIcon /></ListItemIcon>
                <ListItemText primary="Upload Benchmark" />
              </ListItem>
              <ListItem button onClick={() => { setCurrentTab(1); setDrawerOpen(false); }}>
                <ListItemIcon><SearchIcon /></ListItemIcon>
                <ListItemText primary="View Policies" />
              </ListItem>
              <ListItem button onClick={() => { setCurrentTab(2); setDrawerOpen(false); }}>
                <ListItemIcon><HistoryIcon /></ListItemIcon>
                <ListItemText primary="Previous Extractions" />
              </ListItem>
              <ListItem button onClick={() => { setCurrentTab(3); setDrawerOpen(false); }}>
                <ListItemIcon><SettingsIcon /></ListItemIcon>
                <ListItemText primary="Template Manager" />
              </ListItem>
            </List>
            <Divider />
            <List>
              <ListItem>
                <FormControlLabel
                  control={
                    <Switch
                      checked={darkMode}
                      onChange={(e) => setDarkMode(e.target.checked)}
                    />
                  }
                  label="Dark Mode"
                />
              </ListItem>
            </List>
          </Box>
        </Drawer>

        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
          <Tabs value={currentTab} onChange={(e, newValue) => setCurrentTab(newValue)}>
            <Tab label="Upload Benchmark" />
            <Tab label="View Policies" />
            <Tab label="Previous Extractions" />
            <Tab label="Template Manager" />
          </Tabs>

          {/* Upload Tab */}
          {currentTab === 0 && (
            <Paper sx={{ p: 3, mt: 3 }}>
              <Typography variant="h5" gutterBottom>
                Upload CIS Benchmark PDF
              </Typography>
              
              <FileUploader
                file={file}
                setFile={setFile}
                onUpload={handleFileUpload}
                isUploading={isUploading}
                uploadError={uploadError}
              />

              {taskId && extractionStatus && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Extraction Status
                  </Typography>
                  <Alert severity={extractionStatus.status === 'completed' ? 'success' : 'info'}>
                    Status: {extractionStatus.status}
                    {extractionStatus.message && ` - ${extractionStatus.message}`}
                  </Alert>
                  
                  {extractionStatus.status === 'processing' && (
                    <LinearProgress sx={{ mt: 2 }} />
                  )}
                  
                  {extractionStatus.status === 'completed' && (
                    <Box sx={{ mt: 2 }}>
                      <Button
                        variant="contained"
                        onClick={() => setCurrentTab(1)}
                        sx={{ mr: 2 }}
                      >
                        View Extracted Policies
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={() => handleDownload(taskId)}
                      >
                        Download JSON
                      </Button>
                    </Box>
                  )}
                </Box>
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

              {/* Templates Section */}
              <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                <Typography variant="h6" gutterBottom>
                  Saved Templates ({Array.isArray(templates) ? templates.length : 0})
                </Typography>
                
                {isLoadingTemplates ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                    <CircularProgress />
                  </Box>
                ) : !Array.isArray(templates) || templates.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No saved templates yet. Create templates from your policies.
                  </Typography>
                ) : (
                  <List>
                    {templates.map((template) => (
                      <ListItem
                        key={template.id || template.template_id}
                        secondaryAction={
                          <Button
                            size="small"
                            onClick={() => exportTemplate(template.id || template.template_id)}
                            startIcon={<DownloadIcon />}
                          >
                            Export
                          </Button>
                        }
                      >
                        <ListItemText
                          primary={template.name}
                          secondary={`${template.policy_count || template.policy_ids?.length || 0} policies • Created: ${template.created_at ? new Date(template.created_at).toLocaleDateString() : 'N/A'}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </Paper>
            </Paper>
          )}
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;