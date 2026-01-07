const DEFAULT_LOCAL_API_URL = 'http://localhost:8001'
const DEFAULT_PROD_API_URL = 'https://autoban-api.learnai.cz'

type ApiBaseOptions = {
  hostname?: string
  protocol?: string
}

const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1'])

function normalizeHostname(hostname?: string): string | undefined {
  if (!hostname) return undefined
  return hostname.split(':')[0]
}

function normalizeProtocol(protocol?: string): string | undefined {
  if (!protocol) return undefined
  return protocol.endsWith(':') ? protocol : `${protocol}:`
}

function isLocalHost(hostname?: string): boolean {
  if (!hostname) return false
  return LOCAL_HOSTS.has(hostname)
}

function getHostnameFromUrl(url: string): string | undefined {
  try {
    return new URL(url).hostname
  } catch {
    return undefined
  }
}

export function getApiBaseUrl(options: ApiBaseOptions = {}): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL
  const runtimeHostname = normalizeHostname(
    options.hostname ?? (typeof window !== 'undefined' ? window.location.hostname : undefined)
  )
  const runtimeProtocol = normalizeProtocol(
    options.protocol ?? (typeof window !== 'undefined' ? window.location.protocol : undefined)
  )

  if (envUrl) {
    const envHostname = normalizeHostname(getHostnameFromUrl(envUrl))
    const envIsLocal = isLocalHost(envHostname) || envUrl.includes('localhost') || envUrl.includes('127.0.0.1')
    const runtimeIsLocal = isLocalHost(runtimeHostname)

    if (!(runtimeHostname && !runtimeIsLocal && envIsLocal)) {
      return envUrl
    }
  }

  if (runtimeHostname?.endsWith('learnai.cz')) {
    return DEFAULT_PROD_API_URL
  }

  if (isLocalHost(runtimeHostname)) {
    return DEFAULT_LOCAL_API_URL
  }

  if (runtimeHostname && runtimeProtocol) {
    return `${runtimeProtocol}//${runtimeHostname}`
  }

  return DEFAULT_LOCAL_API_URL
}
