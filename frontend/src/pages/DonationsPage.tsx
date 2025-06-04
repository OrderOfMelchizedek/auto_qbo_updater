import { useState, useMemo } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  TextField,
  InputAdornment,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Checkbox,
  FormControlLabel,
  Alert,
  Badge,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
  Menu,
  MenuItem,
} from '@mui/material'
import {
  Search,
  FilterList,
  Merge,
  Edit,
  Delete,
  CheckCircle,
  Warning,
  ViewList,
  ViewModule,
  MoreVert,
  Download,
} from '@mui/icons-material'
import { DataGrid, GridColDef, GridRowSelectionModel } from '@mui/x-data-grid'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { useNotification } from '@/contexts/NotificationContext'
import { api } from '@/services/api'

interface Donation {
  id: string
  donor_name: string
  amount: number
  check_number: string
  payment_date: string
  document_id: string
  status: 'pending' | 'reviewed' | 'synced' | 'duplicate'
  duplicate_of?: string
  email?: string
  address?: string
  notes?: string
}

interface DeduplicationGroup {
  master_id: string
  duplicate_ids: string[]
  donations: Donation[]
}

export const DonationsPage = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedRows, setSelectedRows] = useState<GridRowSelectionModel>([])
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list')
  const [filterMenuAnchor, setFilterMenuAnchor] = useState<null | HTMLElement>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [deduplicationDialogOpen, setDeduplicationDialogOpen] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState<DeduplicationGroup | null>(null)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingDonation, setEditingDonation] = useState<Donation | null>(null)

  const queryClient = useQueryClient()
  const { showSuccess, showError } = useNotification()

  // Fetch donations
  const { data: donations = [], isLoading } = useQuery({
    queryKey: ['donations', statusFilter],
    queryFn: async () => {
      const params = statusFilter !== 'all' ? { status: statusFilter } : {}
      const response = await api.get<Donation[]>('/donations', params)
      return response.data
    },
  })

  // Fetch duplicate groups
  const { data: duplicateGroups = [] } = useQuery({
    queryKey: ['duplicate-groups'],
    queryFn: async () => {
      const response = await api.get<DeduplicationGroup[]>('/donations/duplicates')
      return response.data
    },
  })

  // Update donation mutation
  const updateMutation = useMutation({
    mutationFn: async (donation: Partial<Donation> & { id: string }) => {
      const response = await api.put(`/donations/${donation.id}`, donation)
      return response.data
    },
    onSuccess: () => {
      showSuccess('Donation updated successfully')
      queryClient.invalidateQueries({ queryKey: ['donations'] })
      setEditDialogOpen(false)
    },
    onError: () => {
      showError('Failed to update donation')
    },
  })

  // Merge duplicates mutation
  const mergeMutation = useMutation({
    mutationFn: async (data: { master_id: string; duplicate_ids: string[] }) => {
      const response = await api.post('/donations/merge', data)
      return response.data
    },
    onSuccess: () => {
      showSuccess('Donations merged successfully')
      queryClient.invalidateQueries({ queryKey: ['donations'] })
      queryClient.invalidateQueries({ queryKey: ['duplicate-groups'] })
      setDeduplicationDialogOpen(false)
    },
    onError: () => {
      showError('Failed to merge donations')
    },
  })

  // Mark as reviewed mutation
  const markReviewedMutation = useMutation({
    mutationFn: async (ids: string[]) => {
      const response = await api.post('/donations/mark-reviewed', { donation_ids: ids })
      return response.data
    },
    onSuccess: () => {
      showSuccess('Donations marked as reviewed')
      queryClient.invalidateQueries({ queryKey: ['donations'] })
      setSelectedRows([])
    },
    onError: () => {
      showError('Failed to mark donations as reviewed')
    },
  })

  // Export donations
  const handleExport = async () => {
    try {
      await api.downloadFile('/donations/export', 'donations_export.csv')
      showSuccess('Export downloaded successfully')
    } catch (error) {
      showError('Failed to export donations')
    }
  }

  // Filter donations based on search
  const filteredDonations = useMemo(() => {
    if (!searchTerm) return donations

    const term = searchTerm.toLowerCase()
    return donations.filter(
      (d) =>
        d.donor_name.toLowerCase().includes(term) ||
        d.check_number.toLowerCase().includes(term) ||
        d.email?.toLowerCase().includes(term) ||
        d.notes?.toLowerCase().includes(term)
    )
  }, [donations, searchTerm])

  const columns: GridColDef[] = [
    {
      field: 'donor_name',
      headerName: 'Donor Name',
      flex: 1,
      minWidth: 200,
      renderCell: (params) => (
        <Box>
          <Typography variant="body2">{params.value}</Typography>
          {params.row.email && (
            <Typography variant="caption" color="textSecondary">
              {params.row.email}
            </Typography>
          )}
        </Box>
      ),
    },
    {
      field: 'amount',
      headerName: 'Amount',
      width: 120,
      type: 'number',
      renderCell: (params) => `$${params.value.toLocaleString()}`,
    },
    {
      field: 'check_number',
      headerName: 'Check #',
      width: 100,
    },
    {
      field: 'payment_date',
      headerName: 'Date',
      width: 120,
      renderCell: (params) => format(new Date(params.value), 'MMM d, yyyy'),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => {
        const statusConfig = {
          pending: { label: 'Pending', color: 'warning' as const },
          reviewed: { label: 'Reviewed', color: 'info' as const },
          synced: { label: 'Synced', color: 'success' as const },
          duplicate: { label: 'Duplicate', color: 'error' as const },
        }
        const config = statusConfig[params.value as keyof typeof statusConfig]
        return <Chip label={config.label} color={config.color} size="small" />
      },
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 120,
      sortable: false,
      renderCell: (params) => (
        <Box>
          <IconButton
            size="small"
            onClick={() => {
              setEditingDonation(params.row)
              setEditDialogOpen(true)
            }}
          >
            <Edit fontSize="small" />
          </IconButton>
          {params.row.status === 'duplicate' && (
            <Tooltip title="View duplicates">
              <IconButton
                size="small"
                onClick={() => {
                  const group = duplicateGroups.find(
                    (g) => g.duplicate_ids.includes(params.row.id)
                  )
                  if (group) {
                    setSelectedGroup(group)
                    setDeduplicationDialogOpen(true)
                  }
                }}
              >
                <Merge fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      ),
    },
  ]

  const duplicateCount = duplicateGroups.reduce(
    (acc, group) => acc + group.duplicate_ids.length,
    0
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Donations</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={handleExport}
          >
            Export
          </Button>
          {duplicateCount > 0 && (
            <Badge badgeContent={duplicateCount} color="error">
              <Button
                variant="contained"
                color="warning"
                startIcon={<Merge />}
                onClick={() => setDeduplicationDialogOpen(true)}
              >
                Review Duplicates
              </Button>
            </Badge>
          )}
        </Box>
      </Box>

      {/* Search and Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField
            placeholder="Search donations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
            sx={{ flexGrow: 1 }}
          />
          <IconButton onClick={(e) => setFilterMenuAnchor(e.currentTarget)}>
            <FilterList />
          </IconButton>
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={(_, newMode) => newMode && setViewMode(newMode)}
            size="small"
          >
            <ToggleButton value="list">
              <ViewList />
            </ToggleButton>
            <ToggleButton value="grid">
              <ViewModule />
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Paper>

      {/* Filter Menu */}
      <Menu
        anchorEl={filterMenuAnchor}
        open={Boolean(filterMenuAnchor)}
        onClose={() => setFilterMenuAnchor(null)}
      >
        <MenuItem
          onClick={() => {
            setStatusFilter('all')
            setFilterMenuAnchor(null)
          }}
          selected={statusFilter === 'all'}
        >
          All Donations
        </MenuItem>
        <MenuItem
          onClick={() => {
            setStatusFilter('pending')
            setFilterMenuAnchor(null)
          }}
          selected={statusFilter === 'pending'}
        >
          Pending Review
        </MenuItem>
        <MenuItem
          onClick={() => {
            setStatusFilter('reviewed')
            setFilterMenuAnchor(null)
          }}
          selected={statusFilter === 'reviewed'}
        >
          Reviewed
        </MenuItem>
        <MenuItem
          onClick={() => {
            setStatusFilter('synced')
            setFilterMenuAnchor(null)
          }}
          selected={statusFilter === 'synced'}
        >
          Synced to QuickBooks
        </MenuItem>
      </Menu>

      {/* Selected Actions */}
      {selectedRows.length > 0 && (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2">
              {selectedRows.length} donation{selectedRows.length > 1 ? 's' : ''} selected
            </Typography>
            <Button
              size="small"
              variant="contained"
              startIcon={<CheckCircle />}
              onClick={() => markReviewedMutation.mutate(selectedRows as string[])}
            >
              Mark as Reviewed
            </Button>
          </Box>
        </Paper>
      )}

      {/* Donations Grid */}
      <Paper sx={{ height: 600 }}>
        <DataGrid
          rows={filteredDonations}
          columns={columns}
          loading={isLoading}
          checkboxSelection
          disableRowSelectionOnClick
          rowSelectionModel={selectedRows}
          onRowSelectionModelChange={setSelectedRows}
          initialState={{
            pagination: {
              paginationModel: { pageSize: 25 },
            },
          }}
          pageSizeOptions={[25, 50, 100]}
        />
      </Paper>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Donation</DialogTitle>
        <DialogContent>
          {editingDonation && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
              <TextField
                label="Donor Name"
                value={editingDonation.donor_name}
                onChange={(e) =>
                  setEditingDonation({ ...editingDonation, donor_name: e.target.value })
                }
                fullWidth
              />
              <TextField
                label="Amount"
                type="number"
                value={editingDonation.amount}
                onChange={(e) =>
                  setEditingDonation({ ...editingDonation, amount: parseFloat(e.target.value) })
                }
                fullWidth
              />
              <TextField
                label="Check Number"
                value={editingDonation.check_number}
                onChange={(e) =>
                  setEditingDonation({ ...editingDonation, check_number: e.target.value })
                }
                fullWidth
              />
              <TextField
                label="Email"
                value={editingDonation.email || ''}
                onChange={(e) =>
                  setEditingDonation({ ...editingDonation, email: e.target.value })
                }
                fullWidth
              />
              <TextField
                label="Notes"
                value={editingDonation.notes || ''}
                onChange={(e) =>
                  setEditingDonation({ ...editingDonation, notes: e.target.value })
                }
                multiline
                rows={3}
                fullWidth
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => editingDonation && updateMutation.mutate(editingDonation)}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Deduplication Dialog */}
      <Dialog
        open={deduplicationDialogOpen}
        onClose={() => setDeduplicationDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Review Duplicate Donations</DialogTitle>
        <DialogContent>
          {selectedGroup ? (
            <Box>
              <Alert severity="info" sx={{ mb: 2 }}>
                Select the master record to keep. The other records will be marked as duplicates.
              </Alert>
              <DataGrid
                rows={selectedGroup.donations}
                columns={columns.filter((col) => col.field !== 'actions')}
                checkboxSelection
                disableMultipleRowSelection
                rowSelectionModel={[selectedGroup.master_id]}
                onRowSelectionModelChange={(ids) => {
                  if (ids.length > 0) {
                    setSelectedGroup({ ...selectedGroup, master_id: ids[0] as string })
                  }
                }}
                autoHeight
                hideFooter
              />
            </Box>
          ) : (
            <Box>
              <Typography variant="body1" gutterBottom>
                Found {duplicateGroups.length} groups of potential duplicates
              </Typography>
              {duplicateGroups.map((group, index) => (
                <Paper key={index} sx={{ p: 2, mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Group {index + 1} ({group.donations.length} donations)
                  </Typography>
                  <Button
                    size="small"
                    onClick={() => {
                      setSelectedGroup(group)
                    }}
                  >
                    Review
                  </Button>
                </Paper>
              ))}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeduplicationDialogOpen(false)}>Cancel</Button>
          {selectedGroup && (
            <Button
              variant="contained"
              color="warning"
              onClick={() =>
                mergeMutation.mutate({
                  master_id: selectedGroup.master_id,
                  duplicate_ids: selectedGroup.duplicate_ids,
                })
              }
            >
              Merge Duplicates
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  )
}
