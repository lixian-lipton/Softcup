import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 300000 })

export const healthCheck = () => api.get('/health')
export const getStats = () => api.get('/stats')
export const searchText = (data) => api.post('/search', data)
export const askText = (data) => api.post('/ask', data)
export const askImage = (formData) =>
  api.post('/ask/image', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const getWorkflow = (data) => api.post('/workflow', data)
export const listCases = (status) => api.get('/cases', { params: { status } })
export const createCase = (formData) =>
  api.post('/cases', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const reviewCase = (id, data) => api.post(`/cases/${id}/review`, data)
export const createAnnotation = (data) => api.post('/annotations', data)
export const listAnnotations = () => api.get('/annotations')
export const getGraph = () => api.get('/graph')

export default api
