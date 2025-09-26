import React, { useState } from 'react';
import { Box, Button, Typography, Paper, Alert } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

const FileUploader = ({ onFileChange }) => {
  const [dragActive, setDragActive] = useState(false);
  const [fileError, setFileError] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  // Handle drag events
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  // Handle drop event
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  // Handle file selection
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  // Process the selected file
  const handleFile = (file) => {
    setFileError('');

    // Check if file is a PDF
    if (file.type !== 'application/pdf') {
      setFileError('Please upload a PDF file');
      return;
    }

    // Check file size (limit to 50MB)
    if (file.size > 50 * 1024 * 1024) {
      setFileError('File size should not exceed 50MB');
      return;
    }

    setSelectedFile(file);
    onFileChange(file);
  };

  return (
    <Box>
      <input
        type="file"
        id="file-upload"
        style={{ display: 'none' }}
        accept=".pdf"
        onChange={handleFileChange}
      />

      <Box
        component={Paper}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        sx={{
          border: '2px dashed',
          borderColor: dragActive ? 'primary.main' : 'grey.400',
          borderRadius: 2,
          padding: 4,
          textAlign: 'center',
          cursor: 'pointer',
          backgroundColor: dragActive ? 'action.hover' : 'background.paper',
          transition: 'all 0.3s ease',
          '&:hover': {
            borderColor: 'primary.main',
            backgroundColor: 'action.hover'
          }
        }}
        onClick={() => document.getElementById('file-upload').click()}
      >
        <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          Drag and drop a CIS Benchmark PDF here
        </Typography>
        <Typography variant="body2" color="textSecondary">
          or click to select a file
        </Typography>

        {selectedFile && (
          <Box sx={{ mt: 2, p: 1, backgroundColor: 'action.selected', borderRadius: 1 }}>
            <Typography variant="body2">
              Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
            </Typography>
          </Box>
        )}
      </Box>

      {fileError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {fileError}
        </Alert>
      )}

      <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
        Maximum file size: 50MB. Only PDF files are supported.
      </Typography>
    </Box>
  );
};

export default FileUploader;