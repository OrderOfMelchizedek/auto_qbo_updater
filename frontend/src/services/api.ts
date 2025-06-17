import axios, { AxiosInstance } from 'axios';
import { UploadResponse, ProcessResponse } from '../types';
import { sessionService } from './sessionService';

// In development, use relative URLs to leverage the proxy
// In production, use the environment variable or default to empty string (same origin)
// If running with React proxy, we should NOT use the full URL
const API_BASE_URL = process.env.NODE_ENV === 'development' ? '' : (process.env.REACT_APP_API_URL || '');

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Always send cookies
});

// Add request interceptor to include session ID
api.interceptors.request.use(async (config) => {
  console.log('Axios interceptor - request to:', config.url);

  try {
    // Get session ID from secure session service
    const headers = await sessionService.getHeaders();
    console.log('Session headers retrieved:', headers);

    // Properly merge headers
    Object.entries(headers).forEach(([key, value]) => {
      config.headers.set(key, value);
    });
  } catch (error) {
    console.error('Failed to get session headers:', error);
  }

  console.log('Axios interceptor - config ready');
  return config;
}, (error) => {
  console.error('Request interceptor error:', error);
  return Promise.reject(error);
});

// Add response interceptor for debugging
api.interceptors.response.use(
  (response) => {
    console.log('Response received for:', response.config.url, response);
    return response;
  },
  (error) => {
    console.error('Response error for:', error.config?.url, error);
    return Promise.reject(error);
  }
);

export const uploadFiles = async (files: File[]): Promise<UploadResponse> => {
  console.log('uploadFiles called with', files.length, 'files');

  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });

  console.log('Making upload request to /api/upload');

  try {
    const response = await api.post<UploadResponse>('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    console.log('Upload response received:', response.data);
    return response.data;
  } catch (error) {
    console.error('Upload request failed:', error);
    throw error;
  }
};

export const processDonations = async (uploadId: string): Promise<{ success: boolean; data: { job_id: string; status: string; message: string } }> => {
  const response = await api.post<{ success: boolean; data: { job_id: string; status: string; message: string } }>('/api/process', {
    upload_id: uploadId,
  });

  return response.data;
};

export const getJobStatus = async (jobId: string): Promise<{
  success: boolean;
  data: {
    id: string;
    status: string;
    stage: string;
    progress: number;
    created_at: string;
    updated_at: string;
    result?: ProcessResponse['data'];
    error?: string;
    events: any[];
  };
}> => {
  const response = await api.get(`/api/jobs/${jobId}`);
  return response.data;
};

export const streamJobEvents = (jobId: string, onMessage: (event: any) => void, onError?: (error: any) => void): EventSource => {
  // For EventSource, we need the full URL in development when using proxy
  const baseUrl = process.env.NODE_ENV === 'development' && !API_BASE_URL
    ? `${window.location.protocol}//${window.location.hostname}:${window.location.port}`
    : API_BASE_URL;

  const eventSource = new EventSource(`${baseUrl}/api/jobs/${jobId}/stream`);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (error) {
      console.error('Failed to parse SSE data:', error);
    }
  };

  eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    if (onError) onError(error);
  };

  return eventSource;
};

export const checkHealth = async (): Promise<{ status: string; local_dev_mode: boolean; qbo_environment?: string }> => {
  const response = await api.get<{ status: string; local_dev_mode: boolean; qbo_environment?: string }>('/api/health');
  return response.data;
};

// Export the api instance for use in other services
export const apiService = api;

// Interface for the new customer payload
export interface NewCustomerPayload {
  DisplayName: string;
  GivenName?: string;
  FamilyName?: string;
  CompanyName?: string;
  PrimaryEmailAddr?: string; // String, as per backend expectation for app.py
  PrimaryPhone?: string;   // String, as per backend expectation for app.py
  BillAddr?: {
    Line1?: string;
    City?: string;
    CountrySubDivisionCode?: string; // This is 'state' in the form
    PostalCode?: string;           // This is 'zip' in the form
  };
}

// Function to add a new customer
export const addCustomer = async (customerData: NewCustomerPayload): Promise<any> => {
  try {
    // No need to manually pass sessionId, the axios interceptor handles it.
    const response = await api.post<any>('/api/customers', customerData);
    return response.data; // Should contain { success: true, data: newCustomer }
  } catch (error: any) {
    console.error('Error adding customer:', error.response || error.message || error);
    // Re-throw a more structured error or the original error to be handled by the caller
    throw error.response?.data || new Error(error.message || 'Failed to add customer due to an unknown error');
  }
};

// Function to manually match a donation to a QuickBooks customer
export const manualMatchDonation = async (donation: any, qbCustomerId: string): Promise<any> => {
  try {
    // The axios interceptor handles adding the X-Session-ID header
    const response = await api.post<any>('/api/manual_match', {
      donation: donation,
      qb_customer_id: qbCustomerId,
    });
    return response.data;
  } catch (error: any) {
    console.error('Error matching donation:', error.response || error.message || error);
    throw error.response?.data || new Error(error.message || 'Failed to match donation');
  }
};
