import axios from 'axios'
import { clearSession, getToken } from '../auth'

const api = axios.create({ baseURL: '/api', timeout: 300000 })

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      clearSession()
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)

export const healthCheck = () => api.get('/health')
export const getStats = () => api.get('/stats')
export const login = (data) => api.post('/auth/login', data)
export const register = (data) => api.post('/auth/register', data)
export const fetchMe = () => api.get('/auth/me')
export const changePassword = (data) => api.post('/auth/change-password', data)
export const searchText = (data) => api.post('/search', data)
export const askText = (data) => api.post('/ask', data)
export const askImage = (formData) =>
  api.post('/ask/image', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const getWorkflow = (data) => api.post('/workflow', data)
export const listCases = (params) => api.get('/cases', { params })
export const createCase = (formData) =>
  api.post('/cases', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const reviewCase = (id, data) => api.post(`/cases/${id}/review`, data)
export const createAnnotation = (data) => api.post('/annotations', data)
export const listAnnotations = (params) => api.get('/annotations', { params })
export const reviewAnnotation = (id, data) => api.post(`/annotations/${id}/review`, data)
export const uploadKnowledgeDocument = (formData) =>
  api.post('/knowledge/documents', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const getGraph = () => api.get('/graph')

export default api
