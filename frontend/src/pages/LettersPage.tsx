import { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Card,
  CardContent,
  CardActions,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Skeleton,
  Alert,
  Tabs,
  Tab,
} from '@mui/material'
import {
  Email,
  Download,
  Preview,
  Send,
  Add,
  CheckCircle,
} from '@mui/icons-material'
import { DataGrid, GridColDef } from '@mui/x-data-grid'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { useForm } from 'react-hook-form'
import { useNotification } from '@/contexts/NotificationContext'
import { api } from '@/services/api'

interface LetterTemplate {
  template_id: string
  name: string
  description: string
  is_default: boolean
  created_by: string
}

interface GeneratedLetter {
  donation_id: string
  recipient_name: string
  recipient_email?: string
  template_name: string
  file_url?: string
  generated_at: string
  sent_at?: string
}

interface LetterBatch {
  batch_id: string
  template_id: string
  letters: GeneratedLetter[]
  total_count: number
  created_by: string
  created_at: string
}

interface OrganizationInfo {
  name: string
  address_line1: string
  address_line2?: string
  city: string
  state: string
  postal_code: string
  phone?: string
  email?: string
  ein: string
  treasurer_name: string
  treasurer_title: string
}

export const LettersPage = () => {
  const [tabValue, setTabValue] = useState(0)
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false)
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false)
  const [previewContent, setPreviewContent] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [selectedDonations, setSelectedDonations] = useState<string[]>([])

  const queryClient = useQueryClient()
  const { showSuccess, showError } = useNotification()

  const { register, handleSubmit, reset } = useForm<OrganizationInfo>({
    defaultValues: {
      treasurer_title: 'Treasurer',
    },
  })

  // Fetch letter templates
  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ['letter-templates'],
    queryFn: async () => {
      const response = await api.get<LetterTemplate[]>('/letters/templates')
      return response.data
    },
  })

  // Fetch recent batches
  const { data: recentBatches = [] } = useQuery({
    queryKey: ['letter-batches'],
    queryFn: async () => {
      const response = await api.get<LetterBatch[]>('/letters/batches')
      return response.data
    },
  })

  // Fetch donations that need letters
  const { data: pendingDonations = [] } = useQuery({
    queryKey: ['donations-pending-letters'],
    queryFn: async () => {
      const response = await api.get<any[]>('/donations?needs_letter=true')
      return response.data
    },
  })

  // Generate letters mutation
  const generateMutation = useMutation({
    mutationFn: async (data: {
      donation_ids: string[]
      template_name: string
      organization_info: OrganizationInfo
      send_email: boolean
    }) => {
      const response = await api.post<LetterBatch>('/letters/generate', data)
      return response.data
    },
    onSuccess: (data) => {
      showSuccess(`Generated ${data.total_count} letters successfully`)
      queryClient.invalidateQueries({ queryKey: ['letter-batches'] })
      queryClient.invalidateQueries({ queryKey: ['donations-pending-letters'] })
      setGenerateDialogOpen(false)
      reset()
    },
    onError: () => {
      showError('Failed to generate letters')
    },
  })

  // Preview letter
  const previewMutation = useMutation({
    mutationFn: async (data: {
      template_name: string
      organization_info: OrganizationInfo
    }) => {
      const response = await api.post<string>('/letters/preview', {
        donation_ids: [],
        ...data,
      })
      return response.data
    },
    onSuccess: (html) => {
      setPreviewContent(html)
      setPreviewDialogOpen(true)
    },
    onError: () => {
      showError('Failed to preview letter')
    },
  })

  // Download letter
  const handleDownload = async (letterId: string) => {
    try {
      await api.downloadFile(`/letters/download/${letterId}`, `letter_${letterId}.pdf`)
      showSuccess('Letter downloaded successfully')
    } catch (error) {
      showError('Failed to download letter')
    }
  }

  const donationColumns: GridColDef[] = [
    {
      field: 'donor_name',
      headerName: 'Donor',
      flex: 1,
    },
    {
      field: 'amount',
      headerName: 'Amount',
      width: 120,
      renderCell: (params) => `$${params.value.toLocaleString()}`,
    },
    {
      field: 'payment_date',
      headerName: 'Date',
      width: 120,
      renderCell: (params) => format(new Date(params.value), 'MMM d, yyyy'),
    },
    {
      field: 'email',
      headerName: 'Email',
      flex: 1,
      renderCell: (params) => params.value || 'No email',
    },
  ]

  const letterColumns: GridColDef[] = [
    {
      field: 'recipient_name',
      headerName: 'Recipient',
      flex: 1,
    },
    {
      field: 'template_name',
      headerName: 'Template',
      width: 150,
    },
    {
      field: 'generated_at',
      headerName: 'Generated',
      width: 150,
      renderCell: (params) => format(new Date(params.value), 'MMM d, yyyy h:mm a'),
    },
    {
      field: 'sent_at',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => {
        if (params.value) {
          return <Chip icon={<Send />} label="Sent" color="success" size="small" />
        }
        return <Chip icon={<CheckCircle />} label="Ready" color="info" size="small" />
      },
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 100,
      sortable: false,
      renderCell: (params) => (
        <IconButton
          size="small"
          onClick={() => handleDownload(params.row.donation_id)}
        >
          <Download />
        </IconButton>
      ),
    },
  ]

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Letter Generation</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setGenerateDialogOpen(true)}
        >
          Generate Letters
        </Button>
      </Box>

      <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)} sx={{ mb: 3 }}>
        <Tab label="Templates" />
        <Tab label="Generated Letters" />
        <Tab label="Pending Donations" />
      </Tabs>

      {/* Templates Tab */}
      {tabValue === 0 && (
        <Grid container spacing={3}>
          {templatesLoading ? (
            [1, 2, 3].map((i) => (
              <Grid item xs={12} md={4} key={i}>
                <Skeleton variant="rectangular" height={200} />
              </Grid>
            ))
          ) : (
            templates.map((template) => (
              <Grid item xs={12} md={4} key={template.template_id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Typography variant="h6" sx={{ flexGrow: 1 }}>
                        {template.name}
                      </Typography>
                      {template.is_default && (
                        <Chip label="Default" color="primary" size="small" />
                      )}
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      {template.description}
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Button
                      size="small"
                      startIcon={<Preview />}
                      onClick={() => {
                        setSelectedTemplate(template.template_id)
                        setPreviewDialogOpen(true)
                      }}
                    >
                      Preview
                    </Button>
                    <Button
                      size="small"
                      startIcon={<Email />}
                      onClick={() => {
                        setSelectedTemplate(template.template_id)
                        setGenerateDialogOpen(true)
                      }}
                    >
                      Use Template
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            ))
          )}
        </Grid>
      )}

      {/* Generated Letters Tab */}
      {tabValue === 1 && (
        <Paper sx={{ p: 2 }}>
          {recentBatches.length === 0 ? (
            <Alert severity="info">No letters generated yet</Alert>
          ) : (
            recentBatches.map((batch) => (
              <Box key={batch.batch_id} sx={{ mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Batch {batch.batch_id}
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Created {format(new Date(batch.created_at), 'MMM d, yyyy h:mm a')} by {batch.created_by}
                </Typography>
                <DataGrid
                  rows={batch.letters}
                  columns={letterColumns}
                  getRowId={(row) => row.donation_id}
                  autoHeight
                  hideFooter
                  disableRowSelectionOnClick
                />
              </Box>
            ))
          )}
        </Paper>
      )}

      {/* Pending Donations Tab */}
      {tabValue === 2 && (
        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">
              Donations Pending Letters ({pendingDonations.length})
            </Typography>
            {selectedDonations.length > 0 && (
              <Button
                variant="contained"
                startIcon={<Email />}
                onClick={() => setGenerateDialogOpen(true)}
              >
                Generate for Selected ({selectedDonations.length})
              </Button>
            )}
          </Box>
          <DataGrid
            rows={pendingDonations}
            columns={donationColumns}
            checkboxSelection
            rowSelectionModel={selectedDonations}
            onRowSelectionModelChange={(ids) => setSelectedDonations(ids as string[])}
            autoHeight
            initialState={{
              pagination: {
                paginationModel: { pageSize: 10 },
              },
            }}
            pageSizeOptions={[10, 25, 50]}
          />
        </Paper>
      )}

      {/* Generate Letters Dialog */}
      <Dialog
        open={generateDialogOpen}
        onClose={() => setGenerateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <form onSubmit={handleSubmit((data) => {
          const template = templates.find(t => t.template_id === selectedTemplate)
          if (template) {
            generateMutation.mutate({
              donation_ids: selectedDonations,
              template_name: template.name,
              organization_info: data,
              send_email: false,
            })
          }
        })}>
          <DialogTitle>Generate Letters</DialogTitle>
          <DialogContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
              <FormControl fullWidth>
                <InputLabel>Template</InputLabel>
                <Select
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  label="Template"
                  required
                >
                  {templates.map((template) => (
                    <MenuItem key={template.template_id} value={template.template_id}>
                      {template.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Typography variant="subtitle2" sx={{ mt: 2 }}>
                Organization Information
              </Typography>

              <TextField
                label="Organization Name"
                {...register('name', { required: true })}
                fullWidth
                required
              />
              <TextField
                label="Address Line 1"
                {...register('address_line1', { required: true })}
                fullWidth
                required
              />
              <TextField
                label="Address Line 2"
                {...register('address_line2')}
                fullWidth
              />
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label="City"
                  {...register('city', { required: true })}
                  fullWidth
                  required
                />
                <TextField
                  label="State"
                  {...register('state', { required: true })}
                  sx={{ width: 100 }}
                  required
                />
                <TextField
                  label="ZIP Code"
                  {...register('postal_code', { required: true })}
                  sx={{ width: 120 }}
                  required
                />
              </Box>
              <TextField
                label="EIN"
                {...register('ein', { required: true })}
                fullWidth
                required
                helperText="Federal Tax ID"
              />
              <TextField
                label="Treasurer Name"
                {...register('treasurer_name', { required: true })}
                fullWidth
                required
              />
              <TextField
                label="Treasurer Title"
                {...register('treasurer_title')}
                fullWidth
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setGenerateDialogOpen(false)}>Cancel</Button>
            <Button
              type="button"
              onClick={handleSubmit((data) => {
                const template = templates.find(t => t.template_id === selectedTemplate)
                if (template) {
                  previewMutation.mutate({
                    template_name: template.name,
                    organization_info: data,
                  })
                }
              })}
            >
              Preview
            </Button>
            <Button type="submit" variant="contained">
              Generate
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog
        open={previewDialogOpen}
        onClose={() => setPreviewDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Letter Preview</DialogTitle>
        <DialogContent>
          <Box
            sx={{
              bgcolor: 'white',
              p: 2,
              border: '1px solid #ddd',
              borderRadius: 1,
              minHeight: 400,
            }}
            dangerouslySetInnerHTML={{ __html: previewContent }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
