export type AgentStatus = 'initializing' | 'idle' | 'busy' | 'error' | 'stopping' | 'stopped';

export type AgentType =
  | 'sisyphus'
  | 'oracle'
  | 'explore'
  | 'frontend'
  | 'implement'
  | 'fixer'
  | 'librarian'
  | 'document-writer';

export interface AgentConfig {
  type: AgentType;
  model: string;
  systemPrompt: string;
  temperature?: number;
  maxTokens?: number;
  tools?: ToolDefinition[];
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  toolCalls?: ToolCall[];
  timestamp: Date;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  status: 'pending' | 'running' | 'completed' | 'error';
}

export interface SessionContext {
  sessionId: string;
  projectId: string;
  taskId?: string;
  userId: string;
  messages: Message[];
  memory?: ProjectMemory[];
}

export interface ProjectMemory {
  id: string;
  type: 'pattern' | 'decision' | 'learning' | 'context';
  key: string;
  content: string;
  confidence: number;
}

export interface AgentResponse {
  content: string;
  toolCalls?: ToolCall[];
  tokensUsed: number;
  finished: boolean;
}

export interface HeartbeatPayload {
  agentId: string;
  status: AgentStatus;
  currentTaskId?: string;
  currentSessionId?: string;
  cpuPercent?: number;
  memoryMb?: number;
  timestamp: Date;
}

export interface IPCMessage {
  type: 'session:start' | 'session:message' | 'session:cancel' | 'heartbeat' | 'status' | 'log' | 'error';
  payload: unknown;
}
