'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Terminal,
  MessageSquare,
  Maximize2,
  Minimize2,
  X,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { wsManager } from '@/lib/websocket';
import { TerminalView } from './terminal-view';
import { ChatView } from './chat-view';
import { TerminalInput } from './terminal-input';
import type { ViewMode, SessionState, TerminalMessage, MessageRole } from './types';

interface IntegratedTerminalProps {
  sessionId?: string;
  agentId?: string;
  onClose?: () => void;
  className?: string;
  defaultExpanded?: boolean;
}

export function IntegratedTerminal({
  sessionId,
  agentId,
  onClose,
  className,
  defaultExpanded = false,
}: IntegratedTerminalProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('chat');
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [state, setState] = useState<SessionState>({
    sessionId: sessionId || null,
    agentId: agentId || null,
    status: 'idle',
    messages: [],
  });

  const messageIdCounter = useRef(0);

  const addMessage = useCallback((
    role: TerminalMessage['role'],
    content: string,
    metadata?: TerminalMessage['metadata']
  ) => {
    const message: TerminalMessage = {
      id: `msg-${++messageIdCounter.current}`,
      role,
      content,
      timestamp: new Date(),
      metadata,
    };

    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, message],
    }));

    return message.id;
  }, []);

  const updateMessageStatus = useCallback((
    messageId: string,
    status: 'pending' | 'success' | 'error'
  ) => {
    setState((prev) => ({
      ...prev,
      messages: prev.messages.map((msg) =>
        msg.id === messageId
          ? { ...msg, metadata: { ...msg.metadata, status } }
          : msg
      ),
    }));
  }, []);

  // Subscribe to WebSocket messages
  useEffect(() => {
    if (!sessionId) return;

    const channel = `session:${sessionId}`;

    const unsubscribe = wsManager.subscribe(channel, (data: unknown) => {
      const msg = data as Record<string, unknown>;
      switch (msg.type) {
        case 'message':
          addMessage(
            (msg.role as MessageRole) || 'assistant',
            String(msg.content || ''),
            msg.metadata as TerminalMessage['metadata']
          );
          break;
        case 'status':
          setState((prev) => ({
            ...prev,
            status: msg.status as SessionState['status']
          }));
          break;
        case 'error':
          addMessage('error', String(msg.message || 'An error occurred'));
          break;
      }
    });

    wsManager.connect();
    setState((prev) => ({ ...prev, status: 'connecting' }));

    return () => {
      unsubscribe();
    };
  }, [sessionId, addMessage]);

  const handleSend = useCallback((content: string) => {
    if (!sessionId) {
      addMessage('error', 'No active session. Please start a session first.');
      return;
    }

    const messageId = addMessage('user', content, { status: 'pending' });

    wsManager.sendMessage('message', {
      sessionId,
      content,
    });

    updateMessageStatus(messageId, 'success');
    setState((prev) => ({ ...prev, status: 'running' }));
  }, [sessionId, addMessage, updateMessageStatus]);

  const handleCancel = useCallback(() => {
    if (!sessionId) return;

    wsManager.sendMessage('cancel', {
      sessionId,
    });

    addMessage('system', 'Cancellation requested...');
  }, [sessionId, addMessage]);

  const handleReconnect = useCallback(() => {
    wsManager.connect();
    setState((prev) => ({ ...prev, status: 'connecting' }));
  }, []);

  const getStatusColor = () => {
    switch (state.status) {
      case 'connected':
        return 'bg-success';
      case 'connecting':
        return 'bg-warning';
      case 'running':
        return 'bg-primary animate-pulse';
      case 'disconnected':
        return 'bg-danger';
      default:
        return 'bg-muted';
    }
  };

  return (
    <div
      className={cn(
        'flex flex-col border rounded-lg bg-background shadow-lg',
        isExpanded ? 'fixed inset-4 z-50' : 'h-[400px]',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className={cn('w-2 h-2 rounded-full', getStatusColor())} />
            <span className="text-sm font-medium">
              {sessionId ? `Session: ${sessionId.slice(0, 8)}...` : 'Terminal'}
            </span>
          </div>

          {state.status === 'running' && (
            <Badge variant="outline" className="text-xs">
              Running
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-1">
          <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as ViewMode)}>
            <TabsList className="h-7">
              <TabsTrigger value="chat" className="h-6 px-2">
                <MessageSquare className="w-3 h-3 mr-1" />
                Chat
              </TabsTrigger>
              <TabsTrigger value="terminal" className="h-6 px-2">
                <Terminal className="w-3 h-3 mr-1" />
                Raw
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {state.status === 'disconnected' && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={handleReconnect}
              title="Reconnect"
            >
              <RefreshCw className="w-3 h-3" />
            </Button>
          )}

          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Minimize' : 'Maximize'}
          >
            {isExpanded ? (
              <Minimize2 className="w-3 h-3" />
            ) : (
              <Maximize2 className="w-3 h-3" />
            )}
          </Button>

          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onClose}
              title="Close"
            >
              <X className="w-3 h-3" />
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0">
        {viewMode === 'chat' ? (
          <ChatView messages={state.messages} />
        ) : (
          <TerminalView messages={state.messages} />
        )}
      </div>

      {/* Input */}
      <TerminalInput
        onSend={handleSend}
        onCancel={handleCancel}
        disabled={state.status === 'disconnected'}
        isRunning={state.status === 'running'}
      />
    </div>
  );
}
