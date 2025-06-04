import { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  Sync,
  CheckCircle,
  Error,
  Warning,
  CloudUpload,
  Receipt,
  Person,
  Refresh,
  Info,
} from '@mui/icons-material'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { useNotification } from '@/contexts/NotificationContext'
import { authService } from '@/services/auth'
import { api } from '@/services/api'

interface QBConnectionStatus {
  connected: boolean
  company_name?: string
  last_sync?: string
}

interface SyncableTransaction {
  donation_id: string
  donor_name: string
  amount: number
  check_number: string
  payment_date: string
  customer_exists: boolean
  ready_to_sync: boolean
  issues: string[]
}

interface SyncResult {
  success: boolean
  synced_count: number
  failed_count: number
  errors: Array<{
    donation_id: string
    error: string
  }>
}

export const QuickBooksPage = () => {
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [selectedTransactions, setSelectedTransactions] = useState<string[]>([])
  const [syncProgress, setSyncProgress] = useState(0)
  const [isSyncing, setIsSyncing] = useState(false)

  const queryClient = useQueryClient()
  const { showSuccess, showError, showWarning } = useNotification()

  // Check QB connection
  const { data: connectionStatus, isLoading: connectionLoading } = useQuery({
    queryKey: ['qb-connection'],
    queryFn: async () => {
      const response = await authService.checkQuickBooksConnection()
      return response
    },
  })

  // Get syncable transactions
  const { data: syncableTransactions = [], refetch: refetchTransactions } = useQuery({
    queryKey: ['syncable-transactions'],
    queryFn: async () => {
      const response = await api.get<SyncableTransaction[]>('/quickbooks/syncable')
      return response.data
    },
    enabled: connectionStatus?.connected,
  })

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: async (transactionIds: string[]) => {
      setIsSyncing(true)
      setSyncProgress(0)

      const response = await api.post<SyncResult>('/quickbooks/sync', {
        donation_ids: transactionIds,
      })

      return response.data
    },
    onSuccess: (data) => {
      if (data.synced_count > 0) {
        showSuccess(`Successfully synced ${data.synced_count} transactions`)
      }
      if (data.failed_count > 0) {
        showWarning(`${data.failed_count} transactions failed to sync`)
      }
      queryClient.invalidateQueries({ queryKey: ['syncable-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['donations'] })
      setSyncDialogOpen(false)
      setSelectedTransactions([])
    },
    onError: () => {
      showError('Sync failed. Please try again.')
    },
    onSettled: () => {
      setIsSyncing(false)
      setSyncProgress(0)
    },
  })

  // Connect to QuickBooks
  const handleConnect = async () => {
    try {
      const { auth_url } = await authService.initiateQuickBooksAuth()
      window.location.href = auth_url
    } catch (error) {
      showError('Failed to initiate QuickBooks connection')
    }
  }

  // Disconnect from QuickBooks
  const handleDisconnect = async () => {
    try {
      await authService.disconnectQuickBooks()
      queryClient.invalidateQueries({ queryKey: ['qb-connection'] })
      showSuccess('Disconnected from QuickBooks')
    } catch (error) {
      showError('Failed to disconnect from QuickBooks')
    }
  }

  const readyTransactions = syncableTransactions.filter(t => t.ready_to_sync)
  const issueTransactions = syncableTransactions.filter(t => !t.ready_to_sync)

  if (connectionLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!connectionStatus?.connected) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          QuickBooks Integration
        </Typography>
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Receipt sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            Connect to QuickBooks
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Connect your QuickBooks account to sync donation data
          </Typography>
          <Button
            variant="contained"
            size="large"
            startIcon={<CloudUpload />}
            onClick={handleConnect}
          >
            Connect QuickBooks
          </Button>
        </Paper>
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">QuickBooks Sync</Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={() => refetchTransactions()}
        >
          Refresh
        </Button>
      </Box>

      {/* Connection Status */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <CheckCircle color="success" />
            <Box>
              <Typography variant="body1">
                Connected to <strong>{connectionStatus.company_name}</strong>
              </Typography>
              {connectionStatus.last_sync && (
                <Typography variant="caption" color="text.secondary">
                  Last sync: {format(new Date(connectionStatus.last_sync), 'MMM d, yyyy h:mm a')}
                </Typography>
              )}
            </Box>
          </Box>
          <Button
            size="small"
            color="error"
            onClick={handleDisconnect}
          >
            Disconnect
          </Button>
        </Box>
      </Paper>

      {/* Ready to Sync */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6">
            Ready to Sync ({readyTransactions.length})
          </Typography>
          {readyTransactions.length > 0 && (
            <Button
              variant="contained"
              startIcon={<Sync />}
              onClick={() => {
                setSelectedTransactions(readyTransactions.map(t => t.donation_id))
                setSyncDialogOpen(true)
              }}
            >
              Sync All
            </Button>
          )}
        </Box>

        {readyTransactions.length === 0 ? (
          <Alert severity="info">No transactions ready to sync</Alert>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Donor</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell>Check #</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell>Customer</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {readyTransactions.map((transaction) => (
                  <TableRow key={transaction.donation_id}>
                    <TableCell>{transaction.donor_name}</TableCell>
                    <TableCell align="right">
                      ${transaction.amount.toLocaleString()}
                    </TableCell>
                    <TableCell>{transaction.check_number}</TableCell>
                    <TableCell>
                      {format(new Date(transaction.payment_date), 'MMM d, yyyy')}
                    </TableCell>
                    <TableCell>
                      {transaction.customer_exists ? (
                        <Chip
                          icon={<CheckCircle />}
                          label="Exists"
                          color="success"
                          size="small"
                        />
                      ) : (
                        <Chip
                          icon={<Person />}
                          label="New"
                          color="info"
                          size="small"
                        />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Issues to Resolve */}
      {issueTransactions.length > 0 && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Issues to Resolve ({issueTransactions.length})
          </Typography>
          <List>
            {issueTransactions.map((transaction) => (
              <ListItem key={transaction.donation_id}>
                <ListItemIcon>
                  <Warning color="warning" />
                </ListItemIcon>
                <ListItemText
                  primary={`${transaction.donor_name} - $${transaction.amount}`}
                  secondary={transaction.issues.join(', ')}
                />
                <ListItemSecondaryAction>
                  <Tooltip title="Review donation">
                    <IconButton
                      edge="end"
                      onClick={() => {
                        window.location.href = `/donations?id=${transaction.donation_id}`
                      }}
                    >
                      <Info />
                    </IconButton>
                  </Tooltip>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      {/* Sync Dialog */}
      <Dialog open={syncDialogOpen} onClose={() => !isSyncing && setSyncDialogOpen(false)}>
        <DialogTitle>Sync to QuickBooks</DialogTitle>
        <DialogContent sx={{ minWidth: 400 }}>
          {isSyncing ? (
            <Box sx={{ py: 3 }}>
              <Typography variant="body1" gutterBottom>
                Syncing {selectedTransactions.length} transactions...
              </Typography>
              <LinearProgress
                variant="determinate"
                value={syncProgress}
                sx={{ mt: 2 }}
              />
            </Box>
          ) : (
            <Box>
              <Typography variant="body1" gutterBottom>
                Are you sure you want to sync {selectedTransactions.length} transactions to QuickBooks?
              </Typography>
              <Alert severity="info" sx={{ mt: 2 }}>
                This will create sales receipts in QuickBooks. New customers will be created as needed.
              </Alert>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSyncDialogOpen(false)} disabled={isSyncing}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={() => syncMutation.mutate(selectedTransactions)}
            disabled={isSyncing}
            startIcon={isSyncing ? <CircularProgress size={20} /> : <Sync />}
          >
            {isSyncing ? 'Syncing...' : 'Sync'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
