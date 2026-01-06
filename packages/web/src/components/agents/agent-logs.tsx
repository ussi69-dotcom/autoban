"use client"

import * as React from "react"
import {
  ArrowDown,
  Download,
  Pause,
  Play,
  Search,
  Trash2,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"

export type LogLevel = "debug" | "info" | "warn" | "error"

export interface LogEntry {
  id: string
  timestamp: Date
  level: LogLevel
  message: string
  meta?: Record<string, unknown>
}

interface AgentLogsProps {
  agentId: string
  agentName?: string
  logs?: LogEntry[]
  isConnected?: boolean
  onClose?: () => void
  onClear?: () => void
  onDownload?: () => void
  wsUrl?: string
  className?: string
}

const LOG_LEVEL_COLORS: Record<LogLevel, string> = {
  debug: "text-slate-500 dark:text-slate-400",
  info: "text-blue-600 dark:text-blue-400",
  warn: "text-yellow-600 dark:text-yellow-400",
  error: "text-red-600 dark:text-red-400",
}

const LOG_LEVEL_BG: Record<LogLevel, string> = {
  debug: "bg-slate-500/10",
  info: "bg-blue-500/10",
  warn: "bg-yellow-500/10",
  error: "bg-red-500/10",
}

function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    fractionalSecondDigits: 3,
  })
}

function LogLine({ entry }: { entry: LogEntry }) {
  const [expanded, setExpanded] = React.useState(false)
  const hasMeta = entry.meta && Object.keys(entry.meta).length > 0

  return (
    <div
      className={cn(
        "group flex gap-2 px-3 py-1 font-mono text-xs hover:bg-muted/50 transition-colors",
        entry.level === "error" && "bg-red-500/5"
      )}
    >
      <span className="text-muted-foreground shrink-0 select-none">
        {formatTimestamp(entry.timestamp)}
      </span>
      <span
        className={cn(
          "shrink-0 w-12 text-center rounded px-1 py-0.5 uppercase text-[10px] font-semibold",
          LOG_LEVEL_COLORS[entry.level],
          LOG_LEVEL_BG[entry.level]
        )}
      >
        {entry.level}
      </span>
      <span className="flex-1 whitespace-pre-wrap break-all">
        {entry.message}
        {hasMeta && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="ml-2 text-muted-foreground hover:text-foreground"
          >
            {expanded ? "[-]" : "[+]"}
          </button>
        )}
        {expanded && hasMeta && (
          <pre className="mt-1 rounded bg-muted p-2 text-[10px] overflow-x-auto">
            {JSON.stringify(entry.meta, null, 2)}
          </pre>
        )}
      </span>
    </div>
  )
}

export function AgentLogs({
  agentId,
  agentName = "Agent",
  logs: initialLogs = [],
  isConnected: initialConnected = false,
  onClose,
  onClear,
  onDownload,
  wsUrl,
  className,
}: AgentLogsProps) {
  const [logs, setLogs] = React.useState<LogEntry[]>(initialLogs)
  const [isConnected, setIsConnected] = React.useState(initialConnected)
  const [isPaused, setIsPaused] = React.useState(false)
  const [searchQuery, setSearchQuery] = React.useState("")
  const [levelFilter, setLevelFilter] = React.useState<LogLevel | "all">("all")
  const [autoScroll, setAutoScroll] = React.useState(true)

  const containerRef = React.useRef<HTMLDivElement>(null)
  const wsRef = React.useRef<WebSocket | null>(null)
  const userScrolledRef = React.useRef(false)

  // WebSocket connection
  React.useEffect(() => {
    if (!wsUrl) return

    const connect = () => {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        setIsConnected(true)
        console.log(`[AgentLogs] Connected to ${agentId}`)
      }

      ws.onmessage = (event) => {
        if (isPaused) return

        try {
          const data = JSON.parse(event.data)
          const entry: LogEntry = {
            id: data.id || crypto.randomUUID(),
            timestamp: new Date(data.timestamp || Date.now()),
            level: data.level || "info",
            message: data.message || "",
            meta: data.meta,
          }
          setLogs((prev) => [...prev.slice(-999), entry]) // Keep last 1000 logs
        } catch (err) {
          // Handle plain text messages
          setLogs((prev) => [
            ...prev.slice(-999),
            {
              id: crypto.randomUUID(),
              timestamp: new Date(),
              level: "info",
              message: event.data,
            },
          ])
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        console.log(`[AgentLogs] Disconnected from ${agentId}`)
        // Attempt reconnect after 3 seconds
        setTimeout(connect, 3000)
      }

      ws.onerror = (error) => {
        console.error(`[AgentLogs] WebSocket error:`, error)
      }

      wsRef.current = ws
    }

    connect()

    return () => {
      wsRef.current?.close()
    }
  }, [wsUrl, agentId, isPaused])

  // Update logs from props
  React.useEffect(() => {
    if (initialLogs.length > 0) {
      setLogs(initialLogs)
    }
  }, [initialLogs])

  // Auto-scroll behavior
  React.useEffect(() => {
    if (autoScroll && containerRef.current && !userScrolledRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  // Detect manual scroll
  const handleScroll = React.useCallback(() => {
    if (!containerRef.current) return

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50

    if (isAtBottom) {
      userScrolledRef.current = false
      setAutoScroll(true)
    } else {
      userScrolledRef.current = true
      setAutoScroll(false)
    }
  }, [])

  const scrollToBottom = () => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
      userScrolledRef.current = false
      setAutoScroll(true)
    }
  }

  // Filter logs
  const filteredLogs = React.useMemo(() => {
    return logs.filter((log) => {
      if (levelFilter !== "all" && log.level !== levelFilter) return false
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        return (
          log.message.toLowerCase().includes(query) ||
          JSON.stringify(log.meta || {})
            .toLowerCase()
            .includes(query)
        )
      }
      return true
    })
  }, [logs, levelFilter, searchQuery])

  return (
    <div
      className={cn(
        "flex flex-col rounded-lg border bg-background overflow-hidden",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-2">
        <div className="flex items-center gap-3">
          <h3 className="font-medium">{agentName} Logs</h3>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium",
              isConnected
                ? "bg-green-500/10 text-green-600 dark:text-green-400"
                : "bg-red-500/10 text-red-600 dark:text-red-400"
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
              )}
            />
            {isConnected ? "Live" : "Disconnected"}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={cn(
              "p-1.5 rounded hover:bg-accent transition-colors",
              isPaused && "text-yellow-600 dark:text-yellow-400"
            )}
            title={isPaused ? "Resume" : "Pause"}
          >
            {isPaused ? (
              <Play className="h-4 w-4" />
            ) : (
              <Pause className="h-4 w-4" />
            )}
          </button>
          {onClear && (
            <button
              onClick={onClear}
              className="p-1.5 rounded hover:bg-accent transition-colors"
              title="Clear logs"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
          {onDownload && (
            <button
              onClick={onDownload}
              className="p-1.5 rounded hover:bg-accent transition-colors"
              title="Download logs"
            >
              <Download className="h-4 w-4" />
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded hover:bg-accent transition-colors ml-2"
              title="Close"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 border-b bg-muted/20 px-4 py-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              "h-8 w-full rounded-md border bg-background pl-8 pr-3 text-sm",
              "placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-ring"
            )}
          />
        </div>

        <select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value as LogLevel | "all")}
          className={cn(
            "h-8 rounded-md border bg-background px-3 text-sm",
            "focus:outline-none focus:ring-2 focus:ring-ring"
          )}
        >
          <option value="all">All Levels</option>
          <option value="debug">Debug</option>
          <option value="info">Info</option>
          <option value="warn">Warning</option>
          <option value="error">Error</option>
        </select>

        <span className="text-xs text-muted-foreground">
          {filteredLogs.length} / {logs.length} entries
        </span>
      </div>

      {/* Log content */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto min-h-[300px] max-h-[600px] bg-background"
      >
        {filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
            {logs.length === 0
              ? "No logs yet. Waiting for agent output..."
              : "No logs match your filter."}
          </div>
        ) : (
          <div className="py-1">
            {filteredLogs.map((entry) => (
              <LogLine key={entry.id} entry={entry} />
            ))}
          </div>
        )}
      </div>

      {/* Scroll to bottom button */}
      {!autoScroll && (
        <button
          onClick={scrollToBottom}
          className={cn(
            "absolute bottom-4 right-4 p-2 rounded-full shadow-lg",
            "bg-primary text-primary-foreground",
            "hover:bg-primary/90 transition-colors"
          )}
          title="Scroll to bottom"
        >
          <ArrowDown className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
