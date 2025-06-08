import axios, { AxiosInstance } from 'axios';
import { UploadResponse, ProcessResponse } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include session ID
api.interceptors.request.use((config) => {
  // Get session ID from authService
  const sessionId = localStorage.getItem('qbo_session_id');
  if (sessionId) {
    config.headers['X-Session-ID'] = sessionId;
  }
  return config;
});

export const uploadFiles = async (files: File[]): Promise<UploadResponse> => {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });

  const response = await api.post<UploadResponse>('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const processDonations = async (uploadId: string): Promise<ProcessResponse> => {
  const response = await api.post<ProcessResponse>('/api/process', {
    upload_id: uploadId,
  });

  return response.data;
};

export const checkHealth = async (): Promise<{ status: string; local_dev_mode: boolean }> => {
  const response = await api.get<{ status: string; local_dev_mode: boolean }>('/api/health');
  return response.data;
};

// Export the api instance for use in other services
export const apiService = api;
