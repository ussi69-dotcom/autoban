'use client';

import { useEffect, useRef, useCallback } from 'react';
import type { Terminal } from '@xterm/xterm';
import type { FitAddon } from '@xterm/addon-fit';
import type { TerminalMessage } from './types';

interface TerminalViewProps {
  messages: TerminalMessage[];
  className?: string;
}

export function TerminalView({ messages, className = '' }: TerminalViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const lastMessageCountRef = useRef(0);

  const initTerminal = useCallback(async () => {
    if (!containerRef.current || terminalRef.current) return;

    const { Terminal } = await import('@xterm/xterm');
    const { FitAddon } = await import('@xterm/addon-fit');
    const { WebLinksAddon } = await import('@xterm/addon-web-links');

    const terminal = new Terminal({
      theme: {
        background: '#0a0a0a',
        foreground: '#e4e4e7',
        cursor: '#3b82f6',
        cursorAccent: '#0a0a0a',
        selectionBackground: '#3b82f680',
        black: '#18181b',
        red: '#ef4444',
        green: '#22c55e',
        yellow: '#eab308',
        blue: '#3b82f6',
        magenta: '#a855f7',
        cyan: '#06b6d4',
        white: '#e4e4e7',
        brightBlack: '#52525b',
        brightRed: '#f87171',
        brightGreen: '#4ade80',
        brightYellow: '#facc15',
        brightBlue: '#60a5fa',
        brightMagenta: '#c084fc',
        brightCyan: '#22d3ee',
        brightWhite: '#fafafa',
      },
      fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
      fontSize: 13,
      lineHeight: 1.4,
      cursorBlink: true,
      cursorStyle: 'block',
      scrollback: 10000,
      convertEol: true,
      disableStdin: true,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    terminal.loadAddon(fitAddon);
    terminal.loadAddon(webLinksAddon);
    terminal.open(containerRef.current);
    fitAddon.fit();

    terminalRef.current = terminal;
    fitAddonRef.current = fitAddon;

    // Write existing messages
    messages.forEach((msg) => writeMessage(terminal, msg));
    lastMessageCountRef.current = messages.length;
  }, [messages]);

  useEffect(() => {
    initTerminal();

    return () => {
      terminalRef.current?.dispose();
      terminalRef.current = null;
      fitAddonRef.current = null;
    };
  }, [initTerminal]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      fitAddonRef.current?.fit();
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Write new messages
  useEffect(() => {
    const terminal = terminalRef.current;
    if (!terminal) return;

    const newMessages = messages.slice(lastMessageCountRef.current);
    newMessages.forEach((msg) => writeMessage(terminal, msg));
    lastMessageCountRef.current = messages.length;
  }, [messages]);

  return (
    <div
      ref={containerRef}
      className={`w-full h-full bg-[#0a0a0a] rounded-md overflow-hidden ${className}`}
    />
  );
}

function writeMessage(terminal: Terminal, message: TerminalMessage) {
  const timestamp = message.timestamp.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const roleColors: Record<string, string> = {
    user: '\x1b[36m', // cyan
    assistant: '\x1b[32m', // green
    system: '\x1b[33m', // yellow
    error: '\x1b[31m', // red
  };

  const resetColor = '\x1b[0m';
  const dimColor = '\x1b[2m';
  const roleColor = roleColors[message.role] || resetColor;
  const roleLabel = message.role.charAt(0).toUpperCase() + message.role.slice(1);

  terminal.writeln(`${dimColor}[${timestamp}]${resetColor} ${roleColor}${roleLabel}:${resetColor}`);

  // Write content with proper indentation
  const lines = message.content.split('\n');
  lines.forEach((line) => {
    terminal.writeln(`  ${line}`);
  });

  terminal.writeln('');
}
