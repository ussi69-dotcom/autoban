const DEFAULT_LOCAL_API_URL = 'http://localhost:8001'
const DEFAULT_PROD_API_URL = 'https://autoban-api.learnai.cz'

export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    if (hostname.endsWith('learnai.cz')) {
      return DEFAULT_PROD_API_URL
    }
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return DEFAULT_LOCAL_API_URL
    }
  }

  return DEFAULT_LOCAL_API_URL
}
