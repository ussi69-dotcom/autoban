'use client';

import { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { Bot, User, AlertCircle, Info, Loader2 } from 'lucide-react';
import type { TerminalMessage, MessageRole } from './types';

interface ChatViewProps {
  messages: TerminalMessage[];
  className?: string;
  autoScroll?: boolean;
}

export function ChatView({ messages, className, autoScroll = true }: ChatViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(autoScroll);

  useEffect(() => {
    if (shouldAutoScroll.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    shouldAutoScroll.current = scrollHeight - scrollTop - clientHeight < 100;
  };

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className={cn(
        'flex flex-col gap-3 p-4 overflow-y-auto h-full',
        className
      )}
    >
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <p>No messages yet. Start a conversation with the agent.</p>
        </div>
      ) : (
        messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))
      )}
    </div>
  );
}

function ChatMessage({ message }: { message: TerminalMessage }) {
  const roleConfig = getRoleConfig(message.role);

  return (
    <div
      className={cn(
        'flex gap-3 p-3 rounded-lg',
        roleConfig.bgColor
      )}
    >
      <div className={cn(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
        roleConfig.iconBg
      )}>
        <roleConfig.icon className={cn('w-4 h-4', roleConfig.iconColor)} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={cn('font-medium text-sm', roleConfig.labelColor)}>
            {roleConfig.label}
          </span>
          <span className="text-xs text-muted-foreground">
            {message.timestamp.toLocaleTimeString()}
          </span>
          {message.metadata?.status === 'pending' && (
            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
          )}
        </div>

        <div className="text-sm whitespace-pre-wrap break-words">
          {message.content}
        </div>

        {message.metadata?.tool && (
          <div className="mt-2 text-xs text-muted-foreground">
            Tool: {message.metadata.tool}
            {message.metadata.duration && ` (${message.metadata.duration}ms)`}
          </div>
        )}
      </div>
    </div>
  );
}

function getRoleConfig(role: MessageRole) {
  switch (role) {
    case 'user':
      return {
        icon: User,
        label: 'You',
        bgColor: 'bg-primary/5',
        iconBg: 'bg-primary/10',
        iconColor: 'text-primary',
        labelColor: 'text-primary',
      };
    case 'assistant':
      return {
        icon: Bot,
        label: 'Agent',
        bgColor: 'bg-success/5',
        iconBg: 'bg-success/10',
        iconColor: 'text-success',
        labelColor: 'text-success',
      };
    case 'error':
      return {
        icon: AlertCircle,
        label: 'Error',
        bgColor: 'bg-danger/5',
        iconBg: 'bg-danger/10',
        iconColor: 'text-danger',
        labelColor: 'text-danger',
      };
    case 'system':
    default:
      return {
        icon: Info,
        label: 'System',
        bgColor: 'bg-muted/50',
        iconBg: 'bg-muted',
        iconColor: 'text-muted-foreground',
        labelColor: 'text-muted-foreground',
      };
  }
}
