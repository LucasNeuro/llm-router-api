import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const chatService = {
  sendMessage: async (prompt, options = {}) => {
    const response = await api.post('/chat', {
      prompt,
      sender_phone: options.senderPhone,
      model: options.model,
      generate_audio: options.generateAudio || false,
      use_rag: options.useRag || false,
      rag_namespace: options.ragNamespace,
      rag_top_k: options.ragTopK || 5,
    })
    return response.data
  },

  sendAudio: async (audioFile, options = {}) => {
    const formData = new FormData()
    formData.append('audio', audioFile)
    if (options.senderPhone) formData.append('sender_phone', options.senderPhone)
    if (options.generateAudio) formData.append('generate_audio', 'true')

    const response = await api.post('/chat/audio', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  clearMemory: async (senderPhone) => {
    const response = await api.post('/chat/clear-memory', null, {
      params: { sender_phone: senderPhone },
    })
    return response.data
  },
}

export const ragService = {
  indexDocuments: async (documents, namespace = null) => {
    const response = await api.post('/rag/index', {
      documents,
      namespace,
    })
    return response.data
  },

  search: async (query, topK = 5, namespace = null) => {
    const response = await api.get('/rag/search', {
      params: {
        q: query,
        top_k: topK,
        namespace,
      },
    })
    return response.data
  },
}

export const healthService = {
  check: async () => {
    const response = await api.get('/health')
    return response.data
  },
}

export default api
