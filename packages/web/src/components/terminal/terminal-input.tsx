'use client';

import { useState, useRef, useCallback, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Square, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TerminalInputProps {
  onSend: (message: string) => void;
  onCancel?: () => void;
  disabled?: boolean;
  isRunning?: boolean;
  placeholder?: string;
  className?: string;
}

export function TerminalInput({
  onSend,
  onCancel,
  disabled = false,
  isRunning = false,
  placeholder = 'Type a message... (Ctrl+Enter to send)',
  className,
}: TerminalInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;

    onSend(trimmed);
    setInput('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [input, disabled, onSend]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);

    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  };

  return (
    <div className={cn('flex items-end gap-2 p-3 border-t bg-background', className)}>
      <Textarea
        ref={textareaRef}
        value={input}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled || isRunning}
        className="min-h-[40px] max-h-[200px] resize-none"
        rows={1}
      />

      <div className="flex gap-1">
        {isRunning && onCancel ? (
          <Button
            variant="destructive"
            size="icon"
            onClick={onCancel}
            title="Cancel"
          >
            <Square className="w-4 h-4" />
          </Button>
        ) : (
          <Button
            variant="default"
            size="icon"
            onClick={handleSend}
            disabled={disabled || !input.trim() || isRunning}
            title="Send (Ctrl+Enter)"
          >
            {isRunning ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        )}
      </div>
    </div>
  );
}
