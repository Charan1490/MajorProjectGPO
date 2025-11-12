/**
 * Deployment Manager Component
 * Handles offline GPO deployment package creation and management
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  Card,
  CardContent,
  CardActions,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Chip,
  LinearProgress,
  Alert,
  IconButton,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material';
import {
  Add as AddIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  Build as BuildIcon,
  Visibility as ViewIcon,
  GetApp as PackageIcon,
  Computer as ComputerIcon,
  Security as SecurityIcon,
  Code as CodeIcon,
  Settings as SettingsIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const DeploymentManager = () => {
  // State management
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statistics, setStatistics] = useState(null);
  
  // Dialog states
  const [createDialog, setCreateDialog] = useState(false);
  const [detailsDialog, setDetailsDialog] = useState(false);
  const [buildDialog, setBuildDialog] = useState(false);
  const [selectedPackage, setSelectedPackage] = useState(null);
  
  // Create package form state
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    target_os: 'windows_10_enterprise',
    policy_selection: 'all',
    selected_template: '',
    selected_groups: [],
    selected_tags: [],
    selected_policies: [],
    include_formats: ['lgpo_pol', 'registry_reg', 'powershell_ps1'],
    include_scripts: true,
    include_documentation: true,
    include_verification: true,
    create_zip_package: true,
    use_powershell: true,
    use_batch: true,
    require_admin: true,
    create_backup: true,
    verify_before_apply: true,
    log_changes: true,
    rollback_support: true
  });
  
  // Options data
  const [windowsVersions, setWindowsVersions] = useState([]);
  const [packageFormats, setPackageFormats] = useState([]);
  const [availableGroups, setAvailableGroups] = useState([]);
  const [availableTags, setAvailableTags] = useState([]);
  const [availableTemplates, setAvailableTemplates] = useState([]);
  const [lgpoStatus, setLgpoStatus] = useState(null);
  
  // Build monitoring
  const [buildJobs, setBuildJobs] = useState({});
  
  useEffect(() => {
    fetchPackages();
    fetchStatistics();
    fetchWindowsVersions();
    fetchPackageFormats();
    fetchAvailableOptions();
    fetchLgpoStatus();
  }, []);
  
  const fetchPackages = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/deployment/packages`);
      if (response.data.success) {
        setPackages(response.data.data.packages);
      }
    } catch (err) {
      setError('Failed to fetch deployment packages');
      console.error('Error fetching packages:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchStatistics = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/deployment/statistics`);
      if (response.data.success) {
        setStatistics(response.data.data);
      }
    } catch (err) {
      console.error('Error fetching statistics:', err);
    }
  };
  
  const fetchWindowsVersions = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/deployment/windows-versions`);
      if (response.data.success) {
        setWindowsVersions(response.data.data.versions);
      }
    } catch (err) {
      console.error('Error fetching Windows versions:', err);
    }
  };
  
  const fetchPackageFormats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/deployment/package-formats`);
      if (response.data.success) {
        setPackageFormats(response.data.data.formats);
      }
    } catch (err) {
      console.error('Error fetching package formats:', err);
    }
  };
  
  const fetchAvailableOptions = async () => {
    try {
      // Fetch groups from dashboard
      const groupsResponse = await axios.get(`${API_BASE_URL}/dashboard/groups`);
      if (groupsResponse.data.success) {
        setAvailableGroups(groupsResponse.data.data.groups);
      }
      
      // Fetch tags from dashboard
      const tagsResponse = await axios.get(`${API_BASE_URL}/dashboard/tags`);
      if (tagsResponse.data.success) {
        setAvailableTags(tagsResponse.data.data.tags);
      }
      
      // Fetch templates
      const templatesResponse = await axios.get(`${API_BASE_URL}/templates/`);
      if (templatesResponse.data.templates) {
        setAvailableTemplates(templatesResponse.data.templates);
      }
    } catch (err) {
      console.error('Error fetching options:', err);
    }
  };
  
  const fetchLgpoStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/deployment/lgpo/status`);
      if (response.data.success) {
        setLgpoStatus(response.data.data);
      }
    } catch (err) {
      console.error('Error fetching LGPO status:', err);
    }
  };
  
  const handleCreatePackage = async () => {
    try {
      setLoading(true);
      
      const payload = {
        name: createForm.name,
        description: createForm.description,
        target_os: createForm.target_os,
        include_formats: createForm.include_formats,
        include_scripts: createForm.include_scripts,
        include_documentation: createForm.include_documentation,
        include_verification: createForm.include_verification,
        create_zip_package: createForm.create_zip_package,
        use_powershell: createForm.use_powershell,
        use_batch: createForm.use_batch,
        require_admin: createForm.require_admin,
        create_backup: createForm.create_backup,
        verify_before_apply: createForm.verify_before_apply,
        log_changes: createForm.log_changes,
        rollback_support: createForm.rollback_support
      };
      
      // Add policy selection parameters
      if (createForm.policy_selection === 'template') {
        payload.template_id = createForm.selected_template;
      } else if (createForm.policy_selection === 'groups') {
        payload.group_names = createForm.selected_groups;
      } else if (createForm.policy_selection === 'tags') {
        payload.tag_names = createForm.selected_tags;
      } else if (createForm.policy_selection === 'specific') {
        payload.policy_ids = createForm.selected_policies;
      }
      
      const response = await axios.post(`${API_BASE_URL}/deployment/packages`, payload);
      
      if (response.data.success) {
        setCreateDialog(false);
        resetCreateForm();
        fetchPackages();
        fetchStatistics();
      } else {
        setError(response.data.message || 'Failed to create package');
      }
      
    } catch (err) {
      setError('Error creating deployment package');
      console.error('Error creating package:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const handleBuildPackage = async (packageId) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/deployment/packages/${packageId}/build`);
      
      if (response.data.success) {
        const jobId = response.data.data.job_id;
        setBuildJobs(prev => ({ ...prev, [packageId]: jobId }));
        
        // Start monitoring job progress
        monitorBuildJob(jobId, packageId);
      } else {
        setError(response.data.message || 'Failed to start package build');
      }
      
    } catch (err) {
      setError('Error starting package build');
      console.error('Error building package:', err);
    }
  };
  
  const monitorBuildJob = async (jobId, packageId) => {
    const checkProgress = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/deployment/jobs/${jobId}`);
        
        if (response.data.success) {
          const job = response.data.data;
          
          if (job.status === 'completed' || job.status === 'failed') {
            setBuildJobs(prev => {
              const updated = { ...prev };
              delete updated[packageId];
              return updated;
            });
            fetchPackages();
            fetchStatistics();
          } else {
            // Continue monitoring
            setTimeout(checkProgress, 2000);
          }
        }
      } catch (err) {
        console.error('Error monitoring build job:', err);
        setBuildJobs(prev => {
          const updated = { ...prev };
          delete updated[packageId];
          return updated;
        });
      }
    };
    
    checkProgress();
  };
  
  const handleDownloadPackage = async (packageId) => {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/deployment/packages/${packageId}/download`,
        {},
        { responseType: 'blob' }
      );
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from headers if available
      const contentDisposition = response.headers['content-disposition'];
      let filename = `deployment-package-${packageId}.zip`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
    } catch (err) {
      setError('Error downloading package');
      console.error('Error downloading package:', err);
    }
  };
  
  const handleDeletePackage = async (packageId) => {
    if (!window.confirm('Are you sure you want to delete this deployment package?')) {
      return;
    }
    
    try {
      const response = await axios.delete(`${API_BASE_URL}/deployment/packages/${packageId}`);
      
      if (response.data.success) {
        fetchPackages();
        fetchStatistics();
      } else {
        setError(response.data.message || 'Failed to delete package');
      }
      
    } catch (err) {
      setError('Error deleting package');
      console.error('Error deleting package:', err);
    }
  };
  
  const resetCreateForm = () => {
    setCreateForm({
      name: '',
      description: '',
      target_os: 'windows_10_enterprise',
      policy_selection: 'all',
      selected_template: '',
      selected_groups: [],
      selected_tags: [],
      selected_policies: [],
      include_formats: ['lgpo_pol', 'registry_reg', 'powershell_ps1'],
      include_scripts: true,
      include_documentation: true,
      include_verification: true,
      create_zip_package: true,
      use_powershell: true,
      use_batch: true,
      require_admin: true,
      create_backup: true,
      verify_before_apply: true,
      log_changes: true,
      rollback_support: true
    });
  };
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'processing':
        return <CircularProgress size={20} />;
      default:
        return <InfoIcon color="info" />;
    }
  };
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'processing':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Deployment Package Manager
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Create and manage offline GPO deployment packages for Windows systems
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      
      {/* LGPO Status Alert */}
      {lgpoStatus && !lgpoStatus.available && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          LGPO.exe not found. Download from Microsoft for full functionality.
          Registry files will be generated instead of policy files.
        </Alert>
      )}
      
      {/* Statistics Cards */}
      {statistics && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <PackageIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">{statistics.total_packages}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Total Packages
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <CheckIcon color="success" sx={{ mr: 1 }} />
                  <Typography variant="h6">{statistics.completed_packages}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Completed
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <SecurityIcon color="info" sx={{ mr: 1 }} />
                  <Typography variant="h6">{statistics.total_policies_packaged}</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Policies Packaged
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <BuildIcon color="secondary" sx={{ mr: 1 }} />
                  <Typography variant="h6">{statistics.success_rate.toFixed(1)}%</Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Success Rate
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
      
      {/* Action Buttons */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialog(true)}
        >
          Create Package
        </Button>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={fetchPackages}
        >
          Refresh
        </Button>
      </Box>
      
      {/* Packages Table */}
      <Paper sx={{ width: '100%' }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Package</TableCell>
                <TableCell>Target OS</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Policies</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : packages.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    No deployment packages found
                  </TableCell>
                </TableRow>
              ) : (
                packages.map((pkg) => (
                  <TableRow key={pkg.package_id}>
                    <TableCell>
                      <Box>
                        <Typography variant="subtitle2">
                          {pkg.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {pkg.description}
                        </Typography>
                      </Box>
                    </TableCell>
                    
                    <TableCell>
                      <Chip
                        label={pkg.target_os.replace('_', ' ')}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    </TableCell>
                    
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getStatusIcon(pkg.status)}
                        <Chip
                          label={pkg.status}
                          size="small"
                          color={getStatusColor(pkg.status)}
                          variant="filled"
                        />
                        {buildJobs[pkg.package_id] && (
                          <CircularProgress size={16} />
                        )}
                      </Box>
                    </TableCell>
                    
                    <TableCell>{pkg.source_policies?.length || 0}</TableCell>
                    
                    <TableCell>
                      {new Date(pkg.created_at).toLocaleDateString()}
                    </TableCell>
                    
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Tooltip title="View Details">
                          <IconButton
                            size="small"
                            onClick={() => {
                              setSelectedPackage(pkg);
                              setDetailsDialog(true);
                            }}
                          >
                            <ViewIcon />
                          </IconButton>
                        </Tooltip>
                        
                        {pkg.status === 'pending' && (
                          <Tooltip title="Build Package">
                            <IconButton
                              size="small"
                              onClick={() => handleBuildPackage(pkg.package_id)}
                              disabled={!!buildJobs[pkg.package_id]}
                            >
                              <BuildIcon />
                            </IconButton>
                          </Tooltip>
                        )}
                        
                        {pkg.status === 'completed' && (
                          <Tooltip title="Download Package">
                            <IconButton
                              size="small"
                              onClick={() => handleDownloadPackage(pkg.package_id)}
                            >
                              <DownloadIcon />
                            </IconButton>
                          </Tooltip>
                        )}
                        
                        <Tooltip title="Delete Package">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeletePackage(pkg.package_id)}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
      
      {/* Create Package Dialog */}
      <CreatePackageDialog
        open={createDialog}
        onClose={() => {
          setCreateDialog(false);
          resetCreateForm();
        }}
        formData={createForm}
        onFormChange={setCreateForm}
        onSubmit={handleCreatePackage}
        windowsVersions={windowsVersions}
        packageFormats={packageFormats}
        availableGroups={availableGroups}
        availableTags={availableTags}
        availableTemplates={availableTemplates}
        loading={loading}
      />
      
      {/* Package Details Dialog */}
      <PackageDetailsDialog
        open={detailsDialog}
        onClose={() => {
          setDetailsDialog(false);
          setSelectedPackage(null);
        }}
        package={selectedPackage}
      />
    </Box>
  );
};

// Create Package Dialog Component
const CreatePackageDialog = ({ 
  open, onClose, formData, onFormChange, onSubmit, 
  windowsVersions, packageFormats, availableGroups, availableTags, availableTemplates, loading 
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const steps = ['Basic Info', 'Policy Selection', 'Export Formats', 'Script Options'];
  
  const handleNext = () => {
    setActiveStep((prev) => prev + 1);
  };
  
  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };
  
  const handleSubmit = () => {
    onSubmit();
    setActiveStep(0);
  };
  
  const updateForm = (field, value) => {
    onFormChange(prev => ({ ...prev, [field]: value }));
  };
  
  const isStepValid = (step) => {
    switch (step) {
      case 0:
        return formData.name && formData.description && formData.target_os;
      case 1:
        if (formData.policy_selection === 'groups') {
          return formData.selected_groups.length > 0;
        } else if (formData.policy_selection === 'tags') {
          return formData.selected_tags.length > 0;
        } else if (formData.policy_selection === 'specific') {
          return formData.selected_policies.length > 0;
        }
        return true; // 'all' is always valid
      case 2:
        return formData.include_formats.length > 0;
      default:
        return true;
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Create Deployment Package</DialogTitle>
      
      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
        
        {/* Step Content */}
        {activeStep === 0 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              fullWidth
              label="Package Name"
              value={formData.name}
              onChange={(e) => updateForm('name', e.target.value)}
              required
            />
            <TextField
              fullWidth
              label="Description"
              multiline
              rows={3}
              value={formData.description}
              onChange={(e) => updateForm('description', e.target.value)}
              required
            />
            <FormControl fullWidth required>
              <InputLabel>Target Windows Version</InputLabel>
              <Select
                value={formData.target_os}
                onChange={(e) => updateForm('target_os', e.target.value)}
                label="Target Windows Version"
              >
                {windowsVersions.map((version) => (
                  <MenuItem key={version.value} value={version.value}>
                    {version.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        )}
        
        {activeStep === 1 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Policy Selection Method</InputLabel>
              <Select
                value={formData.policy_selection}
                onChange={(e) => updateForm('policy_selection', e.target.value)}
                label="Policy Selection Method"
              >
                <MenuItem value="all">All Available Policies</MenuItem>
                <MenuItem value="template">Select by Template</MenuItem>
                <MenuItem value="groups">Select by Groups</MenuItem>
                <MenuItem value="tags">Select by Tags</MenuItem>
                <MenuItem value="specific">Specific Policy IDs</MenuItem>
              </Select>
            </FormControl>
            
            {formData.policy_selection === 'template' && (
              <FormControl fullWidth>
                <InputLabel>Select Template</InputLabel>
                <Select
                  value={formData.selected_template || ''}
                  onChange={(e) => updateForm('selected_template', e.target.value)}
                  label="Select Template"
                >
                  {availableTemplates.map((template) => (
                    <MenuItem key={template.template_id} value={template.template_id}>
                      {template.name} ({template.policy_count || 0} policies)
                      {template.description && (
                        <Typography variant="caption" display="block" color="text.secondary">
                          {template.description}
                        </Typography>
                      )}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            
            {formData.policy_selection === 'groups' && (
              <FormControl fullWidth>
                <InputLabel>Select Groups</InputLabel>
                <Select
                  multiple
                  value={formData.selected_groups}
                  onChange={(e) => updateForm('selected_groups', e.target.value)}
                  label="Select Groups"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {availableGroups.map((group) => (
                    <MenuItem key={group.group_id} value={group.name}>
                      {group.name} ({group.policy_ids?.length || 0} policies)
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            
            {formData.policy_selection === 'tags' && (
              <FormControl fullWidth>
                <InputLabel>Select Tags</InputLabel>
                <Select
                  multiple
                  value={formData.selected_tags}
                  onChange={(e) => updateForm('selected_tags', e.target.value)}
                  label="Select Tags"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {availableTags.map((tag) => (
                    <MenuItem key={tag.tag_id} value={tag.name}>
                      {tag.name} ({tag.policy_ids?.length || 0} policies)
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            
            {formData.policy_selection === 'specific' && (
              <TextField
                fullWidth
                label="Policy IDs (comma-separated)"
                multiline
                rows={3}
                value={formData.selected_policies.join(', ')}
                onChange={(e) => updateForm('selected_policies', e.target.value.split(',').map(id => id.trim()).filter(Boolean))}
                placeholder="policy-id-1, policy-id-2, policy-id-3"
              />
            )}
          </Box>
        )}
        
        {activeStep === 2 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="h6" gutterBottom>
              Export Formats
            </Typography>
            
            <FormGroup>
              {packageFormats.map((format) => (
                <FormControlLabel
                  key={format.value}
                  control={
                    <Checkbox
                      checked={formData.include_formats.includes(format.value)}
                      onChange={(e) => {
                        const formats = [...formData.include_formats];
                        if (e.target.checked) {
                          formats.push(format.value);
                        } else {
                          const index = formats.indexOf(format.value);
                          if (index > -1) {
                            formats.splice(index, 1);
                          }
                        }
                        updateForm('include_formats', formats);
                      }}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body1">{format.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {format.description}
                      </Typography>
                    </Box>
                  }
                />
              ))}
            </FormGroup>
            
            <Divider />
            
            <Typography variant="h6" gutterBottom>
              Package Options
            </Typography>
            
            <FormGroup>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.include_scripts}
                    onChange={(e) => updateForm('include_scripts', e.target.checked)}
                  />
                }
                label="Include deployment scripts"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.include_documentation}
                    onChange={(e) => updateForm('include_documentation', e.target.checked)}
                  />
                }
                label="Include documentation"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.include_verification}
                    onChange={(e) => updateForm('include_verification', e.target.checked)}
                  />
                }
                label="Include verification scripts"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.create_zip_package}
                    onChange={(e) => updateForm('create_zip_package', e.target.checked)}
                  />
                }
                label="Create ZIP package"
              />
            </FormGroup>
          </Box>
        )}
        
        {activeStep === 3 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="h6" gutterBottom>
              Script Configuration
            </Typography>
            
            <FormGroup>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.use_powershell}
                    onChange={(e) => updateForm('use_powershell', e.target.checked)}
                  />
                }
                label="Generate PowerShell scripts"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.use_batch}
                    onChange={(e) => updateForm('use_batch', e.target.checked)}
                  />
                }
                label="Generate batch wrapper scripts"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.require_admin}
                    onChange={(e) => updateForm('require_admin', e.target.checked)}
                  />
                }
                label="Require administrator privileges"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.create_backup}
                    onChange={(e) => updateForm('create_backup', e.target.checked)}
                  />
                }
                label="Create system backup before deployment"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.verify_before_apply}
                    onChange={(e) => updateForm('verify_before_apply', e.target.checked)}
                  />
                }
                label="Verify settings before applying"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.log_changes}
                    onChange={(e) => updateForm('log_changes', e.target.checked)}
                  />
                }
                label="Log all changes"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.rollback_support}
                    onChange={(e) => updateForm('rollback_support', e.target.checked)}
                  />
                }
                label="Include rollback scripts"
              />
            </FormGroup>
          </Box>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        {activeStep > 0 && (
          <Button onClick={handleBack}>Back</Button>
        )}
        {activeStep < steps.length - 1 ? (
          <Button 
            onClick={handleNext}
            disabled={!isStepValid(activeStep)}
            variant="contained"
          >
            Next
          </Button>
        ) : (
          <Button 
            onClick={handleSubmit}
            disabled={loading || !isStepValid(activeStep)}
            variant="contained"
          >
            {loading ? <CircularProgress size={20} /> : 'Create Package'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

// Package Details Dialog Component  
const PackageDetailsDialog = ({ open, onClose, package: pkg }) => {
  if (!pkg) return null;
  
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Package Details: {pkg.name}
      </DialogTitle>
      
      <DialogContent>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>
              Basic Information
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">Package ID</Typography>
              <Typography variant="body1" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                {pkg.package_id}
              </Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">Description</Typography>
              <Typography variant="body1">{pkg.description}</Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">Target OS</Typography>
              <Chip label={pkg.target_os.replace('_', ' ')} color="primary" size="small" />
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">Status</Typography>
              <Chip label={pkg.status} color={getStatusColor(pkg.status)} size="small" />
            </Box>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>
              Package Details
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">Created</Typography>
              <Typography variant="body1">
                {new Date(pkg.created_at).toLocaleString()}
              </Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">Last Updated</Typography>
              <Typography variant="body1">
                {new Date(pkg.updated_at).toLocaleString()}
              </Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">Policies Count</Typography>
              <Typography variant="body1">{pkg.source_policies?.length || 0}</Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">Total Files</Typography>
              <Typography variant="body1">{pkg.total_files || 0}</Typography>
            </Box>
            {pkg.package_size_bytes > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">Package Size</Typography>
                <Typography variant="body1">
                  {(pkg.package_size_bytes / 1024).toFixed(1)} KB
                </Typography>
              </Box>
            )}
          </Grid>
          
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>
              Export Configuration
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
              {pkg.export_config?.include_formats?.map((format) => (
                <Chip key={format} label={format.replace('_', ' ')} size="small" variant="outlined" />
              ))}
            </Box>
            
            {pkg.source_groups?.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Source Groups
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {pkg.source_groups.map((group) => (
                    <Chip key={group} label={group} size="small" color="secondary" />
                  ))}
                </Box>
              </Box>
            )}
            
            {pkg.source_tags?.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Source Tags
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {pkg.source_tags.map((tag) => (
                    <Chip key={tag} label={tag} size="small" color="info" />
                  ))}
                </Box>
              </Box>
            )}
          </Grid>
          
          {pkg.validation_results && (
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Validation Results
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                {pkg.integrity_verified ? (
                  <CheckIcon color="success" />
                ) : (
                  <ErrorIcon color="error" />
                )}
                <Typography variant="body1">
                  {pkg.integrity_verified ? 'Package validated successfully' : 'Package validation failed'}
                </Typography>
              </Box>
            </Grid>
          )}
        </Grid>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

function getStatusColor(status) {
  switch (status) {
    case 'completed':
      return 'success';
    case 'failed':
      return 'error';
    case 'processing':
      return 'warning';
    default:
      return 'default';
  }
}

export default DeploymentManager;