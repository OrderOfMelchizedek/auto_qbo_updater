import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  Skeleton,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
} from '@mui/material'
import {
  Receipt,
  Email,
  Warning,
  CheckCircle,
  Schedule,
  AttachMoney,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'
import { api } from '@/services/api'

interface DashboardStats {
  total_donations: number
  total_amount: number
  pending_review: number
  synced_to_quickbooks: number
  letters_generated: number
  recent_uploads: number
}

interface RecentActivity {
  id: string
  type: 'upload' | 'sync' | 'letter' | 'error'
  description: string
  timestamp: string
  status: 'success' | 'pending' | 'error'
}

export const DashboardPage = () => {
  const navigate = useNavigate()

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const response = await api.get<DashboardStats>('/donations/stats')
      return response.data
    },
  })

  const { data: activities, isLoading: activitiesLoading } = useQuery({
    queryKey: ['recent-activities'],
    queryFn: async () => {
      const response = await api.get<RecentActivity[]>('/donations/recent-activity')
      return response.data
    },
  })

  const mockChartData = [
    { name: 'Jan', donations: 45 },
    { name: 'Feb', donations: 52 },
    { name: 'Mar', donations: 48 },
    { name: 'Apr', donations: 61 },
    { name: 'May', donations: 55 },
    { name: 'Jun', donations: 67 },
  ]

  const statCards = [
    {
      title: 'Total Donations',
      value: stats?.total_donations || 0,
      icon: <AttachMoney />,
      color: '#1976d2',
      action: () => navigate('/donations'),
    },
    {
      title: 'Pending Review',
      value: stats?.pending_review || 0,
      icon: <Schedule />,
      color: '#ff9800',
      action: () => navigate('/donations?status=pending'),
    },
    {
      title: 'Synced to QB',
      value: stats?.synced_to_quickbooks || 0,
      icon: <CheckCircle />,
      color: '#4caf50',
      action: () => navigate('/quickbooks'),
    },
    {
      title: 'Letters Generated',
      value: stats?.letters_generated || 0,
      icon: <Email />,
      color: '#9c27b0',
      action: () => navigate('/letters'),
    },
  ]

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'upload':
        return <Receipt color="primary" />
      case 'sync':
        return <CheckCircle color="success" />
      case 'letter':
        return <Email color="secondary" />
      case 'error':
        return <Warning color="error" />
      default:
        return <Receipt />
    }
  }

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'success':
        return <Chip label="Success" color="success" size="small" />
      case 'pending':
        return <Chip label="Pending" color="warning" size="small" />
      case 'error':
        return <Chip label="Error" color="error" size="small" />
      default:
        return null
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Stat Cards */}
        {statCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            {statsLoading ? (
              <Skeleton variant="rectangular" height={140} />
            ) : (
              <Card
                sx={{
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                  }
                }}
                onClick={card.action}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Box sx={{ color: card.color, mr: 2 }}>{card.icon}</Box>
                    <Typography color="textSecondary" gutterBottom>
                      {card.title}
                    </Typography>
                  </Box>
                  <Typography variant="h3">{card.value.toLocaleString()}</Typography>
                </CardContent>
              </Card>
            )}
          </Grid>
        ))}

        {/* Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Donation Trends
            </Typography>
            <ResponsiveContainer width="100%" height="90%">
              <LineChart data={mockChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="donations"
                  stroke="#1976d2"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Recent Activity
            </Typography>
            {activitiesLoading ? (
              <>
                <Skeleton height={60} />
                <Skeleton height={60} />
                <Skeleton height={60} />
              </>
            ) : (
              <List sx={{ overflow: 'auto', maxHeight: 320 }}>
                {activities?.map((activity) => (
                  <ListItem key={activity.id}>
                    <ListItemIcon>{getActivityIcon(activity.type)}</ListItemIcon>
                    <ListItemText
                      primary={activity.description}
                      secondary={format(new Date(activity.timestamp), 'MMM d, h:mm a')}
                    />
                    {getStatusChip(activity.status)}
                  </ListItem>
                )) || (
                  <Typography color="textSecondary" align="center">
                    No recent activity
                  </Typography>
                )}
              </List>
            )}
          </Paper>
        </Grid>

        {/* Quick Actions */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Button
                variant="contained"
                startIcon={<Receipt />}
                onClick={() => navigate('/upload')}
              >
                Upload Documents
              </Button>
              <Button
                variant="outlined"
                startIcon={<AttachMoney />}
                onClick={() => navigate('/donations')}
              >
                Review Donations
              </Button>
              <Button
                variant="outlined"
                startIcon={<CheckCircle />}
                onClick={() => navigate('/quickbooks')}
              >
                Sync to QuickBooks
              </Button>
              <Button
                variant="outlined"
                startIcon={<Email />}
                onClick={() => navigate('/letters')}
              >
                Generate Letters
              </Button>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}
