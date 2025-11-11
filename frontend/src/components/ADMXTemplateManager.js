import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Alert,
  AlertTitle,
  Divider,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card,
  CardContent,
  CardActions,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Checkbox,
  FormControlLabel
} from '@mui/material';
import {
  Download as DownloadIcon,
  Visibility as PreviewIcon,
  CheckCircle as ValidIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  ExpandMore as ExpandMoreIcon,
  Code as CodeIcon,
  Save as SaveIcon,
  FolderOpen as FolderIcon,
  FilePresent as FileIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const ADMXTemplateManager = ({ templates, onRefresh }) => {
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [exportDialog, setExportDialog] = useState(false);
  const [previewDialog, setPreviewDialog] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportResult, setExportResult] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  
  // Export configuration
  const [namespace, setNamespace] = useState('CISBenchmark');
  const [prefix, setPrefix] = useState('CIS');
  const [outputDir, setOutputDir] = useState('admx_output');
  const [validate, setValidate] = useState(true);

  // Handle export dialog open
  const handleExportClick = (template) => {
    setSelectedTemplate(template);
    setExportDialog(true);
    setExportResult(null);
  };

  // Handle preview dialog open
  const handlePreviewClick = async (template) => {
    setSelectedTemplate(template);
    setPreviewDialog(true);
    setExportLoading(true);
    
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/templates/${template.template_id}/export/admx`,
        null,
        {
          params: {
            namespace,
            prefix,
            validate: true
          }
        }
      );
      
      setPreviewData(response.data.data);
    } catch (error) {
      console.error('Error previewing ADMX:', error);
      setPreviewData(null);
    } finally {
      setExportLoading(false);
    }
  };

  // Handle export to files
  const handleExportToFiles = async () => {
    if (!selectedTemplate) return;
    
    setExportLoading(true);
    setExportResult(null);
    
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/templates/${selectedTemplate.template_id}/save-admx`,
        null,
        {
          params: {
            output_dir: outputDir,
            namespace,
            prefix
          }
        }
      );
      
      setExportResult({
        success: true,
        data: response.data.data
      });
    } catch (error) {
      console.error('Error exporting ADMX:', error);
      setExportResult({
        success: false,
        error: error.response?.data?.detail || error.message
      });
    } finally {
      setExportLoading(false);
    }
  };

  // Handle bulk export
  const handleBulkExport = async () => {
    if (templates.length === 0) return;
    
    setExportLoading(true);
    
    try {
      const templateIds = templates.map(t => t.template_id);
      const response = await axios.post(
        `${API_BASE_URL}/api/templates/bulk-export-admx`,
        {
          template_ids: templateIds,
          output_dir: outputDir,
          namespace,
          prefix
        }
      );
      
      setExportResult({
        success: true,
        data: response.data.data,
        bulk: true
      });
    } catch (error) {
      console.error('Error in bulk export:', error);
      setExportResult({
        success: false,
        error: error.response?.data?.detail || error.message
      });
    } finally {
      setExportLoading(false);
    }
  };

  // Get validation severity icon
  const getValidationIcon = (severity) => {
    switch (severity) {
      case 'error':
        return <ErrorIcon color="error" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'info':
      default:
        return <ValidIcon color="info" />;
    }
  };

  return (
    <Box>
      {/* Header */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container alignItems="center" spacing={2}>
          <Grid item xs>
            <Typography variant="h6">
              ADMX Template Manager
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Export CIS policies as Windows Group Policy ADMX/ADML templates
            </Typography>
          </Grid>
          <Grid item>
            <Button
              variant="contained"
              color="primary"
              startIcon={<DownloadIcon />}
              onClick={handleBulkExport}
              disabled={templates.length === 0 || exportLoading}
            >
              Bulk Export All ({templates.length})
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Export Configuration */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          Export Configuration
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Namespace"
              value={namespace}
              onChange={(e) => setNamespace(e.target.value)}
              helperText="ADMX namespace (e.g., CISBenchmark)"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Policy Prefix"
              value={prefix}
              onChange={(e) => setPrefix(e.target.value)}
              helperText="Policy name prefix (e.g., CIS)"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <TextField
              fullWidth
              label="Output Directory"
              value={outputDir}
              onChange={(e) => setOutputDir(e.target.value)}
              helperText="Directory for generated files"
              InputProps={{
                startAdornment: <FolderIcon sx={{ mr: 1, color: 'text.secondary' }} />
              }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={validate}
                  onChange={(e) => setValidate(e.target.checked)}
                />
              }
              label="Validate"
            />
          </Grid>
        </Grid>
      </Paper>

      {/* Template List */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          Available Templates ({templates.length})
        </Typography>
        
        {templates.length === 0 && (
          <Alert severity="info">
            <AlertTitle>No Templates Available</AlertTitle>
            Create some templates first before exporting to ADMX format.
          </Alert>
        )}
        
        <List>
          {templates.map((template) => (
            <React.Fragment key={template.template_id}>
              <ListItem>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="subtitle2">
                        {template.name}
                      </Typography>
                      {template.cis_level && (
                        <Chip label={template.cis_level} size="small" color="primary" />
                      )}
                      <Chip 
                        label={`${template.policy_count || 0} policies`} 
                        size="small" 
                        variant="outlined"
                      />
                    </Box>
                  }
                  secondary={template.description}
                />
                <ListItemSecondaryAction>
                  <Tooltip title="Preview ADMX">
                    <IconButton
                      edge="end"
                      onClick={() => handlePreviewClick(template)}
                      sx={{ mr: 1 }}
                    >
                      <PreviewIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Export to Files">
                    <IconButton
                      edge="end"
                      color="primary"
                      onClick={() => handleExportClick(template)}
                    >
                      <DownloadIcon />
                    </IconButton>
                  </Tooltip>
                </ListItemSecondaryAction>
              </ListItem>
              <Divider />
            </React.Fragment>
          ))}
        </List>
      </Paper>

      {/* Export Dialog */}
      <Dialog
        open={exportDialog}
        onClose={() => setExportDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Export Template to ADMX
        </DialogTitle>
        <DialogContent>
          {selectedTemplate && (
            <Box>
              <Alert severity="info" sx={{ mb: 2 }}>
                <AlertTitle>Exporting: {selectedTemplate.name}</AlertTitle>
                This will generate Windows Group Policy ADMX and ADML files that can be deployed to your domain or local policy store.
              </Alert>
              
              {exportLoading && <LinearProgress sx={{ mb: 2 }} />}
              
              {exportResult && exportResult.success && (
                <Alert severity="success" sx={{ mb: 2 }}>
                  <AlertTitle>Export Successful!</AlertTitle>
                  {exportResult.bulk ? (
                    <>
                      <Typography variant="body2">
                        Exported {exportResult.data.summary.successful} of {exportResult.data.summary.total} templates
                      </Typography>
                      {exportResult.data.summary.failed > 0 && (
                        <Typography variant="body2" color="error">
                          Failed: {exportResult.data.summary.failed}
                        </Typography>
                      )}
                    </>
                  ) : (
                    <>
                      <Typography variant="body2">
                        ADMX: <code>{exportResult.data.admx_file}</code>
                      </Typography>
                      <Typography variant="body2">
                        ADML: <code>{exportResult.data.adml_file}</code>
                      </Typography>
                      {exportResult.data.validation && (
                        <Box mt={1}>
                          <Chip 
                            icon={exportResult.data.validation.is_valid ? <ValidIcon /> : <ErrorIcon />}
                            label={exportResult.data.validation.is_valid ? 'Valid' : 'Has Issues'}
                            color={exportResult.data.validation.is_valid ? 'success' : 'error'}
                            size="small"
                          />
                          <Chip 
                            label={`${exportResult.data.validation.errors_count} errors`}
                            size="small"
                            sx={{ ml: 1 }}
                          />
                          <Chip 
                            label={`${exportResult.data.validation.warnings_count} warnings`}
                            size="small"
                            sx={{ ml: 1 }}
                          />
                        </Box>
                      )}
                    </>
                  )}
                </Alert>
              )}
              
              {exportResult && !exportResult.success && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  <AlertTitle>Export Failed</AlertTitle>
                  {exportResult.error}
                </Alert>
              )}
              
              <Typography variant="body2" color="textSecondary" paragraph>
                Files will be saved to: <code>{outputDir}/</code>
              </Typography>
              
              <Typography variant="body2" color="textSecondary">
                <strong>Deployment Instructions:</strong>
              </Typography>
              <Typography variant="body2" color="textSecondary" component="div">
                <ol>
                  <li>Copy ADMX file to <code>C:\Windows\PolicyDefinitions\</code></li>
                  <li>Copy ADML file to <code>C:\Windows\PolicyDefinitions\en-US\</code></li>
                  <li>Open Group Policy Editor (<code>gpedit.msc</code>)</li>
                  <li>Navigate to Administrative Templates</li>
                  <li>Find "CIS Benchmark Policies" category</li>
                </ol>
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExportDialog(false)}>
            Close
          </Button>
          {!exportResult && (
            <Button
              variant="contained"
              color="primary"
              startIcon={<SaveIcon />}
              onClick={handleExportToFiles}
              disabled={exportLoading}
            >
              Export to Files
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog
        open={previewDialog}
        onClose={() => setPreviewDialog(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          ADMX Template Preview
        </DialogTitle>
        <DialogContent>
          {exportLoading && <LinearProgress />}
          
          {previewData && (
            <Box>
              {/* Validation Results */}
              {previewData.validation && (
                <Alert 
                  severity={previewData.validation.is_valid ? 'success' : 'warning'}
                  sx={{ mb: 2 }}
                >
                  <AlertTitle>
                    Validation: {previewData.validation.is_valid ? 'Passed' : 'Has Issues'}
                  </AlertTitle>
                  <Box display="flex" gap={2}>
                    <Chip 
                      icon={<ErrorIcon />}
                      label={`${previewData.validation.errors_count} Errors`}
                      size="small"
                      color={previewData.validation.errors_count > 0 ? 'error' : 'default'}
                    />
                    <Chip 
                      icon={<WarningIcon />}
                      label={`${previewData.validation.warnings_count} Warnings`}
                      size="small"
                      color={previewData.validation.warnings_count > 0 ? 'warning' : 'default'}
                    />
                    <Chip 
                      label={`${previewData.validation.info_count} Info`}
                      size="small"
                    />
                  </Box>
                  
                  {previewData.validation.issues && previewData.validation.issues.length > 0 && (
                    <Box mt={2}>
                      <Typography variant="subtitle2" gutterBottom>
                        Issues:
                      </Typography>
                      <List dense>
                        {previewData.validation.issues.slice(0, 10).map((issue, idx) => (
                          <ListItem key={idx}>
                            <ListItemIcon>
                              {getValidationIcon(issue.severity)}
                            </ListItemIcon>
                            <ListItemText
                              primary={issue.message}
                              secondary={issue.location || issue.recommendation}
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  )}
                </Alert>
              )}
              
              {/* ADMX Content */}
              <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="subtitle1">
                    <FileIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                    ADMX Content ({previewData.admx_content?.length || 0} characters)
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box
                    component="pre"
                    sx={{
                      p: 2,
                      bgcolor: 'grey.100',
                      borderRadius: 1,
                      overflow: 'auto',
                      maxHeight: 400,
                      fontSize: '0.875rem',
                      fontFamily: 'monospace'
                    }}
                  >
                    {previewData.admx_content}
                  </Box>
                </AccordionDetails>
              </Accordion>
              
              {/* ADML Content */}
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="subtitle1">
                    <FileIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                    ADML Content ({previewData.adml_content?.length || 0} characters)
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box
                    component="pre"
                    sx={{
                      p: 2,
                      bgcolor: 'grey.100',
                      borderRadius: 1,
                      overflow: 'auto',
                      maxHeight: 400,
                      fontSize: '0.875rem',
                      fontFamily: 'monospace'
                    }}
                  >
                    {previewData.adml_content}
                  </Box>
                </AccordionDetails>
              </Accordion>
            </Box>
          )}
          
          {!exportLoading && !previewData && (
            <Alert severity="error">
              Failed to load preview data
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ADMXTemplateManager;
