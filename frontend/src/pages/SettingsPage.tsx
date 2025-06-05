import { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  MenuItem,
} from '@mui/material'
import {
  Save,
  Add,
  Delete,
  Key,
  Business,
  Email,
  CloudUpload,
} from '@mui/icons-material'
import { useForm } from 'react-hook-form'
import { useQuery, useMutation } from '@tanstack/react-query'
import { format } from 'date-fns'
import { useNotification } from '@/contexts/NotificationContext'
import { api } from '@/services/api'

interface Settings {
  organization: {
    name: string
    address: string
    city: string
    state: string
    zip: string
    ein: string
    phone: string
    email: string
  }
  email: {
    enabled: boolean
    from_address: string
    from_name: string
    smtp_host: string
    smtp_port: number
    smtp_username: string
  }
  processing: {
    auto_deduplicate: boolean
    min_confidence_score: number
    default_letter_template: string
  }
}

interface ApiKey {
  id: string
  name: string
  key_prefix: string
  created_at: string
  last_used: string
  expires_at?: string
}

export const SettingsPage = () => {
  const [tabValue, setTabValue] = useState(0)
  const [apiKeyDialogOpen, setApiKeyDialogOpen] = useState(false)
  const [newApiKeyName, setNewApiKeyName] = useState('')
  const [showNewApiKey, setShowNewApiKey] = useState<string | null>(null)

  const { showSuccess, showError } = useNotification()

  // Fetch settings
  const { data: settings, refetch: refetchSettings } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const response = await api.get<Settings>('/settings')
      return response.data
    },
  })

  // Fetch API keys
  const { data: apiKeys = [], refetch: refetchApiKeys } = useQuery({
    queryKey: ['api-keys'],
    queryFn: async () => {
      const response = await api.get<ApiKey[]>('/settings/api-keys')
      return response.data
    },
  })

  const {
    register: registerOrg,
    handleSubmit: handleOrgSubmit,
    reset: resetOrg,
  } = useForm({
    defaultValues: settings?.organization,
  })

  const {
    register: registerEmail,
    handleSubmit: handleEmailSubmit,
    reset: resetEmail,
  } = useForm({
    defaultValues: settings?.email,
  })

  const {
    register: registerProcessing,
    handleSubmit: handleProcessingSubmit,
    reset: resetProcessing,
  } = useForm({
    defaultValues: settings?.processing,
  })

  // Update settings mutation
  const updateMutation = useMutation({
    mutationFn: async (data: { section: string; settings: any }) => {
      const response = await api.put(`/settings/${data.section}`, data.settings)
      return response.data
    },
    onSuccess: () => {
      showSuccess('Settings updated successfully')
      refetchSettings()
    },
    onError: () => {
      showError('Failed to update settings')
    },
  })

  // Create API key mutation
  const createApiKeyMutation = useMutation({
    mutationFn: async (name: string) => {
      const response = await api.post<{ key: string; key_info: ApiKey }>('/settings/api-keys', { name })
      return response.data
    },
    onSuccess: (data) => {
      setShowNewApiKey(data.key)
      refetchApiKeys()
      setApiKeyDialogOpen(false)
      setNewApiKeyName('')
    },
    onError: () => {
      showError('Failed to create API key')
    },
  })

  // Delete API key mutation
  const deleteApiKeyMutation = useMutation({
    mutationFn: async (keyId: string) => {
      await api.delete(`/settings/api-keys/${keyId}`)
    },
    onSuccess: () => {
      showSuccess('API key deleted')
      refetchApiKeys()
    },
    onError: () => {
      showError('Failed to delete API key')
    },
  })

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>

      <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)} sx={{ mb: 3 }}>
        <Tab label="Organization" icon={<Business />} iconPosition="start" />
        <Tab label="Email" icon={<Email />} iconPosition="start" />
        <Tab label="Processing" icon={<CloudUpload />} iconPosition="start" />
        <Tab label="API Keys" icon={<Key />} iconPosition="start" />
      </Tabs>

      {/* Organization Settings */}
      {tabValue === 0 && (
        <Paper sx={{ p: 3 }}>
          <form onSubmit={handleOrgSubmit((data) => updateMutation.mutate({ section: 'organization', settings: data }))}>
            <Typography variant="h6" gutterBottom>
              Organization Information
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Organization Name"
                {...registerOrg('name', { required: true })}
                fullWidth
              />
              <TextField
                label="Address"
                {...registerOrg('address', { required: true })}
                fullWidth
              />
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label="City"
                  {...registerOrg('city', { required: true })}
                  fullWidth
                />
                <TextField
                  label="State"
                  {...registerOrg('state', { required: true })}
                  sx={{ width: 100 }}
                />
                <TextField
                  label="ZIP Code"
                  {...registerOrg('zip', { required: true })}
                  sx={{ width: 120 }}
                />
              </Box>
              <TextField
                label="EIN"
                {...registerOrg('ein', { required: true })}
                helperText="Federal Tax ID"
                fullWidth
              />
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label="Phone"
                  {...registerOrg('phone')}
                  fullWidth
                />
                <TextField
                  label="Email"
                  {...registerOrg('email')}
                  type="email"
                  fullWidth
                />
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 2 }}>
                <Button onClick={() => resetOrg()}>Reset</Button>
                <Button type="submit" variant="contained" startIcon={<Save />}>
                  Save Changes
                </Button>
              </Box>
            </Box>
          </form>
        </Paper>
      )}

      {/* Email Settings */}
      {tabValue === 1 && (
        <Paper sx={{ p: 3 }}>
          <form onSubmit={handleEmailSubmit((data) => updateMutation.mutate({ section: 'email', settings: data }))}>
            <Typography variant="h6" gutterBottom>
              Email Configuration
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <FormControlLabel
                control={<Switch {...registerEmail('enabled')} />}
                label="Enable email notifications"
              />
              <TextField
                label="From Name"
                {...registerEmail('from_name')}
                fullWidth
              />
              <TextField
                label="From Email"
                {...registerEmail('from_address')}
                type="email"
                fullWidth
              />
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2">SMTP Settings</Typography>
              <TextField
                label="SMTP Host"
                {...registerEmail('smtp_host')}
                fullWidth
              />
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label="SMTP Port"
                  {...registerEmail('smtp_port')}
                  type="number"
                  sx={{ width: 120 }}
                />
                <TextField
                  label="SMTP Username"
                  {...registerEmail('smtp_username')}
                  fullWidth
                />
              </Box>
              <Alert severity="info">
                SMTP password is stored securely and cannot be displayed
              </Alert>
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 2 }}>
                <Button onClick={() => resetEmail()}>Reset</Button>
                <Button type="submit" variant="contained" startIcon={<Save />}>
                  Save Changes
                </Button>
              </Box>
            </Box>
          </form>
        </Paper>
      )}

      {/* Processing Settings */}
      {tabValue === 2 && (
        <Paper sx={{ p: 3 }}>
          <form onSubmit={handleProcessingSubmit((data) => updateMutation.mutate({ section: 'processing', settings: data }))}>
            <Typography variant="h6" gutterBottom>
              Processing Configuration
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <FormControlLabel
                control={<Switch {...registerProcessing('auto_deduplicate')} />}
                label="Automatically detect and flag duplicate donations"
              />
              <TextField
                label="Minimum Confidence Score"
                {...registerProcessing('min_confidence_score')}
                type="number"
                inputProps={{ min: 0, max: 1, step: 0.1 }}
                helperText="Minimum confidence score for data extraction (0-1)"
                sx={{ width: 200 }}
              />
              <TextField
                label="Default Letter Template"
                {...registerProcessing('default_letter_template')}
                select
                fullWidth
              >
                <MenuItem value="default_letter.html">Default Letter</MenuItem>
                <MenuItem value="simple_letter.html">Simple Letter</MenuItem>
              </TextField>
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 2 }}>
                <Button onClick={() => resetProcessing()}>Reset</Button>
                <Button type="submit" variant="contained" startIcon={<Save />}>
                  Save Changes
                </Button>
              </Box>
            </Box>
          </form>
        </Paper>
      )}

      {/* API Keys */}
      {tabValue === 3 && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
            <Typography variant="h6">API Keys</Typography>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setApiKeyDialogOpen(true)}
            >
              Create API Key
            </Button>
          </Box>

          {showNewApiKey && (
            <Alert severity="success" sx={{ mb: 3 }} onClose={() => setShowNewApiKey(null)}>
              <Typography variant="body2">
                New API key created. Copy it now as it won't be shown again:
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'monospace', mt: 1 }}>
                {showNewApiKey}
              </Typography>
            </Alert>
          )}

          {apiKeys.length === 0 ? (
            <Alert severity="info">No API keys created yet</Alert>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Key Prefix</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Last Used</TableCell>
                    <TableCell>Expires</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {apiKeys.map((key) => (
                    <TableRow key={key.id}>
                      <TableCell>{key.name}</TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {key.key_prefix}...
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {format(new Date(key.created_at), 'MMM d, yyyy')}
                      </TableCell>
                      <TableCell>
                        {key.last_used
                          ? format(new Date(key.last_used), 'MMM d, yyyy')
                          : 'Never'}
                      </TableCell>
                      <TableCell>
                        {key.expires_at
                          ? format(new Date(key.expires_at), 'MMM d, yyyy')
                          : 'Never'}
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => deleteApiKeyMutation.mutate(key.id)}
                        >
                          <Delete />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      )}

      {/* Create API Key Dialog */}
      <Dialog open={apiKeyDialogOpen} onClose={() => setApiKeyDialogOpen(false)}>
        <DialogTitle>Create API Key</DialogTitle>
        <DialogContent>
          <TextField
            label="Key Name"
            value={newApiKeyName}
            onChange={(e) => setNewApiKeyName(e.target.value)}
            fullWidth
            sx={{ mt: 2 }}
            helperText="A descriptive name for this API key"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApiKeyDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => createApiKeyMutation.mutate(newApiKeyName)}
            disabled={!newApiKeyName}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
