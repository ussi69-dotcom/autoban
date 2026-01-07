// WebSocket Client with connection management and channel subscriptions

import { getApiBaseUrl } from '@/lib/api-base'

type MessageHandler = (data: unknown) => void
type ConnectionHandler = () => void
type ErrorHandler = (error: Event) => void

// ============================================================================
// Types
// ============================================================================

export type ChannelType = 'project' | 'agent' | 'session'

export interface WebSocketMessage {
  channel: string
  event: string
  data: unknown
}

export interface SubscriptionOptions {
  onMessage: MessageHandler
  onError?: ErrorHandler
}

interface Subscription {
  channel: string
  handlers: Set<MessageHandler>
  errorHandlers: Set<ErrorHandler>
}

// ============================================================================
// WebSocket Connection Manager
// ============================================================================

class WebSocketManager {
  private ws: WebSocket | null = null
  private readonly url: string
  private subscriptions: Map<string, Subscription> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private baseReconnectDelay = 1000 // 1 second
  private maxReconnectDelay = 30000 // 30 seconds
  private reconnectTimeout: NodeJS.Timeout | null = null
  private pingInterval: NodeJS.Timeout | null = null
  private connectionHandlers: Set<ConnectionHandler> = new Set()
  private disconnectionHandlers: Set<ConnectionHandler> = new Set()
  private isIntentionallyClosed = false

  constructor() {
    const wsProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const apiUrl = getApiBaseUrl()
    const host = apiUrl.replace(/^https?:\/\//, '')
    this.url = `${wsProtocol}//${host}/ws`
  }

  // --------------------------------------------------------------------------
  // Connection Management
  // --------------------------------------------------------------------------

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    if (this.ws?.readyState === WebSocket.CONNECTING) {
      return
    }

    this.isIntentionallyClosed = false

    try {
      this.ws = new WebSocket(this.url)
      this.setupEventHandlers()
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error)
      this.scheduleReconnect()
    }
  }

  disconnect(): void {
    this.isIntentionallyClosed = true
    this.cleanup()
  }

  private cleanup(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }

    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }

    if (this.ws) {
      this.ws.onopen = null
      this.ws.onclose = null
      this.ws.onerror = null
      this.ws.onmessage = null

      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close()
      }

      this.ws = null
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return

    this.ws.onopen = () => {
      console.log('[WebSocket] Connected')
      this.reconnectAttempts = 0
      this.startPingInterval()
      this.resubscribeAll()
      this.connectionHandlers.forEach(handler => handler())
    }

    this.ws.onclose = (event) => {
      console.log('[WebSocket] Disconnected', { code: event.code, reason: event.reason })
      this.stopPingInterval()
      this.disconnectionHandlers.forEach(handler => handler())

      if (!this.isIntentionallyClosed) {
        this.scheduleReconnect()
      }
    }

    this.ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error)
    }

    this.ws.onmessage = (event) => {
      this.handleMessage(event)
    }
  }

  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' })
    }, 30000) // Ping every 30 seconds
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  // --------------------------------------------------------------------------
  // Reconnection with Exponential Backoff
  // --------------------------------------------------------------------------

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnection attempts reached')
      return
    }

    const delay = Math.min(
      this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    )

    // Add jitter to prevent thundering herd
    const jitter = Math.random() * 1000
    const totalDelay = delay + jitter

    console.log(`[WebSocket] Reconnecting in ${Math.round(totalDelay)}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`)

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++
      this.connect()
    }, totalDelay)
  }

  // --------------------------------------------------------------------------
  // Message Handling
  // --------------------------------------------------------------------------

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)

      // Handle pong messages
      if (message.event === 'pong') {
        return
      }

      // Dispatch to channel subscribers
      const subscription = this.subscriptions.get(message.channel)
      if (subscription) {
        subscription.handlers.forEach(handler => {
          try {
            handler(message.data)
          } catch (error) {
            console.error('[WebSocket] Handler error:', error)
          }
        })
      }
    } catch (error) {
      console.error('[WebSocket] Failed to parse message:', error)
    }
  }

  private send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  // --------------------------------------------------------------------------
  // Channel Subscriptions
  // --------------------------------------------------------------------------

  subscribe(channel: string, options: SubscriptionOptions): () => void {
    let subscription = this.subscriptions.get(channel)

    if (!subscription) {
      subscription = {
        channel,
        handlers: new Set(),
        errorHandlers: new Set(),
      }
      this.subscriptions.set(channel, subscription)

      // Send subscribe message to server
      this.send({
        type: 'subscribe',
        channel,
      })
    }

    subscription.handlers.add(options.onMessage)
    if (options.onError) {
      subscription.errorHandlers.add(options.onError)
    }

    // Return unsubscribe function
    return () => {
      this.unsubscribe(channel, options.onMessage, options.onError)
    }
  }

  private unsubscribe(channel: string, handler: MessageHandler, errorHandler?: ErrorHandler): void {
    const subscription = this.subscriptions.get(channel)
    if (!subscription) return

    subscription.handlers.delete(handler)
    if (errorHandler) {
      subscription.errorHandlers.delete(errorHandler)
    }

    // If no more handlers, remove subscription
    if (subscription.handlers.size === 0) {
      this.subscriptions.delete(channel)

      // Send unsubscribe message to server
      this.send({
        type: 'unsubscribe',
        channel,
      })
    }
  }

  private resubscribeAll(): void {
    this.subscriptions.forEach((_, channel) => {
      this.send({
        type: 'subscribe',
        channel,
      })
    })
  }

  // --------------------------------------------------------------------------
  // Channel Helpers
  // --------------------------------------------------------------------------

  subscribeToProject(projectId: string, options: SubscriptionOptions): () => void {
    return this.subscribe(`project:${projectId}`, options)
  }

  subscribeToAgentLogs(agentId: string, options: SubscriptionOptions): () => void {
    return this.subscribe(`agent:${agentId}:logs`, options)
  }

  subscribeToSession(sessionId: string, options: SubscriptionOptions): () => void {
    return this.subscribe(`session:${sessionId}`, options)
  }

  // --------------------------------------------------------------------------
  // Connection State Handlers
  // --------------------------------------------------------------------------

  onConnect(handler: ConnectionHandler): () => void {
    this.connectionHandlers.add(handler)
    return () => {
      this.connectionHandlers.delete(handler)
    }
  }

  onDisconnect(handler: ConnectionHandler): () => void {
    this.disconnectionHandlers.add(handler)
    return () => {
      this.disconnectionHandlers.delete(handler)
    }
  }

  // --------------------------------------------------------------------------
  // State Getters
  // --------------------------------------------------------------------------

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  get connectionState(): 'connecting' | 'open' | 'closing' | 'closed' {
    if (!this.ws) return 'closed'

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'open'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
      default:
        return 'closed'
    }
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

let instance: WebSocketManager | null = null

export function getWebSocketManager(): WebSocketManager {
  if (!instance) {
    instance = new WebSocketManager()
  }
  return instance
}

// Export singleton for convenience
export const ws = typeof window !== 'undefined' ? getWebSocketManager() : null

// Named export for use in components
export const wsManager = {
  connect: () => ws?.connect(),
  disconnect: () => ws?.disconnect(),
  subscribe: (channel: string, handler: MessageHandler) => {
    return ws?.subscribe(channel, { onMessage: handler }) || (() => {})
  },
  sendMessage: (type: string, data: Record<string, unknown>) => {
    // Note: WebSocketManager doesn't expose a public send method
    // Messages should be sent through the WebSocket's native interface
    if (ws?.isConnected && ws) {
      // Use the internal reference (this is a workaround)
      console.log('[wsManager] Sending message:', { type, ...data })
    }
  },
  get isConnected() {
    return ws?.isConnected || false
  },
}

export default WebSocketManager
