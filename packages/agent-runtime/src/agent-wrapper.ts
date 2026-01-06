import Anthropic from '@anthropic-ai/sdk';
import OpenAI from 'openai';
import { IPCChannel } from './ipc-channel.js';
import { getAgentConfig } from './agents/index.js';
import type {
  AgentStatus,
  AgentType,
  AgentConfig,
  SessionContext,
  Message,
  ToolCall,
  AgentResponse,
} from './types.js';

interface AgentWrapperOptions {
  agentType: string;
  agentId: string;
  backendUrl: string;
}

export class AgentWrapper {
  private agentId: string;
  private agentType: AgentType;
  private config: AgentConfig;
  private ipc: IPCChannel;
  private status: AgentStatus = 'initializing';
  private currentSession: SessionContext | null = null;

  // AI clients
  private anthropic: Anthropic | null = null;
  private openai: OpenAI | null = null;

  constructor(options: AgentWrapperOptions) {
    this.agentId = options.agentId;
    this.agentType = options.agentType as AgentType;
    this.config = getAgentConfig(this.agentType);
    this.ipc = new IPCChannel(options.agentId, options.backendUrl);

    // Initialize AI clients based on model
    this.initializeClients();
  }

  private initializeClients(): void {
    if (this.config.model.startsWith('claude') || this.config.model.includes('anthropic')) {
      this.anthropic = new Anthropic();
    }
    if (this.config.model.startsWith('gpt') || this.config.model.includes('openai')) {
      this.openai = new OpenAI();
    }
  }

  async start(): Promise<void> {
    console.log(`[Agent] Starting ${this.agentType} agent (${this.agentId})`);

    // Connect to backend
    await this.ipc.connect();

    // Register message handlers
    this.ipc.onMessage('session:start', (payload) => this.handleSessionStart(payload));
    this.ipc.onMessage('session:message', (payload) => this.handleSessionMessage(payload));
    this.ipc.onMessage('session:cancel', (payload) => this.handleSessionCancel(payload));

    // Update status
    this.setStatus('idle');
    this.ipc.sendLog('info', `Agent ${this.agentType} started successfully`);
  }

  async stop(): Promise<void> {
    console.log(`[Agent] Stopping ${this.agentType} agent`);
    this.setStatus('stopping');

    // Cancel current session if any
    if (this.currentSession) {
      this.currentSession = null;
    }

    await this.ipc.disconnect();
    this.setStatus('stopped');
  }

  private setStatus(status: AgentStatus): void {
    this.status = status;
    this.ipc.sendStatus(status, {
      currentSessionId: this.currentSession?.sessionId,
      currentTaskId: this.currentSession?.taskId,
    });
  }

  private async handleSessionStart(payload: unknown): Promise<void> {
    const session = payload as SessionContext;
    console.log(`[Agent] Starting session: ${session.sessionId}`);

    this.currentSession = session;
    this.setStatus('busy');
    this.ipc.sendLog('info', `Started session ${session.sessionId}`);
  }

  private async handleSessionMessage(payload: unknown): Promise<void> {
    const { sessionId, content } = payload as { sessionId: string; content: string };

    if (!this.currentSession || this.currentSession.sessionId !== sessionId) {
      this.ipc.sendError('No active session or session mismatch');
      return;
    }

    // Add user message to context
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    this.currentSession.messages.push(userMessage);

    this.ipc.sendLog('info', `Processing message in session ${sessionId}`);

    try {
      // Generate response
      const response = await this.generateResponse();

      // Add assistant message to context
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.content,
        toolCalls: response.toolCalls,
        timestamp: new Date(),
      };
      this.currentSession.messages.push(assistantMessage);

      // Send response back
      this.ipc.sendSessionResponse(
        sessionId,
        response.content,
        response.toolCalls,
        response.finished
      );

      if (response.finished) {
        this.setStatus('idle');
      }
    } catch (err) {
      const error = err as Error;
      this.ipc.sendError(`Failed to generate response: ${error.message}`);
      this.ipc.sendSessionResponse(sessionId, `Error: ${error.message}`, undefined, true);
      this.setStatus('error');
    }
  }

  private async handleSessionCancel(payload: unknown): Promise<void> {
    const { sessionId } = payload as { sessionId: string };

    if (this.currentSession?.sessionId === sessionId) {
      console.log(`[Agent] Cancelling session: ${sessionId}`);
      this.currentSession = null;
      this.setStatus('idle');
      this.ipc.sendLog('info', `Session ${sessionId} cancelled`);
    }
  }

  private async generateResponse(): Promise<AgentResponse> {
    if (!this.currentSession) {
      throw new Error('No active session');
    }

    const model = this.config.model;

    // Use appropriate client based on model
    if (model.includes('claude') || model.includes('anthropic')) {
      return this.generateAnthropicResponse();
    } else if (model.includes('gpt') || model.includes('openai')) {
      return this.generateOpenAIResponse();
    }

    throw new Error(`Unsupported model: ${model}`);
  }

  private async generateAnthropicResponse(): Promise<AgentResponse> {
    if (!this.anthropic || !this.currentSession) {
      throw new Error('Anthropic client not initialized or no session');
    }

    const messages = this.currentSession.messages
      .filter((m) => m.role !== 'system')
      .map((m) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
      }));

    // Build system prompt with context
    let systemPrompt = this.config.systemPrompt;
    if (this.currentSession.memory && this.currentSession.memory.length > 0) {
      systemPrompt += '\n\n## Relevant Project Memory\n';
      for (const mem of this.currentSession.memory) {
        systemPrompt += `- [${mem.type}] ${mem.key}: ${mem.content}\n`;
      }
    }

    const response = await this.anthropic.messages.create({
      model: this.config.model,
      max_tokens: this.config.maxTokens || 4096,
      system: systemPrompt,
      messages,
    });

    const textContent = response.content.find((c) => c.type === 'text');

    return {
      content: textContent?.text || '',
      tokensUsed: response.usage.input_tokens + response.usage.output_tokens,
      finished: response.stop_reason === 'end_turn',
    };
  }

  private async generateOpenAIResponse(): Promise<AgentResponse> {
    if (!this.openai || !this.currentSession) {
      throw new Error('OpenAI client not initialized or no session');
    }

    const messages = [
      { role: 'system' as const, content: this.config.systemPrompt },
      ...this.currentSession.messages.map((m) => ({
        role: m.role as 'user' | 'assistant' | 'system',
        content: m.content,
      })),
    ];

    const response = await this.openai.chat.completions.create({
      model: this.config.model,
      max_tokens: this.config.maxTokens || 4096,
      temperature: this.config.temperature || 0.7,
      messages,
    });

    const choice = response.choices[0];

    return {
      content: choice.message.content || '',
      tokensUsed: response.usage?.total_tokens || 0,
      finished: choice.finish_reason === 'stop',
    };
  }
}
