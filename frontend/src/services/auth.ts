import { api } from './api'

interface LoginResponse {
  access_token: string
  token_type: string
}

interface User {
  email: string
  name?: string
  sub: string
}

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    const response = await api.post<LoginResponse>('/auth/login', formData.toString())
    return response.data
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me')
    return response.data
  },

  async initiateQuickBooksAuth(): Promise<{ auth_url: string }> {
    const response = await api.get<{ auth_url: string }>('/auth/quickbooks/connect')
    return response.data
  },

  async checkQuickBooksConnection(): Promise<{ connected: boolean; company_name?: string }> {
    const response = await api.get<{ connected: boolean; company_name?: string }>('/auth/quickbooks/status')
    return response.data
  },

  async disconnectQuickBooks(): Promise<void> {
    await api.post('/auth/quickbooks/disconnect')
  },
}
