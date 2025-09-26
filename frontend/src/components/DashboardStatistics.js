/**
 * Dashboard Statistics Component
 * Displays comprehensive statistics and compliance metrics
 */

import React from 'react';
import {
  Paper,
  Grid,
  Typography,
  Box,
  LinearProgress,
  Chip,
  Card,
  CardContent,
  CircularProgress
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Security as SecurityIcon,
  Assignment as AssignmentIcon,
  Group as GroupIcon,
  Label as LabelIcon,
  History as HistoryIcon
} from '@mui/icons-material';

const StatCard = ({ title, value, subtitle, icon: Icon, color, progress }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Icon sx={{ color, mr: 1, fontSize: 30 }} />
        <Typography variant="h6" component="div">
          {title}
        </Typography>
      </Box>
      <Typography variant="h4" component="div" sx={{ mb: 1, color }}>
        {value}
      </Typography>
      {subtitle && (
        <Typography variant="body2" color="text.secondary">
          {subtitle}
        </Typography>
      )}
      {progress !== undefined && (
        <Box sx={{ mt: 2 }}>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{ height: 8, borderRadius: 4 }}
            color={color === '#4caf50' ? 'success' : color === '#f44336' ? 'error' : 'primary'}
          />
          <Typography variant="caption" sx={{ mt: 0.5, display: 'block' }}>
            {progress.toFixed(1)}%
          </Typography>
        </Box>
      )}
    </CardContent>
  </Card>
);

const ComplianceChart = ({ stats }) => {
  if (!stats) return null;

  const total = stats.total_policies;
  const enabled = stats.enabled_policies;
  const disabled = stats.disabled_policies;
  const notConfigured = stats.not_configured_policies;
  
  const enabledPercent = total > 0 ? (enabled / total) * 100 : 0;
  const disabledPercent = total > 0 ? (disabled / total) * 100 : 0;
  const notConfiguredPercent = total > 0 ? (notConfigured / total) * 100 : 0;

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Policy Status Distribution
        </Typography>
        <Box sx={{ mt: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2">Enabled</Typography>
            <Typography variant="body2">{enabled} ({enabledPercent.toFixed(1)}%)</Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={enabledPercent}
            sx={{ height: 10, borderRadius: 5, mb: 2 }}
            color="success"
          />
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2">Disabled</Typography>
            <Typography variant="body2">{disabled} ({disabledPercent.toFixed(1)}%)</Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={disabledPercent}
            sx={{ height: 10, borderRadius: 5, mb: 2 }}
            color="error"
          />
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2">Not Configured</Typography>
            <Typography variant="body2">{notConfigured} ({notConfiguredPercent.toFixed(1)}%)</Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={notConfiguredPercent}
            sx={{ height: 10, borderRadius: 5 }}
            color="warning"
          />
        </Box>
      </CardContent>
    </Card>
  );
};

const PriorityBreakdown = ({ stats }) => {
  if (!stats) return null;

  const priorities = [
    { level: 'Critical', count: stats.critical_policies, color: '#d32f2f' },
    { level: 'High', count: stats.high_priority_policies, color: '#f57c00' },
    { level: 'Medium', count: stats.medium_priority_policies, color: '#1976d2' },
    { level: 'Low', count: stats.low_priority_policies, color: '#388e3c' }
  ];

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Priority Distribution
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 2 }}>
          {priorities.map((priority) => (
            <Chip
              key={priority.level}
              label={`${priority.level}: ${priority.count}`}
              sx={{
                backgroundColor: priority.color,
                color: 'white',
                '& .MuiChip-label': { fontWeight: 'bold' }
              }}
            />
          ))}
        </Box>
        <Box sx={{ mt: 2 }}>
          {priorities.map((priority) => {
            const percent = stats.total_policies > 0 ? (priority.count / stats.total_policies) * 100 : 0;
            return (
              <Box key={priority.level} sx={{ mb: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                  <Typography variant="body2">{priority.level}</Typography>
                  <Typography variant="body2">{percent.toFixed(1)}%</Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={percent}
                  sx={{ height: 6, borderRadius: 3, backgroundColor: 'rgba(0,0,0,0.1)' }}
                  style={{ color: priority.color }}
                />
              </Box>
            );
          })}
        </Box>
      </CardContent>
    </Card>
  );
};

const DashboardStatistics = ({ statistics, isLoading = false }) => {
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!statistics) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No statistics available
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Key Metrics */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Policies"
            value={statistics.total_policies}
            subtitle="Imported policies"
            icon={AssignmentIcon}
            color="#1976d2"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Compliance Rate"
            value={`${statistics.compliance_percentage}%`}
            subtitle="Policies configured"
            icon={SecurityIcon}
            color="#4caf50"
            progress={statistics.compliance_percentage}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Critical Compliance"
            value={`${statistics.critical_compliance}%`}
            subtitle="Critical policies configured"
            icon={TrendingUpIcon}
            color="#f44336"
            progress={statistics.critical_compliance}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Recent Changes"
            value={statistics.recent_changes}
            subtitle="Last 24 hours"
            icon={HistoryIcon}
            color="#ff9800"
          />
        </Grid>
      </Grid>

      {/* Secondary Metrics */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={2}>
          <StatCard
            title="Groups"
            value={statistics.total_groups}
            icon={GroupIcon}
            color="#9c27b0"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <StatCard
            title="Ungrouped"
            value={statistics.ungrouped_policies}
            icon={GroupIcon}
            color="#ff5722"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <StatCard
            title="Tags"
            value={statistics.total_tags}
            icon={LabelIcon}
            color="#607d8b"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <StatCard
            title="Untagged"
            value={statistics.untagged_policies}
            icon={LabelIcon}
            color="#795548"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <StatCard
            title="Enabled"
            value={statistics.enabled_policies}
            icon={SecurityIcon}
            color="#4caf50"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <StatCard
            title="Disabled"
            value={statistics.disabled_policies}
            icon={SecurityIcon}
            color="#f44336"
          />
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <ComplianceChart stats={statistics} />
        </Grid>
        <Grid item xs={12} md={6}>
          <PriorityBreakdown stats={statistics} />
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardStatistics;