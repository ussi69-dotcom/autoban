import WebSocket from 'ws';
import { v4 as uuidv4 } from 'uuid';
import type { IPCMessage, HeartbeatPayload, AgentStatus } from './types.js';

export class IPCChannel {
  private ws: WebSocket | null = null;
  private agentId: string;
  private backendUrl: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private messageHandlers: Map<string, (payload: unknown) => void> = new Map();

  constructor(agentId: string, backendUrl: string) {
    this.agentId = agentId;
    this.backendUrl = backendUrl;
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = `${this.backendUrl}/ws/agent?agent_id=${this.agentId}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.on('open', () => {
        console.log(`[IPC] Connected to backend: ${wsUrl}`);
        this.reconnectAttempts = 0;
        this.startHeartbeat();
        resolve();
      });

      this.ws.on('message', (data) => {
        try {
          const message: IPCMessage = JSON.parse(data.toString());
          this.handleMessage(message);
        } catch (err) {
          console.error('[IPC] Failed to parse message:', err);
        }
      });

      this.ws.on('close', () => {
        console.log('[IPC] Connection closed');
        this.stopHeartbeat();
        this.attemptReconnect();
      });

      this.ws.on('error', (err) => {
        console.error('[IPC] WebSocket error:', err);
        if (this.reconnectAttempts === 0) {
          reject(err);
        }
      });
    });
  }

  private handleMessage(message: IPCMessage): void {
    const handler = this.messageHandlers.get(message.type);
    if (handler) {
      handler(message.payload);
    } else {
      console.warn(`[IPC] No handler for message type: ${message.type}`);
    }
  }

  onMessage(type: string, handler: (payload: unknown) => void): void {
    this.messageHandlers.set(type, handler);
  }

  private async attemptReconnect(): Promise<void> {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[IPC] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`[IPC] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    await new Promise((resolve) => setTimeout(resolve, delay));

    try {
      await this.connect();
    } catch (err) {
      console.error('[IPC] Reconnection failed:', err);
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      this.sendHeartbeat({
        agentId: this.agentId,
        status: 'idle', // Will be updated by agent wrapper
        timestamp: new Date(),
      });
    }, 30000); // 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  send(message: IPCMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('[IPC] Cannot send message, not connected');
    }
  }

  sendHeartbeat(payload: HeartbeatPayload): void {
    this.send({ type: 'heartbeat', payload });
  }

  sendStatus(status: AgentStatus, details?: Record<string, unknown>): void {
    this.send({
      type: 'status',
      payload: { agentId: this.agentId, status, details, timestamp: new Date() },
    });
  }

  sendLog(level: 'debug' | 'info' | 'warn' | 'error', message: string): void {
    this.send({
      type: 'log',
      payload: { agentId: this.agentId, level, message, timestamp: new Date() },
    });
  }

  sendError(error: string, details?: Record<string, unknown>): void {
    this.send({
      type: 'error',
      payload: { agentId: this.agentId, error, details, timestamp: new Date() },
    });
  }

  sendSessionResponse(sessionId: string, content: string, toolCalls?: unknown[], finished = false): void {
    this.send({
      type: 'session:message',
      payload: {
        sessionId,
        role: 'assistant',
        content,
        toolCalls,
        finished,
        timestamp: new Date(),
      },
    });
  }

  async disconnect(): Promise<void> {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
