export type MessageRole = 'user' | 'assistant' | 'system' | 'error';

export interface TerminalMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  metadata?: {
    tool?: string;
    duration?: number;
    status?: 'pending' | 'success' | 'error';
  };
}

export interface SessionState {
  sessionId: string | null;
  agentId: string | null;
  status: 'idle' | 'connecting' | 'connected' | 'running' | 'disconnected';
  messages: TerminalMessage[];
}

export type ViewMode = 'terminal' | 'chat';
