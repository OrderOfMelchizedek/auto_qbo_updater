import { useState, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  LinearProgress,
  Alert,
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
} from '@mui/material'
import {
  CloudUpload,
  InsertDriveFile,
  Delete,
  CheckCircle,
  Error,
  Visibility,
} from '@mui/icons-material'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { useNotification } from '@/contexts/NotificationContext'
import { api } from '@/services/api'

interface UploadFile {
  file: File
  id: string
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error'
  progress: number
  error?: string
  result?: ProcessingResult
}

interface ProcessingResult {
  document_id: string
  filename: string
  donations_found: number
  total_amount: number
  processing_time: number
  errors: string[]
}

interface ProcessedDocument {
  id: string
  filename: string
  upload_date: string
  status: string
  donations_count: number
  total_amount: number
  processed_by: string
}

export const UploadPage = () => {
  const [files, setFiles] = useState<UploadFile[]>([])
  const [selectedResult, setSelectedResult] = useState<ProcessingResult | null>(null)
  const { showSuccess, showError } = useNotification()

  const { data: recentDocuments, refetch: refetchDocuments } = useQuery({
    queryKey: ['recent-documents'],
    queryFn: async () => {
      const response = await api.get<ProcessedDocument[]>('/documents/recent')
      return response.data
    },
  })

  const uploadMutation = useMutation({
    mutationFn: async (uploadFile: UploadFile) => {
      // Update status to uploading
      updateFileStatus(uploadFile.id, 'uploading', 0)

      try {
        const response = await api.uploadFile<ProcessingResult>(
          '/documents/upload',
          uploadFile.file,
          (progress) => {
            updateFileStatus(uploadFile.id, 'uploading', progress)
          }
        )

        // Update status to processing
        updateFileStatus(uploadFile.id, 'processing', 100)

        // Simulate processing delay
        await new Promise(resolve => setTimeout(resolve, 2000))

        // Update with result
        updateFileStatus(uploadFile.id, 'completed', 100, undefined, response.data)

        return response.data
      } catch (error: any) {
        const errorMessage = error.response?.data?.detail || 'Upload failed'
        updateFileStatus(uploadFile.id, 'error', 0, errorMessage)
        throw error
      }
    },
    onSuccess: (data) => {
      showSuccess(`Successfully processed ${data.donations_found} donations`)
      refetchDocuments()
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Upload failed')
    },
  })

  const updateFileStatus = (
    id: string,
    status: UploadFile['status'],
    progress: number,
    error?: string,
    result?: ProcessingResult
  ) => {
    setFiles((prev) =>
      prev.map((f) =>
        f.id === id ? { ...f, status, progress, error, result } : f
      )
    )
  }

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadFile[] = acceptedFiles.map((file) => ({
      file,
      id: `${Date.now()}-${Math.random()}`,
      status: 'pending' as const,
      progress: 0,
    }))

    setFiles((prev) => [...prev, ...newFiles])

    // Start uploading each file
    newFiles.forEach((uploadFile) => {
      uploadMutation.mutate(uploadFile)
    })
  }, [uploadMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg'],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
  })

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }

  const getStatusIcon = (status: UploadFile['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle color="success" />
      case 'error':
        return <Error color="error" />
      default:
        return <InsertDriveFile />
    }
  }

  const getStatusChip = (status: string) => {
    const statusConfig = {
      completed: { label: 'Completed', color: 'success' as const },
      processing: { label: 'Processing', color: 'info' as const },
      error: { label: 'Error', color: 'error' as const },
      pending: { label: 'Pending', color: 'default' as const },
    }

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending
    return <Chip label={config.label} color={config.color} size="small" />
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Upload Documents
      </Typography>

      {/* Dropzone */}
      <Paper
        {...getRootProps()}
        sx={{
          p: 4,
          mb: 3,
          textAlign: 'center',
          cursor: 'pointer',
          backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'divider',
          transition: 'all 0.2s',
          '&:hover': {
            backgroundColor: 'action.hover',
            borderColor: 'primary.main',
          },
        }}
      >
        <input {...getInputProps()} />
        <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {isDragActive
            ? 'Drop the files here...'
            : 'Drag & drop files here, or click to select'}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Supported formats: PDF, PNG, JPG (Max size: 10MB)
        </Typography>
      </Paper>

      {/* Upload Queue */}
      {files.length > 0 && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Upload Queue
          </Typography>
          <List>
            {files.map((file) => (
              <ListItem key={file.id}>
                <ListItemIcon>{getStatusIcon(file.status)}</ListItemIcon>
                <ListItemText
                  primary={file.file.name}
                  secondary={
                    <Box>
                      {file.status === 'uploading' && (
                        <LinearProgress
                          variant="determinate"
                          value={file.progress}
                          sx={{ mt: 1 }}
                        />
                      )}
                      {file.status === 'processing' && (
                        <LinearProgress sx={{ mt: 1 }} />
                      )}
                      {file.error && (
                        <Typography variant="caption" color="error">
                          {file.error}
                        </Typography>
                      )}
                      {file.result && (
                        <Typography variant="caption" color="success.main">
                          Found {file.result.donations_found} donations
                        </Typography>
                      )}
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  {file.result && (
                    <IconButton
                      edge="end"
                      onClick={() => setSelectedResult(file.result)}
                      sx={{ mr: 1 }}
                    >
                      <Visibility />
                    </IconButton>
                  )}
                  <IconButton edge="end" onClick={() => removeFile(file.id)}>
                    <Delete />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      {/* Recent Documents */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Recent Documents
        </Typography>
        {recentDocuments && recentDocuments.length > 0 ? (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Filename</TableCell>
                  <TableCell>Upload Date</TableCell>
                  <TableCell align="center">Donations</TableCell>
                  <TableCell align="right">Total Amount</TableCell>
                  <TableCell align="center">Status</TableCell>
                  <TableCell>Uploaded By</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {recentDocuments.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell>{doc.filename}</TableCell>
                    <TableCell>
                      {format(new Date(doc.upload_date), 'MMM d, yyyy h:mm a')}
                    </TableCell>
                    <TableCell align="center">{doc.donations_count}</TableCell>
                    <TableCell align="right">
                      ${doc.total_amount.toLocaleString()}
                    </TableCell>
                    <TableCell align="center">
                      {getStatusChip(doc.status)}
                    </TableCell>
                    <TableCell>{doc.processed_by}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Alert severity="info">No documents uploaded yet</Alert>
        )}
      </Paper>

      {/* Result Dialog */}
      <Dialog
        open={!!selectedResult}
        onClose={() => setSelectedResult(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Processing Result</DialogTitle>
        <DialogContent>
          {selectedResult && (
            <Box>
              <Typography variant="body1" gutterBottom>
                <strong>File:</strong> {selectedResult.filename}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Donations Found:</strong> {selectedResult.donations_found}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Total Amount:</strong> ${selectedResult.total_amount.toLocaleString()}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Processing Time:</strong> {selectedResult.processing_time.toFixed(2)}s
              </Typography>
              {selectedResult.errors.length > 0 && (
                <>
                  <Typography variant="body1" gutterBottom sx={{ mt: 2 }}>
                    <strong>Errors:</strong>
                  </Typography>
                  <List dense>
                    {selectedResult.errors.map((error, index) => (
                      <ListItem key={index}>
                        <ListItemText primary={error} />
                      </ListItem>
                    ))}
                  </List>
                </>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedResult(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
