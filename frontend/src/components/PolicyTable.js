import React, { useState } from 'react';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper, 
  TablePagination,
  Collapse,
  Box,
  IconButton,
  Typography,
  Chip
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';

// Row component for expandable table rows
const PolicyRow = ({ policy }) => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <TableRow 
        sx={{ '& > *': { borderBottom: 'unset' } }}
        hover
      >
        <TableCell>
          <IconButton
            size="small"
            onClick={() => setOpen(!open)}
          >
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell component="th" scope="row">
          {policy.policy_name}
        </TableCell>
        <TableCell>{policy.category}</TableCell>
        <TableCell>{policy.subcategory || '-'}</TableCell>
        <TableCell>
          {policy.cis_level ? (
            <Chip 
              label={`Level ${policy.cis_level}`} 
              size="small" 
              color={policy.cis_level === 1 ? "primary" : "secondary"} 
              variant="outlined"
            />
          ) : (
            '-'
          )}
        </TableCell>
        <TableCell>{policy.required_value || '-'}</TableCell>
      </TableRow>
      
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1, pb: 3 }}>
              <Typography variant="h6" gutterBottom component="div">
                Details
              </Typography>
              
              {policy.description && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2">Description</Typography>
                  <Typography variant="body2">{policy.description}</Typography>
                </Box>
              )}
              
              {policy.rationale && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2">Rationale</Typography>
                  <Typography variant="body2">{policy.rationale}</Typography>
                </Box>
              )}
              
              {policy.impact && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2">Impact</Typography>
                  <Typography variant="body2">{policy.impact}</Typography>
                </Box>
              )}
              
              {policy.registry_path && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2">Registry Path</Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {policy.registry_path}
                  </Typography>
                </Box>
              )}
              
              {policy.gpo_path && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2">GPO Path</Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {policy.gpo_path}
                  </Typography>
                </Box>
              )}
              
              {policy.references && policy.references.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2">References</Typography>
                  <ul style={{ margin: '4px 0' }}>
                    {policy.references.map((ref, index) => (
                      <li key={index}>
                        <Typography variant="body2">{ref}</Typography>
                      </li>
                    ))}
                  </ul>
                </Box>
              )}
              
              <Box sx={{ mb: 1 }}>
                <Typography variant="subtitle2">Additional Information</Typography>
                <Typography variant="body2">
                  Section: {policy.section_number || 'N/A'} | 
                  Page: {policy.page_number || 'N/A'}
                </Typography>
              </Box>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
};

const PolicyTable = ({ policies }) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <Paper sx={{ width: '100%', overflow: 'hidden' }}>
      <TableContainer sx={{ maxHeight: 650 }}>
        <Table stickyHeader aria-label="policy table">
          <TableHead>
            <TableRow>
              <TableCell style={{ width: '50px' }} />
              <TableCell>Policy Name</TableCell>
              <TableCell>Category</TableCell>
              <TableCell>Subcategory</TableCell>
              <TableCell>CIS Level</TableCell>
              <TableCell>Required Value</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {policies
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((policy) => (
                <PolicyRow key={policy.id} policy={policy} />
              ))}
            
            {policies.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  No policies found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      
      <TablePagination
        rowsPerPageOptions={[10, 25, 50, 100]}
        component="div"
        count={policies.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />
    </Paper>
  );
};

export default PolicyTable;