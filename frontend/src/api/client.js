import axios from 'axios'

// Read env var — must start with VITE_ to be exposed by Vite
const RAW_BASE = import.meta.env.VITE_API_BASE_URL

// Build base URL — never double-append /api
const BASE_URL = RAW_BASE
  ? `${RAW_BASE.replace(/\/$/, '')}/api`
  : 'http://127.0.0.1:8000/api'

// Log once on load so you can verify in browser console
console.log('[LexAI] API base URL:', BASE_URL)

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 180000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ─── Request interceptor — log every outgoing request ────────
api.interceptors.request.use(
  (config) => {
    console.log(`[LexAI] → ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`)
    return config
  },
  (error) => Promise.reject(error)
)

// ─── Response interceptor — log errors ───────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error(
      '[LexAI] Request failed:',
      error.message,
      '| URL:', error.config?.url,
      '| Status:', error.response?.status,
      '| Data:', error.response?.data
    )
    return Promise.reject(error)
  }
)

// ─── Legal Query ──────────────────────────────────────────────
// Calls: POST /api/query
export const queryLegal = (
  query,
  chatHistory = [],
  workspaceId = null,
  sessionId   = null
) =>
  api.post('/query', {
    query,
    chat_history: chatHistory,
    workspace_id: workspaceId,
    session_id:   sessionId,
  })

// ─── File Upload ──────────────────────────────────────────────
// Calls: POST /api/upload
export const uploadDocument = (file, query = 'Analyze this document.') => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('query', query)
  return api.post('/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Calls: POST /api/analyze-contract
export const analyzeContract = (file, useLlm = true) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post(`/analyze-contract?use_llm=${useLlm}`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Calls: POST /api/compare
export const compareContracts = (fileA, fileB, useLlm = true) => {
  const fd = new FormData()
  fd.append('file_a', fileA)
  fd.append('file_b', fileB)
  return api.post(`/compare?use_llm=${useLlm}`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ─── Document Generation ──────────────────────────────────────
// Calls: POST /api/generate-document
export const generateDocument = (docType, situation, useLlm = true) =>
  api.post(`/generate-document?use_llm=${useLlm}`, {
    doc_type:  docType,
    situation,
  })

// Calls: GET /api/document-types
export const getDocumentTypes = () =>
  api.get('/document-types')

// ─── Health ───────────────────────────────────────────────────
// Calls: GET /api/health/llm
export const checkHealth = () =>
  api.get('/health/llm')